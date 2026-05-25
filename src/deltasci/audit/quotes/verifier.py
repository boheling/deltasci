"""Quote-in-abstract verifier.

When the AI quotes a paper verbatim inside a CLAIM body, fetch the abstract
and confirm the quote actually appears in it.

This is the verifier that would have caught the BioIntel
"M2-polarized tumor-associated macrophages dominate the osteosarcoma
microenvironment" quote — the abstract for PMID 35562209 is about renal
pelvis adenocarcinoma and contains nothing about macrophages.
"""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from typing import Iterable

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError, get_text

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
QUOTE_RE = re.compile(r"[\"“]([^\"”]{20,400})[\"”]")


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def find_quotes(claim_text: str) -> list[str]:
    """Extract apparent verbatim quotes from a claim body."""

    return [m.group(1).strip() for m in QUOTE_RE.finditer(claim_text)]


def fetch_abstract(pmid: str, timeout: float = 10.0) -> str | None:
    """Return the cited paper's title + abstract as clean text.

    Uses efetch XML (not the plaintext dump) so the result is the structured
    ArticleTitle + AbstractText only — no journal/citation header, author
    affiliations, or personal emails. Papers with no abstract return just the
    title (still a strong topic signal for the support check). Returns None on
    network/parse failure so callers report `skipped`, never a false verdict.
    """

    try:
        xml_text = get_text(
            EFETCH_URL,
            timeout=timeout,
            params={"db": "pubmed", "id": pmid, "rettype": "abstract", "retmode": "xml", "tool": "deltasci"},
        )
    except HTTPError:
        return None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    parts: list[str] = []
    title = root.findtext(".//ArticleTitle")
    if title:
        parts.append(title.strip())
    for ab in root.findall(".//AbstractText"):
        body = "".join(ab.itertext()).strip()
        if body:
            parts.append(body)
    joined = " ".join(parts).strip()
    return joined or None


class QuoteInAbstractAuditor(Auditor):
    name = "quote_in_abstract"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return (
            isinstance(target, dict)
            and target.get("identifier")
            and target["identifier"].kind == "pmid"
            and target.get("claim_text")
            and find_quotes(target["claim_text"])
        )

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_text: str = target["claim_text"]
        claim_source: str = target.get("claim_source", "")

        quotes = find_quotes(claim_text)
        abstract = fetch_abstract(identifier.value, timeout=self.timeout)
        if abstract is None:
            return AuditFinding(
                target_kind="quote",
                target_summary=quotes[0] if quotes else claim_source,
                auditor_name=self.name,
                status="skipped",
                mismatch_reasons=["could not fetch abstract from PubMed efetch"],
                confidence="high",
            )

        normalized_abstract = _normalize(abstract)
        misses: list[str] = []
        hits: list[str] = []
        for q in quotes:
            if _normalize(q) in normalized_abstract:
                hits.append(q)
            else:
                misses.append(q)

        if not misses:
            return AuditFinding(
                target_kind="quote",
                target_summary=hits[0] if hits else "",
                auditor_name=self.name,
                status="verified",
                fetched_metadata={"pmid": identifier.value, "quotes_verified": len(hits)},
                confidence="high",
            )

        return AuditFinding(
            target_kind="quote",
            target_summary=misses[0],
            auditor_name=self.name,
            status="mismatch",
            fetched_metadata={
                "pmid": identifier.value,
                "abstract_excerpt": abstract[:400],
                "quotes_verified": len(hits),
                "quotes_missing": misses,
            },
            mismatch_reasons=[
                f"quote not found in abstract for PMID {identifier.value}: {q!r}" for q in misses
            ],
            confidence="high",
        )


__all__: Iterable[str] = ("QuoteInAbstractAuditor", "find_quotes", "fetch_abstract")
