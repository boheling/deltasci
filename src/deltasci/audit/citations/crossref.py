"""Crossref REST verifier for DOIs."""

from __future__ import annotations

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.citations._match import (
    first_author_in_claim,
    journal_close_match,
    title_close_match,
    year_in_claim,
)
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError, get_json


class CrossrefAuditor(Auditor):
    name = "crossref"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return isinstance(target, dict) and target.get("identifier") and target["identifier"].kind == "doi"

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_source: str = target["claim_source"]
        url = f"https://api.crossref.org/works/{identifier.value}"
        try:
            data = get_json(url, timeout=self.timeout, params={"mailto": "audit@deltasci.local"})
        except HTTPError as exc:
            # Crossref returns 404 for non-existent DOIs — treat as mismatch (fabricated)
            if "404" in str(exc):
                return AuditFinding(
                    target_kind="citation",
                    target_summary=claim_source,
                    auditor_name=self.name,
                    status="mismatch",
                    fetched_metadata={"doi": identifier.value, "found": False},
                    mismatch_reasons=[f"DOI {identifier.value} not found in Crossref"],
                    confidence="high",
                )
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="skipped",
                fetched_metadata={},
                mismatch_reasons=[f"network error: {exc}"],
                confidence="high",
            )

        msg = data.get("message", {})
        actual_title = (msg.get("title") or [""])[0] if isinstance(msg.get("title"), list) else (msg.get("title") or "")
        authors_raw = msg.get("author", []) or []
        actual_authors = [
            f"{a.get('family', '')}{(' ' + a.get('given', '')) if a.get('given') else ''}".strip()
            for a in authors_raw
        ]
        date_parts = (msg.get("issued") or {}).get("date-parts", [[None]])
        actual_year = str(date_parts[0][0]) if date_parts and date_parts[0] else ""
        actual_journal = (msg.get("container-title") or [""])[0] if isinstance(msg.get("container-title"), list) else ""

        reasons: list[str] = []
        if actual_title and not title_close_match(claim_source, actual_title):
            reasons.append(f"title differs: actual {actual_title!r}")
        if not first_author_in_claim(actual_authors, claim_source):
            reasons.append(
                f"first-author mismatch: actual {actual_authors[0] if actual_authors else '?'!r} not in AI claim"
            )
        if not year_in_claim(actual_year, claim_source):
            reasons.append(f"year mismatch: actual {actual_year!r}")
        if not journal_close_match(actual_journal, claim_source):
            reasons.append(f"journal mismatch: actual {actual_journal!r}")

        fetched = {
            "doi": identifier.value,
            "title": actual_title,
            "authors": actual_authors[:5],
            "year": actual_year,
            "journal": actual_journal,
            "url": f"https://doi.org/{identifier.value}",
        }
        if reasons:
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="mismatch",
                fetched_metadata=fetched,
                mismatch_reasons=reasons,
                confidence="high",
            )
        return AuditFinding(
            target_kind="citation",
            target_summary=claim_source,
            auditor_name=self.name,
            status="verified",
            fetched_metadata=fetched,
            confidence="high",
        )
