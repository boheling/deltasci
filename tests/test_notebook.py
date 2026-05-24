"""Tests for v0.3 notebook generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deltasci.hypothesis import (
    EpistemicSummary,
    FalsifiabilityClause,
    FeasibilityScores,
    GroundedHypothesis,
    HypothesisMetadata,
)
from deltasci.notebook import generate_notebook_pack, pack_has_notebook_template
from deltasci.notebook.cells import code_cell, markdown_cell
from deltasci.packs import load_pack
from deltasci.protocol import (
    ComputeRequirements,
    DataAcquisitionPlan,
    ExperimentPlan,
    ProtocolStep,
)


def _hypothesis() -> GroundedHypothesis:
    return GroundedHypothesis(
        title="Test hypothesis",
        statement="Testable statement.",
        domain_grounding={"mechanism": "m", "unmet_need": "u", "expected_impact": "e"},
        technical_approach={"core_method": "cm", "key_innovation": "ki", "implementation_path": "ip"},
        evidence_trail=[],
        knowledge_gaps=[],
        novel_syntheses=[],
        falsifiability=FalsifiabilityClause(prediction="p", threshold="auc>=0.85", null_outcome="auc<=baseline"),
        feasibility_scores=FeasibilityScores(scores={"a": 4}, justifications={"a": "j"}, overall=4.0),
        epistemic_summary=EpistemicSummary(),
        metadata=HypothesisMetadata(
            pack_name="biomed", pack_version="0.1.0", deltasci_version="0.3.0",
            llm_provider="mock", model="mock-1", num_rounds=4,
        ),
    )


def _plan() -> ExperimentPlan:
    return ExperimentPlan(
        title="Test plan",
        summary="A short test plan.",
        data_acquisition=DataAcquisitionPlan(
            primary_dataset="GEO accession GSE152048",
            accession_or_url="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE152048",
            access_constraints="public",
        ),
        steps=[
            ProtocolStep(order=1, name="load data", description="load h5ad"),
            ProtocolStep(order=2, name="train model", description="train HGT"),
        ],
        primary_metric="AUROC",
        success_threshold="AUROC >= 0.85",
        null_outcome="AUROC <= baseline + 0.01",
        baselines=["IFN-γ signature"],
        compute=ComputeRequirements(hardware="A100", estimated_runtime="6h", storage="50GB", cost_estimate="$30"),
        timeline_estimate="4 weeks",
        sample_size_justification="n=60",
    )


def test_pack_has_notebook_template_biomed():
    assert pack_has_notebook_template(load_pack("biomed"))


def test_pack_has_notebook_template_materials():
    assert pack_has_notebook_template(load_pack("materials"))


def test_pack_has_notebook_template_climate():
    assert pack_has_notebook_template(load_pack("climate"))


@pytest.mark.parametrize("pack_name", ["biomed", "materials", "climate"])
def test_generate_writes_three_files(pack_name, tmp_path):
    pack = load_pack(pack_name)
    nb_pack = generate_notebook_pack(pack=pack, hypothesis=_hypothesis(), plan=_plan(), run_dir=tmp_path)
    assert nb_pack is not None
    assert nb_pack.notebook_path.is_file()
    assert nb_pack.requirements_path.is_file()
    assert nb_pack.readme_path.is_file()


@pytest.mark.parametrize("pack_name", ["biomed", "materials", "climate"])
def test_generated_notebook_is_valid_ipynb_json(pack_name, tmp_path):
    pack = load_pack(pack_name)
    generate_notebook_pack(pack=pack, hypothesis=_hypothesis(), plan=_plan(), run_dir=tmp_path)
    nb = json.loads((tmp_path / "10_notebook" / "notebook.ipynb").read_text())
    assert nb["nbformat"] == 4
    assert isinstance(nb["cells"], list)
    assert len(nb["cells"]) >= 6  # header + hypothesis + imports + data + per-step + closing


def test_notebook_contains_step_cells_per_protocol_step(tmp_path):
    pack = load_pack("biomed")
    generate_notebook_pack(pack=pack, hypothesis=_hypothesis(), plan=_plan(), run_dir=tmp_path)
    nb = json.loads((tmp_path / "10_notebook" / "notebook.ipynb").read_text())
    sources = ["".join(c["source"]) if isinstance(c["source"], list) else c["source"] for c in nb["cells"]]
    joined = "\n".join(sources)
    # Each protocol step gets a markdown header
    assert "Step 1: load data" in joined
    assert "Step 2: train model" in joined


def test_biomed_routes_train_step_to_canonical_code(tmp_path):
    """v0.3.1: 'train model' step routes to canonical GNN training code, not a stub."""

    pack = load_pack("biomed")
    generate_notebook_pack(pack=pack, hypothesis=_hypothesis(), plan=_plan(), run_dir=tmp_path)
    nb = json.loads((tmp_path / "10_notebook" / "notebook.ipynb").read_text())
    sources = ["".join(c["source"]) if isinstance(c["source"], list) else c["source"] for c in nb["cells"]]
    joined = "\n".join(sources)
    # Real training code, not generic stub
    assert "TumorClassifier" in joined or "BCEWithLogitsLoss" in joined
    assert "torch_geometric" in joined or "pyg_nn" in joined


def test_notebook_contains_falsifiability_check(tmp_path):
    pack = load_pack("biomed")
    generate_notebook_pack(pack=pack, hypothesis=_hypothesis(), plan=_plan(), run_dir=tmp_path)
    nb = json.loads((tmp_path / "10_notebook" / "notebook.ipynb").read_text())
    sources = ["".join(c["source"]) if isinstance(c["source"], list) else c["source"] for c in nb["cells"]]
    joined = "\n".join(sources)
    assert "Falsifiability check" in joined
    assert "AUROC >= 0.85" in joined
    assert "MIN_LIFT_FOR_HYPOTHESIS" in joined
    assert "falsifies the hypothesis" in joined.lower()


def test_notebook_contains_dataset_accession_in_data_cell(tmp_path):
    pack = load_pack("biomed")
    generate_notebook_pack(pack=pack, hypothesis=_hypothesis(), plan=_plan(), run_dir=tmp_path)
    nb = json.loads((tmp_path / "10_notebook" / "notebook.ipynb").read_text())
    sources = ["".join(c["source"]) if isinstance(c["source"], list) else c["source"] for c in nb["cells"]]
    joined = "\n".join(sources)
    assert "GSE152048" in joined


def test_no_template_returns_none(tmp_path, monkeypatch):
    """A pack without notebook.py should yield None."""

    pack = load_pack("biomed")
    # Point the loader at an empty dir to simulate missing template
    monkeypatch.setattr(pack, "source_path", tmp_path)
    nb_pack = generate_notebook_pack(pack=pack, hypothesis=_hypothesis(), plan=_plan(), run_dir=tmp_path)
    assert nb_pack is None


def test_cell_helpers():
    md = markdown_cell("# Title\n\ntext")
    assert md["cell_type"] == "markdown"
    assert isinstance(md["source"], list)
    code = code_cell("import numpy as np\n# TODO")
    assert code["cell_type"] == "code"
    assert code["execution_count"] is None
    assert code["outputs"] == []
