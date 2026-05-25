"""Tests for reference resolution + verify_paper grouping (offline, mocked network)."""

from __future__ import annotations

import deltasci.paper as paper
from deltasci.audit.base import AuditFinding, AuditReport
from deltasci.paper import Reference, resolve_reference, verify_paper


def test_resolve_reference_accepts_matching_title(monkeypatch):
    monkeypatch.setattr(
        paper,
        "get_json",
        lambda *a, **k: {"message": {"items": [{"DOI": "10.1/x", "title": ["Macrophages in osteosarcoma metastasis"]}]}},
    )
    ref = Reference(number=1, raw="Smith J. Macrophages in osteosarcoma metastasis. Nature. 2020.")
    resolve_reference(ref)
    assert ref.resolved_doi == "10.1/x"


def test_resolve_reference_rejects_mismatched_title(monkeypatch):
    monkeypatch.setattr(
        paper,
        "get_json",
        lambda *a, **k: {"message": {"items": [{"DOI": "10.9/z", "title": ["Quantum entanglement in superconductors"]}]}},
    )
    ref = Reference(number=1, raw="Smith J. Macrophages in osteosarcoma metastasis. Nature. 2020.")
    resolve_reference(ref)
    assert ref.resolved_doi is None  # top hit didn't match → not resolved


_DOC = """Macrophages drive metastasis [1]. AlphaFold predicts protein structure [2].

References

[1] Smith J. Macrophages in osteosarcoma. Nature. 2020. doi:10.1234/aaa
[2] Jumper J. AlphaFold. Nature. 2021. PMID: 34265844
"""


def test_verify_paper_groups_findings_per_reference(monkeypatch):
    fake = AuditReport(
        findings=[
            AuditFinding(
                target_kind="citation",
                target_summary="doi 10.1234/aaa",
                auditor_name="crossref",
                status="mismatch",
                fetched_metadata={"doi": "10.1234/aaa", "found": False},
                mismatch_reasons=["not found"],
            ),
            AuditFinding(
                target_kind="citation",
                target_summary="PMID 34265844",
                auditor_name="pubmed",
                status="verified",
                fetched_metadata={"pmid": "34265844", "title": "AlphaFold"},
            ),
        ]
    )
    monkeypatch.setattr(paper, "verify_claims", lambda claims, **k: fake)

    report = verify_paper(_DOC, resolve=False)
    assert len(report.results) == 2
    by_num = {r.number: r for r in report.results}
    assert by_num[1].verdict == "FABRICATED"  # doi not found
    assert by_num[2].verdict == "PASS"  # pmid verified
    # the in-text claim context is attached to the right reference
    assert "AlphaFold" in by_num[2].claim
    assert "Macrophages" in by_num[1].claim


def test_identifier_fallback_groups_datacite_finding(monkeypatch):
    """Author-year paper (no [n] numbers) → identifier-extraction fallback; a DataCite
    finding that carries BOTH an arxiv id and a 10.48550 DOI must still group onto the
    arXiv reference (regression for the doi-shadows-arxiv grouping bug)."""
    doc = (
        "We build on prior work (Smith et al., 2023).\n\nReferences\n\n"
        "Smith, A. A great paper. arXiv preprint arXiv:2303.08774, 2023.\n"
        "Jones, B. Another. URL https://arxiv.org/abs/2402.14740.\n"
    )
    fake = AuditReport(
        findings=[
            AuditFinding(
                target_kind="citation", target_summary="arXiv:2303.08774", auditor_name="datacite",
                status="verified",
                fetched_metadata={"arxiv": "2303.08774", "doi": "10.48550/arxiv.2303.08774", "title": "A great paper"},
            ),
        ]
    )
    monkeypatch.setattr(paper, "verify_claims", lambda claims, **k: fake)
    report = verify_paper(doc, resolve=False)
    assert report.used_llm_fallback is False
    assert len(report.results) == 2  # both arXiv ids extracted from the author-year bib
    verdicts = {r.reference_raw: r.verdict for r in report.results}
    assert verdicts.get("arXiv:2303.08774") == "PASS"  # grouped despite the DOI in metadata


def test_paper_payload_shape(monkeypatch):
    monkeypatch.setattr(paper, "verify_claims", lambda claims, **k: AuditReport(findings=[]))
    report = verify_paper(_DOC, resolve=False)
    payload = paper.paper_payload(report)
    assert payload["reference_count"] == 2
    assert len(payload["citations"]) == 2
    assert {"number", "verdict", "claim", "reference"} <= payload["citations"][0].keys()
