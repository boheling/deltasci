"""Tests for the mermaid diagram generator."""

from __future__ import annotations

import json

import pytest

from deltasci.diagrams import generate_diagrams
from deltasci.diagrams.generator import (
    render_data_flow_mermaid,
    render_protocol_sequence_mermaid,
    render_schema_mermaid,
)
from deltasci.protocol import (
    DataAcquisitionPlan,
    ExperimentPlan,
    ProtocolStep,
)


def _plan() -> ExperimentPlan:
    return ExperimentPlan(
        title="HLA cross-reactivity",
        summary="x",
        data_acquisition=DataAcquisitionPlan(
            primary_dataset="MARCo",
            accession_or_url="https://marco.igen.org.br/api/correlation-matrix",
        ),
        steps=[
            ProtocolStep(order=1, name="Pull MARCo", inputs=["api"], outputs=["pairs.csv"]),
            ProtocolStep(order=2, name="Featurize", inputs=["pairs.csv"], outputs=["features.csv"]),
            ProtocolStep(order=3, name="Train XGBoost", inputs=["features.csv"], outputs=["model"]),
            ProtocolStep(order=4, name="Evaluate (Spearman)", inputs=["model"], outputs=["rho"]),
        ],
        primary_metric="Spearman ρ",
        success_threshold="0.7",
        null_outcome="ρ <= 0.5",
    )


def test_data_flow_includes_data_steps_and_metric():
    plan = _plan()
    out = render_data_flow_mermaid(plan)
    assert out.startswith("flowchart TD")
    # Each step must appear
    for step in plan.steps:
        assert f"Step {step.order}" in out
    # Data + metric ends present
    assert "MARCo" in out
    assert "Spearman" in out
    assert "0.7" in out


def test_data_flow_handles_duplicate_step_names():
    """Two steps with the same name shouldn't collide on node id."""
    plan = ExperimentPlan(
        title="t", summary="s",
        data_acquisition=DataAcquisitionPlan(primary_dataset="D"),
        steps=[
            ProtocolStep(order=1, name="QC"),
            ProtocolStep(order=2, name="QC"),
        ],
        primary_metric="m", success_threshold="0", null_outcome="n",
    )
    out = render_data_flow_mermaid(plan)
    # Both QC nodes appear, but ids must differ — count node-definition lines.
    node_lines = [ln for ln in out.splitlines() if "QC" in ln and "[" in ln]
    assert len(node_lines) >= 2
    # Find the leading node-id tokens (text before `[`); they must be distinct.
    ids = []
    for ln in node_lines:
        head = ln.strip().split("[", 1)[0].strip()
        if head and "-->" not in head:
            ids.append(head)
    assert len(ids) == len(set(ids)), f"node ids collided: {ids}"


def test_protocol_sequence_renders_actors_and_messages():
    out = render_protocol_sequence_mermaid(_plan())
    assert out.startswith("sequenceDiagram")
    assert "participant Data" in out
    assert "participant Method" in out
    assert "participant Eval" in out
    # Messages
    assert "Step 1" in out and "Step 4" in out


def test_schema_mermaid_returns_empty_when_no_schema():
    assert render_schema_mermaid(None) == ""
    assert render_schema_mermaid({}) == ""
    assert render_schema_mermaid({"nodes": []}) == ""


def test_schema_mermaid_renders_nodes_and_edges():
    schema = {
        "nodes": [
            {"id": "donor", "label": "Donor HLA"},
            {"id": "recipient", "label": "Recipient HLA"},
        ],
        "edges": [{"from": "donor", "to": "recipient", "label": "mismatch"}],
    }
    out = render_schema_mermaid(schema)
    assert out.startswith("graph LR")
    assert "Donor HLA" in out
    assert "Recipient HLA" in out
    assert "mismatch" in out


def test_quotes_in_label_dont_break_parser():
    plan = ExperimentPlan(
        title="t", summary="s",
        data_acquisition=DataAcquisitionPlan(primary_dataset='Dataset "X"'),
        steps=[ProtocolStep(order=1, name='Step with "quotes" and | pipe')],
        primary_metric='metric "q"', success_threshold="", null_outcome="",
    )
    out = render_data_flow_mermaid(plan)
    # Mermaid's `[".."]` syntax treats raw `"` inside as the closing — we must escape.
    assert '"X"' not in out  # raw quotes should not appear unescaped
    assert "&quot;" in out
    assert "&#124;" in out


def test_generate_diagrams_writes_files(tmp_path):
    artifacts = generate_diagrams(_plan(), tmp_path / "12_diagrams")
    assert artifacts.data_flow_path.exists()
    assert artifacts.protocol_sequence_path.exists()
    assert artifacts.schema_path is None
    assert len(artifacts.written_paths) == 2


def test_generate_diagrams_writes_schema_when_provided(tmp_path):
    schema = {"nodes": [{"id": "a", "label": "A"}], "edges": []}
    artifacts = generate_diagrams(_plan(), tmp_path / "12_diagrams", graph_schema=schema)
    assert artifacts.schema_path is not None
    assert artifacts.schema_path.exists()
    assert "graph LR" in artifacts.schema_path.read_text()


def test_generate_diagrams_round_trip_via_summary_json(tmp_path):
    """Smoke test that ExperimentPlan.model_dump() → JSON → model_validate()
    survives the write-and-read round trip used by `deltasci diagrams <run-dir>`."""
    plan = _plan()
    summary = {"protocol": json.loads(plan.model_dump_json())}
    text = json.dumps(summary)
    re_parsed = ExperimentPlan.model_validate(json.loads(text)["protocol"])
    artifacts = generate_diagrams(re_parsed, tmp_path / "12_diagrams")
    out = artifacts.data_flow_path.read_text()
    assert "Pull MARCo" in out
