"""arXiv API verifier."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.citations._match import (
    first_author_in_claim,
    title_close_match,
    year_in_claim,
)
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError, get_text


class ArxivAuditor(Auditor):
    name = "arxiv"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return isinstance(target, dict) and target.get("identifier") and target["identifier"].kind == "arxiv"

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_source: str = target["claim_source"]
        url = "http://export.arxiv.org/api/query"
        try:
            xml_text = get_text(url, timeout=self.timeout, params={"id_list": identifier.value})
        except HTTPError as exc:
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="skipped",
                mismatch_reasons=[f"network error: {exc}"],
                confidence="high",
            )

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="skipped",
                mismatch_reasons=[f"could not parse arXiv response: {exc}"],
                confidence="high",
            )

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entry = root.find("atom:entry", ns)
        if entry is None:
            return AuditFinding(
                target_kind="citation",
                target_summary=claim_source,
                auditor_name=self.name,
                status="mismatch",
                fetched_metadata={"id": identifier.value, "found": False},
                mismatch_reasons=[f"arXiv {identifier.value} not found"],
                confidence="high",
            )

        title_el = entry.find("atom:title", ns)
        actual_title = re.sub(r"\s+", " ", (title_el.text or "")).strip() if title_el is not None else ""
        authors = [
            (a.findtext("atom:name", default="", namespaces=ns) or "").strip()
            for a in entry.findall("atom:author", ns)
        ]
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "")[:4]

        reasons: list[str] = []
        if actual_title and not title_close_match(claim_source, actual_title):
            reasons.append(f"title differs: actual {actual_title!r}")
        if not first_author_in_claim(authors, claim_source):
            reasons.append(f"first-author mismatch: actual {authors[0] if authors else '?'!r} not in AI claim")
        if not year_in_claim(published, claim_source):
            reasons.append(f"year mismatch: actual {published!r}")

        fetched = {
            "arxiv": identifier.value,
            "title": actual_title,
            "authors": authors[:5],
            "year": published,
            "url": f"https://arxiv.org/abs/{identifier.value}",
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
