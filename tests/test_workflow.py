"""Tests for the workflow layer. Scan is mocked (offline); gap runs for real on the injected
scan; verify is mocked to a small AuditReport; the LLM is faked."""

from __future__ import annotations

import deltasci.verify as verify_mod
import deltasci.workflow as wf
import pytest
from deltasci.audit.base import AuditFinding, AuditReport
from deltasci.scan import ScanHit, ScanReport
from deltasci.workflow import WORKFLOWS, run_workflow, workflow_payload


def _audit_report():
    return AuditReport(
        findings=[
            AuditFinding(
                target_kind="citation", target_summary="TAMs dominate (PMID 1)", auditor_name="pubmed",
                status="mismatch", mismatch_reasons=["wrong paper"], confidence="medium",
            ),
            AuditFinding(
                target_kind="citation", target_summary="A verified claim (PMID 2)", auditor_name="pubmed",
                status="verified",
            ),
        ]
    )


def _scan_report():
    hits = [
        ScanHit("openalex", "Closest related method", ["X"], "2022", "Nature", "https://x/1", "10.1/a", "snippet", 0.7),
        ScanHit("arxiv", "Adjacent work", ["Y"], "2021", "arXiv", "https://x/2", "2101.1", "", 0.5),
    ]
    return ScanReport(query="cathode voltage graph", terms=["cathode", "voltage", "graph"], hits=hits, counts={"openalex": 1, "arxiv": 1})


class _FakeLLM:
    def complete(self, system, messages, max_tokens=2048):
        return "## Summary\ngenerated text\nMost promising: 1"


@pytest.fixture(autouse=True)
def _mock_components(monkeypatch):
    monkeypatch.setattr(wf, "scan", lambda text, **kw: _scan_report())
    monkeypatch.setattr(verify_mod, "verify_text", lambda text, **kw: _audit_report())


def test_grant_runs_verify_scan_gap():
    rep = run_workflow("grant", "graph nets predict cathode voltage")
    assert rep.verify is not None and rep.scan is not None and rep.gap is not None
    assert rep.generated == {}  # grant has no generative step
    assert rep.gap.classification in ("CROWDED", "CONTESTED", "OPEN")
    assert "prior art" in rep.headline()


def test_paper_runs_verify_and_scan_but_no_gap():
    rep = run_workflow("paper", "our paper text")
    assert rep.verify is not None and rep.scan is not None
    assert rep.gap is None


def test_review_without_llm_notes_and_skips_generation():
    rep = run_workflow("review", "their paper text")
    assert "review" not in rep.generated
    assert any("review" in n for n in rep.notes)
    assert rep.verify is not None and rep.scan is not None  # deterministic parts still ran


def test_review_with_llm_generates_grounded_review():
    rep = run_workflow("review", "their paper text", llm=_FakeLLM())
    assert "review" in rep.generated
    assert "generated text" in rep.generated["review"]


def test_ideate_with_llm_generates_and_has_no_verify():
    rep = run_workflow("ideate", "a fresh idea", llm=_FakeLLM())
    assert rep.verify is None  # ideate = scan + gap + ideate
    assert rep.scan is not None and rep.gap is not None
    assert "ideate" in rep.generated


def test_ideate_without_llm_notes():
    rep = run_workflow("ideate", "a fresh idea")
    assert "ideate" not in rep.generated
    assert any("ideation" in n for n in rep.notes)


def test_unknown_goal_raises():
    with pytest.raises(ValueError, match="unknown goal"):
        run_workflow("nope", "text")


def test_all_workflows_have_known_steps():
    valid = {"verify", "scan", "gap", "review", "ideate"}
    for _goal, (label, steps) in WORKFLOWS.items():
        assert label and set(steps) <= valid


def test_workflow_payload_shape():
    rep = run_workflow("grant", "graph nets predict cathode voltage")
    p = workflow_payload(rep)
    assert p["goal"] == "grant"
    assert "verify" in p and "gap" in p
    assert p["gap"]["classification"] in ("CROWDED", "CONTESTED", "OPEN")
    assert "headline" in p
