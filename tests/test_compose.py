"""Tests for the generative components (write_review / ideate). The LLM is faked; we assert
the prompt is *grounded* in the real evidence passed in."""

from __future__ import annotations

from deltasci.compose import ideate, write_review
from deltasci.scan import ScanHit


class _CaptureLLM:
    def __init__(self, reply="## Summary\nok\n## Recommendation\nminor revision"):
        self.reply = reply
        self.system = None
        self.prompt = None

    def complete(self, system, messages, max_tokens=2048):
        self.system = system
        self.prompt = messages[0].content
        return self.reply


def _hit(title, url="https://x/1"):
    return ScanHit("openalex", title, ["B. Author"], "2021", "Nature", url, "id", "snippet text")


def test_write_review_grounds_prompt_in_audit_and_prior_art():
    llm = _CaptureLLM()
    out = write_review(
        "We propose a new method.",
        audit_summary="Audit summary: ✗ 1 FAILED AUDIT",
        audit_issues=["FAILED: TAMs claim — wrong paper"],
        related_work=[_hit("A closely related method")],
        llm=llm,
    )
    assert out.startswith("## Summary")
    # the model must have been handed the real audit issue and the retrieved work
    assert "TAMs claim" in llm.prompt
    assert "A closely related method" in llm.prompt
    assert "NEVER invent" in llm.system


def test_write_review_handles_no_issues_and_no_works():
    llm = _CaptureLLM()
    write_review("text", audit_summary="", audit_issues=[], related_work=[], llm=llm)
    assert "no citation issues detected" in llm.prompt
    assert "none retrieved" in llm.prompt


def test_ideate_grounds_prompt_in_gap_and_terms():
    llm = _CaptureLLM(reply="- Direction\nMost promising: 1")
    out = ideate(
        "graph nets for cathode voltage",
        gap_label="Open — little direct prior art",
        novel_terms=["electrolyte", "interface"],
        related_work=[_hit("Cathode voltage paper")],
        llm=llm,
    )
    assert "Most promising" in out
    assert "electrolyte" in llm.prompt
    assert "Open — little direct prior art" in llm.prompt
    assert "Cathode voltage paper" in llm.prompt


def test_ideate_handles_empty_novel_terms():
    llm = _CaptureLLM()
    ideate("idea", gap_label="Crowded", novel_terms=[], related_work=[], llm=llm)
    assert "none" in llm.prompt.lower()
