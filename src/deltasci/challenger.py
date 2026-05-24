"""Adversarial challenge — built-in second-opinion against the synthesized hypothesis.

The challenger reads the hypothesis + experiment plan + risks and tries to
break them. Output is structured so it can be displayed alongside the
hypothesis (web UI tab) and so its citations can run through the audit
pillar (augmentation B from the v0.2 plan).

Pluggable: any LLMAdapter can play the challenger. The default uses whichever
LLMAdapter is already configured (i.e., a separate model from the one that
produced the hypothesis is recommended; same-model challenge still surfaces
many issues but loses the second-opinion benefit).
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from deltasci.hypothesis import EvidenceItem, GroundedHypothesis
from deltasci.llm.base import LLMAdapter, Message
from deltasci.protocol import ExperimentPlan, RiskRegister
from deltasci.transcript import Transcript

ChallengeSeverity = Literal["low", "medium", "high", "critical"]
ChallengeKind = Literal[
    "factual-error",          # the hypothesis asserts something false
    "missing-baseline",       # comparison missing or unrealistic
    "wrong-metric",           # primary metric does not capture what matters
    "data-leakage-risk",      # train/test split allows leakage
    "selection-bias",         # cohort or sampling is not representative
    "confounding",            # a variable explains the result without the hypothesized mechanism
    "novelty-overstated",     # similar work already exists
    "feasibility-overstated", # compute, data access, or timeline unrealistic
    "ethics-or-governance",   # IRB / regulatory / consent gap
    "other",
]


class ChallengeFinding(BaseModel):
    id: str
    kind: ChallengeKind
    severity: ChallengeSeverity
    description: str
    evidence_citations: list[str] = Field(default_factory=list)  # raw source strings (audited downstream)
    suggested_response: str = ""  # what the hypothesis author should do


class ChallengeReport(BaseModel):
    summary: str
    findings: list[ChallengeFinding]
    challenger_provider: str = ""
    challenger_model: str = ""
    citations: list[EvidenceItem] = Field(default_factory=list)  # populated post-audit


CHALLENGE_SYSTEM = """\
You are an adversarial reviewer. A research hypothesis, an experiment plan,
and a risk register have been produced by another agent. Your job is to find
specific, concrete reasons this hypothesis will fail or has been overstated.

Be uncharitable but precise. For each finding, cite real evidence where you
can — papers, repos, prior work — and use the same source-string conventions
the hypothesis uses (so the audit pillar can verify your citations
downstream). If you cannot back a challenge with evidence, say so explicitly.

Aim for 5-9 findings. Fewer than 3 means you are being insufficiently
adversarial and your challenge is not useful.

Output a single JSON object — no commentary, no markdown fences, just JSON.

Required shape:

{
  "summary": "one paragraph stating your overall verdict",
  "findings": [
    {
      "id": "C1",
      "kind": "factual-error | missing-baseline | wrong-metric | data-leakage-risk | selection-bias | confounding | novelty-overstated | feasibility-overstated | ethics-or-governance | other",
      "severity": "low | medium | high | critical",
      "description": "specific, concrete claim about why this fails",
      "evidence_citations": ["author year, journal, PMID 12345678", "github.com/owner/repo"],
      "suggested_response": "what should change in the hypothesis or plan"
    }
    ...
  ]
}
""".strip()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


class ChallengeError(Exception):
    pass


def run_challenge(
    hypothesis: GroundedHypothesis,
    plan: ExperimentPlan | None,
    risks: RiskRegister | None,
    transcript: Transcript,
    llm: LLMAdapter,
) -> ChallengeReport:
    parts = [
        f"Hypothesis:\n{hypothesis.model_dump_json(indent=2)}\n",
    ]
    if plan is not None:
        parts.append(f"Experiment plan:\n{plan.model_dump_json(indent=2)}\n")
    if risks is not None:
        parts.append(f"Risk register:\n{risks.model_dump_json(indent=2)}\n")
    parts.append(f"Transcript:\n\n{transcript.render_markdown()}\n")
    parts.append("Now produce the challenge JSON.")

    raw = llm.complete(system=CHALLENGE_SYSTEM, messages=[Message("user", "\n".join(parts))])
    cleaned = _strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ChallengeError(f"challenger output was not valid JSON: {exc}\n---\n{raw}") from exc

    findings = []
    for i, f in enumerate(data.get("findings") or [], 1):
        findings.append(
            ChallengeFinding(
                id=f.get("id", f"C{i}"),
                kind=f.get("kind", "other"),
                severity=f.get("severity", "medium"),
                description=f.get("description", ""),
                evidence_citations=list(f.get("evidence_citations") or []),
                suggested_response=f.get("suggested_response", ""),
            )
        )
    return ChallengeReport(
        summary=data.get("summary", ""),
        findings=findings,
        challenger_provider=llm.provider_name,
        challenger_model=llm.model_id(),
    )


def render_challenge_md(report: ChallengeReport) -> str:
    lines = [
        "# Challenge report",
        "",
        f"_Challenger: {report.challenger_provider}/{report.challenger_model}_",
        "",
        report.summary,
        "",
        f"**{len(report.findings)} findings.**",
        "",
    ]
    for f in report.findings:
        lines.append(f"## {f.id} · {f.kind} · {f.severity.upper()}")
        lines.append("")
        lines.append(f"**Description.** {f.description}")
        lines.append("")
        if f.evidence_citations:
            lines.append("**Evidence cited:**")
            for c in f.evidence_citations:
                lines.append(f"- {c}")
            lines.append("")
        if f.suggested_response:
            lines.append(f"**Suggested response.** {f.suggested_response}")
            lines.append("")
    return "\n".join(lines)
