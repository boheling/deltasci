from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from deltasci.grounding import GroundingReport
from deltasci.hypothesis import EvidenceItem, KnowledgeGap, NovelSynthesis

# `ResearcherRedirect` is defined in deltasci.interactive but the import is
# deferred to avoid a circular import — interactive.py imports from this module.

RoleName = Literal["domain_scientist", "ml_engineer", "synthesis"]
RoundKind = Literal[
    "domain_r1",
    "engineer_r1",
    "domain_r2",
    "engineer_r2",
    "domain_r3",
    "engineer_r3",
    "synthesis",
]


@dataclass
class RoundEntry:
    role: RoleName
    kind: RoundKind
    text: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = field(default_factory=list)
    novel_syntheses: list[NovelSynthesis] = field(default_factory=list)
    violations_remaining: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Transcript:
    """Append-only record of a co-reasoning session."""

    idea: str
    pack_name: str
    rounds: list[RoundEntry] = field(default_factory=list)
    grounding_reports: list[GroundingReport] = field(default_factory=list)
    redirects: list = field(default_factory=list)  # list[ResearcherRedirect]; deferred type

    def append(self, entry: RoundEntry, report: GroundingReport | None = None) -> None:
        self.rounds.append(entry)
        if report is not None:
            self.grounding_reports.append(report)

    def replace_last(self, entry: RoundEntry, report: GroundingReport | None = None) -> None:
        """Replace the most recent round entry — used by re_do interactive action."""

        if not self.rounds:
            self.rounds.append(entry)
        else:
            self.rounds[-1] = entry
        if report is not None:
            if self.grounding_reports:
                self.grounding_reports[-1] = report
            else:
                self.grounding_reports.append(report)

    def redirects_after(self, round_kind: str) -> list:
        """Return any researcher redirects that landed after the round of this kind."""

        return [r for r in self.redirects if getattr(r, "after_round_kind", None) == round_kind]

    def render_markdown(self) -> str:
        lines = [
            "# Co-Reasoning Transcript",
            "",
            f"**Pack:** `{self.pack_name}`",
            "",
            f"**Idea:** {self.idea}",
            "",
        ]
        for entry in self.rounds:
            lines.append(f"## {entry.kind} — {entry.role}")
            lines.append("")
            lines.append(entry.text.strip())
            lines.append("")
            if entry.evidence:
                lines.append("### Evidence collected")
                for ev in entry.evidence:
                    src = ev.source if ev.source else "—"
                    lines.append(f"- **[{ev.type} · {ev.coverage}]** {ev.claim} — _{src}_")
                lines.append("")
            if entry.knowledge_gaps:
                lines.append("### Knowledge gaps flagged for researcher")
                for gap in entry.knowledge_gaps:
                    lines.append(f"- ({gap.category}) {gap.question}")
                lines.append("")
            if entry.novel_syntheses:
                lines.append("### Novel syntheses proposed")
                for syn in entry.novel_syntheses:
                    rationale = f" — _{syn.rationale}_" if syn.rationale else ""
                    lines.append(f"- {syn.proposed_connection}{rationale}")
                lines.append("")
            for r in self.redirects_after(entry.kind):
                lines.append("### Researcher redirect")
                lines.append("")
                lines.append(f"> {r.feedback}")
                lines.append("")
        return "\n".join(lines)

    def all_evidence(self) -> list[EvidenceItem]:
        out: list[EvidenceItem] = []
        for entry in self.rounds:
            out.extend(entry.evidence)
        return out

    def all_knowledge_gaps(self) -> list[KnowledgeGap]:
        out: list[KnowledgeGap] = []
        for entry in self.rounds:
            out.extend(entry.knowledge_gaps)
        return out

    def all_novel_syntheses(self) -> list[NovelSynthesis]:
        out: list[NovelSynthesis] = []
        for entry in self.rounds:
            out.extend(entry.novel_syntheses)
        return out
