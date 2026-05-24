"""NCBI GEO accession verifier (GSE / GDS / GPL / GSM)."""

from __future__ import annotations

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError, get_json


class GEOAuditor(Auditor):
    name = "geo"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return isinstance(target, dict) and target.get("identifier") and target["identifier"].kind == "geo"

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_source: str = target["claim_source"]
        # Use E-utilities esearch on the gds db (GEO DataSets) — it indexes all GEO accessions.
        try:
            search = get_json(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                timeout=self.timeout,
                params={"db": "gds", "term": identifier.value, "retmode": "json", "tool": "deltasci"},
            )
        except HTTPError as exc:
            return AuditFinding(
                target_kind="dataset",
                target_summary=claim_source,
                auditor_name=self.name,
                status="skipped",
                mismatch_reasons=[f"network error: {exc}"],
                confidence="high",
            )

        ids = (search.get("esearchresult") or {}).get("idlist") or []
        if not ids:
            return AuditFinding(
                target_kind="dataset",
                target_summary=claim_source,
                auditor_name=self.name,
                status="mismatch",
                fetched_metadata={"accession": identifier.value, "found": False},
                mismatch_reasons=[f"GEO accession {identifier.value} not found"],
                confidence="high",
            )

        return AuditFinding(
            target_kind="dataset",
            target_summary=claim_source,
            auditor_name=self.name,
            status="verified",
            fetched_metadata={
                "accession": identifier.value,
                "url": f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={identifier.value}",
            },
            confidence="high",
        )
