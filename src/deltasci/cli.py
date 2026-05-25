"""deltasci command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from deltasci import __version__
from deltasci.config import Config
from deltasci.engine import CoReasoner
from deltasci.llm import get_adapter
from deltasci.packs import BUILTIN_PACK_NAMES, DomainPack, list_packs, load_pack


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--pack", required=True, help="Domain pack name (built-in) or directory path.")
    parser.add_argument("--idea", help="Research idea text. If omitted with --idea-file, reads from file.")
    parser.add_argument("--idea-file", help="Path to a file containing the research idea.")
    parser.add_argument("--out", default=None, help="Output directory (default: ./deltasci-output/).")
    parser.add_argument("--llm", default="auto", help="LLM provider: anthropic, openai, mock, or auto.")
    parser.add_argument("--model", default=None, help="Model id (provider-specific).")
    parser.add_argument(
        "--rounds",
        type=int,
        default=4,
        choices=[4, 6],
        help="Number of dialogue rounds (must be 4 or 6).",
    )
    parser.add_argument(
        "--strictness",
        default="high",
        choices=["high", "medium", "low"],
        help="Grounding strictness.",
    )
    parser.add_argument(
        "--allow-unfalsifiable",
        action="store_true",
        help="Allow synthesis to emit a hypothesis without a falsifiability clause.",
    )
    parser.add_argument(
        "--allow-no-epistemic-gaps",
        action="store_true",
        help=(
            "Allow synthesis when zero KNOWLEDGE_GAPs and zero NOVEL_SYNTHESES were emitted "
            "(by default this is treated as a hallucination signal and synthesis is refused)."
        ),
    )
    parser.add_argument(
        "--no-audit",
        action="store_true",
        help=(
            "Disable the citation/repo audit pass. NOT RECOMMENDED — this is the layer that "
            "catches fabricated PMIDs/DOIs (the BioIntel-style hallucination class). Output "
            "will carry an AUDIT SKIPPED banner."
        ),
    )
    parser.add_argument(
        "--audit-cache",
        default=None,
        help="Path to the audit cache JSON file (default: ~/.cache/deltasci/audit-cache.json).",
    )
    parser.add_argument(
        "--audit-timeout-seconds",
        type=float,
        default=10.0,
        help="Per-request timeout for audit verifiers (default: 10.0).",
    )
    parser.add_argument(
        "--no-protocol",
        action="store_true",
        help="Skip the protocol/experiment-plan generation stage.",
    )
    parser.add_argument(
        "--no-risks",
        action="store_true",
        help="Skip the risk-register generation stage.",
    )
    parser.add_argument(
        "--no-challenge",
        action="store_true",
        help="Skip the adversarial-challenger stage.",
    )
    parser.add_argument(
        "--no-view",
        action="store_true",
        help="Do not auto-launch `deltasci view` on the run dir at the end. Default: launch (unless headless).",
    )
    parser.add_argument(
        "--challenger-llm",
        default=None,
        help="LLM provider for the adversarial challenger (e.g., 'openai' to challenge an Anthropic synthesis). Defaults to the same as --llm.",
    )
    parser.add_argument(
        "--challenger-model",
        default=None,
        help="Model id for the challenger.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help=(
            "Pause for researcher review after the two domain rounds. Each gate offers "
            "approve / redirect / re-do / audit-now. Augmentation D from the v0.2 plan."
        ),
    )
    parser.add_argument(
        "--iterate-on",
        default=None,
        help=(
            "Path to an existing run dir. Archives its current artifacts into "
            "09_iterations/v<n>/ and writes the new run on top, preserving full "
            "audit lineage across re-runs. Augmentation C from the v0.2 plan."
        ),
    )
    parser.add_argument(
        "--no-notebook",
        action="store_true",
        help=(
            "Skip the executable-scaffold notebook in 10_notebook/. (Default: generate "
            "a .ipynb scaffold + requirements.txt + README.md from the pack template.)"
        ),
    )


def cmd_run(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)

    if args.idea and args.idea_file:
        print("error: pass either --idea or --idea-file, not both", file=sys.stderr)
        return 2
    idea = args.idea
    if args.idea_file:
        idea = Path(args.idea_file).read_text(encoding="utf-8").strip()
    if not idea:
        print("error: --idea or --idea-file is required", file=sys.stderr)
        return 2

    auto_view = not args.no_view and sys.stdout.isatty()

    config = Config(
        llm_provider=args.llm,
        model=args.model,
        num_rounds=args.rounds,
        grounding_strictness=args.strictness,
        require_falsifiability=not args.allow_unfalsifiable,
        require_epistemic_humility=not args.allow_no_epistemic_gaps,
        audit_enabled=not args.no_audit,
        audit_cache_path=Path(args.audit_cache) if args.audit_cache else None,
        audit_timeout_seconds=args.audit_timeout_seconds,
        generate_protocol=not args.no_protocol,
        generate_risks=not args.no_risks,
        run_challenge=not args.no_challenge,
        generate_notebook=not args.no_notebook,
        auto_view=auto_view,
        interactive=args.interactive,
        output_dir=Path(args.out) if args.out else Config().output_dir,
    )
    llm = get_adapter(args.llm, args.model)
    challenger_llm = None
    if config.run_challenge and args.challenger_llm:
        challenger_llm = get_adapter(args.challenger_llm, args.challenger_model)

    interaction_handler = None
    if config.interactive:
        from deltasci.interactive import TTYInteractionHandler
        interaction_handler = TTYInteractionHandler()

    reasoner = CoReasoner(
        pack=pack,
        llm=llm,
        config=config,
        challenger_llm=challenger_llm,
        interaction_handler=interaction_handler,
    )

    # Resolve the run dir. Two cases:
    # (1) --iterate-on <existing-run-dir>: archive existing → 09_iterations/v<n>/, reuse the dir.
    # (2) Default: <output_dir>/<timestamp>_<slug>/.
    from deltasci.layout import archive_to_iteration, read_idea_from_run_dir, timestamp_slug

    if args.iterate_on:
        run_dir = Path(args.iterate_on).resolve()
        if not run_dir.is_dir():
            print(f"error: --iterate-on path is not a directory: {run_dir}", file=sys.stderr)
            return 1
        # Allow user to omit --idea when iterating; pull from existing run dir.
        if not idea:
            existing_idea = read_idea_from_run_dir(run_dir)
            if existing_idea:
                idea = existing_idea
                print(f"(iterating with idea read from {run_dir / '00_idea.md'})")
            else:
                print("error: --iterate-on requires an existing 00_idea.md or --idea / --idea-file", file=sys.stderr)
                return 2
        archived = archive_to_iteration(run_dir)
        print(f"archived previous run into {archived.relative_to(run_dir)}/")
    else:
        base = Path(args.out) if args.out else Config().output_dir
        run_dir = base / timestamp_slug(idea)
    config.output_dir = run_dir

    print(f"deltasci {__version__} :: pack={pack.name} :: provider={llm.provider_name} :: model={llm.model_id()}")
    print(f"running {config.num_rounds}-round co-reasoning + protocol + risks{' + challenger' if config.run_challenge else ''} ...")

    result = reasoner.run(idea=idea)
    _write_outputs_staged(
        result, run_dir, idea, pack=pack, generate_notebook=config.generate_notebook
    )
    _print_summary(result, run_dir)

    if config.auto_view:
        _maybe_launch_view(run_dir)
    return 0


def _maybe_launch_view(run_dir: Path) -> None:
    """Best-effort auto-launch the web review surface."""

    import os
    import shutil
    import subprocess

    repo_root = Path(__file__).resolve().parents[2]
    web_dir = repo_root / "web"
    if not web_dir.is_dir() or not (web_dir / "node_modules").is_dir():
        print("(skipping auto-view: web/ not built — run `cd web && npm install` to enable)")
        return
    npm = shutil.which("npm")
    if not npm:
        print("(skipping auto-view: npm not on PATH)")
        return

    env = os.environ.copy()
    env["DELTASCI_RUN_DIR"] = str(run_dir.resolve())
    env["PORT"] = env.get("PORT", "3010")

    # Spawn detached so the run command returns control to the user.
    print(f"\nlaunching review surface at http://localhost:{env['PORT']}")
    print("(Ctrl-C in the spawned terminal to stop the dev server)")
    try:
        subprocess.Popen(
            [npm, "run", "dev"],
            cwd=str(web_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"(auto-view failed to spawn: {exc})")


def cmd_list_packs(args: argparse.Namespace) -> int:
    packs = list_packs()
    if not packs:
        print("(no built-in packs found)")
        return 0
    print(f"Built-in domain packs ({len(packs)}):")
    for name in packs:
        try:
            pack = load_pack(name)
            print(f"  {pack.name:<12} v{pack.version:<6} — {pack.display_name}")
        except Exception as exc:  # noqa: BLE001 - surface load errors per-pack
            print(f"  {name:<12}  (load error: {exc})")
    return 0


def cmd_show_pack(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)
    print(f"# {pack.display_name} ({pack.name}) v{pack.version}\n")
    print(pack.description)
    print()
    print(f"Scoring axes: {', '.join(pack.scoring_rubric.axes)}")
    print(f"Weights:      {pack.scoring_rubric.weights}")
    print()
    print("Evidence rules:")
    for rule in pack.evidence_rules:
        print(f"  - {rule}")
    print()
    print("Lens (excerpt):")
    print(_indent(pack.lens[:500] + ("..." if len(pack.lens) > 500 else ""), "  "))
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    pack = load_pack(args.pack)
    if not pack.example_idea:
        print(f"error: pack {pack.name!r} has no example_idea defined", file=sys.stderr)
        return 1

    config = Config(
        llm_provider=args.llm,
        num_rounds=4,
        require_falsifiability=False,
        require_epistemic_humility=False,
        audit_enabled=False,
        generate_protocol=False,  # mock-only demo skips protocol/risks/challenge
        generate_risks=False,
        run_challenge=False,
        auto_view=False,
        output_dir=Path(args.out) if args.out else Config().output_dir,
    )
    llm = get_adapter(args.llm, None)
    reasoner = CoReasoner(pack=pack, llm=llm, config=config)
    print(f"running demo for pack={pack.name} with provider={llm.provider_name}")
    print(f"idea: {pack.example_idea}\n")
    result = reasoner.run(idea=pack.example_idea)
    _write_outputs(result, config.output_dir)
    _print_summary(result, config.output_dir)
    return 0


def cmd_view(args: argparse.Namespace) -> int:
    """Open a DeltaSci run in the web review surface (deltasci/web/)."""
    import os
    import shutil
    import subprocess

    run_dir = Path(args.run_dir).resolve()
    if not run_dir.is_dir():
        print(f"error: {run_dir} is not a directory", file=sys.stderr)
        return 1
    for needed in ("transcript.md", "summary.json"):
        if not (run_dir / needed).is_file():
            print(f"error: {run_dir} is missing {needed}", file=sys.stderr)
            return 1

    repo_root = Path(__file__).resolve().parents[2]
    web_dir = repo_root / "web"
    if not web_dir.is_dir():
        print(
            f"error: web/ not found at {web_dir}\n"
            "deltasci view requires the source repo (web/ is not bundled in the pip package).",
            file=sys.stderr,
        )
        return 1
    if not (web_dir / "node_modules").is_dir():
        print(
            f"error: dependencies not installed in {web_dir}\n"
            f"run:  cd {web_dir} && npm install",
            file=sys.stderr,
        )
        return 1

    npm = shutil.which("npm")
    if not npm:
        print("error: npm not found on PATH", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["DELTASCI_RUN_DIR"] = str(run_dir)
    env["PORT"] = str(args.port)

    print(f"deltasci view: serving {run_dir}")
    print(f"  → http://localhost:{args.port}")
    print("(Ctrl-C to stop)\n")
    try:
        subprocess.run([npm, "run", "dev"], cwd=str(web_dir), env=env, check=False)
    except KeyboardInterrupt:
        pass
    return 0


def cmd_init_pack(args: argparse.Namespace) -> int:
    target = Path(args.path).resolve()
    if target.exists() and any(target.iterdir()):
        print(f"error: {target} already exists and is not empty", file=sys.stderr)
        return 1
    target.mkdir(parents=True, exist_ok=True)
    (target / "pack.toml").write_text(_PACK_TOML_TEMPLATE.format(name=args.name), encoding="utf-8")
    (target / "lens.md").write_text(_LENS_TEMPLATE.format(name=args.name), encoding="utf-8")
    print(f"scaffolded new domain pack at {target}")
    print("next: edit pack.toml and lens.md, then run:")
    print(f"  deltasci validate-pack {target}")
    return 0


def cmd_validate_pack(args: argparse.Namespace) -> int:
    try:
        pack = DomainPack.from_directory(args.path)
    except Exception as exc:  # noqa: BLE001 - validation surface
        print(f"INVALID :: {exc}", file=sys.stderr)
        return 1
    print(f"OK :: {pack.name} v{pack.version} loaded from {pack.source_path}")
    print(f"  display_name = {pack.display_name}")
    print(f"  axes         = {pack.scoring_rubric.axes}")
    print(f"  rules        = {len(pack.evidence_rules)}")
    print(f"  lens chars   = {len(pack.lens)}")
    if not pack.example_idea:
        print("  warning: no example_idea — `deltasci demo --pack` will not work")
    return 0


def _write_outputs(result, output_dir: Path) -> None:
    """Legacy flat-layout writer. Kept for back-compat with v0.1.x callers (e.g.,
    older generator scripts). New runs go through _write_outputs_staged."""

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "transcript.md").write_text(result.transcript.render_markdown(), encoding="utf-8")
    (output_dir / "hypothesis.md").write_text(
        _render_hypothesis_md(result.hypothesis, audit_report=result.audit_report),
        encoding="utf-8",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(
            {
                "hypothesis": result.hypothesis.model_dump(),
                "grounding": result.grounding_summary.to_dict(),
                "audit": result.audit_report.model_dump(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_outputs_staged(
    result,
    run_dir: Path,
    idea: str,
    *,
    pack=None,
    generate_notebook: bool = True,
) -> None:
    """v0.2.0 staged-layout writer: numbered subdirs per stage, top-level convenience copies.

    v0.3.0 adds optional 10_notebook/ generation when `pack` is provided and has a
    notebook.py template.
    """

    from deltasci.challenger import render_challenge_md
    from deltasci.layout import RunPaths
    from deltasci.notebook import generate_notebook_pack, pack_has_notebook_template
    from deltasci.protocol import render_protocol_md, render_risks_md

    run_dir.mkdir(parents=True, exist_ok=True)
    paths = RunPaths(run_dir)

    # 00_idea.md
    paths.idea_file().write_text(f"# Research idea\n\n{idea.strip()}\n", encoding="utf-8")

    # 01-04: per-round transcripts
    for entry in result.transcript.rounds:
        rd = paths.round_dir(entry.kind)
        if rd is not None:
            (rd / "transcript.md").write_text(entry.text.strip() + "\n", encoding="utf-8")

    # 05_synthesis: hypothesis + summary
    syn_dir = paths.stage("synthesis")
    rendered_hypothesis = _render_hypothesis_md(result.hypothesis, audit_report=result.audit_report)
    (syn_dir / "hypothesis.md").write_text(rendered_hypothesis, encoding="utf-8")

    summary_payload = {
        "hypothesis": result.hypothesis.model_dump(),
        "grounding": result.grounding_summary.to_dict(),
        "audit": result.audit_report.model_dump(),
    }
    if result.plan is not None:
        summary_payload["protocol"] = result.plan.model_dump()
    if result.risks is not None:
        summary_payload["risks"] = result.risks.model_dump()
    if result.challenge is not None:
        summary_payload["challenge"] = result.challenge.model_dump()
    (syn_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    # 06_protocol
    if result.plan is not None:
        proto_dir = paths.stage("protocol")
        (proto_dir / "protocol.md").write_text(render_protocol_md(result.plan), encoding="utf-8")
        (proto_dir / "experiment_plan.json").write_text(
            json.dumps(result.plan.model_dump(), indent=2), encoding="utf-8"
        )

    # 07_risks
    if result.risks is not None:
        risks_dir = paths.stage("risks")
        (risks_dir / "risks.md").write_text(render_risks_md(result.risks), encoding="utf-8")
        (risks_dir / "risk_register.json").write_text(
            json.dumps(result.risks.model_dump(), indent=2), encoding="utf-8"
        )

    # 08_audits: separate citation audit + codex challenge
    audit_dir = paths.stage("audits")
    (audit_dir / "citations.json").write_text(
        json.dumps(result.audit_report.model_dump(), indent=2), encoding="utf-8"
    )
    if result.challenge is not None:
        (audit_dir / "codex.json").write_text(
            json.dumps(result.challenge.model_dump(), indent=2), encoding="utf-8"
        )
        (audit_dir / "codex.md").write_text(render_challenge_md(result.challenge), encoding="utf-8")

    # 10_notebook (v0.3.0) — optional executable scaffold
    notebook_pack = None
    if generate_notebook and pack is not None and result.plan is not None and pack_has_notebook_template(pack):
        notebook_pack = generate_notebook_pack(
            pack=pack,
            hypothesis=result.hypothesis,
            plan=result.plan,
            run_dir=run_dir,
        )

    # Top-level convenience copies (web UI default-reads these)
    (run_dir / "transcript.md").write_text(result.transcript.render_markdown(), encoding="utf-8")
    (run_dir / "hypothesis.md").write_text(rendered_hypothesis, encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")

    # Top-level manifest pointing at all stages
    manifest = {
        "deltasci_version": result.hypothesis.metadata.deltasci_version,
        "pack": result.hypothesis.metadata.pack_name,
        "model": result.hypothesis.metadata.model,
        "stages": {
            "idea": "00_idea.md",
            "framing": "01_framing/",
            "engineering": "02_engineering/",
            "refinement": "03_refinement/",
            "plan": "04_plan/",
            "synthesis": "05_synthesis/",
            "protocol": "06_protocol/" if result.plan else None,
            "risks": "07_risks/" if result.risks else None,
            "audits": "08_audits/",
            "notebook": "10_notebook/" if notebook_pack else None,
        },
        "counts": {
            "evidence_well_covered": result.hypothesis.epistemic_summary.well_covered_count,
            "evidence_sparse": result.hypothesis.epistemic_summary.sparse_count,
            "knowledge_gaps": result.hypothesis.epistemic_summary.knowledge_gap_count,
            "novel_syntheses": result.hypothesis.epistemic_summary.novel_synthesis_count,
            "audit_verified": result.audit_report.verified_count,
            "audit_failed": result.audit_report.mismatch_count,
            "challenge_findings": len(result.challenge.findings) if result.challenge else 0,
            "notebook_cells": notebook_pack.cell_count if notebook_pack else 0,
        },
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _print_summary(result, output_dir: Path) -> None:
    h = result.hypothesis
    es = h.epistemic_summary
    audit = result.audit_report
    print()
    print(f"hypothesis: {h.title}")
    print(f"  overall feasibility:        {h.feasibility_scores.overall}")
    print(f"  well-covered claims:        {es.well_covered_count}")
    print(f"  sparse-coverage claims:     {es.sparse_count}")
    print(f"  knowledge gaps (researcher): {es.knowledge_gap_count}")
    print(f"  novel syntheses (verify):   {es.novel_synthesis_count}")
    print(f"  grounding violations:       {result.grounding_summary.total_violations}")
    print(f"  falsifiability threshold:   {h.falsifiability.threshold}")
    if result.plan is not None:
        print(f"  experiment plan:            {len(result.plan.steps)} steps · primary metric: {result.plan.primary_metric}")
    if result.risks is not None:
        sev_counts = {}
        for r in result.risks.items:
            sev_counts[r.severity] = sev_counts.get(r.severity, 0) + 1
        sev_str = " · ".join(f"{k}={v}" for k, v in sev_counts.items())
        print(f"  risks identified:           {len(result.risks.items)} ({sev_str})")
    if result.challenge is not None:
        print(f"  challenger findings:        {len(result.challenge.findings)} from {result.challenge.challenger_provider}/{result.challenge.challenger_model}")
    print(f"  {audit.banner()}")
    if audit.mismatch_count:
        print(f"  ⚠ {audit.mismatch_count} citation(s) FAILED AUDIT — see hypothesis.md 'Failed audit' section")
    if es.warnings:
        print("  warnings:")
        for w in es.warnings:
            print(f"    ! {w}")
    print()
    print(f"outputs written to: {output_dir.resolve()}")
    print(f"  - manifest.json                     (run-level metadata)")
    print(f"  - 05_synthesis/hypothesis.md        (top-level read also at hypothesis.md)")
    print(f"  - 05_synthesis/summary.json         (full schema dump; back-compat copy at summary.json)")
    if result.plan is not None:
        print(f"  - 06_protocol/protocol.md           (experiment plan)")
        print(f"  - 06_protocol/experiment_plan.json")
    if result.risks is not None:
        print(f"  - 07_risks/risks.md                 (risk register)")
        print(f"  - 07_risks/risk_register.json")
    print(f"  - 08_audits/citations.json          (citation audit results)")
    if result.challenge is not None:
        print(f"  - 08_audits/codex.json + .md        (adversarial challenge)")
    notebook_path = output_dir / "10_notebook" / "notebook.ipynb"
    if notebook_path.is_file():
        print(f"  - 10_notebook/notebook.ipynb        (executable scaffold — fill in TODOs)")
        print(f"  - 10_notebook/requirements.txt + README.md")


def _render_hypothesis_md(h, audit_report=None) -> str:
    lines = [f"# {h.title}", ""]
    if audit_report is not None:
        lines.append(f"> {audit_report.banner()}")
        if audit_report.mismatch_count:
            lines.append("> **⚠ One or more citations FAILED AUDIT — see the 'Failed audit' section below before relying on this hypothesis.**")
        lines.append("")
    lines.extend([h.statement, "", "## Domain grounding"])
    for k, v in h.domain_grounding.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Technical approach")
    for k, v in h.technical_approach.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("")
    lines.append("## Falsifiability")
    lines.append(f"- **prediction**: {h.falsifiability.prediction}")
    lines.append(f"- **threshold**: {h.falsifiability.threshold}")
    lines.append(f"- **null outcome**: {h.falsifiability.null_outcome}")
    lines.append("")
    lines.append("## Feasibility scores")
    for axis, score in h.feasibility_scores.scores.items():
        just = h.feasibility_scores.justifications.get(axis, "")
        lines.append(f"- **{axis}**: {score}/5 — {just}")
    lines.append(f"- **overall (weighted)**: {h.feasibility_scores.overall}")
    lines.append("")
    lines.append("## Evidence trail")
    well_covered = [ev for ev in h.evidence_trail if ev.coverage == "well-covered"]
    sparse = [ev for ev in h.evidence_trail if ev.coverage == "sparse"]

    lines.append("")
    lines.append("### AI-confident foundations (well-covered)")
    if not well_covered:
        lines.append("_(none)_")
    else:
        lines.append("| # | Type | Claim | Source |")
        lines.append("|---|------|-------|--------|")
        for i, ev in enumerate(well_covered, 1):
            claim = ev.claim.replace("|", "\\|")
            source = ev.source.replace("|", "\\|") or "—"
            lines.append(f"| {i} | {ev.type} | {claim} | {source} |")

    lines.append("")
    lines.append("### Likely-reliable, please verify (sparse coverage)")
    if not sparse:
        lines.append("_(none)_")
    else:
        lines.append("| # | Type | Claim | Source |")
        lines.append("|---|------|-------|--------|")
        for i, ev in enumerate(sparse, 1):
            claim = ev.claim.replace("|", "\\|")
            source = ev.source.replace("|", "\\|") or "—"
            lines.append(f"| {i} | {ev.type} | {claim} | {source} |")

    lines.append("")
    lines.append("### Researcher knowledge required")
    if not h.knowledge_gaps and not h.novel_syntheses:
        lines.append("_(none — but be wary: a hypothesis with zero researcher-required entries may be a hallucination signal)_")
    else:
        if h.knowledge_gaps:
            lines.append("")
            lines.append("**Knowledge gaps the AI flagged for researcher input:**")
            lines.append("")
            for i, gap in enumerate(h.knowledge_gaps, 1):
                lines.append(f"{i}. _({gap.category})_ {gap.question}")
        if h.novel_syntheses:
            lines.append("")
            lines.append("**Novel syntheses the AI is proposing (not stated by any single source):**")
            lines.append("")
            for i, syn in enumerate(h.novel_syntheses, 1):
                rationale = f" — _{syn.rationale}_" if syn.rationale else ""
                lines.append(f"{i}. {syn.proposed_connection}{rationale}")

    if audit_report is not None and audit_report.findings:
        lines.append("")
        lines.append("## Citation audit")
        verified = [f for f in audit_report.findings if f.status == "verified"]
        mismatches = [f for f in audit_report.findings if f.status == "mismatch"]
        skipped = [f for f in audit_report.findings if f.status == "skipped"]

        if verified:
            lines.append("")
            lines.append(f"### ✓ Verified ({len(verified)})")
            lines.append("| Auditor | AI claim | Verified record |")
            lines.append("|---------|----------|-----------------|")
            for f in verified:
                fm = f.fetched_metadata
                actual_summary = (
                    f"{fm.get('title', '') or fm.get('repo', '') or fm.get('id', '') or fm.get('accession', '')}"
                    f" — {fm.get('url', '')}"
                ).strip(" —")
                ai_claim = f.target_summary.replace("|", "\\|")
                actual = actual_summary.replace("|", "\\|") or "—"
                lines.append(f"| {f.auditor_name} | {ai_claim} | {actual} |")

        if mismatches:
            lines.append("")
            lines.append(f"### ✗ FAILED AUDIT ({len(mismatches)}) — likely hallucinated")
            lines.append("")
            lines.append("> These citations did not match the records at the cited identifiers. **Verify or remove before using this hypothesis.** This is the BioIntel-style failure mode the audit pillar exists to surface.")
            for i, f in enumerate(mismatches, 1):
                lines.append("")
                lines.append(f"**Failed audit #{i}** ({f.auditor_name})")
                lines.append("")
                lines.append(f"- **AI claimed:** {f.target_summary}")
                fm = f.fetched_metadata
                if fm.get("found") is False:
                    lines.append(f"- **Actual:** identifier not found in {f.auditor_name}.")
                else:
                    actual_bits = []
                    if fm.get("title"):
                        actual_bits.append(f"title={fm['title']!r}")
                    if fm.get("authors"):
                        actual_bits.append(f"first-author={fm['authors'][0]!r}")
                    if fm.get("year"):
                        actual_bits.append(f"year={fm['year']!r}")
                    if fm.get("journal"):
                        actual_bits.append(f"journal={fm['journal']!r}")
                    if fm.get("url"):
                        actual_bits.append(f"url={fm['url']}")
                    lines.append(f"- **Actual at identifier:** {', '.join(actual_bits) or '(no metadata returned)'}")
                if f.mismatch_reasons:
                    lines.append("- **Mismatch reasons:**")
                    for r in f.mismatch_reasons:
                        lines.append(f"  - {r}")

        if skipped:
            lines.append("")
            lines.append(f"### … Skipped ({len(skipped)})")
            lines.append("> Audit could not run for these (network error, timeout). Re-run audit with `deltasci audit <run-dir>`.")
            for f in skipped[:5]:
                reason = f.mismatch_reasons[0] if f.mismatch_reasons else ""
                lines.append(f"- {f.auditor_name}: {f.target_summary[:80]} — {reason}")

    lines.append("")
    lines.append("## Epistemic summary")
    es = h.epistemic_summary
    lines.append(f"- well-covered claims: **{es.well_covered_count}**")
    lines.append(f"- sparse-coverage claims: **{es.sparse_count}**")
    lines.append(f"- knowledge gaps flagged: **{es.knowledge_gap_count}**")
    lines.append(f"- novel syntheses proposed: **{es.novel_synthesis_count}**")
    if es.warnings:
        lines.append("")
        lines.append("**Warnings:**")
        for w in es.warnings:
            lines.append(f"- {w}")

    lines.append("")
    lines.append(f"_Generated by DeltaScience {h.metadata.deltasci_version} :: pack {h.metadata.pack_name} v{h.metadata.pack_version} :: {h.metadata.llm_provider}/{h.metadata.model}_")
    return "\n".join(lines)


def cmd_preflight(args: argparse.Namespace) -> int:
    """Static-analyze a notebook scaffold before executing it."""

    from deltasci.preflight import analyze_notebook

    target = Path(args.run_dir)
    # Allow pointing at a run dir OR directly at a .ipynb
    if target.is_dir():
        candidates = [
            target / "10_notebook" / "notebook.ipynb",
            target / "notebook.ipynb",
        ]
        nb_path = next((p for p in candidates if p.is_file()), None)
        if nb_path is None:
            print(f"error: no notebook.ipynb found in {target} (looked at 10_notebook/notebook.ipynb and notebook.ipynb)", file=sys.stderr)
            return 1
    elif target.suffix == ".ipynb" and target.is_file():
        nb_path = target
    else:
        print(f"error: {target} is neither a run dir nor a .ipynb file", file=sys.stderr)
        return 1

    report = analyze_notebook(nb_path)
    if args.json:
        print(report.to_json())
    else:
        print(report.render_terminal())
    return 1 if report.has_errors else 0


def cmd_discover_api(args: argparse.Namespace) -> int:
    """Launch headed Playwright, capture network traffic, identify data endpoints."""

    try:
        from deltasci.acquisition.discover_api import discover_api
    except ImportError as exc:
        print(
            f"error: deltasci.acquisition not available ({exc}). "
            "Install Playwright extras: pip install 'deltasci[discover]' && playwright install chromium",
            file=sys.stderr,
        )
        return 1

    out_dir = Path(args.out) if args.out else None
    try:
        result = discover_api(
            url=args.url,
            describe=args.describe,
            out_dir=out_dir,
            timeout_seconds=args.timeout_seconds,
        )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"\ncaptured {result['request_count']} network requests")
    print(f"  XHR/fetch:  {result['xhr_count']}")
    print(f"  identified endpoints: {len(result['endpoints'])}")
    print(f"\noutputs in {result['out_dir']}:")
    print(f"  - capture.json     (raw network log)")
    print(f"  - endpoints.json   (annotated candidates)")
    print(f"  - api_stub.py      (Python requests-based stub for the most-likely endpoint)")
    return 0


def cmd_marco_stratify(args: argparse.Namespace) -> int:
    """Pull MARCo cross-reactivity correlations stratified by patient
    demographics (sex / pregnancies / transplants / transfusions) via
    `/api/analyze`, with a min-N gate so underpowered cohorts surface as
    flagged rows instead of silently dropping."""
    import pandas as pd

    from deltasci.acquisition import (
        BY_PARITY_FEMALE, BY_SEX, BY_TRANSFUSION_LOAD, BY_TRANSPLANT_HISTORY,
        OVERALL, SENSITIZATION_ROUTES,
        MinNGate, StratumCache, pull_stratified, rows_to_dataframe,
    )

    pairs_csv = Path(args.pairs_csv)
    if not pairs_csv.is_file():
        print(f"error: {pairs_csv} not found", file=sys.stderr)
        return 1
    df = pd.read_csv(pairs_csv)
    if "allele1" not in df.columns or "allele2" not in df.columns:
        print(f"error: {pairs_csv} must have allele1 + allele2 columns", file=sys.stderr)
        return 1
    if args.limit:
        df = df.head(args.limit)
    pairs = list(zip(df["allele1"], df["allele2"]))

    sets = {
        "sensitization": SENSITIZATION_ROUTES,
        "sex": (OVERALL, *BY_SEX),
        "transplant": (OVERALL, *BY_TRANSPLANT_HISTORY),
        "parity": (OVERALL, *BY_PARITY_FEMALE),
        "transfusion": (OVERALL, *BY_TRANSFUSION_LOAD),
    }
    strata = sets.get(args.strata)
    if strata is None:
        print(f"error: unknown strata-set {args.strata!r}; pick from {list(sets)}", file=sys.stderr)
        return 1

    gate = MinNGate(
        min_total_samples=args.min_total,
        min_a1_positives=args.min_positives,
        min_a2_positives=args.min_positives,
    )
    cache = StratumCache(Path(args.cache_dir))

    print(f"=== deltasci marco-stratify  ({len(pairs)} pairs × {len(strata)} strata = "
          f"{len(pairs) * len(strata)} calls; min-N gate: total≥{args.min_total}, "
          f"each_pos≥{args.min_positives}) ===")
    rows = pull_stratified(pairs, strata, gate=gate, cache=cache,
                           workers=args.workers, progress_every=args.progress_every)
    out = rows_to_dataframe(rows)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"\nwrote {len(out)} rows → {out_path}")

    print("\nretained per stratum:")
    print(out.groupby("stratum")["retained"].value_counts().unstack(fill_value=0).to_string())
    print("\ncorrelation summary (retained rows only):")
    print(out[out["retained"]].groupby("stratum")["correlation"]
          .describe()[["count", "mean", "std", "min", "max"]].round(3).to_string())
    return 0


def cmd_compute_sa_positions(args: argparse.Namespace) -> int:
    """Compute per-locus solvent-accessible (SA) residue masks from public PDB
    structures via Biopython's Shrake-Rupley algorithm. Output is a JSON file
    consumed by the biomed-serology pack as a license-free proxy for HLA-EMMA's
    gated SA list.
    """
    from deltasci.structural import compute_all_loci, write_sa_positions_json

    loci, metadata = compute_all_loci(threshold_rel_sasa=args.threshold)
    out = Path(args.out) if args.out else None
    out_path = write_sa_positions_json(loci, metadata, out_path=out)

    print(f"=== deltasci compute-sa-positions  (threshold rel SASA ≥ {args.threshold:.2f}) ===")
    print(f"wrote {out_path}")
    print()
    for locus, sa in loci.items():
        print(f"  {locus:6s}  pdb={sa.reference_pdb:5s} chain={sa.chain_id}  "
              f"{len(sa.positions):>2d} / {sa.n_residues_evaluated} positions in β1")
    print()
    print("note: this is a DSSP-style SA *proxy*, NOT the HLA-EMMA mask. "
          "The downstream feature is named `dssp_sa_mismatch_count` to keep "
          "the comparability gap explicit.")
    return 0


def cmd_postexec(args: argparse.Namespace) -> int:
    """Walk an executed notebook + summary.json and write a post-execution
    update — measured metrics, risk-status badges, next-step status, new
    issues, and an Execution Update section appended to hypothesis.md."""
    from deltasci.postexec import analyze_run
    from deltasci.postexec.renderer import write_postexec_artifacts

    run_dir = Path(args.run_dir).resolve()
    if not (run_dir / "summary.json").is_file():
        print(f"error: {run_dir / 'summary.json'} not found", file=sys.stderr)
        return 1
    if not (run_dir / "10_notebook" / "notebook.ipynb").is_file():
        print(f"error: {run_dir / '10_notebook' / 'notebook.ipynb'} not found "
              "(no executed notebook to analyze)", file=sys.stderr)
        return 1
    report = analyze_run(run_dir)
    written = write_postexec_artifacts(run_dir, report)

    print(f"=== deltasci postexec — {run_dir.name} ===")
    print(f"measured metrics       : {len(report.metrics)}")
    print(f"risk statuses          : {len(report.risk_statuses)}  "
          f"(resolved: {sum(1 for r in report.risk_statuses if r.status == 'resolved')})")
    print(f"next-step statuses     : {len(report.next_step_statuses)}  "
          f"(done: {sum(1 for s in report.next_step_statuses if s.status == 'done')})")
    print(f"new issues surfaced    : {len(report.new_issues)}")
    print(f"achievements           : {len(report.achievements)}")
    print()
    print("wrote:")
    for p in written:
        print(f"  - {p.relative_to(run_dir.parent) if run_dir.parent in p.parents else p}")
    return 0


def cmd_diagrams(args: argparse.Namespace) -> int:
    """Generate mermaid diagrams (data-flow + protocol-sequence + optional schema)
    for an existing run dir, written to <run-dir>/12_diagrams/."""

    from deltasci.diagrams import STAGE_DIR, generate_diagrams
    from deltasci.protocol import ExperimentPlan

    run_dir = Path(args.run_dir).resolve()
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        print(f"error: {summary_path} not found", file=sys.stderr)
        return 1
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    plan_data = payload.get("protocol")
    if not plan_data:
        print(f"error: no 'protocol' section in {summary_path}", file=sys.stderr)
        return 1
    try:
        plan = ExperimentPlan.model_validate(plan_data)
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not parse experiment plan: {exc}", file=sys.stderr)
        return 1

    schema = None
    if args.schema:
        try:
            schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"warning: could not load schema {args.schema}: {exc}", file=sys.stderr)

    out_dir = run_dir / STAGE_DIR
    artifacts = generate_diagrams(plan, out_dir, graph_schema=schema)
    print(f"wrote {len(artifacts.written_paths)} diagram(s) to {out_dir}:")
    for p in artifacts.written_paths:
        print(f"  - {p.name}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Re-audit an existing run directory's evidence trail."""

    from deltasci.audit import MultiLayerAuditor
    from deltasci.audit.cache import AuditCache
    from deltasci.hypothesis import GroundedHypothesis

    run_dir = Path(args.run_dir).resolve()
    summary_path = run_dir / "summary.json"
    if not summary_path.is_file():
        print(f"error: {summary_path} not found", file=sys.stderr)
        return 1

    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    hypothesis_data = payload.get("hypothesis", {})
    try:
        hypothesis = GroundedHypothesis.model_validate(hypothesis_data)
    except Exception as exc:  # noqa: BLE001
        print(f"error: could not parse hypothesis schema in {summary_path}: {exc}", file=sys.stderr)
        return 1

    cache = AuditCache(Path(args.audit_cache) if args.audit_cache else None)
    auditor = MultiLayerAuditor(cache=cache)
    print(f"auditing {run_dir} ({len(hypothesis.evidence_trail)} evidence items) ...")
    report = auditor.audit(hypothesis.evidence_trail)
    print(report.banner())

    if report.mismatch_count:
        print()
        print("FAILED AUDIT details:")
        for f in report.findings:
            if f.status != "mismatch":
                continue
            print(f"  ✗ [{f.auditor_name}] AI claimed: {f.target_summary[:100]}")
            for r in f.mismatch_reasons:
                print(f"      → {r}")

    corroboration_payload: dict | None = None
    if getattr(args, "corroborate", False):
        from deltasci.audit.citations.corroboration import fetch_neighbors

        s2_findings = [
            f for f in report.findings
            if f.auditor_name == "semantic_scholar" and f.status == "verified"
        ]
        print(f"\ncorroborating {len(s2_findings)} verified Semantic Scholar findings (1-hop) ...")
        corroboration_payload = {}
        for f in s2_findings:
            paper_id = f.fetched_metadata.get("paper_id")
            if not paper_id:
                continue
            result = fetch_neighbors(paper_id, limit=int(args.corroborate_limit))
            corroboration_payload[paper_id] = result.to_dict()
            print(
                f"  {f.target_summary[:60]:<60s} "
                f"cites={result.citation_count}, refs={result.reference_count}"
                + (f", err={result.error}" if result.error else "")
            )

    if args.write:
        # Re-render hypothesis.md and rewrite summary.json with the fresh audit.
        payload["audit"] = report.model_dump()
        if corroboration_payload is not None:
            payload["corroboration"] = corroboration_payload
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        (run_dir / "hypothesis.md").write_text(
            _render_hypothesis_md(hypothesis, audit_report=report),
            encoding="utf-8",
        )
        print(f"\nupdated {summary_path} and {run_dir / 'hypothesis.md'}")

    return 0 if not report.mismatch_count else 2


