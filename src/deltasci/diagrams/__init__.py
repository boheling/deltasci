"""Diagram generation for DeltaScience runs.

Emits mermaid sources from the structured experiment plan. Mermaid is preferred
over rasterized AI-generated images because:
  - text source is auditable + diffable
  - the rendered diagram is deterministic from the same experiment_plan.json
  - no risk of hallucinated axis labels / bands / regions in *data* figures

Three diagrams per run, written to `<run-dir>/12_diagrams/`:

    data_flow.mmd       — flowchart from data_acquisition → each protocol step
                          → primary_metric. Step nodes are clickable in the web
                          UI; tooltips carry the step description.
    protocol_seq.mmd    — sequenceDiagram showing protocol step ordering with
                          inputs / outputs as messages between roles.
    schema.mmd          — graph (or classDiagram) for any explicit graph schema
                          in `experiment_plan.json` (e.g., the donor-recipient
                          HLA bipartite graph). Skipped when no schema is present.
"""

from __future__ import annotations

from pathlib import Path

from deltasci.diagrams.generator import (
    DiagramArtifacts,
    DiagramSet,
    generate_diagrams,
    render_data_flow_mermaid,
    render_protocol_sequence_mermaid,
    render_schema_mermaid,
)

__all__ = [
    "DiagramArtifacts",
    "DiagramSet",
    "generate_diagrams",
    "render_data_flow_mermaid",
    "render_protocol_sequence_mermaid",
    "render_schema_mermaid",
    "STAGE_DIR",
]

STAGE_DIR = Path("12_diagrams")
