from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run_cli(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "deltasci", *args],
        cwd=cwd or ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_cli_version():
    p = _run_cli(["-V"])
    assert p.returncode == 0
    assert "deltasci" in p.stdout


def test_cli_list_packs():
    p = _run_cli(["list-packs"])
    assert p.returncode == 0, p.stderr
    for name in ("biomed", "materials", "climate"):
        assert name in p.stdout


def test_cli_show_pack():
    p = _run_cli(["show-pack", "biomed"])
    assert p.returncode == 0, p.stderr
    assert "Biomedical" in p.stdout
    assert "Scoring axes" in p.stdout


def test_cli_init_pack(tmp_path):
    target = tmp_path / "scratchpack"
    p = _run_cli(["init-pack", "scratchpack", "--path", str(target)])
    assert p.returncode == 0, p.stderr
    assert (target / "pack.toml").is_file()
    assert (target / "lens.md").is_file()


def test_cli_validate_pack_builtin():
    pack_path = ROOT / "src" / "deltasci" / "packs" / "biomed"
    p = _run_cli(["validate-pack", str(pack_path)])
    assert p.returncode == 0, p.stderr
    assert "OK" in p.stdout


def test_cli_validate_pack_invalid(tmp_path):
    bogus = tmp_path / "broken"
    bogus.mkdir()
    (bogus / "pack.toml").write_text("[meta]\nname = 'broken'\n")  # missing fields
    (bogus / "lens.md").write_text("x")
    p = _run_cli(["validate-pack", str(bogus)])
    assert p.returncode != 0


def test_cli_demo_with_mock(tmp_path):
    out_dir = tmp_path / "out"
    p = _run_cli(["demo", "--pack", "biomed", "--llm", "mock", "--out", str(out_dir)])
    assert p.returncode == 0, p.stderr
    assert (out_dir / "transcript.md").is_file()
    assert (out_dir / "hypothesis.md").is_file()
    assert (out_dir / "summary.json").is_file()
    payload = json.loads((out_dir / "summary.json").read_text())
    assert "hypothesis" in payload
    assert "grounding" in payload


def test_cli_view_missing_dir(tmp_path):
    """cmd_view exits non-zero with a clear error when run-dir doesn't exist."""

    p = _run_cli(["view", str(tmp_path / "nope")])
    assert p.returncode != 0
    assert "not a directory" in p.stderr.lower() or "is not a directory" in p.stderr.lower()


def test_cli_view_dir_missing_summary(tmp_path):
    """cmd_view exits non-zero when run-dir lacks summary.json."""

    out_dir = tmp_path / "empty"
    out_dir.mkdir()
    (out_dir / "transcript.md").write_text("placeholder")
    p = _run_cli(["view", str(out_dir)])
    assert p.returncode != 0
    assert "summary" in p.stderr.lower() or "missing" in p.stderr.lower()


def test_cli_audit_missing_summary(tmp_path):
    """cmd_audit exits non-zero when run-dir has no summary.json."""

    out_dir = tmp_path / "noaudit"
    out_dir.mkdir()
    p = _run_cli(["audit", str(out_dir)])
    assert p.returncode != 0
    assert "not found" in p.stderr.lower() or "summary" in p.stderr.lower()