def _read_text_input(args: argparse.Namespace) -> str | None:
    """Resolve --text / --file / stdin to text, or print an error and return None."""

    if args.text is not None:
        text = args.text
    elif args.file:
        if args.file == "-":
            text = sys.stdin.read()
        else:
            path = Path(args.file)
            if not path.is_file():
                print(f"error: file not found: {path}", file=sys.stderr)
                return None
            text = path.read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        print("error: provide --text, --file PATH, --pdf PATH, or pipe text on stdin", file=sys.stderr)
        return None
    if not text.strip():
        print("error: empty input", file=sys.stderr)
        return None
    return text


def _paper_failed(counts: dict) -> int:
    return counts.get("FABRICATED", 0) + counts.get("METADATA-MISMATCH", 0) + counts.get("UNSUPPORTED", 0)


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify citations/claims in ANY text, snippet or whole paper.

    Snippet mode (default): --text / --file / stdin → checks each cited identifier.
    Paper mode (--pdf PATH, or --paper on text input): parses the bibliography, resolves
    every reference, and verifies each citation in the context of the sentence citing it.
    Exit code 2 if anything fails audit.
    """

    from deltasci.audit import render_findings_md, render_findings_terminal
    from deltasci.audit.cache import AuditCache
    from deltasci.audit.intake import claims_from_source, detect_format, split_stats
    from deltasci.verify import verify_claims, verify_payload

    cache = AuditCache(Path(args.audit_cache)) if args.audit_cache else AuditCache()

    # --- paper mode: whole-document verification ------------------------------------
    if args.pdf or args.paper:
        from deltasci.paper import paper_payload, render_paper_terminal, verify_paper

        if args.pdf:
            from deltasci.paper import extract_pdf_text

            pdf_path = Path(args.pdf)
            if not pdf_path.is_file():
                print(f"error: PDF not found: {pdf_path}", file=sys.stderr)
                return 2
            try:
                text = extract_pdf_text(str(pdf_path))
            except RuntimeError as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2
            if not text.strip():
                print("error: no extractable text in PDF (scanned image?)", file=sys.stderr)
                return 2
        else:
            text = _read_text_input(args)
            if text is None:
                return 2

        llm = None
        if args.llm:
            try:
                from deltasci.llm import get_adapter

                llm = get_adapter(args.llm)
            except (RuntimeError, ValueError) as exc:
                print(f"warning: LLM fallback disabled ({exc})", file=sys.stderr)
        report = verify_paper(
            text,
            check_support=not args.no_support,
            cache=cache,
            max_references=args.max_references or None,
            llm=llm,
        )
        if args.json:
            print(json.dumps(paper_payload(report), indent=2))
        else:
            print(render_paper_terminal(report, show_passed=not args.quiet_passed))
        return 0 if not _paper_failed(report.counts()) else 2

    # --- snippet mode ---------------------------------------------------------------
    text = _read_text_input(args)
    if text is None:
        return 2

    try:
        claims = claims_from_source(text, fmt=args.format)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: could not parse input as {args.format!r}: {exc}", file=sys.stderr)
        return 2

    resolved_fmt = detect_format(text) if args.format == "auto" else args.format
    uncited_note = ""
    if resolved_fmt == "text":
        _cited, uncited = split_stats(text)
        if uncited:
            uncited_note = f"note: {uncited} sentence(s) had no verifiable identifier and were not checked."

    if not claims:
        if args.json:
            print(json.dumps({"verdicts": {}, "findings": [], "note": "no verifiable citations found"}, indent=2))
        else:
            print("no verifiable citations found in input.")
            if uncited_note:
                print(uncited_note)
        return 0

    report = verify_claims(claims, check_support=not args.no_support, cache=cache)

    if args.json:
        print(json.dumps(verify_payload(report), indent=2))
    elif args.markdown:
        print(render_findings_md(report))
        if uncited_note:
            print(f"\n_{uncited_note}_")
    else:
        print(render_findings_terminal(report, show_passed=not args.quiet_passed))
        if uncited_note:
            print(uncited_note)

    return 0 if not report.mismatch_count else 2


def _indent(text: str, prefix: str) -> str:
    return "\n".join(prefix + line for line in text.splitlines())


_PACK_TOML_TEMPLATE = """\
[meta]
name = "{name}"
display_name = "TODO: human-readable name"
version = "0.1.0"
description = "TODO: 1-2 sentence description of this scientific domain."
example_idea = "TODO: a canonical research idea for `deltasci demo --pack {name}`."

