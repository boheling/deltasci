"""Final synthesis: turn a transcript into a GroundedHypothesis."""

from __future__ import annotations

import json
import re

from deltasci.hypothesis import (
    EpistemicSummary,
    EvidenceItem,
    FalsifiabilityClause,
    FeasibilityScores,
    GroundedHypothesis,
    HypothesisMetadata,
    KnowledgeGap,
    NovelSynthesis,
)
from deltasci.llm.base import LLMAdapter, Message
from deltasci.packs import DomainPack
from deltasci.transcript import Transcript

SYNTHESIS_SYSTEM = """\
You are the synthesis step of a structured AI4Science co-reasoning workflow.
Read the full transcript and produce a final grounded hypothesis as a single
JSON object — no commentary, no markdown fences, just JSON.

The JSON object MUST have these top-level fields:
- title: str, concise.
- statement: str, one paragraph stating the hypothesis.
- domain_grounding: object with keys "mechanism", "unmet_need", "expected_impact".
- technical_approach: object with keys "core_method", "key_innovation",
  "implementation_path".
- falsifiability: object with keys "prediction", "threshold", "null_outcome".
  ALL THREE FIELDS ARE REQUIRED. The threshold MUST be measurable.
- feasibility_scores: object mapping each rubric axis to an integer in [1, 5].
- feasibility_justifications: object mapping each rubric axis to a one-sentence
  justification.

The CLAIM, KNOWLEDGE_GAP, and NOVEL_SYNTHESIS items collected during the rounds
are aggregated automatically — do NOT re-emit them in this JSON.

Rubric axes for this domain pack: {axes}

If the transcript does not support a falsifiable prediction with a measurable
threshold, output exactly:
    {{"error": "no_falsifiable_clause", "reason": "<one sentence>"}}
""".strip()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


class SynthesisError(Exception):
    """Raised when synthesis cannot produce a valid hypothesis."""


def assemble(
    transcript: Transcript,
    pack: DomainPack,
    llm: LLMAdapter,
    deltasci_version: str,
    require_falsifiability: bool = True,
    require_epistemic_humility: bool = True,
) -> GroundedHypothesis:
    system = SYNTHESIS_SYSTEM.format(axes=", ".join(pack.scoring_rubric.axes))
    user = (
        f"Research idea: {transcript.idea}\n\n"
        f"Domain pack: {pack.name} ({pack.display_name})\n\n"
        f"Transcript:\n\n{transcript.render_markdown()}\n\n"
        f"Now produce the JSON object."
    )
    raw = llm.complete(system=system, messages=[Message("user", user)])
    return _parse_synthesis(
        raw=raw,
        transcript=transcript,
        pack=pack,
        llm=llm,
        deltasci_version=deltasci_version,
        require_falsifiability=require_falsifiability,
        require_epistemic_humility=require_epistemic_humility,
    )


