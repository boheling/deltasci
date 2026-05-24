"""Tests for the v0.2 protocol + risks + challenger pipelines."""

from __future__ import annotations

import json

import pytest

from deltasci.challenger import ChallengeError, run_challenge
from deltasci.config import Config
from deltasci.engine import CoReasoner
from deltasci.hypothesis import (
    EpistemicSummary,
    EvidenceItem,
    FalsifiabilityClause,
    FeasibilityScores,
    GroundedHypothesis,
    HypothesisMetadata,
)
from deltasci.llm.mock import MockLLM
from deltasci.protocol import (
    ProtocolError,
    RisksError,
    assemble_protocol,
    assemble_risks,
    render_protocol_md,
    render_risks_md,
)
from deltasci.transcript import Transcript


def _stub_hypothesis() -> GroundedHypothesis:
    return GroundedHypothesis(
        title="t",
        statement="s",
        domain_grounding={"mechanism": "m", "unmet_need": "u", "expected_impact": "e"},
        technical_approach={"core_method": "cm", "key_innovation": "ki", "implementation_path": "ip"},
        evidence_trail=[],
        knowledge_gaps=[],
        novel_syntheses=[],
        falsifiability=FalsifiabilityClause(prediction="p", threshold="auc>=0.85", null_outcome="auc<=baseline"),
        feasibility_scores=FeasibilityScores(scores={"a": 4}, justifications={"a": "j"}, overall=4.0),
        epistemic_summary=EpistemicSummary(),
        metadata=HypothesisMetadata(
            pack_name="biomed", pack_version="0.1.0", deltasci_version="0.2.0",
            llm_provider="mock", model="mock-1", num_rounds=4,
        ),
    )


def _scripted_protocol() -> str:
    return json.dumps({
        "title": "Test plan",
        "summary": "A short plan.",
        "data_acquisition": {
            "primary_dataset": "Test cohort",
            "accession_or_url": "https://example.org/data",
            "access_constraints": "DUA",
            "fallback_datasets": ["alt1"],
        },
        "steps": [
            {"order": 1, "name": "load", "description": "load data", "inputs": ["raw"], "outputs": ["df"],
             "method_citations": ["github.com/example/loader"]},
            {"order": 2, "name": "train", "description": "train model", "inputs": ["df"], "outputs": ["model"],
             "method_citations": ["Smith 2024"]},
        ],
        "primary_metric": "AUC",
        "success_threshold": "AUC >= 0.85",
        "null_outcome": "AUC <= baseline + 0.01",
        "baselines": ["logistic regression"],
        "compute": {"hardware": "1x A100", "estimated_runtime": "8h", "storage": "50GB", "cost_estimate": "$10"},
        "timeline_estimate": "4 weeks",
        "sample_size_justification": "n=200 cases for 80% power",
    })


def _scripted_risks() -> str:
    return json.dumps({
        "summary": "Three plausible failure modes.",
        "items": [
            {"id": "R1", "category": "data", "severity": "high",
             "description": "Cohort size too small",
             "likely_failure_mode": "wide CIs",
             "mitigation": "expand cohort",
             "counter_evidence_citations": []},
            {"id": "R2", "category": "evaluation", "severity": "medium",
             "description": "AUC may not reflect clinical utility",
             "likely_failure_mode": "high AUC, low decision-curve net benefit",
             "mitigation": "add DCA",
             "counter_evidence_citations": ["Vickers 2006"]},
            {"id": "R3", "category": "external-validity", "severity": "high",
             "description": "Single-site only",
             "likely_failure_mode": "no transfer",
             "mitigation": "external cohort",
             "counter_evidence_citations": []},
        ],
    })


def _scripted_challenge() -> str:
    return json.dumps({
        "summary": "Three concrete failures the hypothesis hand-waves.",
        "findings": [
            {"id": "C1", "kind": "missing-baseline", "severity": "high",
             "description": "Logistic regression baseline insufficient",
             "evidence_citations": ["github.com/example/baseline"],
             "suggested_response": "add random forest"},
            {"id": "C2", "kind": "novelty-overstated", "severity": "medium",
             "description": "Similar work exists",
             "evidence_citations": ["Doe 2023"],
             "suggested_response": "narrow novelty claim"},
            {"id": "C3", "kind": "wrong-metric", "severity": "high",
             "description": "AUC inappropriate for class-imbalanced setting",
             "evidence_citations": [],
             "suggested_response": "use AUPRC + sensitivity at fixed FPR"},
        ],
    })


