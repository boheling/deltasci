from __future__ import annotations

import pytest
from pydantic import ValidationError

from deltasci.hypothesis import (
    EpistemicSummary,
    EvidenceItem,
    FalsifiabilityClause,
    FeasibilityScores,
    GroundedHypothesis,
    HypothesisMetadata,
    KnowledgeGap,
    NovelSynthesis,
)


def test_evidence_item_observation_allows_empty_source():
    EvidenceItem(claim="x", type="observation", source="", coverage="well-covered")


def test_evidence_item_published_requires_source():
    with pytest.raises(ValidationError):
        EvidenceItem(claim="x", type="published-evidence", source="", coverage="well-covered")


def test_evidence_item_coverage_required():
    with pytest.raises(ValidationError):
        EvidenceItem(claim="x", type="observation", source="")  # type: ignore[call-arg]


def test_evidence_item_uncovered_rejected():
    with pytest.raises(ValidationError):
        EvidenceItem(claim="x", type="observation", source="", coverage="uncovered")  # type: ignore[arg-type]


def test_knowledge_gap_default_category():
    gap = KnowledgeGap(question="What does the lab do here?")
    assert gap.category == "other"


def test_knowledge_gap_invalid_category():
    with pytest.raises(ValidationError):
        KnowledgeGap(question="x", category="not-a-category")  # type: ignore[arg-type]


def test_novel_synthesis_minimum():
    syn = NovelSynthesis(proposed_connection="A ↔ B")
    assert syn.rationale == ""


def test_falsifiability_requires_all_three_fields():
    with pytest.raises(ValidationError):
        FalsifiabilityClause(prediction="", threshold="x", null_outcome="y")


def test_feasibility_scores_in_range():
    with pytest.raises(ValidationError):
        FeasibilityScores(scores={"a": 6}, justifications={"a": ""}, overall=6.0)


def test_grounded_hypothesis_round_trip():
    h = GroundedHypothesis(
        title="t",
        statement="s",
        domain_grounding={"mechanism": "m"},
        technical_approach={"core_method": "cm"},
        evidence_trail=[EvidenceItem(claim="c", type="observation", source="", coverage="sparse")],
        knowledge_gaps=[KnowledgeGap(question="?", category="lab-tribal-knowledge")],
        novel_syntheses=[NovelSynthesis(proposed_connection="x", rationale="y")],
        falsifiability=FalsifiabilityClause(prediction="p", threshold="t", null_outcome="n"),
        feasibility_scores=FeasibilityScores(scores={"a": 3}, justifications={"a": "j"}, overall=3.0),
        epistemic_summary=EpistemicSummary(
            well_covered_count=0,
            sparse_count=1,
            knowledge_gap_count=1,
            novel_synthesis_count=1,
            warnings=[],
        ),
        metadata=HypothesisMetadata(
            pack_name="biomed",
            pack_version="0.1.0",
            deltasci_version="0.1.1",
            llm_provider="mock",
            model="mock-1",
            num_rounds=4,
        ),
    )
    dumped = h.model_dump()
    loaded = GroundedHypothesis.model_validate(dumped)
    assert loaded.title == "t"
    assert loaded.knowledge_gaps[0].category == "lab-tribal-knowledge"
    assert loaded.novel_syntheses[0].rationale == "y"
