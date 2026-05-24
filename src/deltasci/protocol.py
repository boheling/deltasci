"""Protocol + Risks schemas + assemblers.

These are 5th-and-6th-stage outputs of a deltasci run. Each is produced by a
dedicated role (ProtocolEngineer, RiskAnalyst) after the synthesis stage, and
each contains claims that flow through the same audit pillar as the round
CLAIMs (augmentation A from the v0.2 plan).
"""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from deltasci.hypothesis import EvidenceItem, GroundedHypothesis
from deltasci.llm.base import LLMAdapter, Message
from deltasci.transcript import Transcript


# --- Protocol -----------------------------------------------------------------


class ProtocolStep(BaseModel):
    order: int
    name: str
    description: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    method_citations: list[str] = Field(default_factory=list)  # raw source strings


class DataAcquisitionPlan(BaseModel):
    primary_dataset: str = ""
    accession_or_url: str = ""
    access_constraints: str = ""  # IRB / DUA / DAA, etc.
    fallback_datasets: list[str] = Field(default_factory=list)


class ComputeRequirements(BaseModel):
    hardware: str = ""
    estimated_runtime: str = ""
    storage: str = ""
    cost_estimate: str = ""


class ExperimentPlan(BaseModel):
    title: str
    summary: str
    data_acquisition: DataAcquisitionPlan
    steps: list[ProtocolStep]
    primary_metric: str
    success_threshold: str  # mirrors hypothesis.falsifiability.threshold
    null_outcome: str       # mirrors hypothesis.falsifiability.null_outcome
    baselines: list[str] = Field(default_factory=list)
    compute: ComputeRequirements = Field(default_factory=ComputeRequirements)
    timeline_estimate: str = ""
    sample_size_justification: str = ""
    citations: list[EvidenceItem] = Field(default_factory=list)


# --- Risks --------------------------------------------------------------------


RiskCategory = Literal[
    "data",                  # data unavailable / biased / leakage
    "method",                # model class wrong, training instability, overfitting
    "evaluation",            # wrong metric, distribution shift, unrepresentative test set
    "translation",           # statistical significance ≠ clinical / domain meaningfulness
    "ethics-or-governance",  # IRB, consent, regulatory pathway
    "external-validity",    # results don't generalize beyond training cohort
    "incentive-or-process",  # researcher bias, p-hacking, garden-of-forking-paths
    "confounding",           # a third variable explains the result
    "novelty-overstated",    # claimed novelty is incorrect or smaller than framed
    "other",
]
RiskSeverity = Literal["low", "medium", "high", "critical"]


class RiskItem(BaseModel):
    id: str
    category: RiskCategory
    severity: RiskSeverity
    description: str
    likely_failure_mode: str
    mitigation: str
    counter_evidence_citations: list[str] = Field(default_factory=list)  # raw source strings


class RiskRegister(BaseModel):
    summary: str  # one paragraph
    items: list[RiskItem]
    citations: list[EvidenceItem] = Field(default_factory=list)


# --- Synthesis prompts --------------------------------------------------------


PROTOCOL_SYSTEM = """\
You are the Protocol Engineer step of a structured AI4Science co-reasoning
workflow. Read the synthesized hypothesis and the full transcript, and produce
a concrete experiment plan as a single JSON object — no commentary, no
markdown fences, just JSON.

The plan must be execution-ready: a researcher reading it should know exactly
what data to acquire, what steps to run in what order, what baselines to
compare against, what metric to compute, and how long it will take.

Required JSON shape:

{
  "title": "...",
  "summary": "one paragraph",
  "data_acquisition": {
    "primary_dataset": "...",
    "accession_or_url": "...",
    "access_constraints": "...",
    "fallback_datasets": []
  },
  "steps": [
    {"order": 1, "name": "...", "description": "...",
     "inputs": [...], "outputs": [...],
     "method_citations": ["author year, journal", "github.com/..."]}
    ...
  ],
  "primary_metric": "...",
  "success_threshold": "must mirror hypothesis.falsifiability.threshold exactly",
  "null_outcome": "must mirror hypothesis.falsifiability.null_outcome exactly",
  "baselines": ["..."],
  "compute": {"hardware": "...", "estimated_runtime": "...",
              "storage": "...", "cost_estimate": "..."},
  "timeline_estimate": "...",
  "sample_size_justification": "..."
}

Citations in `method_citations` follow the same grounding tag conventions as
CLAIMs. They will be audited downstream.
""".strip()


