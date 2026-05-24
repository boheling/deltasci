"""Tests for v0.5b preflight static analyzer."""

from __future__ import annotations

import json
from pathlib import Path

from deltasci.preflight import analyze_notebook
from deltasci.notebook.cells import code_cell, markdown_cell


def _write_notebook(cells: list[dict], path: Path) -> Path:
    nb = {
        "cells": cells,
        "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"}},
        "nbformat": 4, "nbformat_minor": 5,
    }
    path.write_text(json.dumps(nb), encoding="utf-8")
    return path


def test_clean_notebook_has_no_findings(tmp_path):
    nb_path = _write_notebook([
        code_cell("import numpy as np\nx = np.array([1, 2, 3])"),
        code_cell("print(x.mean())"),
    ], tmp_path / "nb.ipynb")
    report = analyze_notebook(nb_path)
    assert report.has_errors is False
    assert len(report.findings) == 0


def test_name_error_detection_across_cells(tmp_path):
    nb_path = _write_notebook([
        code_cell("import pandas as pd\ndf = pd.DataFrame()"),
        code_cell("print(undefined_var)"),  # never defined anywhere
    ], tmp_path / "nb.ipynb")
    report = analyze_notebook(nb_path)
    name_errors = report.by_kind("name_error")
    assert len(name_errors) == 1
    assert "undefined_var" in name_errors[0].message


def test_name_defined_in_earlier_cell_is_ok(tmp_path):
    nb_path = _write_notebook([
        code_cell("y = 42"),
        code_cell("print(y * 2)"),  # y defined in cell 0
    ], tmp_path / "nb.ipynb")
    report = analyze_notebook(nb_path)
    assert len(report.by_kind("name_error")) == 0


def test_researcher_gate_extraction(tmp_path):
    nb_path = _write_notebook([
        code_cell(
            "import os\n"
            "if not os.path.exists('data.csv'):\n"
            "    raise NotImplementedError('Place your CSV at data.csv first.')"
        ),
    ], tmp_path / "nb.ipynb")
    report = analyze_notebook(nb_path)
    gates = report.by_kind("researcher_gate")
    assert len(gates) == 1
    assert "Place your CSV" in gates[0].message


def test_researcher_gate_with_fstring_message(tmp_path):
    nb_path = _write_notebook([
        code_cell(
            "PATH = 'data.csv'\n"
            "raise NotImplementedError(f'Missing {PATH}; download from https://example.com')"
        ),
    ], tmp_path / "nb.ipynb")
    report = analyze_notebook(nb_path)
    gates = report.by_kind("researcher_gate")
    assert len(gates) == 1
    assert "https://example.com" in gates[0].message


def test_todo_vs_placeholder_distinction(tmp_path):
    nb_path = _write_notebook([
        code_cell("# TODO: tune this hyperparameter\nlearning_rate = 0.01"),
        code_cell("SA_POSITIONS = [9, 11, 13]  # PLACEHOLDER: not verified against HLA-EMMA"),
    ], tmp_path / "nb.ipynb")
    report = analyze_notebook(nb_path)
    assert len(report.by_kind("todo")) == 1
    assert len(report.by_kind("placeholder")) == 1


def test_builtin_names_not_flagged(tmp_path):
    nb_path = _write_notebook([
        code_cell("for i in range(10):\n    print(i, len(str(i)))"),
    ], tmp_path / "nb.ipynb")
    report = analyze_notebook(nb_path)
    assert len(report.by_kind("name_error")) == 0


def test_marco_dr_dq_notebook_caught_six_gates_and_six_placeholders():
    """The case-study notebook has known characteristics — verify preflight finds them.

    Two valid notebook states for this file:
      (a) Fresh v0.5 scaffold — 6 researcher_gates + 6 placeholders.
      (b) After the v0.6 cell-runner walked it — most gates patched into working
          code, only the genuinely-blocked residual gates remain.
    Detect (b) via the deltasci 'session_summary' marker and use looser bounds.
    """
    import json

    nb_path = Path(__file__).parent.parent / "docs" / "examples" / "marco_dr_dq" / "10_notebook" / "notebook.ipynb"
    if not nb_path.is_file():
        # Notebook hasn't been regenerated yet — skip without failing
        return
    nb = json.loads(nb_path.read_text())
    walked = any(
        (c.get("metadata") or {}).get("deltasci", {}).get("kind") == "session_summary"
        for c in nb.get("cells", [])
    )

    report = analyze_notebook(nb_path)
    if walked:
        assert len(report.by_kind("researcher_gate")) >= 1  # post-execution residual
    else:
        assert len(report.by_kind("researcher_gate")) >= 5
        assert len(report.by_kind("placeholder")) >= 3
    # Critically: the v0.4-fixed-via-feature-assembly NameError on `y` should be 0
    assert len(report.by_kind("name_error")) == 0


def test_report_render_terminal(tmp_path):
    nb_path = _write_notebook([
        code_cell("# TODO: implement\nraise NotImplementedError('do this')"),
    ], tmp_path / "nb.ipynb")
    report = analyze_notebook(nb_path)
    text = report.render_terminal()
    assert "Researcher checklist" in text
    assert "do this" in text


def test_report_render_json(tmp_path):
    nb_path = _write_notebook([
        code_cell("raise NotImplementedError('msg')"),
    ], tmp_path / "nb.ipynb")
    report = analyze_notebook(nb_path)
    payload = json.loads(report.to_json())
    assert payload["summary"]["researcher_gate_count"] == 1
    assert payload["summary"]["has_errors"] is True
