"""File-based audit cache. Keyed by (verifier_name, identifier_kind, identifier_value)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from deltasci.audit.base import AuditFinding


def default_cache_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "deltasci" / "audit-cache.json"


class AuditCache:
    """Tiny JSON-on-disk cache. Verified findings live longer than failures."""

    DEFAULT_VERIFIED_TTL_SECS = 30 * 24 * 3600
    DEFAULT_FAILURE_TTL_SECS = 7 * 24 * 3600

    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else default_cache_path()
        self._cache: dict[str, dict] = {}
        self._dirty = False
        self._loaded = False

    def _key(self, verifier: str, kind: str, value: str) -> str:
        return f"{verifier}::{kind}::{value}"

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        if not self.path.is_file():
            return
        try:
            self._cache = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            self._cache = {}

    def get(self, verifier: str, kind: str, value: str) -> AuditFinding | None:
        self._load()
        entry = self._cache.get(self._key(verifier, kind, value))
        if not entry:
            return None
        cached_at = entry.get("cached_at", 0)
        finding_data = entry.get("finding", {})
        ttl = (
            self.DEFAULT_VERIFIED_TTL_SECS
            if finding_data.get("status") == "verified"
            else self.DEFAULT_FAILURE_TTL_SECS
        )
        if time.time() - cached_at > ttl:
            return None
        try:
            return AuditFinding.model_validate(finding_data)
        except Exception:
            return None

    def put(self, verifier: str, kind: str, value: str, finding: AuditFinding) -> None:
        self._load()
        # Only cache deterministic outcomes; never cache 'skipped' (transient errors).
        if finding.status == "skipped":
            return
        self._cache[self._key(verifier, kind, value)] = {
            "cached_at": time.time(),
            "finding": finding.model_dump(),
        }
        self._dirty = True

    def flush(self) -> None:
        if not self._dirty:
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._cache, indent=2), encoding="utf-8")
            self._dirty = False
        except OSError:
            pass
