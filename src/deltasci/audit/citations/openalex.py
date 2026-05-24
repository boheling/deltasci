"""OpenAlex verifier — fallback for DOIs that Crossref doesn't resolve."""

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


class OpenAlexAuditor(Auditor):
    name = "openalex"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return isinstance(target, dict) and target.get("identifier") and target["identifier"].kind in ("doi", "pmid")

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_source: str = target["claim_source"]
        if identifier.kind == "doi":
            url = f"https://api.openalex.org/works/doi:{identifier.value}"
        else:
            url = f"https://api.openalex.org/works/pmid:{identifier.value}"
        try:
            data = get_json(url, timeout=self.timeout)
        except HTTPError as exc:
            if "404" in str(exc):
                return AuditFinding(
                    target_kind="citation",
                    target_summary=claim_source,
                    auditor_name=self.name,
                    status="mismatch",
                    fetched_metadata={"id": identifier.value, "found": False},
                    mismatch_reasons=[f"{identifier.kind.upper()} {identifier.value} not found in OpenAlex"],
                    confidence="medium",
                )
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="skipped",
                mismatch_reasons=[f"network error: {exc}"],
                confidence="high",
            )

        actual_title = data.get("title") or ""
        authors_raw = data.get("authorships", []) or []
        actual_authors = [a.get("author", {}).get("display_name", "") for a in authors_raw if a.get("author")]
        actual_year = str(data.get("publication_year") or "")
        actual_journal = ((data.get("primary_location") or {}).get("source") or {}).get("display_name") or ""

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
            "id": identifier.value,
            "title": actual_title,
            "authors": actual_authors[:5],
            "year": actual_year,
            "journal": actual_journal,
            "url": data.get("doi") or data.get("id") or "",
        }
        if reasons:
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="mismatch",
                fetched_metadata=fetched,
                mismatch_reasons=reasons,
                confidence="medium",
            )
        return AuditFinding(
            target_kind="citation",
            target_summary=claim_source,
            auditor_name=self.name,
            status="verified",
            fetched_metadata=fetched,
            confidence="medium",
        )
