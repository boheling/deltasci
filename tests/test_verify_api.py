"""Tests for the shared verify core (deltasci.verify) and the MCP tool wiring."""

from __future__ import annotations

import pytest

from deltasci.audit.base import AuditFinding, AuditReport
from deltasci.verify import verify_claims, verify_payload, verify_text


class _FakeAuditor:
    def __init__(self, findings):
        self._findings = findings

    def audit(self, claims):
        return AuditReport(findings=self._findings)


_FABRICATED = AuditFinding(
    target_kind="citation",
    target_summary="PMID 35562209",
    auditor_name="pubmed",
    status="mismatch",
    fetched_metadata={"found": False},
    mismatch_reasons=["no record found"],
)
_VERIFIED = AuditFinding(
    target_kind="citation",
    target_summary="PMID 12345678",
    auditor_name="pubmed",
    status="verified",
    fetched_metadata={"pmid": "12345678"},
)


def test_verify_claims_empty_returns_empty_report():
    assert verify_claims([]).findings == []


def test_verify_text_uses_support_auditor_by_default(monkeypatch):
    seen = {}

    def fake_verify_auditor(cache=None, max_workers=4, support=True):
        seen["support"] = True
        return _FakeAuditor([_VERIFIED])

    monkeypatch.setattr("deltasci.audit.runner.verify_auditor", fake_verify_auditor)
    report = verify_text("Backed by PMID 12345678.")
    assert seen.get("support") is True
    assert report.verified_count == 1


def test_verify_text_no_support_uses_plain_auditor(monkeypatch):
    monkeypatch.setattr("deltasci.audit.runner.verify_auditor", lambda cache=None, max_workers=4, support=True: _FakeAuditor([_VERIFIED]))
    report = verify_text("Backed by PMID 12345678.", check_support=False)
    assert report.verified_count == 1


def test_verify_auditor_drops_semantic_scholar_without_key(monkeypatch):
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)
    from deltasci.audit.runner import verify_auditor

    names = {a.name for a in verify_auditor().auditors}
    assert "claim_support" in names
    assert "semantic_scholar" not in names


def test_verify_payload_labels_findings():
    payload = verify_payload(AuditReport(findings=[_FABRICATED, _VERIFIED]))
    assert payload["verdicts"] == {"FABRICATED": 1, "PASS": 1}
    verdicts = {f["verdict"] for f in payload["findings"]}
    assert verdicts == {"FABRICATED", "PASS"}
    assert "summary" in payload


def test_mcp_tool_returns_payload(monkeypatch):
    """If the MCP SDK is installed, the tool wraps verify_text → verify_payload."""

    pytest.importorskip("mcp")
    monkeypatch.setattr("deltasci.audit.runner.verify_auditor", lambda cache=None, max_workers=4, support=True: _FakeAuditor([_FABRICATED]))
    from deltasci.mcp_server import verify_scientific_claims

    # FastMCP wraps the function; call the underlying fn if wrapped, else call directly.
    fn = getattr(verify_scientific_claims, "fn", verify_scientific_claims)
    result = fn(text="We rely on PMID 35562209.")
    assert result["verdicts"]["FABRICATED"] == 1
