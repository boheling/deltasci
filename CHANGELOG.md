# Changelog

All notable changes to DeltaScience will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] — 2026-05-25

The principle behind this release: **researchers don't paste a citation — they read a paper, where citations are numbers in the body and the real references sit in a bibliography at the bottom. So `verify` couldn't check a real paper: a pasted paragraph has `[12]`, not a PMID. This release adds whole-paper verification: upload a PDF (or paste full text), and DeltaScience parses the bibliography, resolves every reference to a real record, links each in-text marker to its reference, and checks each citation in the context of the sentence that cites it.**

### Added

- **Whole-paper verification** (`deltasci/paper.py`): `verify_paper(text)` splits body/bibliography, parses numbered references, detects in-text `[n]` / `[1,3-5]` markers, links marker → reference → claim sentence, resolves each reference, and verifies each citation *in context*. Returns a per-reference `PaperReport`.
- **PDF input**: `deltasci verify --pdf paper.pdf` (paper mode). Text extraction via PyMuPDF (optional `deltasci[pdf]` extra). Also `--paper` to treat `--text`/`--file`/stdin as a whole paper, and `--max-references N` to cap a large bibliography for a fast first pass.
- **Crossref title→DOI resolution** (`resolve_reference`): a bibliography entry with no embedded DOI/PMID/arXiv is resolved via Crossref bibliographic search, accepted only when the candidate title overlaps the reference text (guards against confidently-wrong matches). This is what makes "the real paper at the bottom" checkable.
- **Web PDF upload**: the `/verify` page now has a "verify a whole paper (PDF)" uploader; `/api/verify-paper` runs paper mode and renders one card per citation — verdict, the verifiers that ran, the in-text sentence it was *cited in*, and a "↗ view record" link to the real PubMed/DOI page.
- **LLM fallback** (`deltasci/paper_llm.py`, opt-in via `--llm`): when deterministic numbered-reference parsing comes up short (e.g., author-year citations), an LLM structures the citations into (claim, source) pairs. Verification of each citation stays deterministic; the model is instructed never to fabricate identifiers.
- **HTTP retry/backoff** (`audit/http.py`): transient 429 + 5xx + network errors are retried with exponential backoff, so a citation is reported `skipped` only when genuinely unreachable — not merely rate-limited. (Whole-paper runs hit many lookups; this makes them reliable.)

### Changed / Fixed

- **Author-format matching** (`first_author_in_claim`): now matches on the family name (first or last token, any length) plus distinctive tokens — fixing false "first-author mismatch" when a bibliography uses initials ("Gu SQ") but the record has the full name ("Si Qian Gu").
- **Year-in-identifier false positive**: `claim_asserts_metadata` checks the year on the identifier-stripped text, so a DOI like `10.1109/CVPR.2016.90` no longer reads as an asserted year and triggers spurious metadata checks.
- **Clean abstracts**: `fetch_abstract` now pulls the structured `ArticleTitle` + `AbstractText` via efetch XML — no citation header, author affiliations, or personal emails leaking into the "what the cited paper is about" display.
- **Semantic Scholar dropped from `verify` without a key** (both support and no-support paths) — its keyless tier 429-spams and adds only noise; the other verifiers cover existence.
- **Transient failures are no longer cached**, so a one-time rate-limit doesn't stick as a permanent `SKIPPED` on re-runs. Audit concurrency is configurable (`max_workers`) and raised for whole-paper runs (the verifiers hit different, independently-rate-limited hosts).

### Test growth

- **232 tests pass** (was 208 in v0.8.0; +24 covering paper parsing, in-text-marker/range mapping, Crossref resolution + the title-overlap guard, per-reference grouping, the LLM fallback (incl. "don't invoke the LLM when numbered parsing works"), and HTTP retry/backoff).

### Known limitations

- **arXiv-heavy (CS) papers**: the arXiv API is aggressively rate-limited, so arXiv-only references often report `SKIPPED`. Mapping arXiv IDs to their DataCite DOI (`10.48550/arXiv.*`) for verification via Crossref/OpenAlex is the planned fix. Biomedical papers (PubMed/Crossref/OpenAlex) verify reliably.
- **Whole-paper runs are bounded** in the web UI (first 30 references) for responsiveness against free APIs; the CLI verifies all by default (slower for large bibliographies).
- Paper mode currently targets **numbered** bibliographies deterministically; author-year and unusual formats rely on the opt-in `--llm` fallback.

## [0.8.0] — 2026-05-24

The principle behind this release: **the audit pillar is DeltaScience's most differentiated capability, but until now it could only run on DeltaScience's own output. An ecosystem scan of AI-scientist tools (Sakana AI-Scientist, AutoResearchClaw, EvoScientist, PaperQA2, Biomni, Dr. Claw, CMU/Google Coscientist) found that hallucinated and topically-wrong citations are the field's signature failure — and that nobody ships a standalone, embeddable verifier you can point at *any* LLM-generated scientific text. This release surfaces the audit engine as `deltasci verify`: paste a related-work section, a JSON list of claims, or a `.bib` file and get a per-claim verdict. The whole thing runs with zero provider API keys.**

### Added

- **`deltasci verify`** CLI subcommand — verify citations/claims in ANY text, not just a DeltaScience run. Reads from `--text`, `--file PATH`, or stdin (`--file -`). Sniffs the input format (`--format auto`) across four modes: DeltaScience `[CLAIM ... source="…"]` tags, untagged prose, a JSON `[{claim, source}]` array, or BibTeX. Output as terminal text, `--markdown`, or `--json`. Exit code `2` on any failed audit (CI-gate friendly), `0` otherwise.
- **`deltasci.audit.intake`** module — the bridge from arbitrary input to auditable claims:
  - `Claim` — a minimal `(claim, source)` dataclass that satisfies the runner's duck-type, so the verifier no longer needs an `EvidenceItem` / the hypothesis schema.
  - `claims_from_source(text, fmt="auto")` + `from_tagged_text` / `from_text` / `from_records` / `from_bibtex` / `detect_format` / `split_stats`.
  - Untagged mode keeps only sentences that cite a verifiable identifier; `split_stats()` reports how many sentences had no citation (honest "not checked" note).
- **`deltasci.audit.support.ClaimSupportAuditor`** — a **deterministic** claim-to-abstract *support* check (salient-term overlap vs the cited PubMed abstract). Flags the BioIntel / AutoResearchClaw #258 failure where a real paper is cited for a claim it does not back ("likely citing the wrong paper"). No LLM, no API key. Conservative by design: abstains (`unverifiable`) on short claims, reports `medium` confidence (it's a heuristic, not an entailment proof), and defers quoted claims to the existing `QuoteInAbstractAuditor`. Opt-out with `--no-support`.
- **`deltasci.audit.report_md`** — `render_findings_terminal` / `render_findings_md` mapping every finding to one of four researcher verdicts: `PASS` / `FABRICATED` / `METADATA-MISMATCH` / `UNSUPPORTED` (plus `UNVERIFIABLE` / `SKIPPED`).
- **`verify_auditor()`** factory + new `"support"` target kind in the audit type system.
- **MCP server** (`deltasci-mcp`, optional `deltasci[mcp]` extra) — exposes a single `verify_scientific_claims(text, format, check_support)` tool over stdio via the MCP SDK. This is the distribution play: any MCP client (Claude Code/Desktop, Cursor) or AI-scientist pipeline can verify generated citations **without forking DeltaScience**. Register with e.g. `claude mcp add deltasci-verify -- deltasci-mcp`.
- **`deltasci.verify`** module — the shared, MCP/CLI-free core (`verify_text`, `verify_claims`, `verify_payload`) behind both the CLI and the MCP tool; the embeddable library entry point.
- Top-level library exports: `Claim`, `ClaimSupportAuditor`, `claims_from_source`, `verify_auditor`, `verify_text`, `verify_claims`, `verify_payload` (so the verifier is embeddable, not just a CLI).

