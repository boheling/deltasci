"""Audit pillar for DeltaScience.

The audit layer turns "the AI claims this PMID supports its claim" into
"deltasci fetched the actual record at this PMID and the metadata matches
(or doesn't)".

Default-on; surfaces failures prominently rather than silently dropping them.
Keeping this layer's first-pass checks deterministic (pure API + string
comparison) is non-negotiable: an LLM-driven verifier can hallucinate the
verification, which is exactly the failure mode this pillar exists to prevent.
"""

from deltasci.audit.base import (
    AuditFinding,
    AuditReport,
    AuditStatus,
    Auditor,
    TargetKind,
)
from deltasci.audit.extractor import (
    Identifier,
    IdentifierKind,
    extract_identifiers,
)
from deltasci.audit.runner import MultiLayerAuditor, default_auditor

__all__ = [
    "Auditor",
    "AuditFinding",
    "AuditReport",
    "AuditStatus",
    "Identifier",
    "IdentifierKind",
    "MultiLayerAuditor",
    "TargetKind",
    "default_auditor",
    "extract_identifiers",
]
