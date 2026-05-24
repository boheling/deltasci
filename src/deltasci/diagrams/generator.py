"""Mermaid diagram generator for DeltaScience runs.

Pure-Python; no LLM round-trip. The diagrams are deterministic functions of
`ExperimentPlan` (and optionally an explicit graph schema), so we keep them
out of the audit pillar — they cannot hallucinate beyond the plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from deltasci.protocol import ExperimentPlan, ProtocolStep


@dataclass
class DiagramSet:
    data_flow: str
    protocol_sequence: str
    schema: str = ""

    def has_schema(self) -> bool:
        return bool(self.schema.strip())


@dataclass
class DiagramArtifacts:
    out_dir: Path
    data_flow_path: Path
    protocol_sequence_path: Path
    schema_path: Path | None = None
    written_paths: list[Path] = field(default_factory=list)


def _slug(text: str, *, fallback: str) -> str:
    """Mermaid node IDs must match `[A-Za-z][A-Za-z0-9_]*` and be unique. We
    derive a deterministic id from the step name; collisions get a suffix.
    """
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    if not slug or not slug[0].isalpha():
        slug = fallback
    return slug[:40] or fallback


def _quote(label: str) -> str:
    """Escape a mermaid node label so quotes / angle brackets don't break parsing."""
    label = label.replace('"', '&quot;').replace("\n", " ").replace("|", "&#124;")
    return label


def render_data_flow_mermaid(plan: ExperimentPlan) -> str:
    """Top-down flowchart: data → step1 → step2 → … → metric."""
    lines: list[str] = ["flowchart TD"]
    used: set[str] = set()

    def fresh_id(text: str, fallback: str) -> str:
        base = _slug(text, fallback=fallback)
        candidate = base
        counter = 2
        while candidate in used:
            candidate = f"{base}_{counter}"
            counter += 1
        used.add(candidate)
        return candidate

    data_label = plan.data_acquisition.primary_dataset or "Data acquisition"
    accession = plan.data_acquisition.accession_or_url
    if accession:
        data_label += f" ({accession})"
    data_id = fresh_id(plan.data_acquisition.primary_dataset or "data", fallback="Data")
    lines.append(f'    {data_id}["📊 {_quote(data_label)}"]')

    prev_id = data_id
    for step in sorted(plan.steps, key=lambda s: s.order):
        step_id = fresh_id(step.name, fallback=f"Step{step.order}")
        title = f"Step {step.order}: {step.name}"
        lines.append(f'    {step_id}["{_quote(title)}"]')
        lines.append(f"    {prev_id} --> {step_id}")
        prev_id = step_id

    metric_id = fresh_id(plan.primary_metric or "metric", fallback="Metric")
    metric_label = plan.primary_metric or "primary metric"
    threshold = plan.success_threshold or ""
    metric_full = f"🎯 {metric_label}" + (f" ≥ {threshold}" if threshold else "")
    lines.append(f'    {metric_id}["{_quote(metric_full)}"]')
    lines.append(f"    {prev_id} --> {metric_id}")

    # Style hints
    lines.append(f"    classDef data fill:#fef3c7,stroke:#b45309,color:#1f2937;")
    lines.append(f"    classDef metric fill:#dcfce7,stroke:#15803d,color:#1f2937;")
    lines.append(f"    class {data_id} data;")
    lines.append(f"    class {metric_id} metric;")

    return "\n".join(lines) + "\n"


def render_protocol_sequence_mermaid(plan: ExperimentPlan) -> str:
    """Sequence-diagram of protocol steps as messages between roles."""
    lines: list[str] = ["sequenceDiagram"]
    lines.append("    participant Data as Data")
    lines.append("    participant Method as Method")
    lines.append("    participant Eval as Evaluation")

    for step in sorted(plan.steps, key=lambda s: s.order):
        actor = "Data" if step.order <= max(1, len(plan.steps) // 4) else (
            "Eval" if "eval" in step.name.lower() else "Method"
        )
        target = "Method" if actor == "Data" else ("Eval" if actor == "Method" else "Data")
        in_label = ", ".join(step.inputs[:2]) if step.inputs else "—"
        out_label = ", ".join(step.outputs[:2]) if step.outputs else "—"
        msg = f"Step {step.order}: {step.name}"
        lines.append(f'    {actor}->>{target}: {_quote(msg)}')
        if step.outputs:
            lines.append(f"    Note over {target}: outputs: {_quote(out_label)}")

    if plan.primary_metric:
        threshold = (" ≥ " + plan.success_threshold) if plan.success_threshold else ""
        lines.append(f"    Eval-->>Method: {_quote(plan.primary_metric + threshold)}")
    return "\n".join(lines) + "\n"


def render_schema_mermaid(graph_schema: dict | None) -> str:
    """Optional graph-schema diagram. `graph_schema` shape (when present in
    experiment_plan.metadata): {"nodes": [{"id": "donor", "label": "Donor HLA"},
    ...], "edges": [{"from": "donor", "to": "recipient", "label": "mismatch"}]}.
    Returns empty string if schema absent or empty.
    """
    if not graph_schema:
        return ""
    nodes = graph_schema.get("nodes") or []
    edges = graph_schema.get("edges") or []
    if not nodes:
        return ""
    lines: list[str] = ["graph LR"]
    for n in nodes:
        nid = _slug(n.get("id", ""), fallback="N")
        label = _quote(n.get("label") or n.get("id") or "node")
        lines.append(f'    {nid}["{label}"]')
    for e in edges:
        a = _slug(e.get("from", ""), fallback="A")
        b = _slug(e.get("to", ""), fallback="B")
        lbl = e.get("label", "")
        connector = f"-- {_quote(lbl)} -->" if lbl else "-->"
        lines.append(f"    {a} {connector} {b}")
    return "\n".join(lines) + "\n"


def generate_diagrams(
    plan: ExperimentPlan,
    out_dir: Path,
    *,
    graph_schema: dict | None = None,
) -> DiagramArtifacts:
    """Render mermaid sources to `<out_dir>/{data_flow,protocol_seq,schema}.mmd`.

    Returns paths actually written. The schema file is only written when a
    non-empty graph_schema is provided.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    diagrams = DiagramSet(
        data_flow=render_data_flow_mermaid(plan),
        protocol_sequence=render_protocol_sequence_mermaid(plan),
        schema=render_schema_mermaid(graph_schema) if graph_schema else "",
    )

    artifacts = DiagramArtifacts(
        out_dir=out_dir,
        data_flow_path=out_dir / "data_flow.mmd",
        protocol_sequence_path=out_dir / "protocol_seq.mmd",
    )
    artifacts.data_flow_path.write_text(diagrams.data_flow, encoding="utf-8")
    artifacts.protocol_sequence_path.write_text(diagrams.protocol_sequence, encoding="utf-8")
    artifacts.written_paths = [artifacts.data_flow_path, artifacts.protocol_sequence_path]

    if diagrams.has_schema():
        artifacts.schema_path = out_dir / "schema.mmd"
        artifacts.schema_path.write_text(diagrams.schema, encoding="utf-8")
        artifacts.written_paths.append(artifacts.schema_path)

    return artifacts


def _step_label(step: ProtocolStep) -> str:  # pragma: no cover — convenience
    return f"{step.order}. {step.name}"
