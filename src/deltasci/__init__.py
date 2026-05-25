"""DeltaScience: two-perspective co-reasoning for AI4Science hypothesis generation."""

from deltasci.audit import (
    AuditFinding,
    AuditReport,
    Claim,
    ClaimSupportAuditor,
    MultiLayerAuditor,
    claims_from_source,
    verify_auditor,
)
from deltasci.config import Config
from deltasci.engine import CoReasoner, Result
from deltasci.hypothesis import (
    EpistemicSummary,
    EvidenceItem,
    FalsifiabilityClause,
    FeasibilityScores,
    GroundedHypothesis,
    KnowledgeGap,
    NovelSynthesis,
)
from deltasci.packs import DomainPack, list_packs, load_pack
from deltasci.transcript import RoundEntry, Transcript
from deltasci.verify import verify_claims, verify_payload, verify_text

__version__ = "0.9.0"

__all__ = [
    "AuditFinding",
    "AuditReport",
    "Claim",
    "ClaimSupportAuditor",
    "CoReasoner",
    "Config",
    "claims_from_source",
    "verify_auditor",
    "DomainPack",
    "EpistemicSummary",
    "EvidenceItem",
    "FalsifiabilityClause",
    "FeasibilityScores",
    "GroundedHypothesis",
    "KnowledgeGap",
    "MultiLayerAuditor",
    "NovelSynthesis",
    "Result",
    "RoundEntry",
    "Transcript",
    "list_packs",
    "load_pack",
    "verify_claims",
    "verify_payload",
    "verify_text",
    "__version__",
]