def _parse_synthesis(
    *,
    raw: str,
    transcript: Transcript,
    pack: DomainPack,
    llm: LLMAdapter,
    deltasci_version: str,
    require_falsifiability: bool,
    require_epistemic_humility: bool,
) -> GroundedHypothesis:
    cleaned = _strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SynthesisError(f"Synthesis output was not valid JSON: {exc}\n---\n{raw}") from exc

    if isinstance(data, dict) and data.get("error") == "no_falsifiable_clause":
        raise SynthesisError(
            f"Synthesis refused: no falsifiable clause supported by the transcript. "
            f"Reason: {data.get('reason', 'unspecified')}"
        )

    falsifiability_data = data.get("falsifiability") or {}
    if require_falsifiability:
        for required in ("prediction", "threshold", "null_outcome"):
            if not falsifiability_data.get(required, "").strip():
                raise SynthesisError(
                    f"Synthesis output is missing falsifiability.{required}. "
                    f"DeltaScience requires every hypothesis to be falsifiable."
                )

    scores = data.get("feasibility_scores", {})
    justifications = data.get("feasibility_justifications", {})
    for axis in pack.scoring_rubric.axes:
        if axis not in scores:
            raise SynthesisError(f"Synthesis is missing feasibility score for rubric axis {axis!r}")
        if axis not in justifications:
            justifications[axis] = ""

    overall = _weighted_overall(scores, pack)

    evidence_trail = _dedupe_evidence(transcript.all_evidence())
    knowledge_gaps = _dedupe_gaps(transcript.all_knowledge_gaps())
    novel_syntheses = _dedupe_syntheses(transcript.all_novel_syntheses())

    well_covered = sum(1 for ev in evidence_trail if ev.coverage == "well-covered")
    sparse = sum(1 for ev in evidence_trail if ev.coverage == "sparse")
    warnings: list[str] = []
    if require_epistemic_humility and not knowledge_gaps and not novel_syntheses:
        raise SynthesisError(
            "Synthesis refused: the transcript has zero KNOWLEDGE_GAPs and zero "
            "NOVEL_SYNTHESES across all rounds. This is a hallucination signal — "
            "the AI is claiming complete certainty across an entire research idea. "
            "Re-run with stricter prompting or accept --allow-no-epistemic-gaps."
        )
    if not knowledge_gaps:
        warnings.append("zero knowledge gaps flagged — verify the AI is being honest about training-distribution edges")
    if not novel_syntheses:
        warnings.append("zero novel syntheses proposed — hypothesis may be a literature summary rather than a new direction")
    if sparse > well_covered and well_covered > 0:
        warnings.append("sparse-coverage citations outnumber well-covered ones — verify citations carefully")

    summary = EpistemicSummary(
        well_covered_count=well_covered,
        sparse_count=sparse,
        knowledge_gap_count=len(knowledge_gaps),
        novel_synthesis_count=len(novel_syntheses),
        warnings=warnings,
    )

    hypothesis = GroundedHypothesis(
        title=data["title"],
        statement=data["statement"],
        domain_grounding=data.get("domain_grounding", {}),
        technical_approach=data.get("technical_approach", {}),
        evidence_trail=evidence_trail,
        knowledge_gaps=knowledge_gaps,
        novel_syntheses=novel_syntheses,
        falsifiability=FalsifiabilityClause(**falsifiability_data),
        feasibility_scores=FeasibilityScores(
            scores={k: int(v) for k, v in scores.items()},
            justifications={k: str(v) for k, v in justifications.items()},
            overall=overall,
        ),
        epistemic_summary=summary,
        metadata=HypothesisMetadata(
            pack_name=pack.name,
            pack_version=pack.version,
            deltasci_version=deltasci_version,
            llm_provider=llm.provider_name,
            model=llm.model_id(),
            num_rounds=len(transcript.rounds),
        ),
    )
    return hypothesis


def _weighted_overall(scores: dict, pack: DomainPack) -> float:
    rubric = pack.scoring_rubric
    total_weight = sum(rubric.weights)
    if total_weight == 0:
        return 0.0
    weighted = 0.0
    for axis, weight in zip(rubric.axes, rubric.weights):
        weighted += float(scores.get(axis, 0)) * weight
    return round(weighted / total_weight, 2)


def _dedupe_evidence(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[tuple[str, str, str, str]] = set()
    out: list[EvidenceItem] = []
    for it in items:
        key = (it.type, it.coverage, it.source, it.claim)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _dedupe_gaps(items: list[KnowledgeGap]) -> list[KnowledgeGap]:
    seen: set[tuple[str, str]] = set()
    out: list[KnowledgeGap] = []
    for it in items:
        key = (it.category, it.question)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


def _dedupe_syntheses(items: list[NovelSynthesis]) -> list[NovelSynthesis]:
    seen: set[str] = set()
    out: list[NovelSynthesis] = []
    for it in items:
        if it.proposed_connection in seen:
            continue
        seen.add(it.proposed_connection)
        out.append(it)
    return out
