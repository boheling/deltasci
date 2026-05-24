"""1-hop citation corroboration via Semantic Scholar.

Given a verified citation (paperId), pulls the first N citing papers and the
first N references. The audit report can then surface "claim is from a paper
cited N times in S2" and (when --corroborate is on) the titles of the papers
that cite it.

Distinct from the verifier in `semscholar.py`: that file confirms the AI's
identifier resolves; this file walks the surrounding citation neighborhood.

Lives separate so the heavier (rate-limited) corroboration calls are opt-in
rather than defaulted in the audit hot path.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from deltasci.audit.http import HTTPError, get_json

S2_API_BASE = "https://api.semanticscholar.org/graph/v1"
NEIGHBOR_FIELDS = "title,year,authors.name,venue,citationCount"


@dataclass
class CorroborationResult:
    paper_id: str
    citation_count: int = 0
    reference_count: int = 0
    citing_papers: list[dict] = field(default_factory=list)
    cited_papers: list[dict] = field(default_factory=list)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "citation_count": self.citation_count,
            "reference_count": self.reference_count,
            "citing_papers": self.citing_papers,
            "cited_papers": self.cited_papers,
            "error": self.error,
        }


def fetch_neighbors(
    paper_id: str,
    *,
    limit: int = 10,
    timeout: float = 15.0,
    api_key: str | None = None,
) -> CorroborationResult:
    """Walk one citation hop from `paper_id` via S2 and return up to `limit`
    citing + cited papers each. Used by the audit pipeline when --corroborate
    is set, and by the report renderer to render a "cited by" panel.
    """
    if not paper_id:
        return CorroborationResult(paper_id=paper_id, error="empty paper_id")

    headers = {"x-api-key": api_key} if api_key else {}
    out = CorroborationResult(paper_id=paper_id)

    try:
        citing_data = get_json(
            f"{S2_API_BASE}/paper/{paper_id}/citations?limit={limit}&fields={NEIGHBOR_FIELDS}",
            timeout=timeout,
            headers=headers,
        )
        out.citing_papers = [
            _flatten(item.get("citingPaper") or {}) for item in (citing_data.get("data") or [])
        ]
    except HTTPError as exc:
        out.error = f"citing fetch failed: {exc}"

    try:
        ref_data = get_json(
            f"{S2_API_BASE}/paper/{paper_id}/references?limit={limit}&fields={NEIGHBOR_FIELDS}",
            timeout=timeout,
            headers=headers,
        )
        out.cited_papers = [
            _flatten(item.get("citedPaper") or {}) for item in (ref_data.get("data") or [])
        ]
    except HTTPError as exc:
        # Don't clobber the citing-side error, but still record this one.
        out.error = (out.error + " | " if out.error else "") + f"references fetch failed: {exc}"

    out.citation_count = len(out.citing_papers)
    out.reference_count = len(out.cited_papers)
    return out


def _flatten(paper: dict) -> dict:
    """Compact paper-record for the audit report."""
    authors = [a.get("name", "") for a in (paper.get("authors") or [])][:3]
    return {
        "title": paper.get("title", ""),
        "year": paper.get("year", ""),
        "venue": paper.get("venue", ""),
        "first_authors": authors,
        "citation_count": paper.get("citationCount", 0),
    }
