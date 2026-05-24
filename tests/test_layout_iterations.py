"""Tests for v0.2.1 iteration archiving (09_iterations/)."""

from __future__ import annotations

from pathlib import Path

import pytest

from deltasci.layout import (
    archive_to_iteration,
    existing_iteration_count,
    read_idea_from_run_dir,
    timestamp_slug,
)


def _write_minimal_run(run_dir: Path, idea: str = "test idea") -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "00_idea.md").write_text(f"# Research idea\n\n{idea}\n")
    (run_dir / "01_framing").mkdir()
    (run_dir / "01_framing" / "transcript.md").write_text("framing transcript")
    (run_dir / "05_synthesis").mkdir()
    (run_dir / "05_synthesis" / "hypothesis.md").write_text("# hypothesis")
    (run_dir / "05_synthesis" / "summary.json").write_text('{"hypothesis": {}}')
    (run_dir / "08_audits").mkdir()
    (run_dir / "08_audits" / "citations.json").write_text("[]")
    (run_dir / "transcript.md").write_text("full transcript")
    (run_dir / "hypothesis.md").write_text("# hypothesis")
    (run_dir / "summary.json").write_text('{"hypothesis": {}}')
    (run_dir / "manifest.json").write_text('{"counts": {}}')


def test_existing_iteration_count_zero(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run(run_dir)
    assert existing_iteration_count(run_dir) == 0


def test_archive_to_iteration_creates_v1(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run(run_dir, idea="first attempt")
    archived = archive_to_iteration(run_dir)
    assert archived.name == "v1"
    assert archived.parent.name == "09_iterations"
    # Original artifacts moved
    assert not (run_dir / "00_idea.md").exists()
    assert not (run_dir / "01_framing").exists()
    assert not (run_dir / "summary.json").exists()
    # Archived artifacts present
    assert (archived / "00_idea.md").is_file()
    assert (archived / "01_framing" / "transcript.md").is_file()
    assert (archived / "summary.json").is_file()


def test_archive_to_iteration_increments(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run(run_dir, idea="first")
    v1 = archive_to_iteration(run_dir)
    assert v1.name == "v1"

    _write_minimal_run(run_dir, idea="second attempt")
    v2 = archive_to_iteration(run_dir)
    assert v2.name == "v2"
    assert (v2 / "00_idea.md").read_text().endswith("second attempt\n")
    # v1 still preserved
    assert (v1 / "00_idea.md").read_text().endswith("first\n")


def test_archive_preserves_iterations_subdir(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run(run_dir)
    archive_to_iteration(run_dir)
    # 09_iterations/ stays at top level
    assert (run_dir / "09_iterations" / "v1").is_dir()
    # And does NOT get archived into v2
    _write_minimal_run(run_dir, idea="second")
    archive_to_iteration(run_dir)
    assert not (run_dir / "09_iterations" / "v2" / "09_iterations").exists()


def test_archive_missing_dir_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        archive_to_iteration(tmp_path / "nope")


def test_read_idea_from_run_dir_top_level(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run(run_dir, idea="reading the idea back out")
    assert read_idea_from_run_dir(run_dir) == "reading the idea back out"


def test_read_idea_from_archived(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run(run_dir, idea="archived attempt")
    archive_to_iteration(run_dir)
    # Top-level 00_idea.md no longer exists; reader falls back to most-recent iteration
    assert read_idea_from_run_dir(run_dir) == "archived attempt"


def test_timestamp_slug_uses_idea():
    s = timestamp_slug("Predict graft survival from HLA mismatch")
    assert "predict" in s
    assert "graft" in s
    assert s[:8].isdigit()
