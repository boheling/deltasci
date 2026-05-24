"""HuggingFace Hub model/dataset existence verifier."""

from __future__ import annotations

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError, get_json


class HuggingFaceAuditor(Auditor):
    name = "huggingface"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return isinstance(target, dict) and target.get("identifier") and target["identifier"].kind == "huggingface"

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_source: str = target["claim_source"]
        # Try the models endpoint first; fall back to datasets.
        for kind, url in (
            ("model", f"https://huggingface.co/api/models/{identifier.value}"),
            ("dataset", f"https://huggingface.co/api/datasets/{identifier.value}"),
        ):
            try:
                data = get_json(url, timeout=self.timeout)
                fetched = {
                    "kind": kind,
                    "id": data.get("id", identifier.value),
                    "downloads": data.get("downloads", 0),
                    "url": f"https://huggingface.co/{identifier.value}",
                }
                return AuditFinding(
                    target_kind="repo",
                    target_summary=claim_source,
                    auditor_name=self.name,
                    status="verified",
                    fetched_metadata=fetched,
                    confidence="high",
                )
            except HTTPError as exc:
                if "404" in str(exc):
                    continue
                return AuditFinding(
                    target_kind="repo",
                    target_summary=claim_source,
                    auditor_name=self.name,
                    status="skipped",
                    mismatch_reasons=[f"network error: {exc}"],
                    confidence="high",
                )

        return AuditFinding(
            target_kind="repo",
            target_summary=claim_source,
            auditor_name=self.name,
            status="mismatch",
            fetched_metadata={"id": identifier.value, "found": False},
            mismatch_reasons=[f"HuggingFace id {identifier.value!r} not found as model or dataset"],
            confidence="high",
        )
