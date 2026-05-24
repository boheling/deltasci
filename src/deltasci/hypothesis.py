from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EvidenceType = Literal[
    "published-evidence",
    "established-guideline",
    "observation",
    "engineering-precedent",
]

# `uncovered` is intentionally NOT permitted on EvidenceItem — uncovered claims
# must be expressed as KnowledgeGap, not faked as a citation.
Coverage = Literal["well-covered", "sparse"]

# Categories the AI can use to explain why a claim sits outside its training distribution.
GapCategory = Literal[
    "lab-tribal-knowledge",
    "paywalled-or-non-OA",
    "non-english-literature",
    "niche-subfield",
    "unpublished-or-pilot-data",
    "patent-or-clinical-practice",
    "novel-cross-disciplinary-connection",
    "other",
]


class EvidenceItem(BaseModel):
    """A single grounded claim, with both its external sourcing and the AI's self-assessed coverage."""

    claim: str = Field(min_length=1)
    type: EvidenceType
    source: str = ""  # citation; required except for `observation`
    coverage: Coverage  # AI's honest self-assessment of training coverage
    verified: bool = False

    @field_validator("source")
    @classmethod
    def _source_required_for_evidence(cls, v: str, info) -> str:
        type_ = info.data.get("type")
        if type_ in {"published-evidence", "established-guideline", "engineering-precedent"} and not v.strip():
            raise ValueError(f"source is required when type={type_!r}")
        return v


class KnowledgeGap(BaseModel):
    """An honest acknowledgment that a needed fact is plausibly outside AI's training distribution.

    The AI emits these instead of fabricating citations. They are presented to the
    researcher as 'researcher knowledge required'.
    """

    question: str = Field(min_length=1)
    category: GapCategory = "other"


class NovelSynthesis(BaseModel):
    """A connection or leap the AI is proposing that no source explicitly states.

    Distinct from a citation: the AI is saying 'I am combining these ideas in a way
    I cannot find written down anywhere — verify with researcher.'
    """

    proposed_connection: str = Field(min_length=1)
    rationale: str = ""  # one-line why this leap is plausible


class FalsifiabilityClause(BaseModel):
    """A falsifiable prediction with a measurable threshold and a null outcome.

    DeltaScience refuses to emit a hypothesis without one of these.
    """

    prediction: str = Field(min_length=1)
    threshold: str = Field(min_length=1)
    null_outcome: str = Field(min_length=1)


class FeasibilityScores(BaseModel):
    """Domain-pack-defined feasibility axes, each scored 1-5 with justification."""

    scores: dict[str, int]
    justifications: dict[str, str]
    overall: float

    @field_validator("scores")
    @classmethod
    def _scores_in_range(cls, v: dict[str, int]) -> dict[str, int]:
        for axis, score in v.items():
            if not (1 <= score <= 5):
                raise ValueError(f"score for {axis!r} must be in [1, 5], got {score}")
        return v


class EpistemicSummary(BaseModel):
    """A snapshot of how the AI characterized its own knowledge across the dialogue.

    Used by callers to decide how much human review the hypothesis needs.
    """

    well_covered_count: int = 0
    sparse_count: int = 0
    knowledge_gap_count: int = 0
    novel_synthesis_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class HypothesisMetadata(BaseModel):
    pack_name: str
    pack_version: str
    deltasci_version: str
    llm_provider: str
    model: str
    num_rounds: int
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GroundedHypothesis(BaseModel):
    """The final synthesized output of a co-reasoning session."""

    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    domain_grounding: dict[str, str]
    technical_approach: dict[str, str]
    evidence_trail: list[EvidenceItem] = Field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)
    novel_syntheses: list[NovelSynthesis] = Field(default_factory=list)
    falsifiability: FalsifiabilityClause
    feasibility_scores: FeasibilityScores
    epistemic_summary: EpistemicSummary
    metadata: HypothesisMetadata
