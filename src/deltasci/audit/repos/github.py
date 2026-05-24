"""GitHub repository existence verifier."""

from __future__ import annotations

from deltasci.audit.base import AuditFinding, Auditor
from deltasci.audit.extractor import Identifier
from deltasci.audit.http import HTTPError, get_json


class GitHubAuditor(Auditor):
    name = "github"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def can_audit(self, target: object) -> bool:
        return isinstance(target, dict) and target.get("identifier") and target["identifier"].kind == "github"

    def audit(self, target: dict) -> AuditFinding:
        identifier: Identifier = target["identifier"]
        claim_source: str = target["claim_source"]
        owner_repo = identifier.value.rstrip("/")
        # Strip a trailing .git if it slipped in.
        if owner_repo.endswith(".git"):
            owner_repo = owner_repo[:-4]
        url = f"https://api.github.com/repos/{owner_repo}"
        try:
            data = get_json(url, timeout=self.timeout)
        except HTTPError as exc:
            if "404" in str(exc):
                return AuditFinding(
                    target_kind="repo",
                    target_summary=claim_source,
                    auditor_name=self.name,
                    status="mismatch",
                    fetched_metadata={"repo": owner_repo, "found": False},
                    mismatch_reasons=[f"GitHub repo {owner_repo!r} does not exist"],
                    confidence="high",
                )
            # Rate-limited or network error — skip rather than mark as fabricated.
            return AuditFinding(
                target_kind="repo",
                target_summary=claim_source,
                auditor_name=self.name,
                status="skipped",
                mismatch_reasons=[f"network error: {exc}"],
                confidence="high",
            )

        fetched = {
            "repo": data.get("full_name", owner_repo),
            "description": data.get("description", "") or "",
            "stars": data.get("stargazers_count", 0),
            "url": data.get("html_url", f"https://github.com/{owner_repo}"),
        }
        return AuditFinding(
            target_kind="repo",
            target_summary=claim_source,
            auditor_name=self.name,
            status="verified",
            fetched_metadata=fetched,
            confidence="high",
        )