RISKS_SYSTEM = """\
You are the Risk Analyst step of a structured AI4Science co-reasoning
workflow. Read the hypothesis, the experiment plan, and the full transcript,
and produce a structured risk register as a single JSON object — no
commentary, no markdown fences, just JSON.

You are adversarial. Surface the specific ways this hypothesis or experiment
plan can fail. For each risk, name the failure mode, classify severity, and
propose a concrete mitigation. Cite real counter-evidence where you can.

Required JSON shape:

{
  "summary": "one paragraph",
  "items": [
    {
      "id": "R1",
      "category": "data | method | evaluation | translation | ethics-or-governance | external-validity | incentive-or-process | confounding | novelty-overstated | other",
      "severity": "low | medium | high | critical",
      "description": "...",
      "likely_failure_mode": "...",
      "mitigation": "...",
      "counter_evidence_citations": ["..."]
    }
    ...
  ]
}

Aim for 5-10 items. A risk register with fewer than 3 items is suspect
(claims excessive confidence in the design).
""".strip()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        if text.endswith("```"):
            text = text[: -3]
    return text.strip()


class ProtocolError(Exception):
    pass


class RisksError(Exception):
    pass


def assemble_protocol(
    hypothesis: GroundedHypothesis,
    transcript: Transcript,
    llm: LLMAdapter,
) -> ExperimentPlan:
    user = (
        f"Synthesized hypothesis:\n{hypothesis.model_dump_json(indent=2)}\n\n"
        f"Transcript:\n\n{transcript.render_markdown()}\n\n"
        f"Now produce the experiment plan JSON."
    )
    raw = llm.complete(system=PROTOCOL_SYSTEM, messages=[Message("user", user)])
    cleaned = _strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"protocol output was not valid JSON: {exc}\n---\n{raw}") from exc

    # Re-shape steps so order is integer-typed.
    steps_raw = data.get("steps") or []
    steps = []
    for i, s in enumerate(steps_raw, 1):
        steps.append(
            ProtocolStep(
                order=int(s.get("order", i)),
                name=s.get("name", f"step {i}"),
                description=s.get("description", ""),
                inputs=list(s.get("inputs") or []),
                outputs=list(s.get("outputs") or []),
                method_citations=list(s.get("method_citations") or []),
            )
        )

    da = data.get("data_acquisition") or {}
    cm = data.get("compute") or {}
    return ExperimentPlan(
        title=data.get("title") or hypothesis.title,
        summary=data.get("summary", ""),
        data_acquisition=DataAcquisitionPlan(
            primary_dataset=da.get("primary_dataset", ""),
            accession_or_url=da.get("accession_or_url", ""),
            access_constraints=da.get("access_constraints", ""),
            fallback_datasets=list(da.get("fallback_datasets") or []),
        ),
        steps=steps,
        primary_metric=data.get("primary_metric", ""),
        success_threshold=data.get("success_threshold") or hypothesis.falsifiability.threshold,
        null_outcome=data.get("null_outcome") or hypothesis.falsifiability.null_outcome,
        baselines=list(data.get("baselines") or []),
        compute=ComputeRequirements(
            hardware=cm.get("hardware", ""),
            estimated_runtime=cm.get("estimated_runtime", ""),
            storage=cm.get("storage", ""),
            cost_estimate=cm.get("cost_estimate", ""),
        ),
        timeline_estimate=data.get("timeline_estimate", ""),
        sample_size_justification=data.get("sample_size_justification", ""),
    )


