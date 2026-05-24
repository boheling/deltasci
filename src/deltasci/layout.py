"""Run-directory layout helpers.

v0.2.0 introduced a numbered-stage subdir structure that makes a run dir
diffable, navigable, and iteration-aware:

    deltasci-output/<timestamp>_<slug>/
    ├── 00_idea.md
    ├── 01_framing/        round 1 transcript
    ├── 02_engineering/    round 2 transcript
    ├── 03_refinement/     round 3 transcript
    ├── 04_plan/           round 4 transcript
    ├── 05_synthesis/      hypothesis.md + summary.json
    ├── 06_protocol/       protocol.md + experiment_plan.json
    ├── 07_risks/          risks.md + risk_register.json
    ├── 08_audits/         citations.json + codex.json + ...
    └── 09_iterations/     v1/, v2/, ... (previous full trees)

Readers (web UI, `deltasci audit`) detect either layout. v0.1.x flat-layout
runs (with hypothesis.md + summary.json + transcript.md at top level) remain
readable as a fallback.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

STAGE_DIRS: dict[str, str] = {
    "idea": "00_idea.md",  # file, not dir
    "framing": "01_framing",
    "engineering": "02_engineering",
    "refinement": "03_refinement",
    "plan": "04_plan",
    "synthesis": "05_synthesis",
    "protocol": "06_protocol",
    "risks": "07_risks",
    "audits": "08_audits",
    "iterations": "09_iterations",
}

ROUND_TO_STAGE: dict[str, str] = {
    "domain_r1": "framing",
    "engineer_r1": "engineering",
    "domain_r2": "refinement",
    "engineer_r2": "plan",
}


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len].rstrip("-") or "run"


def timestamp_slug(idea: str | None = None) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    if idea:
        return f"{ts}_{slugify(idea)}"
    return ts


def is_staged(run_dir: Path) -> bool:
    return (run_dir / "05_synthesis").is_dir()


def is_flat(run_dir: Path) -> bool:
    return (run_dir / "summary.json").is_file() and not is_staged(run_dir)


class RunPaths:
    """Resolves the right path for each artifact, regardless of layout.

    Always writes the staged layout. Reads detect flat or staged.
    """

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = Path(run_dir)
        self.staged = is_staged(self.run_dir)

    # --- write paths (always staged) ---

    def stage(self, name: str) -> Path:
        path = self.run_dir / STAGE_DIRS[name]
        path.mkdir(parents=True, exist_ok=True)
        return path

    def idea_file(self) -> Path:
        return self.run_dir / STAGE_DIRS["idea"]

    def round_dir(self, round_kind: str) -> Path | None:
        stage = ROUND_TO_STAGE.get(round_kind)
        return self.stage(stage) if stage else None

    # --- read paths (layout-detecting) ---

    def hypothesis_md(self) -> Path:
        if self.staged:
            return self.run_dir / "05_synthesis" / "hypothesis.md"
        return self.run_dir / "hypothesis.md"

    def summary_json(self) -> Path:
        if self.staged:
            return self.run_dir / "05_synthesis" / "summary.json"
        return self.run_dir / "summary.json"

    def transcript_md(self) -> Path:
        # Top-level transcript.md is always written (flat for v0.1.x; back-compat
        # convenience for v0.2.0 readers like the web UI). Staged per-round
        # transcripts are also written under 0X_*/ subdirs.
        return self.run_dir / "transcript.md"

    def protocol_md(self) -> Path | None:
        p = self.run_dir / "06_protocol" / "protocol.md"
        return p if p.is_file() else None

    def experiment_plan_json(self) -> Path | None:
        p = self.run_dir / "06_protocol" / "experiment_plan.json"
        return p if p.is_file() else None

    def risks_md(self) -> Path | None:
        p = self.run_dir / "07_risks" / "risks.md"
        return p if p.is_file() else None

    def risk_register_json(self) -> Path | None:
        p = self.run_dir / "07_risks" / "risk_register.json"
        return p if p.is_file() else None

    def citation_audit_json(self) -> Path | None:
        if self.staged:
            p = self.run_dir / "08_audits" / "citations.json"
            return p if p.is_file() else None
        # In flat layout the audit was inside summary.json
        return None

    def codex_audit_json(self) -> Path | None:
        p = self.run_dir / "08_audits" / "codex.json"
        return p if p.is_file() else None

    def manifest_json(self) -> Path:
        return self.run_dir / "manifest.json"


# --- Iteration archiving (v0.2.1) -------------------------------------------


def existing_iteration_count(run_dir: Path) -> int:
    """Count existing iteration archives under <run_dir>/09_iterations/."""

    iter_root = run_dir / STAGE_DIRS["iterations"]
    if not iter_root.is_dir():
        return 0
    return sum(1 for d in iter_root.iterdir() if d.is_dir() and d.name.startswith("v"))


def archive_to_iteration(run_dir: Path) -> Path:
    """Move all stage artifacts at run_dir top-level into 09_iterations/v<n>/.

    Preserves: 00_idea.md, 01_framing/ ... 08_audits/, plus top-level
    transcript.md / hypothesis.md / summary.json / manifest.json. Leaves
    09_iterations/ itself in place (it accumulates).

    Returns the path to the new v<n> directory.
    """

    import shutil

    if not run_dir.is_dir():
        raise FileNotFoundError(f"run dir does not exist: {run_dir}")

    iter_root = run_dir / STAGE_DIRS["iterations"]
    iter_root.mkdir(parents=True, exist_ok=True)

    next_version = existing_iteration_count(run_dir) + 1
    target = iter_root / f"v{next_version}"
    if target.exists():
        raise FileExistsError(f"iteration target already exists: {target}")
    target.mkdir()

    archive_names = [
        "00_idea.md",
        "01_framing",
        "02_engineering",
        "03_refinement",
        "04_plan",
        "05_synthesis",
        "06_protocol",
        "07_risks",
        "08_audits",
        "10_notebook",
        "transcript.md",
        "hypothesis.md",
        "summary.json",
        "manifest.json",
    ]
    for name in archive_names:
        src = run_dir / name
        if not src.exists():
            continue
        shutil.move(str(src), str(target / name))

    return target


def read_idea_from_run_dir(run_dir: Path) -> str | None:
    """Best-effort read of the run dir's research idea."""

    candidates = [
        run_dir / "00_idea.md",
    ]
    iter_root = run_dir / STAGE_DIRS["iterations"]
    if iter_root.is_dir():
        # Newest iteration carries the most recent idea.
        for d in sorted(iter_root.iterdir(), reverse=True):
            if d.is_dir() and (d / "00_idea.md").is_file():
                candidates.append(d / "00_idea.md")
                break
    for p in candidates:
        if p.is_file():
            text = p.read_text(encoding="utf-8").strip()
            # Strip the "# Research idea\n\n" header if present.
            for marker in ("# Research idea\n\n", "# Research idea\n"):
                if text.startswith(marker):
                    return text[len(marker):].strip()
            return text
    return None
