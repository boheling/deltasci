"""DeltaScience: two-perspective co-reasoning for AI4Science hypothesis generation."""

from deltasci.audit import AuditFinding, AuditReport, MultiLayerAuditor
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

__version__ = "0.7.3"

__all__ = [
    "AuditFinding",
    "AuditReport",
    "CoReasoner",
    "Config",
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
    "__version__",
]
