"""Tag extraction and grounding-violation detection.

Three first-class tags the role LLMs may emit:

    [CLAIM type=<TYPE> coverage=<COVERAGE> source="<CITATION>"]<claim>[/CLAIM]
    [KNOWLEDGE_GAP category=<CATEGORY>]<question for researcher>[/KNOWLEDGE_GAP]
    [NOVEL_SYNTHESIS rationale="<one-line>"]<proposed connection>[/NOVEL_SYNTHESIS]

CLAIM tags must declare a `coverage` of either `well-covered` or `sparse`.
A claim the AI thinks is `uncovered` must instead be a KNOWLEDGE_GAP — the AI is
not allowed to fabricate citations for material outside its training distribution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from deltasci.hypothesis import EvidenceItem, EvidenceType, GapCategory, KnowledgeGap, NovelSynthesis

VALID_EVIDENCE_TYPES: frozenset[EvidenceType] = frozenset(
    {"published-evidence", "established-guideline", "observation", "engineering-precedent"}
)
VALID_COVERAGES: frozenset[str] = frozenset({"well-covered", "sparse"})
VALID_GAP_CATEGORIES: frozenset[GapCategory] = frozenset(
    {
        "lab-tribal-knowledge",
        "paywalled-or-non-OA",
        "non-english-literature",
        "niche-subfield",
        "unpublished-or-pilot-data",
        "patent-or-clinical-practice",
        "novel-cross-disciplinary-connection",
        "other",
    }
)

CLAIM_TAG_RE = re.compile(r"\[CLAIM\s+([^\]]*?)\](.*?)\[/CLAIM\]", re.DOTALL)
GAP_TAG_RE = re.compile(r"\[KNOWLEDGE_GAP(?:\s+([^\]]*?))?\](.*?)\[/KNOWLEDGE_GAP\]", re.DOTALL)
SYN_TAG_RE = re.compile(r"\[NOVEL_SYNTHESIS(?:\s+([^\]]*?))?\](.*?)\[/NOVEL_SYNTHESIS\]", re.DOTALL)
ATTR_RE = re.compile(r'(\w+)\s*=\s*(?:"([^"]*)"|(\S+))')


def _parse_attrs(attr_str: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in ATTR_RE.finditer(attr_str or ""):
        key = m.group(1)
        val = m.group(2) if m.group(2) is not None else (m.group(3) or "")
        out[key] = val
    return out


@dataclass
class GroundingViolation:
    text: str
    reason: str
    raw_attrs: dict[str, str] = field(default_factory=dict)


@dataclass
class GroundingReport:
    items: list[EvidenceItem] = field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = field(default_factory=list)
    novel_syntheses: list[NovelSynthesis] = field(default_factory=list)
    violations: list[GroundingViolation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def total_signals(self) -> int:
        return len(self.items) + len(self.knowledge_gaps) + len(self.novel_syntheses)


def extract_signals(text: str) -> GroundingReport:
    """Pull every CLAIM / KNOWLEDGE_GAP / NOVEL_SYNTHESIS tag out of `text`."""

    report = GroundingReport()

    for match in CLAIM_TAG_RE.finditer(text):
        attrs = _parse_attrs(match.group(1))
        body = match.group(2).strip()
        type_ = attrs.get("type", "")
        coverage = attrs.get("coverage", "")
        source = attrs.get("source", "")

        if type_ not in VALID_EVIDENCE_TYPES:
            report.violations.append(
                GroundingViolation(
                    text=body,
                    reason=f"unknown evidence type {type_!r}; must be one of {sorted(VALID_EVIDENCE_TYPES)}",
                    raw_attrs=attrs,
                )
            )
            continue
        if coverage not in VALID_COVERAGES:
            if coverage == "uncovered":
                report.violations.append(
                    GroundingViolation(
                        text=body,
                        reason="coverage='uncovered' is not allowed on a CLAIM — emit a KNOWLEDGE_GAP instead",
                        raw_attrs=attrs,
                    )
                )
            else:
                report.violations.append(
                    GroundingViolation(
                        text=body,
                        reason=f"missing or invalid coverage={coverage!r}; must be one of {sorted(VALID_COVERAGES)}",
                        raw_attrs=attrs,
                    )
                )
            continue

        try:
            item = EvidenceItem(claim=body, type=type_, source=source, coverage=coverage)  # type: ignore[arg-type]
        except ValueError as exc:
            report.violations.append(GroundingViolation(text=body, reason=str(exc), raw_attrs=attrs))
            continue
        report.items.append(item)

    for match in GAP_TAG_RE.finditer(text):
        attrs = _parse_attrs(match.group(1) or "")
        body = match.group(2).strip()
        category = attrs.get("category", "other")
        if category not in VALID_GAP_CATEGORIES:
            report.violations.append(
                GroundingViolation(
                    text=body,
                    reason=f"unknown KNOWLEDGE_GAP category {category!r}; must be one of {sorted(VALID_GAP_CATEGORIES)}",
                    raw_attrs=attrs,
                )
            )
            continue
        try:
            gap = KnowledgeGap(question=body, category=category)  # type: ignore[arg-type]
        except ValueError as exc:
            report.violations.append(GroundingViolation(text=body, reason=str(exc), raw_attrs=attrs))
            continue
        report.knowledge_gaps.append(gap)

    for match in SYN_TAG_RE.finditer(text):
        attrs = _parse_attrs(match.group(1) or "")
        body = match.group(2).strip()
        rationale = attrs.get("rationale", "")
        try:
            syn = NovelSynthesis(proposed_connection=body, rationale=rationale)
        except ValueError as exc:
            report.violations.append(GroundingViolation(text=body, reason=str(exc), raw_attrs=attrs))
            continue
        report.novel_syntheses.append(syn)

    return report


def check_against_rules(report: GroundingReport, evidence_rules: Iterable[dict]) -> GroundingReport:
    """Apply pack-specific evidence rules (regex on source, etc.) on top of structural validation."""

    rules = {rule["type"]: rule for rule in evidence_rules if "type" in rule}
    new_items: list[EvidenceItem] = []
    for item in report.items:
        rule = rules.get(item.type)
        if rule and "source_pattern" in rule and item.source:
            if not re.search(rule["source_pattern"], item.source):
                report.violations.append(
                    GroundingViolation(
                        text=item.claim,
                        reason=(
                            f"source {item.source!r} does not match {item.type!r} pattern "
                            f"{rule['source_pattern']!r} for this domain"
                        ),
                        raw_attrs={"type": item.type, "source": item.source},
                    )
                )
                continue
        new_items.append(item)
    report.items = new_items
    return report


def format_violations_for_repair(violations: list[GroundingViolation]) -> str:
    if not violations:
        return ""
    lines = ["Your previous response had these grounding violations:"]
    for v in violations:
        snippet = v.text[:120].replace("\n", " ")
        lines.append(f"- {v.reason} :: text={snippet!r}")
    lines.append("Please re-emit the response with proper tagging. Remember:")
    lines.append("- Every factual claim must be in a CLAIM with type, coverage (well-covered|sparse), and source.")
    lines.append("- For anything outside your training distribution, use [KNOWLEDGE_GAP] instead of fabricating a CLAIM.")
    lines.append("- For connections you are proposing that no source explicitly states, use [NOVEL_SYNTHESIS].")
    return "\n".join(lines)


# Back-compat alias for existing callers/tests.
def extract_claims(text: str) -> GroundingReport:  # pragma: no cover - thin alias
    return extract_signals(text)
