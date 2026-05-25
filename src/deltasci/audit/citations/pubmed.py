"""PubMed E-utilities verifier — checks PMID metadata against AI claim.

NCBI E-utilities is free, no API key required, ~3 req/sec without a key.
We pass `tool=deltasci` per NCBI's politeness recommendation.

This is the verifier that would have caught the BioIntel
"PMID 35562209 = Zhou Y et al, osteosarcoma macrophages" failure:
the actual record at 35562209 is Gu et al, renal pelvis adenocarcinoma.
"""

from __future__ import annotations

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.citations._match import (
    claim_asserts_metadata,
    first_author_in_claim,
    journal_close_match,
    title_close_match,
    year_in_claim,
)
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError, get_json

ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


class PubMedAuditor(Auditor):
    name = "pubmed"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return isinstance(target, dict) and target.get("identifier") and target["identifier"].kind == "pmid"

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_source: str = target["claim_source"]

        try:
            data = get_json(
                ESUMMARY_URL,
                timeout=self.timeout,
                params={"db": "pubmed", "id": identifier.value, "retmode": "json", "tool": "deltasci"},
            )
        except HTTPError as exc:
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="skipped",
                fetched_metadata={},
                mismatch_reasons=[f"network error: {exc}"],
                confidence="high",
            )

        result = data.get("result", {}).get(identifier.value)
        if not result or "uids" in result:  # uids appears at the index level only
            # Could also be {"error": "..."}, treat as not-found.
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="mismatch",
                fetched_metadata={"pmid": identifier.value, "found": False},
                mismatch_reasons=[f"PMID {identifier.value} not found in PubMed"],
                confidence="high",
            )

        actual_title = result.get("title", "")
        actual_authors = [a.get("name", "") for a in result.get("authors", []) if a.get("name")]
        actual_year = (result.get("pubdate") or "")[:4]
        actual_journal = result.get("fulljournalname") or result.get("source") or ""

        # An esummary "record" with no title, authors, or date is a stub/error for a
        # numerically-valid-but-nonexistent PMID — treat as not-found (fabricated), not
        # a metadata mismatch, so all verifiers agree on the FABRICATED verdict.
        if not actual_title and not actual_authors and not actual_year:
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="mismatch",
                fetched_metadata={"pmid": identifier.value, "found": False},
                mismatch_reasons=[f"PMID {identifier.value} not found in PubMed"],
                confidence="high",
            )

        fetched = {
            "pmid": identifier.value,
            "title": actual_title,
            "authors": actual_authors[:5],  # truncate for output sanity
            "year": actual_year,
            "journal": actual_journal,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{identifier.value}/",
        }

        reasons: list[str] = []
        if claim_asserts_metadata(claim_source, identifier):
            if not title_close_match(claim_source, actual_title):
                reasons.append(f"title differs: AI claim does not contain >50% of tokens from actual title {actual_title!r}")
            if not first_author_in_claim(actual_authors, claim_source):
                reasons.append(
                    f"first-author mismatch: actual first author {actual_authors[0] if actual_authors else '?'!r} "
                    f"not present in AI claim"
                )
            if not year_in_claim(actual_year, claim_source):
                reasons.append(f"year mismatch: actual year {actual_year!r} not in AI claim")
            if not journal_close_match(actual_journal, claim_source):
                reasons.append(f"journal mismatch: actual journal {actual_journal!r} not in AI claim")

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
            mismatch_reasons=[],
            confidence="high",
        )