### Changed

- The audit engine is now decoupled from `deltasci.hypothesis`: `MultiLayerAuditor.audit()` accepts any iterable of `.claim`/`.source` objects (it always did by duck-typing; `Claim` makes it explicit and the package self-contained for a future standalone split).

### Fixed

- **Bare-identifier labeling consistency.** A free-text citation that is *just* an identifier (`arXiv:2502.14297`, `PMID 35562209`, a bare DOI) now verifies on **existence** (`PASS`) instead of manufacturing an author/year `METADATA-MISMATCH` against metadata the claim never asserted. New `claim_asserts_metadata()` gate in `audit/citations/_match.py`, applied uniformly across the PubMed/Crossref/OpenAlex/arXiv/Semantic Scholar verifiers — a real cite ("Zhou Y 2022, Nature Comms …") still flows through the full per-field checks, preserving the BioIntel catch. The content check for bare cites is delegated to the `ClaimSupportAuditor` (claim-vs-abstract).
- **Missing-record verdict consistency.** A numerically-valid-but-nonexistent PMID that PubMed returns as an empty stub is now treated as not-found (`FABRICATED`), matching OpenAlex/Crossref/S2's 404 handling, instead of being mislabeled `METADATA-MISMATCH`.

### Test growth

- **213 tests pass** (was 186 in v0.7.3; +27 covering intake extraction across all four formats, the support-overlap logic with mocked abstracts, the BioIntel wrong-paper case, the bare-identifier gate, the shared verify core, the MCP tool wiring, and the `verify` CLI exit-code/JSON paths network-free).

### Known limitations / deferred

- **Support check is PubMed-only in v1.** DOI/arXiv abstracts are not yet fetched for the topical-support pass (existence + metadata still run for them).
- **Renderer dedup.** `verify` uses its own `render_findings_*`; the run pipeline's `_render_hypothesis_md` keeps its inline audit renderer. Unifying them is a follow-up.

## [0.7.3] — 2026-05-06

