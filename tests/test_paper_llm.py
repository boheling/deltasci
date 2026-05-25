"""Tests for the LLM citation-extraction fallback (offline; fake adapter, no network)."""

from __future__ import annotations

import deltasci.paper as paper
from deltasci.audit.base import AuditFinding, AuditReport
from deltasci.paper import verify_paper
from deltasci.paper_llm import _parse_json_array, llm_extract_citations


class _FakeLLM:
    def __init__(self, response: str, *, fail_if_called: bool = False) -> None:
        self._r = response
        self.calls = 0
        self._fail = fail_if_called

    def complete(self, system, messages, max_tokens=2048) -> str:
        self.calls += 1
        if self._fail:
            raise AssertionError("LLM should not have been called (deterministic parse worked)")
        return self._r

    def model_id(self) -> str:
        return "fake"


def test_parse_json_array_handles_fences_and_prose():
    assert _parse_json_array('```json\n[{"claim":"a","source":"b"}]\n```') == [{"claim": "a", "source": "b"}]
    assert _parse_json_array('Here you go: [{"claim":"a","source":"b"}] done') == [{"claim": "a", "source": "b"}]
    assert _parse_json_array("not json at all") == []


def test_llm_extract_citations_builds_claims():
    resp = '[{"claim": "Transformers use self-attention.", "source": "arXiv:1706.03762"}, {"claim": "x", "source": ""}]'
    claims = llm_extract_citations("paper text", _FakeLLM(resp))
    assert len(claims) == 1  # the empty-source item is dropped
    assert claims[0].source == "arXiv:1706.03762"


_AUTHOR_YEAR_DOC = (
    "Transformers rely on self-attention (Vaswani et al., 2017). "
    "CRISPR-Cas9 enables programmable genome editing (Jinek et al., 2012)."
)


def test_verify_paper_uses_llm_fallback_when_not_numbered(monkeypatch):
    llm_resp = (
        '[{"claim": "Transformers rely on self-attention.", "source": "arXiv:1706.03762"}, '
        '{"claim": "CRISPR-Cas9 enables programmable genome editing.", "source": "PMID 22745249"}]'
    )
    fake_report = AuditReport(
        findings=[
            AuditFinding(target_kind="citation", target_summary="arXiv:1706.03762", auditor_name="arxiv",
                         status="verified", fetched_metadata={"arxiv": "1706.03762", "title": "Attention"}),
            AuditFinding(target_kind="citation", target_summary="PMID 22745249", auditor_name="pubmed",
                         status="mismatch", fetched_metadata={"pmid": "22745249", "found": False},
                         mismatch_reasons=["not found"]),
        ]
    )
    monkeypatch.setattr(paper, "verify_claims", lambda claims, **k: fake_report)

    report = verify_paper(_AUTHOR_YEAR_DOC, resolve=False, llm=_FakeLLM(llm_resp))
    assert report.used_llm_fallback is True
    assert len(report.results) == 2
    by_claim = {r.claim: r.verdict for r in report.results}
    assert by_claim["Transformers rely on self-attention."] == "PASS"
    assert by_claim["CRISPR-Cas9 enables programmable genome editing."] == "FABRICATED"


def test_numbered_paper_does_not_invoke_llm(monkeypatch):
    monkeypatch.setattr(paper, "verify_claims", lambda claims, **k: AuditReport(findings=[]))
    doc = (
        "A result holds [1].\n\nReferences\n\n"
        "[1] Smith J. A paper. Nature. 2020. PMID: 12345678\n"
        "[2] Doe A. Another. 2019. PMID: 23456789\n"
        "[3] Roe B. Third. 2018. PMID: 34567890\n"
    )
    fake = _FakeLLM("[]", fail_if_called=True)
    report = verify_paper(doc, resolve=False, llm=fake)
    assert report.used_llm_fallback is False
    assert fake.calls == 0  # deterministic numbered parse handled it
