"""Unit tests for the Semantic Scholar audit source + 1-hop corroboration helper.

Mocks `deltasci.audit.http.get_json` so no live network. Live-API smoke is
covered by the existing test_audit_live.py marker pattern (out of scope here).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from deltasci.audit.citations.corroboration import fetch_neighbors
from deltasci.audit.citations.semscholar import SemanticScholarAuditor
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError


def _doi_target():
    return {
        "identifier": Identifier(kind="doi", value="10.1126/science.abc1234", raw="10.1126/science.abc1234"),
        "claim_source": "Smith 2024, Science: Title close enough — DOI 10.1126/science.abc1234",
        "claim_text": "x",
    }


def test_can_audit_accepts_doi_pmid_arxiv():
    auditor = SemanticScholarAuditor()
    assert auditor.can_audit(_doi_target())
    assert auditor.can_audit(
        {"identifier": Identifier(kind="pmid", value="12345678", raw="12345678"), "claim_source": "", "claim_text": ""}
    )
    assert auditor.can_audit(
        {"identifier": Identifier(kind="arxiv", value="2401.00001", raw="2401.00001"), "claim_source": "", "claim_text": ""}
    )


def test_can_audit_rejects_unsupported_kinds():
    auditor = SemanticScholarAuditor()
    assert not auditor.can_audit(
        {"identifier": Identifier(kind="github_repo", value="org/repo", raw="org/repo"), "claim_source": "", "claim_text": ""}
    )


def test_audit_returns_verified_when_metadata_matches():
    fake_response = {
        "paperId": "abc123",
        "corpusId": 999,
        "title": "Title close enough",
        "authors": [{"name": "Jane Smith"}, {"name": "John Doe"}],
        "year": 2024,
        "venue": "Science",
        "citationCount": 247,
        "referenceCount": 60,
        "tldr": {"text": "Short summary."},
    }
    with patch("deltasci.audit.citations.semscholar.get_json", return_value=fake_response):
        auditor = SemanticScholarAuditor()
        finding = auditor.audit(_doi_target())
    assert finding.status == "verified"
    assert finding.fetched_metadata["paper_id"] == "abc123"
    assert finding.fetched_metadata["citation_count"] == 247
    assert finding.fetched_metadata["tldr"] == "Short summary."


def test_audit_flags_mismatch_on_title_diff():
    fake_response = {
        "paperId": "abc123",
        "title": "Completely different paper about something unrelated",
        "authors": [{"name": "Jane Smith"}],
        "year": 2024,
        "venue": "Science",
        "citationCount": 0,
        "referenceCount": 0,
        "tldr": None,
    }
    with patch("deltasci.audit.citations.semscholar.get_json", return_value=fake_response):
        auditor = SemanticScholarAuditor()
        finding = auditor.audit(_doi_target())
    assert finding.status == "mismatch"
    assert any("title differs" in r for r in finding.mismatch_reasons)


def test_audit_returns_mismatch_on_404():
    def raise_404(*args, **kwargs):
        raise HTTPError("404 Not Found for ...")

    with patch("deltasci.audit.citations.semscholar.get_json", side_effect=raise_404):
        auditor = SemanticScholarAuditor()
        finding = auditor.audit(_doi_target())
    assert finding.status == "mismatch"
    assert any("not found in Semantic Scholar" in r for r in finding.mismatch_reasons)


def test_audit_skipped_on_network_error():
    def raise_network(*args, **kwargs):
        raise HTTPError("network error: Connection refused")

    with patch("deltasci.audit.citations.semscholar.get_json", side_effect=raise_network):
        auditor = SemanticScholarAuditor()
        finding = auditor.audit(_doi_target())
    assert finding.status == "skipped"


def test_audit_passes_api_key_via_header(monkeypatch):
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key-xyz")

    captured: dict = {}

    def fake_get(url, **kwargs):
        captured["headers"] = kwargs.get("headers", {})
        return {
            "paperId": "abc",
            "title": "Title close enough",
            "authors": [{"name": "Jane Smith"}],
            "year": 2024,
            "venue": "Science",
        }

    with patch("deltasci.audit.citations.semscholar.get_json", side_effect=fake_get):
        auditor = SemanticScholarAuditor()
        auditor.audit(_doi_target())
    assert captured["headers"].get("x-api-key") == "test-key-xyz"


# --- Corroboration helper -----------------------------------------------------


def test_fetch_neighbors_returns_empty_for_blank_paper_id():
    result = fetch_neighbors("")
    assert result.error == "empty paper_id"
    assert result.citing_papers == []


def test_fetch_neighbors_flattens_citing_and_cited():
    citations_response = {
        "data": [
            {
                "citingPaper": {
                    "title": "Citing paper one",
                    "year": 2025,
                    "venue": "Cell",
                    "authors": [{"name": "A"}, {"name": "B"}, {"name": "C"}, {"name": "D"}],
                    "citationCount": 3,
                }
            }
        ]
    }
    references_response = {
        "data": [
            {
                "citedPaper": {
                    "title": "Foundational reference",
                    "year": 2010,
                    "venue": "Nature",
                    "authors": [{"name": "Older Author"}],
                    "citationCount": 500,
                }
            }
        ]
    }

    call_log: list[str] = []

    def fake_get(url, **kwargs):
        call_log.append(url)
        if "/citations" in url:
            return citations_response
        if "/references" in url:
            return references_response
        raise AssertionError(f"unexpected url: {url}")

    with patch("deltasci.audit.citations.corroboration.get_json", side_effect=fake_get):
        result = fetch_neighbors("paper-1")

    assert result.citation_count == 1
    assert result.reference_count == 1
    assert result.citing_papers[0]["title"] == "Citing paper one"
    # Truncated to first 3 authors
    assert result.citing_papers[0]["first_authors"] == ["A", "B", "C"]
    assert result.cited_papers[0]["title"] == "Foundational reference"
    assert any("/citations" in u for u in call_log)
    assert any("/references" in u for u in call_log)


def test_fetch_neighbors_records_partial_failure():
    def fake_get(url, **kwargs):
        if "/citations" in url:
            return {"data": [{"citingPaper": {"title": "ok", "year": 2024, "venue": "", "authors": []}}]}
        raise HTTPError("503 Server Error")

    with patch("deltasci.audit.citations.corroboration.get_json", side_effect=fake_get):
        result = fetch_neighbors("paper-1")

    assert result.citation_count == 1
    assert result.reference_count == 0
    assert "references fetch failed" in result.error
