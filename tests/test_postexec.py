"""Unit tests for the postexec analyzer + renderer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deltasci.postexec.analyzer import (
    Achievement,
    PostExecReport,
    RiskStatus,
    analyze_run,
    classify_next_steps,
    classify_risks,
    derive_achievements,
    extract_metrics,
    find_new_issues,
)
from deltasci.postexec.renderer import (
    append_execution_update_to_hypothesis,
    render_addendum_markdown,
    render_risks_markdown_with_status,
    update_summary_json,
    write_postexec_artifacts,
)


# --- Fixtures -----------------------------------------------------------------


def _stream(text: str) -> dict:
    return {"output_type": "stream", "name": "stdout", "text": text}


def _code(src: str, outputs: list[dict] | None = None) -> dict:
    return {"cell_type": "code", "source": src, "outputs": outputs or [], "metadata": {}}


def _obs(of_cell: int, text: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {"deltasci": {"kind": "observation", "of_cell": of_cell}},
        "source": text,
    }


def _stub_cells_for_marco_like_run() -> list[dict]:
    return [
        _code(
            "# === Step 1: MARCo data extraction (iterated) ===\n"
            "# pulled live from /api/correlation-matrix\n",
            outputs=[_stream(
                "pulling MARCo correlation-matrix (DRDQDP × 3 manufacturer_kits)…\n"
                "wrote data/marco_pairs.csv: 10,796 pairs\n"
                "MARCo pairs:        10,796\n"
                "after locus filter: 1,766 pairs\n"
            )],
        ),
        _obs(0, "> **Observation (cell 0)** — executed cleanly\n> via /api/correlation-matrix\n"),
        _code(
            "# === Step 8: Evaluate per-locus + platform-stratified ===\n",
            outputs=[_stream(
                "POOLED held-out Spearman ρ:        0.8848\n\n"
                "Per-locus Spearman ρ:\n"
                "  DRB1   : n= 910, ρ = 0.8622\n"
                "  DQ     : n= 846, ρ = 0.8919\n"
                "Best baseline: hlamatchmaker_eplet (ρ = 0.6807)\n"
                "Model lift over best baseline: +0.2041\n"
                "Platform-discrepant pairs (|ρ_imm - ρ_ol| > 0.15): 98\n"
                "  Predicted ρ vs cross-platform consensus: ρ = 0.8640\n"
            )],
        ),
        _obs(2, "> **Observation (cell 2)** — executed cleanly"),
        _code(
            "# === Falsifiability check ===\n",
            outputs=[_stream(
                "pooled Spearman ρ (model):    0.8848\n"
                "pooled Spearman ρ (baseline): 0.6807\n"
                "lift over best baseline:      +0.2041\n"
                "falsifiability check PASSED\n"
            )],
        ),
        _obs(4, "> **Observation (cell 4)** — executed cleanly"),
    ]


# --- Metric extraction --------------------------------------------------------


def test_extract_metrics_pulls_pooled_rho_lift_and_per_locus():
    metrics = extract_metrics(_stub_cells_for_marco_like_run())
    by_name = {m.name: m for m in metrics}

    assert "pooled_spearman_rho" in by_name
    assert by_name["pooled_spearman_rho"].value == pytest.approx(0.8848)
    assert "falsifiability_lift" in by_name
    assert by_name["falsifiability_lift"].value == pytest.approx(0.2041)
    assert "falsifiability_passed" in by_name
    assert by_name["falsifiability_passed"].value == 1.0
    assert "per_locus_rho_DRB1" in by_name
    assert by_name["per_locus_rho_DRB1"].value == pytest.approx(0.8622)
    assert "per_locus_rho_DQ" in by_name
    assert by_name["per_locus_rho_DQ"].value == pytest.approx(0.8919)
    assert by_name["platform_consensus_rho"].value == pytest.approx(0.8640)


def test_extract_metrics_skips_cells_with_no_stdout():
    cells = [_code("# no output", outputs=[])]
    assert extract_metrics(cells) == []


# --- Risk classification ------------------------------------------------------


def test_classify_risks_marks_marco_bulk_extraction_resolved():
    risks = [
        {
            "id": "R1",
            "severity": "critical",
            "description": "MARCo bulk-extraction feasibility is unconfirmed; programmatic per-pair extraction may take weeks if no API exists, and may trigger rate-limiting.",
            "likely_failure_mode": "extraction takes 2+ months; partial coverage forces analysis to subset.",
        },
        {
            "id": "R5",
            "severity": "low",
            "description": "Compute exceeds budget — unrelated to data acquisition.",
        },
    ]
    statuses = classify_risks(risks, _stub_cells_for_marco_like_run())
    by_id = {r.risk_id: r for r in statuses}

    assert by_id["R1"].status == "resolved"
    assert by_id["R1"].evidence_cell == 0
    assert "/api/" in by_id["R1"].evidence_snippet.lower() or "api" in by_id["R1"].evidence_snippet.lower()
    # R5 has no matching family — should remain still_open
    assert by_id["R5"].status == "still_open"


# --- Next-step classification -------------------------------------------------


def test_classify_next_steps_marks_steps_done_when_executed_cleanly():
    steps = [
        {"order": 1, "name": "MARCo data extraction"},
        {"order": 8, "name": "Evaluate per-locus + platform-stratified"},
        {"order": 99, "name": "External validation cohort"},
    ]
    statuses = classify_next_steps(steps, _stub_cells_for_marco_like_run())
    by_name = {s.name: s for s in statuses}
    assert by_name["MARCo data extraction"].status == "done"
    assert by_name["Evaluate per-locus + platform-stratified"].status == "done"
    assert by_name["External validation cohort"].status == "outstanding"


# --- New issues ---------------------------------------------------------------


def test_find_new_issues_flags_placeholders_and_synthetic_substitutions():
    cells = [
        _code(
            "# === Step 4: HLA-EMMA ===\n"
            "SA_POSITIONS = [9, 11, 13]  # PLACEHOLDER:NOT-VERIFIED\n"
        ),
        _code(
            "# === Step 5: HLAMatchmaker ===\n"
            "eplet_df['source'] = 'SYNTHETIC_PROXY'\n"
        ),
        _code(
            "raise NotImplementedError('researcher gate')",
            outputs=[{
                "output_type": "error",
                "ename": "NotImplementedError",
                "evalue": "researcher gate",
                "traceback": [],
            }],
        ),
    ]
    issues = find_new_issues(cells)
    kinds = sorted({i.kind for i in issues})
    assert kinds == ["placeholder", "researcher_gate", "synthetic_substitution"]


# --- Achievements -------------------------------------------------------------


def test_derive_achievements_includes_falsifiability_and_resolved_critical_risks():
    cells = _stub_cells_for_marco_like_run()
    metrics = extract_metrics(cells)
    risks = [{"id": "R1", "severity": "critical",
              "description": "MARCo bulk-extraction may take weeks"}]
    risk_statuses = classify_risks(risks, cells)
    achievements = derive_achievements(metrics, risk_statuses)
    headlines = " | ".join(a.headline for a in achievements)
    assert "Falsifiability gate PASSED" in headlines
    assert "0.8848" in headlines
    assert "Risk R1" in headlines


# --- Renderers ----------------------------------------------------------------


def test_render_addendum_markdown_has_required_sections():
    report = PostExecReport(
        metrics=extract_metrics(_stub_cells_for_marco_like_run()),
        risk_statuses=[RiskStatus(
            risk_id="R1", severity="critical", description="bulk extraction",
            status="resolved", evidence_cell=0, evidence_snippet="via api",
        )],
        next_step_statuses=[],
        new_issues=[],
        achievements=[Achievement(headline="hello", detail="world")],
    )
    md = render_addendum_markdown(report)
    assert "# Execution Update" in md
    assert "Headline achievements" in md
    assert "Measured metrics" in md
    assert "Risk register — post-execution status" in md
    assert "✅" in md or "resolved" in md


def test_risks_md_status_badge_is_idempotent():
    src = (
        "# Risk register\n\n"
        "## R1 · data · CRITICAL\n\nText about R1.\n\n"
        "## R2 · method · HIGH\n\nText about R2.\n"
    )
    report = PostExecReport(
        risk_statuses=[
            RiskStatus(risk_id="R1", severity="critical", description="x", status="resolved"),
            RiskStatus(risk_id="R2", severity="high",     description="y", status="still_open"),
        ],
    )
    once = render_risks_markdown_with_status(src, report)
    twice = render_risks_markdown_with_status(once, report)
    assert "R1 · data · CRITICAL · ✅ resolved" in once
    assert "R2 · method · HIGH · 🟡 still open" in once
    # idempotent
    assert once == twice


def test_append_execution_update_idempotent():
    hyp = "# Hypothesis\n\nBody.\n"
    add = "Some addendum content."
    once = append_execution_update_to_hypothesis(hyp, add)
    twice = append_execution_update_to_hypothesis(once, add + "\nrevised")
    assert "deltasci:execution-update v1" in once
    assert once.count("deltasci:execution-update v1") == 1
    assert twice.count("deltasci:execution-update v1") == 1
    assert "revised" in twice


def test_update_summary_json_adds_postexec_block():
    summary = {"hypothesis": {"title": "x"}}
    report = PostExecReport()
    out = update_summary_json(summary, report)
    assert "postexec" in out
    assert set(out["postexec"].keys()) == {
        "metrics", "risk_statuses", "next_step_statuses", "new_issues", "achievements",
    }


# --- End-to-end ---------------------------------------------------------------


def test_analyze_run_round_trip(tmp_path):
    run_dir = tmp_path / "fakerun"
    (run_dir / "10_notebook").mkdir(parents=True)
    (run_dir / "10_notebook" / "notebook.ipynb").write_text(json.dumps({
        "cells": _stub_cells_for_marco_like_run(),
    }), encoding="utf-8")
    summary = {
        "risks": {"items": [{"id": "R1", "severity": "critical",
                              "description": "MARCo bulk-extraction may take weeks"}]},
        "protocol": {"steps": [{"order": 1, "name": "MARCo data extraction"}]},
    }
    (run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    report = analyze_run(run_dir)
    assert any(rs.status == "resolved" for rs in report.risk_statuses)
    assert any(s.status == "done" for s in report.next_step_statuses)
    assert any(m.name == "pooled_spearman_rho" for m in report.metrics)


def test_write_postexec_artifacts_writes_expected_files(tmp_path):
    run_dir = tmp_path / "fakerun"
    (run_dir / "10_notebook").mkdir(parents=True)
    (run_dir / "10_notebook" / "notebook.ipynb").write_text(json.dumps({
        "cells": _stub_cells_for_marco_like_run(),
    }), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps({
        "risks": {"items": []}, "protocol": {"steps": []},
    }), encoding="utf-8")
    (run_dir / "hypothesis.md").write_text("# H\n\nBody.\n", encoding="utf-8")
    (run_dir / "07_risks").mkdir(parents=True)
    (run_dir / "07_risks" / "risks.md").write_text(
        "# Risk register\n\n## R1 · data · CRITICAL\n\nText.\n", encoding="utf-8",
    )

    report = analyze_run(run_dir)
    written = write_postexec_artifacts(run_dir, report)
    names = {p.name for p in written}
    assert "execution_update.md" in names
    assert "report.json" in names
    assert "hypothesis.md" in names
    assert "summary.json" in names

    # Idempotency: writing twice does not duplicate the addendum.
    write_postexec_artifacts(run_dir, report)
    hyp_text = (run_dir / "hypothesis.md").read_text()
    assert hyp_text.count("deltasci:execution-update v1") == 1
