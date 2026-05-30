"""High-level verification API — the shared core behind `deltasci verify` and the MCP server.

This module has **no MCP / CLI dependency**, so it's the embeddable entry point for
library users and stays unit-testable without the MCP SDK installed.

    from deltasci.verify import verify_text, verify_payload
    report = verify_text("TAMs dominate the microenvironment (PMID 35562209).")
    payload = verify_payload(report)   # {summary, verdicts, findings[]} — JSON-ready
"""

from __future__ import annotations

from typing import Iterable

from deltasci.audit import runner  # module import so monkeypatching runner.* works everywhere
from deltasci.audit.base import AuditReport
from deltasci.audit.cache import AuditCache
from deltasci.audit.intake import Claim, claims_from_source
from deltasci.audit.report_md import summary_counts, verdict


def verify_claims(
    claims: Iterable[Claim],
    *,
    check_support: bool = True,
    cache: AuditCache | None = None,
    max_workers: int = 4,
) -> AuditReport:
    """Audit already-extracted claims. `check_support` adds the claim-to-abstract pass.

    `max_workers` controls audit concurrency; whole-paper runs raise it because the
    verifiers hit several *different* hosts (Crossref / OpenAlex / arXiv / PubMed) that
    don't share a rate limit, so more workers improves cross-host throughput.
    """

    claims = list(claims)
    if not claims:
        return AuditReport(findings=[])
    auditor = runner.verify_auditor(cache=cache, max_workers=max_workers, support=check_support)
    return auditor.audit(claims)


def verify_text(
    text: str,
    *,
    fmt: str = "auto",
    check_support: bool = True,
    cache: AuditCache | None = None,
) -> AuditReport:
    """Extract claims from `text` (auto-sniffed format) and audit them."""

    return verify_claims(claims_from_source(text, fmt=fmt), check_support=check_support, cache=cache)


def verify_payload(report: AuditReport, *, coverage: dict | None = None) -> dict:
    """JSON-ready dict: a one-line summary, verdict counts, and per-finding verdicts.

    `coverage` (from `intake.coverage_stats`) is included when present so the caller can
    honestly report references that had no checkable identifier and were NOT verified —
    rather than letting "N verified" silently hide the unchecked ones.
    """

    payload = {
        "summary": report.banner(),
        "verdicts": summary_counts(report),
        "findings": [{**f.model_dump(), "verdict": verdict(f)} for f in report.findings],
    }
    if coverage is not None:
        payload["coverage"] = coverage
    return payload


__all__ = ["verify_claims", "verify_payload", "verify_text"]