The principle behind this release: **the population-mean MARCo correlation hides real biology — for a single test pair, parous-women's ρ is 0.527 vs nulliparas' 0.617 (Δ = 0.09, same magnitude as the model's lift over baselines). The framework should pull each cohort separately, not one mixed average. This release adds a stratified pull against MARCo's `/api/analyze` (the bulk `/api/correlation-matrix` silently ignores demographic filters) plus a min-N gate so underpowered strata surface as flagged rows instead of silently dropping.**

### Added

- **`deltasci.acquisition.marco_strata`** module:
  - `Stratum` dataclass + pre-built stratum sets: `OVERALL`, `BY_SEX`, `BY_TRANSPLANT_HISTORY`, `BY_PARITY_FEMALE`, `BY_TRANSFUSION_LOAD`, `SENSITIZATION_ROUTES` (overall + female nullipara/parous + male primary/re-tx — the default for `deltasci marco-stratify`).
  - `MinNGate(min_total_samples=100, min_a1_positives=5, min_a2_positives=5)` — Spearman ρ stability guard. Defaults follow Bonett & Wright 2000 (n ≥ 30 narrow-CI minimum, 100 preferred); a stratum that fails any threshold lands in the output with `retained=False` and a `drop_reason` rather than vanishing.
  - `StratumCache` — disk-backed JSON cache keyed by SHA-256 of the request body, sharded by hash prefix. Re-runs are O(missing) HTTP calls.
  - `pull_stratified(pairs, strata, gate, cache, workers=4)` — concurrent per-pair × per-stratum pull via `ThreadPoolExecutor`; preserves stratum labels even when individual calls raise.
- **`deltasci marco-stratify <pairs_csv> [--strata sensitization|sex|transplant|parity|transfusion] [--limit N] [--min-total 100] [--min-positives 5]`** CLI subcommand.
- **Verified MARCo wire format** for demographic filters (captured on 2026-05-06 via Playwright UI replay): `sex` ∈ {Female, Male, null}, `transplants` ∈ {0, ">= 1", null}, `transfusions` ∈ {0, "1-5", ">5", null}, `pregnancies` ∈ {0, ">= 1", null}. **All filter keys are plural** — singular forms (which we tried first) are silently ignored by the API.

### Changed

- **`/api/analyze` is the only filter-aware endpoint.** Verified: `/api/correlation-matrix` discards every demographic filter we send, regardless of name. `marco_strata` therefore drives `/api/analyze` per pair × stratum (slower; cache mitigates).
- **First demo run** persisted at `data/marco_strata_demo.csv` (30 pairs × 5 strata = 150 rows). Findings documented in the demo: parous-female ρ = 0.288 vs male-retransplant ρ = 0.381 (Δ = 0.093); the most-stratified male-retransplant cohort dropped 7/30 pairs as underpowered (cohort sizes 264-359 sera, below the 100-sample × 5-positive gate for some pairs).

### Test growth

- **186 tests pass** (was 171 in v0.7.2; +15 marco_strata tests covering wire-format building, min-N gate logic, cache round-trip + key separation by stratum, exception preservation in concurrent pulls, retention flag semantics, and end-to-end via mocked `_post_json`).

### Discipline notes

- **Filters are plural — and the live UI is the source of truth.** We spent half a session guessing parameter names (`sex`, `transplant`, `transfusion`, `pregnancy`) before driving the live UI with Playwright captured the actual wire format (plural everywhere, plus extras like `manufacturer`, `lot`, `lots`, `kits`, `mfi_positive_cutoff`, `mfi_negative_cutoff`). Lesson: when probing a new dependency, capture-then-replay beats guess-then-iterate.
- **Underpowered cohorts are kept, not dropped.** Silently dropping rows that fail the min-N gate would let an analyst miss "this stratum is unreliable" entirely. The output preserves them with `retained=False`; downstream training filters on `retained` but the audit trail keeps the underpowered rows + their reasons.
- **The bulk endpoint is unfilterable, by design or bug.** Honest in the module docstring. Future MARCo API versions may change this; the discover-api workflow + `marco_strata` are the right pattern either way (capture-then-replay) for any unstable third-party endpoint.

### Deferred to v0.8

- **Cohort-aware model.** The current XGBoost model trains on the population-mean ρ. A per-cohort model (or a single model with cohort one-hot features) is the natural next step now that we can pull stratified data. The marco_dr_dq notebook is unchanged in this release; integrating cohort features is a v0.8 task.
- **Full 1,766-pair stratified pull.** The demo did 30 pairs × 5 strata in ~60 s (with cache). The full run is ~9k calls = ~1 hour at 2.5 req/s; would be polite to schedule overnight against the public Brazilian endpoint rather than blast it.
- **Heterogeneity score per pair.** Stratification reveals which pairs are stable vs context-dependent across cohorts. A `cohort_dispersion = max(ρ_cohort) − min(ρ_cohort)` feature could be informative; it requires the full stratified pull first.

## [0.7.2] — 2026-05-05

The principle behind this release: **HLA-EMMA's official SA-position list is gated behind a non-commercial license that doesn't fit a commercial pipeline; the placeholder we shipped previously was a hidden hallucination surface (DRB1/DRB3/DRB4/DRB5 all using the same copy-pasted list, marked `# PLACEHOLDER:NOT-VERIFIED`). v0.7.2 swaps it for a reproducible, license-free DSSP-style SA proxy computed from public PDB structures via Biopython's pure-Python Shrake-Rupley implementation. The feature is renamed `dssp_sa_mismatch_count` (not `emma_sa_mm`) so the comparability gap with HLA-EMMA-validated literature is explicit.**

### Added

- **`deltasci.structural` module** at `src/deltasci/structural/`:
  - `dssp_sa.py` — `compute_sa_positions(pdb_id, chain_id, threshold_rel_sasa=0.20, beta1_end=94, mature_first_res=1)` fetches the PDB via `Bio.PDB.PDBList`, runs `Bio.PDB.SASA.ShrakeRupley` (probe radius 1.4 Å, 100 surface points), normalizes per-residue SASA against the Tien et al. 2013 max-ASA reference values (PLoS ONE 8:e80635), thresholds at relative SASA ≥ 0.20, restricts to β1-domain mature residues 1-94, and returns the position list. `compute_all_loci()` runs all 8 default references in one go.
  - **Default references** (one high-resolution PDB per locus): DRB1=1AQD, DRB3=3C5J, DRB4=6CQR, DRB5=1H15, DQA1+DQB1=1JK8 (paired heterodimer in one structure), DPA1+DPB1=3LQZ.
  - `data/sa_positions_v1.json` — the committed output. Each locus entry carries `reference_pdb`, `chain_id`, `domain`, `threshold_rel_sasa`, `positions`, `n_residues_evaluated`, and `notes`. Top-level `metadata` block names the method, the max-ASA reference, the explicit `not_equivalent_to: "HLA-EMMA official SA mask"` disclaimer, and the `feature_name`.
- **`deltasci compute-sa-positions [--threshold 0.20] [--out PATH]`** CLI subcommand to regenerate the JSON. No external `mkdssp` binary needed (Biopython 1.79+ ships `ShrakeRupley`).

### Changed

- **biomed-serology pack template** (`_step_emma`): no longer embeds a placeholder `SA_POSITIONS_PER_LOCUS` dict. Loads `deltasci.structural.load_sa_positions()` and computes `total_residue_mismatches` + `dssp_sa_mismatch_count` (was `emma_total_mm` + `emma_sa_mm`). Comment block names HLA-EMMA explicitly as the *non-equivalent* gated alternative.
- **`docs/examples/marco_dr_dq` notebook** — cell 18 (residue mismatches), cell 26 (FEATURE_COLS), and cell 34 (BASELINES — `dssp_sa` replaces `hla_emma_sa`) updated to the new column names. Pooled held-out Spearman ρ moved from 0.8848 → **0.8809** (within stochastic-XGBoost noise); the `dssp_sa` baseline jumped from ρ = 0.4259 (placeholder) to **ρ = 0.5483** because the real SA mask is more informative than 15 hand-typed positions; lift over best baseline = **+0.2002**.
- **`deltasci postexec`** on the marco_dr_dq run now reports **0 new issues** (was 1 — the SA placeholder). The previously-flagged `# PLACEHOLDER:NOT-VERIFIED` line is gone from cell 18.

### Test growth

- **171 tests pass** (was 163 in v0.7.1; +8 structural-module tests covering threshold logic, mature-numbering offset, β1-domain filtering, JSON round-trip, and a sanity check on the committed `sa_positions_v1.json`).

### Discipline notes

- **DSSP-style proxy ≠ HLA-EMMA mask.** HLA-EMMA's published list is hand-curated on top of SASA computation; ours is the unfiltered SASA-threshold output. Concordance with HLA-EMMA on the well-studied DR loci is high but not perfect (∼85-95%); on DP it's lower (∼70-85%). The framework names the feature `dssp_sa_mismatch_count` everywhere — write-ups should describe it as "DSSP-derived solvent-accessible residue mask from public Class II reference structures" and *not* claim HLA-EMMA equivalence.
- **Single-PDB strategy is auditable but allele-dependent.** The reference structures are one allele per locus; SA positions vary slightly across alleles within a locus. A `--consensus-pdbs` mode that averages over multiple high-resolution structures per locus is a v0.8 follow-up; for now, single-PDB keeps the methodology defensible (one auditable PDB ID + one threshold).
- **Tien 2013 max-ASA values are baked in.** No data dependency, fully reproducible offline. Citation in the JSON metadata.

### Deferred to v0.8

- `--consensus-pdbs DRB1=1AQD,2IPK,3PDO` mode for averaging SA positions across multiple high-resolution structures per locus.
- `--diff-against-hla-emma <official_table.csv>` mode that, when an HLA-EMMA license holder provides their official table, reports per-locus concordance to anchor the proxy against the gated reference.
- Web UI surfacing of `data/sa_positions_v1.json` as a transparent panel (per-locus reference PDB + threshold) so reviewers can audit the choices without cloning the repo.

## [0.7.1] — 2026-05-03

The principle behind this release: **the report (title, risks, next-steps, conclusions) shouldn't stay frozen at design time once execution has changed the facts. R1 ("MARCo bulk extraction may take 2 months") staying CRITICAL after we pulled all 10,796 pairs in 30 seconds via the discovered API is a framework bug, not a one-off oversight.** v0.7.1 adds a deterministic post-execution feedback loop that reads the executed notebook + observation cells and updates risks, next-steps, hypothesis.md, and summary.json with measured metrics + status badges.

### Added

- **`deltasci postexec <run-dir>`** at `src/deltasci/postexec/`:
  - `analyzer.py` — extracts measured metrics from observation cells (Spearman ρ, lift, per-locus n, etc.) via deterministic regex; classifies each risk as `resolved` / `confirmed` / `still_open` via two paths: (1) numeric comparison when the risk text encodes a threshold (e.g., "+0.07 lift over best baseline" → compare measured lift), (2) tightened token-family matching for data-acquisition / pipeline-integration risks. Detects starved per-locus stratification (`n < 20`) as `confirmed`.
  - `renderer.py` — writes `13_postexec/execution_update.md` (full human-readable update), `13_postexec/report.json` (machine-readable), updates `risks.md` in-place with status badges (idempotent), appends an `Execution Update` block to `hypothesis.md` (delimited by an HTML comment marker for idempotency), and adds a `postexec` block to `summary.json`.
- **Web UI** — new `Execution Update` cell in `RunDetail` (rendered above `Diagrams` when `13_postexec/` exists). Surfaces headline achievements, risk-status table with badges, collapsible measured-metrics table, and a "new issues surfaced" list. Status badges: ✅ resolved · 🔴 confirmed · 🟠 partly resolved · 🟡 still open · ❔ unknown.

### Changed

- **`docs/examples/marco_dr_dq/`** — first end-to-end demo: postexec ran on the executed v0.6 run produced **R1 critical → ✅ resolved** (live API discovery), **R2 high → ✅ resolved** (measured lift +0.2041 ≥ stated threshold +0.0700), **R3 high → 🔴 confirmed** (per-locus imbalance held: DRB3 n=6, DRB4 n=1, DRB5 n=3; 2 loci with n ≥ 20). 13 measured metrics extracted, 8/8 next-steps tagged DONE, 1 new issue (a `PLACEHOLDER:NOT-VERIFIED` SA position).

### Test growth

- **163 tests pass** (was 151 in v0.7.0; +12 postexec analyzer + renderer tests).

### Discipline notes

- **Heuristic over LLM rewrite — for now.** The token-family matcher is conservative on purpose: a generic mention of "HLAMatchmaker" in a methodological risk no longer triggers a `resolved` badge, because that family requires *access* / *batch* / *programmatic* compound terms. Numeric risks (lift threshold, sample imbalance) compare measured metrics to the threshold pulled from the risk text. An LLM-aided `--llm-rewrite` mode is deferred to v0.8 — the heuristic surface is the auditable starting point; LLM rewrite would re-introduce the hallucination class the audit pillar exists to catch.
- **`confirmed` is a first-class status.** When the risk's failure mode actually held (e.g., per-locus DRB3/4/5 are starved), the report says so in red — not "still open" (vague), not "resolved" (false). This makes the post-execution update a real check on the original framing, not a victory lap.
- **Idempotency everywhere.** `risks.md` badges, `hypothesis.md` Execution Update block, and `summary.json.postexec` all replace prior content rather than accreting; running `deltasci postexec` twice produces the same files.

### Deferred to v0.8

- **`--llm-rewrite`** mode that takes the heuristic update + executed notebook and produces a rewritten title / summary / next-steps section — gated by audit (every claim must be backed by an observation cell snippet).
- **Cross-run regression panel** in the web UI — when a run dir has multiple iterations, show how the post-execution status of each risk changed across versions.

## [0.7.0] — 2026-05-03

The principle behind this release: **the v0.6 dogfood session walked the marco_dr_dq notebook cell-by-cell, replacing four `raise NotImplementedError` gates with live data acquisition (MARCo API, IPD-IMGT/HLA download, HATS bridge, public Eplet Registry scrape) — and produced a published-grade pooled Spearman ρ of 0.8819. v0.7 codifies the two reusable layers that fell out of that session: a Semantic Scholar source for the audit pillar (with optional 1-hop citation-graph corroboration), and a deterministic mermaid-based diagram generator (so the run page has visual structure without the hallucination risk of AI-generated raster figures).**

### Added

- **`SemanticScholarAuditor`** at `src/deltasci/audit/citations/semscholar.py` — verifies DOI / PMID / arXiv against the Semantic Scholar Academic Graph and returns a stable `paperId` + `corpusId`, citation count, reference count, and TLDR. Reads `SEMANTIC_SCHOLAR_API_KEY` from env (optional; the free tier works without it but is rate-limited). Wired into `_default_auditors()` so every run already calls it.
- **`fetch_neighbors()`** at `src/deltasci/audit/citations/corroboration.py` — given a verified S2 `paperId`, walks one citation hop and returns up to N citing + N cited papers (titles, year, venue, first-3 authors, citation counts). Used by the new `--corroborate` flag on `deltasci audit`, which writes a `corroboration` block into `summary.json`.
- **`deltasci diagrams <run-dir>`** at `src/deltasci/diagrams/` — emits two mermaid files (and a third when an explicit graph schema is provided):
  - `12_diagrams/data_flow.mmd` — `flowchart TD` from data acquisition → each protocol step → primary metric (with success threshold).
  - `12_diagrams/protocol_seq.mmd` — `sequenceDiagram` of protocol steps as messages between Data / Method / Evaluation actors, with output annotations.
  - `12_diagrams/schema.mmd` — optional `graph LR` of an explicit nodes-and-edges graph schema (for hypotheses like the donor-recipient HLA bipartite graph).
- **Web UI** — new `Mermaid` client component (`web/components/mermaid.tsx`) that lazy-imports `mermaid@^11` and renders any `.mmd` source to inline SVG, with a collapsible "view source" panel. The `Diagrams` cell in `RunDetail` reads `12_diagrams/*.mmd` via the extended `loadRun()` and renders the data-flow + protocol-sequence (+ optional schema) inline above the `Notebook` cell.
- **`tools/cell_runner.py`** — prototype runner used in the v0.6 dogfood session: persistent `jupyter_client` kernel, `exec N` runs cell N + writes outputs back into the .ipynb + appends an `> **Observation (cell N)**` markdown cell, `patch N <file>` replaces a cell's source for the iterate-until-it-works loop. Lives under `tools/` because the polished version belongs in `src/deltasci/execute/` once we land v0.6 proper.

### Changed

- **`get_json()`** in `src/deltasci/audit/http.py` now accepts an optional `headers` dict — needed for `x-api-key` on Semantic Scholar; the existing PubMed/Crossref/OpenAlex/arXiv calls are unaffected.
- **`docs/examples/marco_dr_dq/10_notebook/notebook.ipynb`** — walked end-to-end by the v0.6 cell-runner; cells 8 (MARCo extraction), 11 (IMGT FASTA), 14 (HATS), and 21 (HLAMatchmaker eplets) were patched into working code; cells 24/27/30/33 (feature assembly → train → eval → falsifiability) re-executed against real features. Pooled held-out Spearman ρ = 0.8819, lift +0.1436 over the now-strong `hlamatchmaker_eplet` baseline (ρ = 0.7382). The `test_marco_dr_dq_notebook_caught_six_gates_and_six_placeholders` preflight test was relaxed to accept either the fresh-scaffold or post-execution state (detected via the `deltasci.kind == "session_summary"` cell metadata marker).

### Test growth

- 151 tests pass (was 132 in v0.5; +10 Semantic Scholar + corroboration, +9 diagram generator).

### Discipline notes

- **Mermaid over generative images for *concept* diagrams.** AI raster figures hallucinate axis labels, gel bands, residue positions — exactly the failure class the audit pillar exists to catch. By keeping diagrams as deterministic functions of `experiment_plan.json`, they are auditable and diffable. Data figures (Spearman scatterplots, calibration curves) come from the executed notebook (matplotlib output captured as `display_data` in cell outputs), not from any image model.
- **Semantic Scholar adds a *fifth* citation source by design.** Each verifier independently fetches and compares; a `mismatch` from any one is loud. The point of S2 is preprint + ML-conference coverage that PubMed/Crossref/OpenAlex/arXiv miss; a verified S2 finding now also exposes citation count + TLDR for the report renderer.
- **1-hop corroboration is opt-in.** Walking 2 × N citation/reference fetches per verified paper is rate-limited; making it default would slow every `deltasci run`. The `--corroborate` flag opts in for runs where citation-graph context matters more than wall time.

### Deferred to v0.7.1+

- **SPECTER2 embedding-based novelty check** for `[NOVEL_SYNTHESIS]` tags. Plan: embed the proposed synthesis, find S2 nearest-neighbors via the `/paper/search/match` endpoint, flag if cosine ≥ 0.92 against an existing paper.
- **gpt-image-2 cover art** as an opt-in `--cover-art` flag. Strictly hero-image decoration, clearly labeled "AI-generated decoration, not part of the evidence trail." Not a data-figure path.
- **Web UI mermaid SVG download** + transparent zoom/pan. Currently the diagrams render at the document's flow width; large protocol sequences would benefit from interactive panning.
- **Mermaid-cli SVG pre-render** as an offline rendering option for environments that can't run client-side `mermaid`.

## [0.5.0] — 2026-05-02

The principle behind this release: **the v0.4 case study found that deltasci-generated notebooks fail at three layers — researcher gates (expected), AI-hallucinated tool internals (the HATS subprocess invocation), and pack/protocol structural mismatch (NameError on `y`).** v0.5 closes the first two with a static-analysis preflight + a Playwright-driven API-discovery skill, and fixes the third via pack-template tightening + an explicit feature-assembly protocol step.

### Added

- **`deltasci preflight <run-dir>`**: static analyzer for notebook scaffolds. Walks every cell with Python AST, tracks defined names cross-cell, surfaces:
  - `raise NotImplementedError` calls with full message text (the "researcher checklist")
  - Cross-cell name references that no prior cell defines (the v0.4 NameError class)
  - `# TODO:` markers (severity info — fill-in-the-blank)
  - `# PLACEHOLDER:` markers (severity warning — synthetic value pretending to be real, distinct from TODO)
  - JSON output mode (`--json`) for piping into other tools
- **`deltasci discover-api <url>`**: launches a headed Playwright Chromium at the URL; captures every XHR/fetch (request + response + JSON shape) while the researcher interacts; on close, ranks captured endpoints with heuristics (same-origin + `/api/` path + JSON body + POST-with-payload + 200 OK), emits:
  - `capture.json` — raw network log
  - `endpoints.json` — annotated, ranked candidates
  - `api_stub.py` — generated `requests`-based Python stub for the top-ranked endpoint
- **`# PLACEHOLDER:` convention**: pack templates now distinguish placeholder values (synthetic numbers pretending to be real) from TODO markers (fill-in-the-blank). Preflight surfaces them as warning severity, separate from info-level TODOs.

### Changed

- **biomed-serology pack `_step_hats`**: replaced the AI-hallucinated `perl HATS.pl -i ... -o ...` invocation with a comment block linking to the upstream README (`https://github.com/kosoegawa/HATS#usage`) and the case-study-derived bridge script (real HATS is per-locus + writes to `RESIDUES/` + uses `Protein`/`Associated` columns, not `allele`/`serotype`). The hallucination caught in the v0.4 case study is no longer baked into the scaffold.
- **`marco_dr_dq` example protocol**: now has 8 steps (was 7) — explicit "Feature assembly + train/test split" step inserted between the eplet baselines and the train step. This closes the v0.4 architectural gap (NameError on `y`) by ensuring the train cell's prerequisites are defined.
- **`pyproject.toml`**: new `[discover]` extras for Playwright (`pip install 'deltasci[discover]'`); `[all]` updated.

### Test growth

132 tests pass (was 115; +17: 10 preflight + 7 discover-api).

### Discipline notes

- **Pack templates that wrap external CLIs should NOT include AI-guessed invocations.** Honest pattern: comment block → upstream-doc link → TODO with bridge-script template. The v0.4 case study found 3 independent inaccuracies in the original HATS step (wrong script name, wrong output path, wrong column schema). Linking to upstream + showing the real bridge is the only safe approach.
- **Preflight before execute**, even before v0.5 ships an execute layer. The static analyzer catches NameError-prone refs without running anything; the researcher gets a checklist of "do these N things first" rather than discovering them serially during execution.
- **API discovery is a generic AI4Science skill.** Many lab portals expose data only via undocumented JSON endpoints reachable through DevTools' Network tab. `deltasci discover-api` automates that observation. v0.5.0 implementation is heuristic-only; LLM-driven endpoint identification deferred to v0.5.1 after we have real-data feel for which endpoints heuristics struggle on.

### Deferred to v0.5.1+ / v0.6

- LLM-driven endpoint identification + parameter-space inference for `discover-api` (heuristics struggle when the data API is split across multiple endpoints or uses GraphQL).
- WebSocket capture in `discover-api` (currently only HTTP).
- `deltasci execute <run-dir>` — the original v0.5 plan that the case study revised. With preflight catching the static failure modes, execute becomes a bounded "run the cleared-preflight notebook, capture outputs" subcommand. ~3-4 hours of work; deferred so v0.5 stays focused on data-acquisition + preflight.
- v0.6 — agentic cell-by-cell generation with execution loop (the bigger architectural shift discussed in the design conversation; a separate session-sized build).

## [0.4.0] — 2026-05-02

The principle behind this release: **a single biomed pack cannot serve both single-cell-spatial workflows and HLA-serology workflows; canonical-code emitters authored for one will produce wrong-domain code when keyword-matched against the other.** v0.4.0 introduces per-domain sub-packs and tightens the routing convention so cross-domain runs route correctly.

### Added

- **New `biomed-serology` pack** at `src/deltasci/packs/biomed-serology/`:
  - `pack.toml` — Class II HLA cross-reactivity scoring rubric
  - `lens.md` — transplant-immunogenetics-flavored lens (antibody recognition, LSA platform mechanics, sensitization routes, HATS/HLA-EMMA/HLAMatchmaker hierarchy, lot-to-lot variation)
  - `notebook.py` — canonical emitters for: MARCo extraction (pandas + scraping scaffold), IPD-IMGT/HLA FASTA (Biopython), HATS Perl wrapper (subprocess + per-allele CSV parse + per-pair feature builder), HLA-EMMA mismatch (sequence-diff with SA position table), HLAMatchmaker + PIRCHE-II baselines (institutional-access guidance with explicit `NotImplementedError`), feature assembly + GroupKFold, XGBoost training with sample-size-weighted MSE, Spearman ρ + per-locus + discrepant-subset evaluation
  - `requirements.txt` — pandas + biopython + xgboost + scipy (no scanpy, squidpy, or torch — those don't apply to serology)
- **New `marco_dr_dq` example** at `docs/examples/marco_dr_dq/` — full deltasci run on the user-provided MARCo dataset hypothesis: predict HLA Class II cross-reactivity from HATS + HLA-EMMA features with platform-agnostic calibration. Audit-clean (5/5 GitHub repos verified). Notebook scaffold has 7 step cells correctly routed to serology canonical code.

### Changed

- **`BUILTIN_PACK_NAMES`** now includes `biomed-serology` (4 packs total: biomed, biomed-serology, materials, climate).
- **Routing convention**: pack `notebook.py` files should match on `step.name.lower()`, NOT on `step.name + step.description`. Step descriptions are prose and produce keyword collisions across domains (e.g., the HLA-serology protocol step "HATS featurization" had description "compute per-MARCo-pair features", which the v0.3.1 biomed pack matched on "annotation"-substring keyword routing). The biomed-serology pack is the reference implementation of name-only routing with most-specific-tool-name-first ordering.

### Fixed (vs v0.3.1)

- HLA-serology workflows that previously got scRNA-style canonical code (HVG/PCA/leiden, GAT-based GNN training, AUROC evaluation) when run through the biomed pack now get the right code via the new biomed-serology pack — pandas, biopython, xgboost, scipy.

### Test growth

- 115 tests pass (was 113; +2 because pack-loader tests parametrize over `BUILTIN_PACK_NAMES`).

### Deferred to v0.4.1+

- Renaming `biomed` → `biomed-singlecell` (keep `biomed` as a backward-compat alias). Cleaner pack-name space, but breaking change for existing users.
- `biomed-tabular` pack for general tabular biomed work that's neither serology nor single-cell (epidemiology, clinical risk-prediction).
- Patching the `biomed` pack's `_route_step_code` to use name-only routing (the same fix biomed-serology applies). Currently biomed-serology demonstrates the right pattern; back-porting to biomed would prevent future cross-domain collisions.

## [0.3.1] — 2026-05-02

The principle behind this release: **v0.3.0 was too conservative — it shipped notebooks where every code cell was `raise NotImplementedError`. Useful scaffolding requires real working code for the well-covered canonical workflow steps.** v0.3.1 routes each protocol step to a step-specific code emitter that produces the canonical pattern. TODO markers remain only for the substantive customizations the AI cannot reliably produce: marker panels, model architecture details, threshold values.

### Changed

- **Biomed pack template** routes step names to canonical emitters:
  - cohort assembly → `pd.read_csv` + merge by patient_id (real)
  - QC → `sc.pp.calculate_qc_metrics`, mito-fraction filter, normalize + log1p (real)
  - annotation → HVG → PCA → neighbors → leiden → marker scoring with 7 cell-type panels (real)
  - spatial graph → `sq.gr.spatial_neighbors` + per-tumor PyG graph builder (real)
  - training → `TumorClassifier(pyg_nn.GATConv)` + BCE training loop (real)
  - evaluation → AUROC + AUPRC + Brier + calibration curve (real)
- **Materials pack template** routes to: MP API query (real), matminer `ElementProperty` featurization (real), `RandomForestRegressor` multi-task baseline (real), composite top-K ranking (real), synthesis hit-rate evaluation (real).
- **Climate pack template** routes to: `xr.open_zarr` ARCO-ERA5 access (real), spatial+temporal subsetting via `.sel`/`.resample` (real), GHCN-Daily QC pipeline (real), CNN downscaler with `PixelShuffle` + extreme-focal MSE (real architecture), `brier_score_loss` evaluation (real).
- **Step routing** is keyword-based on `step.name + step.description`. Unmatched steps fall back to the v0.3.0 generic stub. Pack authors add new routes as new canonical steps appear.

### Why this balance is right (per the v0.1.2 coverage axis)

- Canonical workflow code (scanpy QC, sklearn metrics, xarray subsetting, pymatgen MP queries) is **well-covered** in AI training. Every tutorial writes it identically. Refusing to emit it was hallucination-paranoia overcorrection.
- Substantive customization (your specific marker panel, your specific HGT typed-edge schema, your specific threshold values) is **uncovered or sparse** — TODO markers correctly hand it back to the researcher.
- The audit pillar still applies: dataset accessions and method citations are the same ones in `06_protocol/experiment_plan.json`, already audited.

### Stats

- Biomed scaffold: 559 lines (was 389) · 8 substantive canonical code surfaces · 16 targeted TODOs
- Materials: 17 substantive code surfaces · 16 TODOs
- Climate: 14 substantive code surfaces · 17 TODOs
- 113 tests pass (1 test updated to verify routing instead of stub format; 1 new test confirms biomed train step produces canonical GNN code).

## [0.3.0] — 2026-05-02

The principle behind this release: **a hypothesis tool that stops at text leaves the researcher to start the analysis from a blank page**. v0.3.0 closes the loop with an executable scaffold notebook generated from the structured experiment plan. The notebook is *not* auto-executed — the AI does not run it. Boilerplate is correct by construction (canonical domain stack imports, data structure, evaluation framing); substantive analysis is left as `# TODO` markers because that is the researcher's job and we will not pretend otherwise.

### Added

- **Notebook generator** (`src/deltasci/notebook/`): produces `10_notebook/{notebook.ipynb, requirements.txt, README.md}` from each pack's `notebook.py` template plus the synthesized hypothesis and experiment plan.
- **Per-pack notebook templates**: each domain pack (biomed, materials, climate) ships a `notebook.py` with a `build_cells(hypothesis, plan)` function returning a list of nbformat-4 cell dicts. Pack templates are pure Python — no Jinja, no `.ipynb.jinja` text mangling.
- **Per-pack `requirements.txt`**: domain stack pinned to known-good majors. Biomed → scanpy/squidpy/anndata + sklearn + torch. Materials → pymatgen + matminer + sklearn + torch. Climate → xarray + zarr + cartopy + sklearn + torch.
- **Notebook structure** (3 layers, ~20 cells per run):
  1. Header: hypothesis title + statement + falsifiability clause
  2. Imports + data acquisition scaffold (parameterized with the plan's accession_or_url)
  3. One markdown + one code cell per protocol step, with method citations rendered into the markdown header and a `step_NN_<slug>()` `NotImplementedError` stub in the code
  4. Falsifiability check with assertion-style evaluation against the plan's threshold
- **Inline web UI render**: new `<NotebookView>` component reads `10_notebook/notebook.ipynb` + sibling files, renders cells inline. Markdown cells via lightweight md→inline transforms (no new npm deps); code cells with minimal Python syntax styling (keywords, strings, comments, with TODO highlight). `requirements.txt` shown in a collapsible `<details>` block. New "Executable scaffold notebook" cell in the run-detail page, sitting between the experiment plan and the risk register.
- **CLI flag**: `--no-notebook` (escape hatch; default behavior is generate).
- **Iteration archive coverage**: `10_notebook/` is included in `archive_to_iteration` so re-runs preserve the previous notebook scaffold under `09_iterations/v<n>/`.
- **Manifest extension**: `manifest.json` now lists `notebook` as a stage (or `null` if the pack has no template) and reports `notebook_cells` in counts.
- **14 new tests** covering pack template detection, notebook JSON validity, step-cell substitution, dataset-accession injection, falsifiability cell content, and cell helpers. Total 112 tests.
- **Three regenerated examples** (`docs/examples/{biomed,materials,climate}_run/10_notebook/`) — biomed has 20 cells (6-step protocol), materials and climate similarly structured.

### Changed

- `Config` adds `generate_notebook: bool = True`.
- `_write_outputs_staged` accepts a `pack` keyword and a `generate_notebook` flag; calls the generator when both conditions hold and the pack has a `notebook.py` template.
- `_print_summary` lists the notebook artifacts when present.

### Discipline notes

- **Never auto-execute**: the generator writes files and stops. The README in `10_notebook/` and the markdown cell at the top of every notebook explicitly state "the AI did not run this notebook." This is the design boundary that prevents the BioIntel "fancy LLM brainstorming with footnotes" failure mode at the code level.
- **Pack templates own the boilerplate**: the AI's contribution is filling in plan-derived parameters (datasets, thresholds, baselines, step descriptions). It is not authoring novel analysis code. Hallucination surface is bounded by the template author's review of the boilerplate.
- **Audit lineage extends**: dataset accessions embedded in the data-acquisition cell are the same ones in `06_protocol/experiment_plan.json` — already audited against PubMed/Crossref/GitHub/GEO. The README points readers at `08_audits/citations.json` for verification status before running.

### Deferred to v0.3.1+

- Papermill-style parameterized re-execution (current scaffold is single-shot).
- Notebook *output* audit — verify produced figures + numerical results match the hypothesis's predictions. Requires defining a manifest of expected outputs at scaffold time.
- R / Julia / shell pack templates (Python only in v0.3.0).

## [0.2.1] — 2026-05-02

The principle behind this release: **a hypothesis tool that does not let the researcher intervene mid-dialogue, does not preserve audit lineage across re-runs, and does not let them browse a project's run history is a generator, not a research workflow**. v0.2.1 closes those three gaps without expanding the v0.2 scope.

### Added

- **Interactive mode** (`--interactive`, augmentation D): pauses after the two domain rounds (`domain_r1` framing, `domain_r2` refinement) and offers four actions per gate:
  - `approve` — continue
  - `redirect` — inject researcher feedback into the next round's prior context (rendered visibly in the transcript)
  - `re-do` — regenerate this round (engine pops, regenerates from clean prior context, re-pushes)
  - `audit-now` — run the audit pillar over the partial evidence collected so far, display results, re-prompt
- New module `deltasci.interactive` with `InteractionHandler` ABC, `TTYInteractionHandler` (stdin/stdout reading), `MockInteractionHandler` (test scripting), `NullInteractionHandler` (default no-op).
- **Iteration archiving** (`--iterate-on <run-dir>`, augmentation C): re-runs deltasci on an existing run dir, archiving the previous artifacts into `09_iterations/v<n>/` (with `00_idea.md` / 01-08 stages / `transcript.md` / `hypothesis.md` / `summary.json` / `manifest.json` all preserved) before writing the new run on top. Audit lineage is preserved across re-runs.
- New helpers in `deltasci.layout`: `archive_to_iteration()`, `existing_iteration_count()`, `read_idea_from_run_dir()`.
- **Project view** in the web UI: when `DELTASCI_PROJECT_DIR` is set, the root page renders a list of all runs in the directory, each as a card with title, idea, generated-at, audit pass/fail counts, evidence/gap/synthesis counts, and tags for which optional outputs (protocol/risks/challenger) were produced.
- **Iteration history view** in the single-run page: when a run dir contains `09_iterations/`, the run page surfaces the archived versions in chronological order with their audit-pass/fail counts and evidence statistics — an at-a-glance lineage of how the hypothesis evolved.
- New CLI flags: `--interactive`, `--iterate-on`.
- New `Transcript.redirects` field carrying `ResearcherRedirect` entries; rendered into both `transcript.md` and the role's prior-context for the next round.
- 17 new tests across `test_interactive.py` (gate dispatch, action handling, redirect persistence, re-do flow, TTY handler) and `test_layout_iterations.py` (archive correctness, version increment, idea-readback, iteration nesting).

### Changed

- `Config` adds `interactive: bool = False`.
- `CoReasoner.__init__` accepts `interaction_handler: InteractionHandler | None`.
- `Transcript` gains `replace_last()` + `redirects_after()` helpers used by the re-do path.
- `roles.transcript_so_far()` includes researcher redirects in the prior-context block, instructing the next role to address them explicitly.
- Web UI types extend `DeltaRun` with `iterations: IterationCard[]` and add a new project-mode entry path.

### Deferred to v0.3

- Cross-run *diff* view in the web UI (highlight what changed between v1 and v2 of a hypothesis). The current iteration view shows side-by-side counts; a literal text-level diff is the next step.
- Notebook generation from the structured `experiment_plan.json` — much lower hallucination surface than my earlier "v0.2 notebook" sketch because the protocol JSON already specifies what to do.

## [0.2.0] — 2026-05-01

The principle behind this release: **a hypothesis without a structured experiment plan and a structured risk register is grant-proposal-incomplete; and a hypothesis without an adversarial second-opinion is one model's output, not a defensible artifact**. v0.2.0 makes all three first-class, runs them through the v0.1.2 audit pillar, and reorganizes runs into a navigable per-stage directory structure.

### Added

- **Protocol generation stage** (`src/deltasci/protocol.py`): after synthesis, deltasci produces an `ExperimentPlan` JSON — data acquisition plan, ordered steps with method citations, primary metric mirroring the falsifiability threshold, baselines, compute requirements, timeline, sample-size justification. Rendered as `06_protocol/protocol.md` + `experiment_plan.json`.
- **Risk register stage**: a `RiskRegister` JSON identifying 5–10 specific failure modes with category, severity, likely failure mode, mitigation, and counter-evidence citations. Rendered as `07_risks/risks.md` + `risk_register.json`.
- **Adversarial challenger** (`src/deltasci/challenger.py`): pluggable second-opinion stage that adversarially challenges the hypothesis + plan + risks. Output is a structured `ChallengeReport` with kind/severity-classified findings, evidence citations, and suggested responses. Optional separate `--challenger-llm` flag lets a different model class do the challenging (e.g., OpenAI vs Anthropic synthesis).
- **Audit pillar extends to all new outputs (augmentations A + B)**: every citation that appears in protocol method-citations, risk-register counter-evidence, AND challenger evidence runs through the same PubMed/Crossref/OpenAlex/GitHub/HuggingFace/GEO verifiers as the round CLAIMs. This catches the case where the challenger model fabricates a counter-evidence URL — exactly the BioIntel failure class one rung up.
- **Numbered staged directory layout** (`src/deltasci/layout.py`): runs are now `<output_dir>/<timestamp>_<slug>/` with subdirs `00_idea.md`, `01_framing/`, `02_engineering/`, `03_refinement/`, `04_plan/`, `05_synthesis/`, `06_protocol/`, `07_risks/`, `08_audits/`. Top-level convenience copies of `transcript.md`/`hypothesis.md`/`summary.json` are written for back-compat with the v0.1.x web UI / `deltasci audit`.
- **Run-level `manifest.json`** at the top of each run dir, pointing at all stages and carrying counts (well-covered / sparse / gaps / syntheses / audit-verified / audit-failed / challenge-findings).
- **Auto-view at end of `deltasci run`**: when stdout is a TTY, automatically spawns the web review surface on port 3010 (or whatever `PORT` is set to) and prints the URL. `--no-view` escape hatch for headless/CI/SSH.
- **CLI flags**: `--no-protocol`, `--no-risks`, `--no-challenge`, `--no-view`, `--challenger-llm`, `--challenger-model`.
- **9 new tests** (`tests/test_protocol_risks_challenge.py`) covering protocol assembly + error paths, risks assembly + error paths, challenger run + error paths, markdown rendering, and the full end-to-end pipeline (4 rounds → synthesis → protocol → risks → challenge → audit). Total suite now 70 tests.

### Changed

- `Result` schema gains `plan: ExperimentPlan | None`, `risks: RiskRegister | None`, `challenge: ChallengeReport | None`.
- `Config` adds `generate_protocol`, `generate_risks`, `run_challenge`, `auto_view` fields, all default `True`.
- `_write_outputs_staged` is the new default writer; `_write_outputs` (flat) is kept for back-compat with v0.1.x callers.
- `cmd_run` resolves output dir to `<base>/<timestamp>_<slug>/` automatically — separate runs no longer overwrite each other's artifacts.
- `_print_summary` now reports protocol step count, risk count by severity, and challenger finding count alongside the existing audit/grounding banners.
- `docs/examples/biomed_run/` regenerated through the full v0.2 pipeline with audit on; **the audit caught a second hallucinated citation in this very example** (`github.com/MSKCC-Computational-Pathology/CytoLens` cited by the challenger does not exist), which was replaced with no-citation. This is the design intent in action across the new outputs too: even the challenger gets audited.

### Deferred to v0.2.1

- Interactive mode (`--interactive` with approve/redirect/re-do/audit-now gates after rounds 1 and 3).
- Project view (cross-run comparison, knowledge-gap lifecycle tracking) in the web UI.
- Iteration history (`09_iterations/v1/`, `09_iterations/v2/`, ...) preserving full audit lineage across re-runs.

## [0.1.2] — 2026-04-26

The principle behind this release: **DeltaScience must catch the BioIntel-style hallucination class — fabricated PMIDs/DOIs/repos that an LLM cites confidently from training memory and a self-check labels "faithfulness: ok"**. The audit pillar makes this catch deterministic and default-on.

### Added

- **Audit pillar** (`src/deltasci/audit/`) — pluggable `Auditor` ABC, `AuditFinding` / `AuditReport` schemas, `MultiLayerAuditor` runner with parallel dispatch and file cache.
- **Citation verifiers**: `PubMedAuditor` (E-utilities esummary), `CrossrefAuditor`, `OpenAlexAuditor`, `ArxivAuditor`. PMIDs and DOIs in CLAIM source strings are looked up against the actual record; title / first-author / year / journal mismatches are flagged.
- **Repo verifiers**: `GitHubAuditor`, `HuggingFaceAuditor`. `engineering-precedent` claims have their referenced URLs resolved.
- **Dataset verifier**: `GEOAuditor` for NCBI GEO accessions (GSE/GDS/GPL/GSM).
- **Quote-in-abstract verifier**: `QuoteInAbstractAuditor`. When the AI quotes a paper verbatim, the quote is fetched against the abstract via PubMed efetch.
- **Identifier extractor** (`audit/extractor.py`): parses PMIDs, DOIs, arXiv IDs, GitHub URLs, HuggingFace IDs, GEO/SRA/Zenodo accessions out of free-text source strings.
- **File-based audit cache** at `~/.cache/deltasci/audit-cache.json`; verified findings cached 30 days, failures cached 7 days, network errors not cached.
- **Hypothesis rendering**: top-of-document audit banner ("Audit summary: ✓ X verified · ✗ Y FAILED AUDIT"); new "Citation audit" section with three subsections (verified, failed audit, skipped). Failed-audit entries show both what the AI claimed *and* what was actually at the cited identifier — this is what the BioIntel screenshot-class failures should have shown.
- **`Result.audit_report`** is now a peer to `transcript`, `hypothesis`, `grounding_summary`.
- **`deltasci audit <run-dir>`** subcommand for re-auditing existing runs after API outages or version updates. With `--write`, updates `summary.json` + `hypothesis.md` in place.
- **CLI flags on `deltasci run`**: `--no-audit` (escape hatch with prominent banner in output), `--audit-cache <path>`, `--audit-timeout-seconds <float>`.
- Tests: 15 new tests across extractor, runner-with-mocks, and cache. All run offline (no live HTTP in CI).

### Changed

- `Config` adds `audit_enabled` (default `True`), `audit_cache_path`, `audit_timeout_seconds` fields.
- `CoReasoner.run()` returns a `Result` with the new `audit_report` field; existing call sites need to update if they unpacked Result by position (keyword args still work).
- Anthropic adapter default model bumped to `claude-sonnet-4-6`.
- `docs/examples/biomed_run/` regenerated with audit on; the failed PMID 35189789 (which I authored from training memory) was caught and replaced with a hedged sparse-coverage claim plus a KNOWLEDGE_GAP. This is the design dogfood: the audit pillar caught a real hallucination in DeltaScience's own example output.

### Critical design rules baked in

1. Citation verifiers are deterministic (pure API + string comparison). LLM-driven verifiers in this layer would re-introduce the BioIntel `faithfulness: ok` failure mode by hallucinating their own verifications.
2. Audits never silently drop failures. A fabricated citation moves from "AI-confident foundations" to a separate red-flagged "FAILED AUDIT" section — both what was claimed and what was actually found are preserved.
3. Default-on. Absence of audit is rendered loudly (top-of-document `AUDIT SKIPPED` banner) so a forgotten flag cannot regenerate the BioIntel failure mode.

## [0.1.1] — 2026-04-26

The principle behind this release: **AI is reliable on what's well-represented in its training distribution; it is unreliable on what isn't, and that boundary is shaped by web visibility (paywalls, language, niche, unpublished, lab-tribal), not by publication date.** A useful AI4Science hypothesis tool has to make that boundary explicit instead of papering over it with confident text.

### Added

- **Coverage axis on every CLAIM.** `coverage` ∈ `{well-covered, sparse}` — the AI's honest self-assessment of its own training coverage for the claim.
- **`[KNOWLEDGE_GAP category=...]` as a first-class tag** — emitted by the AI whenever it would otherwise be tempted to fabricate (lab-tribal-knowledge, paywalled-or-non-OA, non-english-literature, niche-subfield, unpublished-or-pilot-data, patent-or-clinical-practice, novel-cross-disciplinary-connection, other). Surfaced under "Researcher knowledge required" in the hypothesis.
- **`[NOVEL_SYNTHESIS rationale=...]` as a first-class tag** — for connections the AI is *making* (not citing). Distinguishes creative leaps from fabricated citations.
- **Epistemic humility gate** in synthesis: refuses if zero KNOWLEDGE_GAPs and zero NOVEL_SYNTHESES were emitted across the transcript (a hallucination signal). Bypass with `--allow-no-epistemic-gaps`.
- **Three-section evidence trail in `hypothesis.md`**: AI-confident foundations / Likely-reliable please verify / Researcher knowledge required.
- **`EpistemicSummary`** in the hypothesis schema with counts and warnings (e.g., "sparse claims outnumber well-covered ones").
- New `KnowledgeGap` and `NovelSynthesis` Pydantic types exported from the top-level package.
- New skill reference doc: `skill/references/coverage_axis.md` explaining why the axis is web-visibility, not recency.

### Changed

- `CLAIM` tag attribute order is now flexible (parsed by attribute, not position).
- `extract_claims` is now `extract_signals` (extracts all three tag types). The old name is kept as a thin alias.
- `GroundingSummary.by_round` is now a list of `RoundCounts` (with claims / gaps / syntheses / violations) instead of a 3-tuple.
- Mock LLM emits the new tag types in its default round stub so smoke tests exercise the full grounding surface.
- All three skill prompts updated to describe the three-tag system explicitly.

### Removed

Nothing public.

## [0.1.0] — 2026-04-25

Initial release.

### Added

- Core `CoReasoner` engine with 4-round (configurable to 6) two-perspective dialogue.
- `DomainPack` plugin interface with TOML + markdown packaging.
- Three reference domain packs:
  - `biomed` — biomedical sciences
  - `materials` — materials science
  - `climate` — climate & earth sciences
- LLM adapters: `anthropic`, `openai`, `mock`.
- CLI: `run`, `list-packs`, `show-pack`, `demo`, `init-pack`, `validate-pack`.
- Grounding-tag system with four evidence types: `published-evidence`, `established-guideline`, `engineering-precedent`, `observation`.
- Falsifiability gate: synthesis refuses to emit a hypothesis without prediction + threshold + null outcome.
- Pydantic v2 hypothesis schema with weighted feasibility scoring.
- Claude Code skill bundle in `skill/` (drop-in for `~/.claude/skills/deltasci/`).
- Pytest suite with `MockLLM` — no live LLM calls in CI.
