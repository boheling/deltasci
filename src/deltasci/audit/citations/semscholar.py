"""Semantic Scholar verifier — covers DOI, PMID, and arXiv IDs against the
Semantic Scholar Academic Graph.

Why add S2 alongside PubMed/Crossref/OpenAlex/arXiv:
  - Catches preprints + ML conference papers the others miss.
  - Returns a stable canonical `paperId` per work that resolves regardless of
    which identifier the AI cited (PMID vs DOI vs arXiv).
  - Exposes `citationCount` so the audit report can flag claims backed by
    well-cited papers vs niche ones — useful corroboration signal even before
    the full 1-hop citation-graph walk (handled in `corroboration.py`).
"""

from __future__ import annotations

import os

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.citations._match import (
    first_author_in_claim,
    title_close_match,
    year_in_claim,
)
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError, get_json

S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
S2_FIELDS = "paperId,corpusId,externalIds,title,authors,year,venue,citationCount,referenceCount,tldr"


def _s2_url_for(identifier: Identifier) -> str | None:
    if identifier.kind == "doi":
        return f"{S2_API_BASE}/paper/DOI:{identifier.value}?fields={S2_FIELDS}"
    if identifier.kind == "pmid":
        return f"{S2_API_BASE}/paper/PMID:{identifier.value}?fields={S2_FIELDS}"
    if identifier.kind == "arxiv":
        return f"{S2_API_BASE}/paper/arXiv:{identifier.value}?fields={S2_FIELDS}"
    return None


class SemanticScholarAuditor(Auditor):
    name = "semantic_scholar"

    def __init__(self, timeout: float = 15.0, api_key: str | None = None) -> None:
        self.timeout = timeout
        self.api_key = api_key or os.environ.get("SEMANTIC_SCHOLAR_API_KEY")

    def can_audit(self, target: object) -> bool:
        if not isinstance(target, dict):
            return False
        ident = target.get("identifier")
        return bool(ident) and ident.kind in ("doi", "pmid", "arxiv")

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_source: str = target["claim_source"]
        url = _s2_url_for(identifier)
        if url is None:  # pragma: no cover — guarded by can_audit
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="skipped",
                mismatch_reasons=["unsupported identifier kind"],
                confidence="high",
            )
        try:
            data = get_json(url, timeout=self.timeout, headers=self._headers())
        except HTTPError as exc:
            if "404" in str(exc):
                return AuditFinding(
                    target_kind="citation",
                    target_summary=claim_source,
                    auditor_name=self.name,
                    status="mismatch",
                    fetched_metadata={"id": identifier.value, "found": False},
                    mismatch_reasons=[f"{identifier.kind.upper()} {identifier.value} not found in Semantic Scholar"],
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
        actual_authors = [a.get("name", "") for a in (data.get("authors") or [])]
        actual_year = str(data.get("year") or "")
        actual_venue = data.get("venue") or ""
        citation_count = data.get("citationCount", 0) or 0
        reference_count = data.get("referenceCount", 0) or 0
        tldr_text = (data.get("tldr") or {}).get("text", "") if data.get("tldr") else ""

        reasons: list[str] = []
        if actual_title and not title_close_match(claim_source, actual_title):
            reasons.append(f"title differs: actual {actual_title!r}")
        if not first_author_in_claim(actual_authors, claim_source):
            reasons.append(
                f"first-author mismatch: actual {actual_authors[0] if actual_authors else '?'!r} not in AI claim"
            )
        if not year_in_claim(actual_year, claim_source):
            reasons.append(f"year mismatch: actual {actual_year!r}")

        fetched = {
            "id": identifier.value,
            "paper_id": data.get("paperId", ""),
            "corpus_id": data.get("corpusId", 0),
            "title": actual_title,
            "authors": actual_authors[:5],
            "year": actual_year,
            "venue": actual_venue,
            "citation_count": citation_count,
            "reference_count": reference_count,
            "tldr": tldr_text,
        }
        status = "mismatch" if reasons else "verified"
        return AuditFinding(
            target_kind="citation",
            target_summary=claim_source,
            auditor_name=self.name,
            status=status,
            fetched_metadata=fetched,
            mismatch_reasons=reasons,
            confidence="medium",
        )

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key} if self.api_key else {}
