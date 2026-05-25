"""DataCite verifier for arXiv works.

arXiv mints a DataCite DOI — ``10.48550/arXiv.<id>`` — for every paper. The arXiv export
API is aggressively rate-limited (429s under any concurrency), so we verify arXiv
identifiers against DataCite instead: it's generous, needs no key, and returns clean
title / author / year metadata. This is what makes arXiv-heavy (CS/ML) bibliographies
verifiable.
"""

from __future__ import annotations

import re

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.citations._match import (
    claim_asserts_metadata,
    first_author_in_claim,
    title_close_match,
    year_in_claim,
)
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError, get_json

DATACITE_URL = "https://api.datacite.org/dois/"
_VERSION_RE = re.compile(r"v\d+$")


class DataCiteArxivAuditor(Auditor):
    name = "datacite"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return isinstance(target, dict) and target.get("identifier") and target["identifier"].kind == "arxiv"

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_source: str = target["claim_source"]
        bare = _VERSION_RE.sub("", identifier.value)  # DataCite DOI has no version suffix
        doi = f"10.48550/arXiv.{bare}"

        try:
            data = get_json(DATACITE_URL + doi, timeout=self.timeout)
        except HTTPError as exc:
            if "404" in str(exc):
                return AuditFinding(
                    target_kind="citation",
                    target_summary=claim_source,
                    auditor_name=self.name,
                    status="mismatch",
                    fetched_metadata={"arxiv": identifier.value, "found": False},
                    mismatch_reasons=[f"arXiv {identifier.value} not found in DataCite"],
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

        attrs = (data.get("data") or {}).get("attributes") or {}
        titles = attrs.get("titles") or []
        actual_title = (titles[0].get("title", "") if titles else "").strip()
        actual_authors = [c.get("name", "") for c in (attrs.get("creators") or []) if c.get("name")]
        actual_year = str(attrs.get("publicationYear") or "")

        fetched = {
            "arxiv": identifier.value,
            "doi": doi,
            "title": actual_title,
            "authors": actual_authors[:5],
            "year": actual_year,
            "url": f"https://arxiv.org/abs/{bare}",
        }

        reasons: list[str] = []
        if claim_asserts_metadata(claim_source, identifier):
            if actual_title and not title_close_match(claim_source, actual_title):
                reasons.append(f"title differs: actual {actual_title!r}")
            if not first_author_in_claim(actual_authors, claim_source):
                reasons.append(f"first-author mismatch: actual {actual_authors[0] if actual_authors else '?'!r} not in AI claim")
            if not year_in_claim(actual_year, claim_source):
                reasons.append(f"year mismatch: actual {actual_year!r}")

        return AuditFinding(
            target_kind="citation",
            target_summary=claim_source,
            auditor_name=self.name,
            status="mismatch" if reasons else "verified",
            fetched_metadata=fetched,
            mismatch_reasons=reasons,
            confidence="medium",
        )
