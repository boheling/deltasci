# deltasci/web — auditable hypothesis review surface

A Next.js 15 review web app for DeltaSci co-reasoning runs. Loads one run's `transcript.md` + `summary.json` and renders it as an inspectable, four-section, human-in-the-loop review page.

The component layer is ported from [BioIntel](https://github.com/openLAIR/biointel)'s notebook + reproduction-scoreboard surfaces and adapted to DeltaSci's `EvidenceItem` / `KnowledgeGap` / `NovelSynthesis` schemas. Same visual DNA: cream / ink / teal / burgundy palette, Source Serif + IBM Plex Mono + Geist Sans, `<details>`-driven progressive disclosure, `<Section>` accent blocks for the human-in-the-loop panels.

## Quick start

```bash
# from the deltasci repo root
cd web && npm install
cd ..

# generate or pick a run output
python docs/examples/_generators/biomed_run.py

# launch the review surface pointed at that run
deltasci view docs/examples/biomed_run
# → http://localhost:3010
```

The `deltasci view <run-dir>` CLI command (added in `src/deltasci/cli.py`) sets `DELTASCI_RUN_DIR=<absolute path>` and spawns `npm run dev` in `web/`. The root page reads that env var (or falls back to the bundled `web/data/biomed_run/`).

## What gets rendered

For each run, the page surfaces these review sections:

| Section | Source | What you can do |
|---|---|---|
| Hypothesis statement + domain grounding | `summary.json#hypothesis.statement` + `domain_grounding` | See the load-bearing claim and its mechanism / unmet need / expected impact in one frame |
| Falsifiability clause | `summary.json#hypothesis.falsifiability` | Read the prediction, the threshold, and the null outcome — the things that would make you stop believing it |
| Technical approach | `summary.json#hypothesis.technical_approach` | Core method, key innovation, implementation path |
| Per-round transcript cells | `transcript.md` | Walk the dialogue round-by-round, role-tagged. Inline `[CLAIM]/[KNOWLEDGE_GAP]/[NOVEL_SYNTHESIS]` tags are stripped from prose and re-rendered structurally below |
| Evidence trail · AI-confident foundations | `evidence_trail` filtered to `coverage="well-covered"` | Audit the source on each claim |
| Evidence trail · Likely-reliable, please verify | `evidence_trail` filtered to `coverage="sparse"` | Specifics the AI hedged on — verify before relying on |
| Researcher knowledge required | `knowledge_gaps` | Each gap expands into a 4-section panel (why-flagged, fair-concern, expert-prompt, expert-persona) derived deterministically from the gap category |
| Novel syntheses | `novel_syntheses` | Connections the AI is proposing rather than citing — explicit "this needs verification" framing |
| Feasibility scorecard | `feasibility_scores` | Per-axis score bar + expandable justification |

## The auditable-component pattern

The shape that ports cleanly from BioIntel:

- **Cell** — section header + accent border + body slot. One per logical section of the page.
- **Code / Out / Note / Badge / RoleBadge / InlineBadge** — primitive content cells.
- **AuditableClaim** — one row per `EvidenceItem`, with coverage badge (teal=well-covered / burgundy=sparse) + type label + source link.
- **KnowledgeGapPanel** — `<details>` row per `KnowledgeGap`, expanding into the 4-section human-in-the-loop panel. The "judge's reasoning" analog from BioIntel is replaced here by a deterministic mapping from the AI's self-declared gap category (`lib/categoryGuidance.ts`).
- **NovelSynthesisCard** — the AI's leap, with a literal "AI's rationale" callout and a "this is a leap, not a citation — verify" footer.
- **FeasibilityRow / FeasibilityScorecard** — per-axis row with a 0–5 score bar + expandable justification.
- **EpistemicSummaryStrip** — the four global counts (well-covered / sparse / gaps / novel) + warnings, top-of-page.

Why this pattern. Most LLM hypothesis-generation UIs flatten the model's output into one confident voice. DeltaSci already preserves the underlying epistemic structure in its data model (`coverage`, `KnowledgeGap.category`, `NovelSynthesis.rationale`). All this UI does is *not throw that structure away*. Every claim shows its coverage. Every gap shows what the AI couldn't know and what kind of expert would close it. Every novel synthesis is explicitly framed as a leap. The reviewer can see the gaps as easily as the conclusions.

## Architecture

```
web/
  app/
    layout.tsx           # Source Serif + IBM Plex Mono + Geist Sans
    globals.css          # cream/ink/teal/burgundy tokens
    page.tsx             # main review page (reads $DELTASCI_RUN_DIR)
  components/
    notebook.tsx         # Cell, Code, Out, Note, NotebookHeader, Badge, RoleBadge, InlineBadge
    auditable.tsx        # AuditableClaim, KnowledgeGapPanel, NovelSynthesisCard, FeasibilityRow, EpistemicSummaryStrip, Section
  lib/
    types.ts             # TypeScript mirror of deltasci's Pydantic schemas
    loadRun.ts           # Reads transcript.md + summary.json from $DELTASCI_RUN_DIR
    categoryGuidance.ts  # Maps GapCategory → (whyFlagged, fairConcern, expertPrompt, expertPersona)
  data/
    biomed_run/          # Bundled default run (mirrors docs/examples/biomed_run/)
  package.json
  tailwind.config.ts
  tsconfig.json
  next.config.ts
```

## Roadmap

- **Multi-run browser** — `app/runs/[id]/page.tsx` for browsing across multiple runs in one directory tree (deferred — the CLI single-run flow is the v1 use case).
- **Inline tag rendering inside transcript prose** — currently tags are stripped to inner text. A future iteration could render claims/gaps/syntheses as inline pop-out chips inside the round body.
- **Custom expert-persona overrides** — `categoryGuidance.ts` ships defaults; users running their own runs may want to override the expert-persona suggestions per gap category.
- **PDF export** — a per-run PDF analog to BioIntel's hypothesis packet, useful for sharing a frozen review with collaborators.
- **Extracted shared component library** — once a third project (e.g. tx-workbench) needs the same components, factor out `glassbox-ui` (or similar) as a standalone npm package. Until then, copy-and-adapt is the right move.

## License

MIT — same as the parent deltasci project.
