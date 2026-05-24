"""Audit type system and base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

AuditStatus = Literal["verified", "mismatch", "unverifiable", "skipped"]
"""Status of a single audit check.

- verified: the claimed identifier resolved AND its metadata matches the AI's claim.
- mismatch: the identifier resolved BUT metadata differs from the AI's claim.
- unverifiable: no parseable identifier in the source string (e.g., "Susal & Opelz, CTS, multiple papers").
- skipped: audit could not run (network error, timeout, --no-audit, etc.).

A claim is NEVER marked `verified` unless the verifier actually fetched the
record and compared metadata. This prevents the BioIntel `faithfulness: ok`
failure mode where the verifier marks a fabricated PMID as fine.
"""

TargetKind = Literal[
    "citation",   # CLAIM with type=published-evidence/established-guideline
    "repo",       # CLAIM with type=engineering-precedent
    "dataset",    # GEO/SRA/dbGaP accession in any source
    "quote",      # verbatim quote in claim text
    "notebook",   # generated notebook artifact (v0.2)
    "data",       # generated dataset artifact (v0.2)
    "figure",     # generated figure artifact (v0.2)
]


class AuditFinding(BaseModel):
    """One audit result. Each evidence item or artifact gets one or more findings."""

    target_kind: TargetKind
    target_summary: str
    """What the AI claimed (the source string, the repo URL, the quote text)."""

    auditor_name: str
    """Which verifier produced this finding (e.g., "pubmed", "github")."""

    status: AuditStatus
    fetched_metadata: dict = Field(default_factory=dict)
    """What the verifier actually returned, for transparency in the rendered output."""

    mismatch_reasons: list[str] = Field(default_factory=list)
    """Field-level diffs when status='mismatch' (e.g., 'title differs: AI=X, actual=Y')."""

    confidence: Literal["high", "medium", "low"] = "high"
    """How confident we are in this finding. 'low' on partial matches; 'high' on exact resolves."""

    audited_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AuditReport(BaseModel):
    """Aggregated findings across an entire run."""

    findings: list[AuditFinding] = Field(default_factory=list)
    skipped: bool = False
    skipped_reason: str = ""

    @property
    def verified_count(self) -> int:
        return sum(1 for f in self.findings if f.status == "verified")

    @property
    def mismatch_count(self) -> int:
        return sum(1 for f in self.findings if f.status == "mismatch")

    @property
    def unverifiable_count(self) -> int:
        return sum(1 for f in self.findings if f.status == "unverifiable")

    @property
    def skipped_count(self) -> int:
        return sum(1 for f in self.findings if f.status == "skipped")

    def banner(self) -> str:
        if self.skipped:
            return f"⚠️  AUDIT SKIPPED — citations not verified ({self.skipped_reason})"
        v, m, u, s = self.verified_count, self.mismatch_count, self.unverifiable_count, self.skipped_count
        parts = []
        if v:
            parts.append(f"✓ {v} verified")
        if m:
            parts.append(f"✗ {m} FAILED AUDIT")
        if u:
            parts.append(f"⊘ {u} unverifiable")
        if s:
            parts.append(f"… {s} skipped")
        if not parts:
            return "Audit summary: (no findings)"
        return "Audit summary: " + " · ".join(parts)


class Auditor(ABC):
    """Base interface for all audit verifiers.

    Implementations should be DETERMINISTIC where possible. LLM-based verifiers
    are allowed but must consume freshly-retrieved evidence (e.g., the abstract
    fetched from PubMed) and never rely on the LLM's training memory.
    """

    name: str

    @abstractmethod
    def can_audit(self, target: Any) -> bool:
        """Return True if this auditor knows how to check `target`."""

    @abstractmethod
    def audit(self, target: Any) -> AuditFinding:
        """Run the check and produce a finding. Must never raise; return status='skipped' on error."""