[[evidence_rules]]
type = "published-evidence"
source_pattern = "\\\\d{{4}}"  # require a 4-digit year in citations

[scoring_rubric]
axes = ["data_availability", "technical_feasibility", "domain_relevance", "novelty"]
weights = [1.0, 1.0, 1.5, 1.0]
"""


_LENS_TEMPLATE = """\
# {name} Lens

Describe how a senior researcher in this domain reasons about new ideas.
Use 4-6 sections with concrete bullet questions. Examples below.

## 1. Mechanism / first principles
- What underlying laws / processes govern this idea?
- What's well-established vs. contested in the field?

## 2. Data
- Which canonical datasets exist? Which are restricted?
- What systematic biases or gaps do they carry?

## 3. Methodology realism
- What's the smallest meaningful effect or improvement?
- What baselines are non-negotiable?

## 4. Validation pathway
- How will this be evaluated end-to-end?
- What would constitute a successful real-world demonstration?

## 5. Things to flag explicitly
- Domain-specific failure modes a generalist would miss.
- Common pitfalls that produce apparent-but-fake results.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deltasci",
        description="DeltaScience: two-perspective co-reasoning for AI4Science hypothesis generation.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"deltasci {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Run a 4-round co-reasoning session.")
    _add_run_args(p_run)
    p_run.set_defaults(func=cmd_run)

    p_list = sub.add_parser("list-packs", help="List built-in domain packs.")
    p_list.set_defaults(func=cmd_list_packs)

    p_show = sub.add_parser("show-pack", help="Show details of a domain pack.")
    p_show.add_argument("pack", help="Pack name or directory.")
    p_show.set_defaults(func=cmd_show_pack)

    p_demo = sub.add_parser("demo", help="Run the pack's example idea (uses --llm mock by default).")
    p_demo.add_argument("--pack", required=True)
    p_demo.add_argument("--llm", default="mock")
    p_demo.add_argument("--out", default=None)
    p_demo.set_defaults(func=cmd_demo)

    p_init = sub.add_parser("init-pack", help="Scaffold a new domain pack directory.")
    p_init.add_argument("name", help="Pack name (lowercase, hyphen-or-underscore).")
    p_init.add_argument("--path", default=None, help="Target directory (default: ./packs/<name>/).")
    p_init.set_defaults(func=lambda a: cmd_init_pack(_init_pack_args(a)))

    p_validate = sub.add_parser("validate-pack", help="Lint a domain pack directory.")
    p_validate.add_argument("path", help="Path to a domain pack directory.")
    p_validate.set_defaults(func=cmd_validate_pack)

    p_view = sub.add_parser(
        "view",
        help="Open a DeltaSci run in the web review surface (deltasci/web/).",
    )
    p_view.add_argument("run_dir", help="Path to a run output directory (must contain transcript.md + summary.json).")
    p_view.add_argument("--port", type=int, default=3010, help="Port for the dev server (default: 3010).")
    p_view.set_defaults(func=cmd_view)

    p_audit = sub.add_parser(
        "audit",
        help="Re-audit an existing run's citations against PubMed/Crossref/GitHub/etc.",
    )
    p_audit.add_argument("run_dir", help="Path to a run output directory containing summary.json.")
    p_audit.add_argument(
        "--write",
        action="store_true",
        help="Update summary.json + hypothesis.md in place with the fresh audit results.",
    )
    p_audit.add_argument("--audit-cache", default=None, help="Path to the audit cache JSON.")
    p_audit.add_argument(
        "--corroborate",
        action="store_true",
        help=(
            "After verifying citations, walk one citation hop on each verified paper via "
            "Semantic Scholar and write the citing/cited neighbors into summary.json under "
            "'corroboration'. Slower (rate-limited); opt-in."
        ),
    )
    p_audit.add_argument(
        "--corroborate-limit",
        type=int,
        default=10,
        help="Max citing/cited papers to fetch per verified paper when --corroborate is set (default: 10).",
    )
    p_audit.set_defaults(func=cmd_audit)

    p_verify = sub.add_parser(
        "verify",
        help=(
            "Verify citations/claims in ANY text (a pasted related-work section, a "
            "JSON list of claims, or a .bib file) — not just a DeltaScience run. "
            "Checks each cited PMID/DOI/arXiv/GitHub identifier exists, its metadata "
            "matches, and (by default) that the cited paper actually supports the claim."
        ),
    )
    src = p_verify.add_mutually_exclusive_group()
    src.add_argument("--text", default=None, help="Text to verify, inline.")
    src.add_argument("--file", default=None, help="Path to a file to verify (use '-' for stdin).")
    src.add_argument(
        "--pdf",
        default=None,
        help=(
            "Path to a PDF paper. Paper mode: parses the bibliography, resolves every "
            "reference, and verifies each citation in the context of the sentence citing "
            "it. Requires the PDF extra: pip install 'deltasci[pdf]'."
        ),
    )
    p_verify.add_argument(
        "--paper",
        action="store_true",
        help="Treat --text/--file/stdin as a whole paper (body + references), not a snippet.",
    )
    p_verify.add_argument(
        "--max-references",
        type=int,
        default=0,
        help="Paper mode: cap how many references to verify (0 = all). Useful for a fast "
        "first pass on a large bibliography against rate-limited APIs.",
    )
    p_verify.add_argument(
        "--llm",
        default=None,
        help="Paper mode: provider (anthropic|openai|auto) for the LLM fallback used when "
        "deterministic numbered-reference parsing comes up short (e.g., author-year citations). "
        "Verification of each citation stays deterministic. Requires a provider key.",
    )
    p_verify.add_argument(
        "--format",
        default="auto",
        choices=["auto", "tagged", "text", "records", "bibtex"],
        help=(
            "Input format. 'auto' (default) sniffs it: DeltaScience [CLAIM] tags, untagged "
            "prose, a JSON [{claim, source}] array, or BibTeX."
        ),
    )
    p_verify.add_argument(
        "--no-support",
        action="store_true",
        help=(
            "Disable the claim-to-abstract support check (existence + metadata only). "
            "Relaxes the gate: UNSUPPORTED findings won't be raised."
        ),
    )
    p_verify.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    p_verify.add_argument("--markdown", action="store_true", help="Emit a markdown report instead of terminal output.")
    p_verify.add_argument("--quiet-passed", action="store_true", help="Hide PASS findings in terminal output.")
    p_verify.add_argument("--audit-cache", default=None, help="Path to the audit cache JSON.")
    p_verify.set_defaults(func=cmd_verify)

    p_pre = sub.add_parser(
        "preflight",
        help="Static-analyze a run-dir's notebook scaffold for NameErrors / TODOs / placeholders / researcher gates before executing.",
    )
    p_pre.add_argument(
        "run_dir",
        help="Path to a run output dir containing 10_notebook/notebook.ipynb (or directly to a .ipynb file).",
    )
    p_pre.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON report instead of terminal-friendly summary.",
    )
    p_pre.set_defaults(func=cmd_preflight)

    p_disc = sub.add_parser(
        "discover-api",
        help="Launch a headed Playwright browser and capture XHR/fetch traffic while you interact, then identify the data-bearing endpoint and emit a Python `requests` stub.",
    )
    p_disc.add_argument("url", help="URL to open and capture network traffic against.")
    p_disc.add_argument(
        "--describe",
        default="",
        help="One-sentence description of what data you're trying to extract (e.g., 'per-allele-pair MFI Spearman correlation'). Helps the analyzer pick the right endpoint.",
    )
    p_disc.add_argument(
        "--out",
        default=None,
        help="Output dir (default: ./deltasci-discover/<timestamp>/). Writes capture.json + api_stub.py.",
    )
    p_disc.add_argument(
        "--timeout-seconds",
        type=int,
        default=300,
        help="Maximum browser session length in seconds (default: 300). Press Ctrl-C in the terminal to capture early.",
    )
    p_disc.set_defaults(func=cmd_discover_api)

    p_strat = sub.add_parser(
        "marco-stratify",
        help="Pull MARCo correlations stratified by patient demographics "
             "(sex / pregnancies / transplants / transfusions); min-N gate flags "
             "underpowered cohorts instead of silently dropping them.",
    )
    p_strat.add_argument("pairs_csv", help="CSV with allele1 + allele2 columns (e.g. data/marco_pairs.csv).")
    p_strat.add_argument("--strata", default="sensitization",
                          help="Pre-built stratum set: sensitization (default), sex, transplant, parity, transfusion.")
    p_strat.add_argument("--out", default="data/marco_strata.csv",
                          help="Output CSV path (default: data/marco_strata.csv).")
    p_strat.add_argument("--cache-dir", default="data/_marco_strata_cache",
                          help="Disk cache directory (default: data/_marco_strata_cache).")
    p_strat.add_argument("--limit", type=int, default=0,
                          help="Only pull the first N pairs (0 = all).")
    p_strat.add_argument("--workers", type=int, default=4, help="Concurrent HTTP workers (default 4).")
    p_strat.add_argument("--progress-every", type=int, default=100,
                          help="Print progress every N completed calls (0 to silence).")
    p_strat.add_argument("--min-total", type=int, default=100,
                          help="Min total sera per stratum to retain (default 100).")
    p_strat.add_argument("--min-positives", type=int, default=5,
                          help="Min positive samples per allele to retain (default 5).")
    p_strat.set_defaults(func=cmd_marco_stratify)

    p_sa = sub.add_parser(
        "compute-sa-positions",
        help="Compute per-locus solvent-accessible residue masks from public PDB "
             "structures (DSSP-style proxy for the gated HLA-EMMA SA mask).",
    )
    p_sa.add_argument(
        "--threshold",
        type=float,
        default=0.20,
        help="Relative-SASA threshold for marking a residue solvent-accessible (default: 0.20, Tien 2013 convention).",
    )
    p_sa.add_argument(
        "--out",
        default=None,
        help="Output JSON path (default: src/deltasci/structural/data/sa_positions_v1.json).",
    )
    p_sa.set_defaults(func=cmd_compute_sa_positions)

    p_post = sub.add_parser(
        "postexec",
        help="Walk an executed run-dir, extract measured metrics + risk-status, append an Execution Update to hypothesis.md.",
    )
    p_post.add_argument(
        "run_dir",
        help="Path to a run output dir containing summary.json + 10_notebook/notebook.ipynb (executed).",
    )
    p_post.set_defaults(func=cmd_postexec)

    p_diag = sub.add_parser(
        "diagrams",
        help="Generate mermaid diagrams (data-flow + protocol-sequence + optional schema) for an existing run-dir.",
    )
    p_diag.add_argument(
        "run_dir",
        help="Path to a run output dir containing summary.json with a `protocol` section.",
    )
    p_diag.add_argument(
        "--schema",
        default=None,
        help="Optional path to a JSON file describing an explicit graph schema (nodes, edges) to render alongside.",
    )
    p_diag.set_defaults(func=cmd_diagrams)

    return parser


def _init_pack_args(args: argparse.Namespace) -> argparse.Namespace:
    if not args.path:
        args.path = f"./packs/{args.name}"
    return args


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


_ = BUILTIN_PACK_NAMES  # keep symbol exported for users importing from cli