def test_assemble_protocol_round_trip():
    h = _stub_hypothesis()
    t = Transcript(idea="x", pack_name="biomed")
    llm = MockLLM(responses=[_scripted_protocol()])
    plan = assemble_protocol(hypothesis=h, transcript=t, llm=llm)
    assert plan.title == "Test plan"
    assert len(plan.steps) == 2
    assert plan.steps[0].order == 1
    assert plan.success_threshold == "AUC >= 0.85"


def test_assemble_protocol_invalid_json():
    llm = MockLLM(responses=["not json"])
    with pytest.raises(ProtocolError):
        assemble_protocol(hypothesis=_stub_hypothesis(), transcript=Transcript(idea="x", pack_name="b"), llm=llm)


def test_assemble_risks_round_trip():
    llm = MockLLM(responses=[_scripted_risks()])
    register = assemble_risks(
        hypothesis=_stub_hypothesis(),
        plan=assemble_protocol(_stub_hypothesis(), Transcript(idea="x", pack_name="b"), MockLLM(responses=[_scripted_protocol()])),
        transcript=Transcript(idea="x", pack_name="b"),
        llm=llm,
    )
    assert len(register.items) == 3
    assert {r.severity for r in register.items} == {"high", "medium", "high"} - set()  # at least the values appear
    assert register.items[0].id == "R1"


def test_assemble_risks_invalid_json():
    llm = MockLLM(responses=["{not json"])
    with pytest.raises(RisksError):
        assemble_risks(
            hypothesis=_stub_hypothesis(),
            plan=assemble_protocol(_stub_hypothesis(), Transcript(idea="x", pack_name="b"), MockLLM(responses=[_scripted_protocol()])),
            transcript=Transcript(idea="x", pack_name="b"),
            llm=llm,
        )


def test_run_challenge_round_trip():
    llm = MockLLM(responses=[_scripted_challenge()])
    report = run_challenge(
        hypothesis=_stub_hypothesis(),
        plan=None,
        risks=None,
        transcript=Transcript(idea="x", pack_name="b"),
        llm=llm,
    )
    assert len(report.findings) == 3
    assert report.challenger_provider == "mockllm"


def test_run_challenge_invalid_json():
    llm = MockLLM(responses=["nope"])
    with pytest.raises(ChallengeError):
        run_challenge(
            hypothesis=_stub_hypothesis(),
            plan=None, risks=None,
            transcript=Transcript(idea="x", pack_name="b"),
            llm=llm,
        )


def test_render_protocol_md_contains_steps():
    plan = assemble_protocol(_stub_hypothesis(), Transcript(idea="x", pack_name="b"), MockLLM(responses=[_scripted_protocol()]))
    md = render_protocol_md(plan)
    assert "## Steps" in md
    assert "1. load" in md
    assert "2. train" in md
    assert "AUC >= 0.85" in md


def test_render_risks_md_contains_severities():
    register = assemble_risks(
        _stub_hypothesis(),
        assemble_protocol(_stub_hypothesis(), Transcript(idea="x", pack_name="b"), MockLLM(responses=[_scripted_protocol()])),
        Transcript(idea="x", pack_name="b"),
        MockLLM(responses=[_scripted_risks()]),
    )
    md = render_risks_md(register)
    assert "HIGH" in md
    assert "MEDIUM" in md
    assert "Mitigation" in md


def test_full_pipeline_with_protocol_risks_challenge(biomed_pack, scripted_round_responses, scripted_synthesis_response):
    """End-to-end: 4 rounds + synthesis + protocol + risks + challenge, all scripted."""

    responses = (
        list(scripted_round_responses)
        + [scripted_synthesis_response]
        + [_scripted_protocol(), _scripted_risks(), _scripted_challenge()]
    )
    llm = MockLLM(responses=responses)

    config = Config(
        num_rounds=4,
        audit_enabled=False,
        generate_protocol=True,
        generate_risks=True,
        run_challenge=True,
        auto_view=False,
    )
    reasoner = CoReasoner(pack=biomed_pack, llm=llm, config=config)
    result = reasoner.run(idea="A real idea for an end-to-end run.")

    assert result.plan is not None
    assert result.risks is not None
    assert result.challenge is not None
    assert len(result.plan.steps) == 2
    assert len(result.risks.items) == 3
    assert len(result.challenge.findings) == 3
