"""Tests for MultiLayerAuditor with mocked Auditor implementations.

No live HTTP. Live-API tests live in test_audit_live.py and are gated by
@pytest.mark.live.
"""

from __future__ import annotations

import pytest

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.cache import AuditCache
from deltasci.audit.runner import MultiLayerAuditor
from deltasci.hypothesis import EvidenceItem


class _MockPubMedVerifier(Auditor):
    name = "pubmed"

    def __init__(self, return_status: str = "verified") -> None:
        self.return_status = return_status
        self.call_count = 0

    def can_audit(self, target):
        return target.get("identifier") and target["identifier"].kind == "pmid"

    def audit(self, target):
        self.call_count += 1
        return AuditFinding(
            target_kind="citation",
            target_summary=target["claim_source"],
            auditor_name=self.name,
            status=self.return_status,
            fetched_metadata={"pmid": target["identifier"].value},
            mismatch_reasons=[] if self.return_status == "verified" else ["mocked mismatch"],
        )


@pytest.fixture
def isolated_cache(tmp_path):
    return AuditCache(tmp_path / "audit-cache.json")


def test_runner_no_identifiers_returns_empty(isolated_cache):
    items = [EvidenceItem(claim="x", type="observation", source="", coverage="well-covered")]
    auditor = MultiLayerAuditor(auditors=[_MockPubMedVerifier()], cache=isolated_cache)
    report = auditor.audit(items)
    assert report.findings == []


def test_runner_dispatches_to_pmid_verifier(isolated_cache):
    items = [
        EvidenceItem(
            claim="x",
            type="published-evidence",
            source="Foo 2020, J Bar, PMID 12345678",
            coverage="well-covered",
        )
    ]
    auditor = MultiLayerAuditor(auditors=[_MockPubMedVerifier()], cache=isolated_cache)
    report = auditor.audit(items)
    assert len(report.findings) == 1
    assert report.findings[0].status == "verified"


def test_runner_records_mismatch(isolated_cache):
    items = [
        EvidenceItem(
            claim="x",
            type="published-evidence",
            source="Fake Author 2020, PMID 35562209",
            coverage="well-covered",
        )
    ]
    auditor = MultiLayerAuditor(
        auditors=[_MockPubMedVerifier(return_status="mismatch")],
        cache=isolated_cache,
    )
    report = auditor.audit(items)
    assert report.mismatch_count == 1
    assert "FAILED AUDIT" in report.banner()


def test_runner_uses_cache(isolated_cache):
    items = [
        EvidenceItem(
            claim="x",
            type="published-evidence",
            source="Foo 2020, PMID 12345678",
            coverage="well-covered",
        )
    ]
    verifier = _MockPubMedVerifier()
    auditor = MultiLayerAuditor(auditors=[verifier], cache=isolated_cache)
    auditor.audit(items)
    auditor.audit(items)
    # Second call should hit cache
    assert verifier.call_count == 1


def test_audit_report_banner_skipped():
    from deltasci.audit.base import AuditReport

    r = AuditReport(skipped=True, skipped_reason="--no-audit")
    assert "AUDIT SKIPPED" in r.banner()
    assert "--no-audit" in r.banner()