def assemble_risks(
    hypothesis: GroundedHypothesis,
    plan: ExperimentPlan,
    transcript: Transcript,
    llm: LLMAdapter,
) -> RiskRegister:
    user = (
        f"Hypothesis:\n{hypothesis.model_dump_json(indent=2)}\n\n"
        f"Experiment plan:\n{plan.model_dump_json(indent=2)}\n\n"
        f"Transcript:\n\n{transcript.render_markdown()}\n\n"
        f"Now produce the risk-register JSON."
    )
    raw = llm.complete(system=RISKS_SYSTEM, messages=[Message("user", user)])
    cleaned = _strip_code_fences(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RisksError(f"risk-register output was not valid JSON: {exc}\n---\n{raw}") from exc

    items = []
    for i, r in enumerate(data.get("items") or [], 1):
        items.append(
            RiskItem(
                id=r.get("id", f"R{i}"),
                category=r.get("category", "other"),
                severity=r.get("severity", "medium"),
                description=r.get("description", ""),
                likely_failure_mode=r.get("likely_failure_mode", ""),
                mitigation=r.get("mitigation", ""),
                counter_evidence_citations=list(r.get("counter_evidence_citations") or []),
            )
        )
    return RiskRegister(summary=data.get("summary", ""), items=items)


# --- Markdown renderers -------------------------------------------------------


def render_protocol_md(plan: ExperimentPlan) -> str:
    lines = [
        f"# Experiment plan — {plan.title}",
        "",
        plan.summary,
        "",
        "## Data acquisition",
        f"- **Primary dataset**: {plan.data_acquisition.primary_dataset or '—'}",
        f"- **Accession / URL**: {plan.data_acquisition.accession_or_url or '—'}",
        f"- **Access constraints**: {plan.data_acquisition.access_constraints or '—'}",
    ]
    if plan.data_acquisition.fallback_datasets:
        lines.append(f"- **Fallback datasets**: {', '.join(plan.data_acquisition.fallback_datasets)}")
    lines.append("")
    lines.append("## Steps")
    for s in plan.steps:
        lines.append("")
        lines.append(f"### {s.order}. {s.name}")
        if s.description:
            lines.append(s.description)
        if s.inputs:
            lines.append(f"- **Inputs**: {', '.join(s.inputs)}")
        if s.outputs:
            lines.append(f"- **Outputs**: {', '.join(s.outputs)}")
        if s.method_citations:
            lines.append(f"- **Methods cited**: {', '.join(s.method_citations)}")
    lines.append("")
    lines.append("## Evaluation")
    lines.append(f"- **Primary metric**: {plan.primary_metric}")
    lines.append(f"- **Success threshold**: {plan.success_threshold}")
    lines.append(f"- **Null outcome**: {plan.null_outcome}")
    if plan.baselines:
        lines.append(f"- **Baselines**: {', '.join(plan.baselines)}")
    lines.append("")
    lines.append("## Compute")
    lines.append(f"- **Hardware**: {plan.compute.hardware or '—'}")
    lines.append(f"- **Estimated runtime**: {plan.compute.estimated_runtime or '—'}")
    lines.append(f"- **Storage**: {plan.compute.storage or '—'}")
    lines.append(f"- **Cost estimate**: {plan.compute.cost_estimate or '—'}")
    lines.append("")
    lines.append("## Timeline")
    lines.append(plan.timeline_estimate or "_(not specified)_")
    lines.append("")
    lines.append("## Sample-size justification")
    lines.append(plan.sample_size_justification or "_(not specified)_")
    return "\n".join(lines)


def render_risks_md(register: RiskRegister) -> str:
    lines = ["# Risk register", "", register.summary, "", f"**{len(register.items)} risks identified.**", ""]
    for r in register.items:
        lines.append(f"## {r.id} · {r.category} · {r.severity.upper()}")
        lines.append("")
        lines.append(f"**Description.** {r.description}")
        lines.append("")
        lines.append(f"**Likely failure mode.** {r.likely_failure_mode}")
        lines.append("")
        lines.append(f"**Mitigation.** {r.mitigation}")
        if r.counter_evidence_citations:
            lines.append("")
            lines.append("**Counter-evidence cited:**")
            for c in r.counter_evidence_citations:
                lines.append(f"- {c}")
        lines.append("")
    return "\n".join(lines)
