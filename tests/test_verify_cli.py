"""End-to-end tests for `deltasci verify` — network-free via a patched auditor."""

from __future__ import annotations

import json

from deltasci.audit.base import AuditFinding, AuditReport
from deltasci.cli import main


class _FakeAuditor:
    def __init__(self, findings):
        self._findings = findings

    def audit(self, claims):
        # claims must have flowed through intake; sanity-check the duck-type.
        assert all(hasattr(c, "claim") and hasattr(c, "source") for c in claims)
        return AuditReport(findings=self._findings)


_FABRICATED = AuditFinding(
    target_kind="citation",
    target_summary="PMID 35562209",
    auditor_name="pubmed",
    status="mismatch",
    fetched_metadata={"found": False},
    mismatch_reasons=["no record found for PMID 35562209"],
)
_VERIFIED = AuditFinding(
    target_kind="citation",
    target_summary="PMID 12345678",
    auditor_name="pubmed",
    status="verified",
    fetched_metadata={"pmid": "12345678", "title": "A real paper"},
)


def test_verify_no_citations_exits_zero(capsys):
    rc = main(["verify", "--text", "This sentence has no citations whatsoever."])
    assert rc == 0
    assert "no verifiable citations" in capsys.readouterr().out


def test_verify_fabricated_exits_two(monkeypatch, capsys):
    monkeypatch.setattr("deltasci.audit.runner.verify_auditor", lambda cache=None, max_workers=4, support=True: _FakeAuditor([_FABRICATED]))
    rc = main(["verify", "--text", "We rely on prior work, PMID 35562209, for this."])
    out = capsys.readouterr().out
    assert rc == 2
    assert "FABRICATED" in out


def test_verify_json_output(monkeypatch, capsys):
    monkeypatch.setattr("deltasci.audit.runner.verify_auditor", lambda cache=None, max_workers=4, support=True: _FakeAuditor([_FABRICATED]))
    rc = main(["verify", "--text", "PMID 35562209 backs this.", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2
    assert payload["verdicts"]["FABRICATED"] == 1
    assert payload["findings"][0]["verdict"] == "FABRICATED"


def test_verify_no_support_uses_metadata_only(monkeypatch, capsys):
    monkeypatch.setattr("deltasci.audit.runner.verify_auditor", lambda cache=None, max_workers=4, support=True: _FakeAuditor([_VERIFIED]))
    rc = main(["verify", "--text", "Backed by PMID 12345678.", "--no-support"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PASS" in out


def test_verify_records_format(monkeypatch, capsys):
    monkeypatch.setattr("deltasci.audit.runner.verify_auditor", lambda cache=None, max_workers=4, support=True: _FakeAuditor([_VERIFIED]))
    rc = main(["verify", "--format", "records", "--text", '[{"claim": "c", "source": "PMID 12345678"}]'])
    assert rc == 0
    assert "PASS" in capsys.readouterr().out
