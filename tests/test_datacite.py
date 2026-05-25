"""Tests for the DataCite arXiv verifier (offline; mocked get_json)."""

from __future__ import annotations

import deltasci.audit.citations.datacite as dc
from deltasci.audit.citations.datacite import DataCiteArxivAuditor
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError


def _target(value: str) -> dict:
    return {"identifier": Identifier(kind="arxiv", value=value, raw=f"arXiv:{value}"), "claim_source": f"arXiv:{value}"}


def test_datacite_verified(monkeypatch):
    monkeypatch.setattr(
        dc,
        "get_json",
        lambda *a, **k: {"data": {"attributes": {"titles": [{"title": "GPT-4 Technical Report"}],
                                                 "creators": [{"name": "OpenAI"}], "publicationYear": 2023}}},
    )
    f = DataCiteArxivAuditor().audit(_target("2303.08774"))
    assert f.status == "verified"
    assert f.fetched_metadata["title"] == "GPT-4 Technical Report"
    # Carries BOTH the arxiv id and the DataCite DOI (the grouping must handle both).
    assert f.fetched_metadata["arxiv"] == "2303.08774"
    assert f.fetched_metadata["doi"] == "10.48550/arXiv.2303.08774"


def test_datacite_not_found(monkeypatch):
    def boom(*a, **k):
        raise HTTPError("404 Not Found for https://api.datacite.org/...")

    monkeypatch.setattr(dc, "get_json", boom)
    f = DataCiteArxivAuditor().audit(_target("9999.99999"))
    assert f.status == "mismatch"
    assert f.fetched_metadata["found"] is False


def test_datacite_strips_version_suffix(monkeypatch):
    seen = {}

    def cap(url, *a, **k):
        seen["url"] = url
        return {"data": {"attributes": {}}}

    monkeypatch.setattr(dc, "get_json", cap)
    DataCiteArxivAuditor().audit(_target("2303.08774v2"))
    assert "10.48550/arXiv.2303.08774" in seen["url"]
    assert "v2" not in seen["url"]
