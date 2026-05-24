# Case study — executing the marco_dr_dq notebook scaffold

**Date**: 2026-05-02
**Notebook**: `docs/examples/marco_dr_dq/10_notebook/notebook.ipynb`
**deltasci version**: 0.4.0
**Pack used**: `biomed-serology`
**Goal**: empirically determine what level of human-in-the-loop work is required to execute a deltasci-generated notebook end-to-end, and what gaps exist between the generated scaffold and a working pipeline. Inform the v0.5 execution-layer design.

## Setup

- Fresh Python venv (3.14)
- `pip install nbclient jupyter biopython xgboost scipy scikit-learn pandas matplotlib` — **20 seconds**
- Clean working dir: only the notebook + nothing pre-staged

## Pre-flight (before execute)

- Notebook: 22 cells, 598 lines
- 6 explicit `# TODO` markers
- 6 `raise NotImplementedError` calls (each marks a researcher gate)

## Execution log

### Failure 1 — cell 4 (Step 1: MARCo data extraction)

```
NotImplementedError: MARCo bulk data not present. Either contact contato@igen.org.br
for the institutional CSV matrix, or implement a Playwright-driven per-pair scraper.
Place result at: data/marco_pairs.csv
```

**Severity**: expected · **Class**: researcher gate · **Time to resolve**: depends on access path.

The error message clearly tells the researcher what's needed and where to put it. For the case study I generated 31 synthetic pairs across DR/DQ loci to push past it.

**deltasci-correct**: ✅ The scaffold correctly gated on a missing data file with a useful error message.

---

### Failure 2 — cell 6 (Step 2: IPD-IMGT/HLA sequence retrieval)

```
NotImplementedError: IPD-IMGT/HLA FASTA missing. Download from:
  https://raw.githubusercontent.com/ANHIG/IMGTHLA/Latest/fasta/hla_prot.fasta
and place at data/hla_prot.fasta
```

**Severity**: expected · **Class**: researcher gate · **Time to resolve**: 1 second (`curl -sL <URL> -o data/hla_prot.fasta`).

The URL in the error message is correct and works. 14 MB download.

**deltasci-correct**: ✅ The scaffold gave a working URL.

After fix: cell 6 succeeded — Biopython parsed the FASTA, indexed 2-field alleles, and the sanity-check filter against MARCo coverage worked silently.

---

### Failure 3 — cell 8 (Step 3: HATS featurization)

```
NotImplementedError: HATS not cloned. Run: git clone https://github.com/kosoegawa/HATS.git tools/HATS
```

**Severity**: expected · **Class**: researcher gate · **Time to resolve**: 1 second (`git clone --depth 1`).

After clone, the next failure exposes **three structural inaccuracies** in the AI-generated scaffold:

#### 3a. Wrong subprocess invocation

The notebook scaffold says:
```python
result = subprocess.run(['perl', f'{HATS_PERL_DIR}/HATS.pl', '-i', IMGT_FASTA, '-o', HATS_OUTPUT], ...)
```

**Reality**: HATS has no `HATS.pl`. It's a per-locus pipeline:
```
runHlaA.pl   runHlaB.pl   runHlaC.pl
runDPA1.pl   runDPB1.pl
runDQA1.pl   runDQB1.pl
runDRB1.pl   runDRB3.pl   runDRB4.pl   runDRB5.pl
```

Each script reads from `input/hla_prot.fasta.<version>` (note: filename includes the IPD-IMGT/HLA database release version) and writes to `RESULTS/`, `TWORESULTS/`, `RESIDUES/` directories.

#### 3b. Wrong output path

Scaffold expected: `data/hats_per_allele.csv`.
Reality: per-locus files like `RESIDUES/DRB1_DEP_3.63.0_2026-05-02.csv` and `TWORESULTS/DRB1_Protein_Antigen_Table_IMGT_HLA_3.63.0_2026-05-02.csv`.

#### 3c. Wrong column names

Scaffold assumed columns `['allele', 'serotype', ...]` with key-residue cols having descriptive names.
Reality: `['Protein', 'AA/AN/BR', 'Qualifier', 9, 10, 11, 12, ...]` (numeric column names = residue positions; `Protein` instead of `allele`; `Associated`/`Split`/`Broad` for serotype).

#### 3d. CSV parsing quirk

Some rows in `TWORESULTS/*Antigen_Table*.csv` have 9 columns instead of 8 (an unmapped-protein indicator field appears variably). Pandas C parser fails with `ParserError`. Real-world CSV quirk that requires `on_bad_lines='skip'` to bridge.

**Time to resolve**: ~30 minutes for a researcher familiar with HATS to write a bridge script that:
1. Maps `Protein` → `allele`, `Associated` → `serotype`
2. Concatenates per-locus RESIDUES files
3. Adds `on_bad_lines='skip'` to handle the variable-column quirk

**deltasci-INCORRECT**: ❌ The AI-generated subprocess call, output path, and column schema are all hallucinated. The AI knew the github URL but not the actual tool layout.

**Lesson for v0.5**: Pack templates that wrap external CLI tools should NOT pretend to know the exact invocation. The honest pattern is: provide the github URL, point the researcher at the README, leave the actual subprocess call as an explicit TODO with a comment block linking to upstream docs.

---

### Failure 4 — cell 12 (Step 5: HLAMatchmaker + PIRCHE-II baselines)

```
NotImplementedError: HLAMatchmaker + PIRCHE-II features missing. Recommended path:
  1) Email HLAMatchmaker maintainer for batch eplet count CSV
  2) Email PIRCHE-II maintainer for batch indirect-recognition CSV
  3) Or compute eplet counts yourself from the public Eplet Registry tables
Output expected at data/eplet_features.csv with columns:
     allele1, allele2, hlamatchmaker_eplet_count, pirche_ii_score
```

**Severity**: expected · **Class**: researcher gate · **Time to resolve**: weeks-to-months for institutional access; 1 day for Eplet Registry self-compute; 0 minutes for a synthetic placeholder (case study path).

Step 4 (HLA-EMMA mismatch profiling) succeeded silently between failures 3 and 4 — the sequence-diff code with placeholder SA position lists worked. **Note**: the SA position lists in the scaffold are placeholders, not the real HLA-EMMA SA positions. Researcher must look these up.

**deltasci-correct**: ✅ The scaffold's three-path guidance for HLAMatchmaker/PIRCHE-II access is honest and actionable.

---

### Failure 5 — cell 14 (Step 6: Train XGBoost regressor)

```
NameError: name 'y' is not defined
```

**Severity**: STRUCTURAL deltasci issue · **Class**: pack/protocol mismatch · **Time to resolve**: requires understanding of the codebase.

The Train cell references `X`, `y`, `sample_weight`, `fold_indices`, `FEATURE_COLS` — variables that should be defined in a feature-assembly step. **There is no feature-assembly step in the protocol**. The protocol has 7 steps (MARCo extraction → IMGT FASTA → HATS → HLA-EMMA → HLAMatchmaker → Train → Evaluate), and the synthesis stage that authored it omitted the intermediate plumbing step.

The pack's `_route_step_code` has a `_step_feature_assembly` emitter, but no protocol step matches its keywords (`"feature assembly"`, `"train/test split"`, `"groupkfold"`). So feature assembly is silently skipped, and Step 6's emitter assumes prerequisites that don't exist.

**deltasci-INCORRECT**: ❌ The pack template's notebook emitters have implicit cross-cell prerequisites (`_step_train` assumes `_step_feature_assembly` ran first), but nothing enforces that the protocol includes both steps.

**Lesson for v0.5**: Pack templates should either:
1. Declare prerequisite-emitter relationships and the generator auto-inserts feature-assembly cells when train/eval cells are present
2. Make each step's code self-contained with all needed locals
3. Make the synthesis stage aware of canonical-step expectations from the pack and refuse to emit a protocol that's missing them

This is a real architectural gap — the notebook layer's correctness depends on the protocol layer including all the right steps, but the two layers don't communicate that requirement.

---

## Summary

### What worked

- **Steps 1, 2**: scaffold-correct, error messages were directly actionable (data path, download URL)
- **Step 4**: HLA-EMMA sequence-diff code worked silently (with placeholder SA positions)
- **Step 5**: institutional-access TODO was honest and clearly explained

### What was wrong but recoverable

- **Step 3 (HATS)**: 3 structural inaccuracies in the AI-generated subprocess invocation. ~30 minutes of researcher debugging to bridge real HATS output → notebook's expected schema.
- **Placeholder SA positions** in step 4: not flagged as wrong, but real values would need researcher lookup.

### What was structurally broken

- **Step 6 NameError**: the protocol is missing a feature-assembly step that the pack template's train emitter requires. **This is a deltasci architectural issue** — the synthesis stage and the pack template don't share an expected step list.

### Researcher time-to-running estimate

For a researcher familiar with HLA serology + Python:

| Phase | Time |
|-------|------|
| Read errors, set 3 file paths | 5 min |
| Download IPD-IMGT/HLA FASTA + clone HATS | 1 min |
| Run real HATS per-locus + write bridge script for output schema | 30-60 min |
| Replace placeholder SA positions with real values from HLA-EMMA distribution | 30 min |
| Author feature-assembly cell to fix Step 6 NameError | 30 min |
| Acquire HLAMatchmaker + PIRCHE-II features (institutional path) | weeks |
| **Total to "runs end-to-end"** | **~1.5-2.5 hours** if HLAMatchmaker is bypassed with synthetic; otherwise weeks |

### Implications for v0.5 (execution layer)

1. **Auto-execute would surface failures faster but not fix them.** All 5 failures above would happen identically; the value of `deltasci execute` is in capturing logs + manifest, not auto-resolving.

2. **Pre-flight check is high-value, low-cost.** Before executing, scan the notebook for:
   - `NotImplementedError` raises (count + show messages)
   - Cross-cell variable references (does any cell reference a name no prior cell defines?)
   - Missing files referenced in the data-acquisition cell
   This would have caught Failure 5 (the NameError) statically without running anything.

3. **Pack templates need a "prerequisite" declaration.** Each emitter should declare what cells must precede it. The generator inserts plumbing automatically when needed.

4. **Subprocess wrappers around external CLIs (Perl, R, etc.) are high-hallucination-risk.** Pack templates should NOT include AI-guessed invocations. Honest pattern: TODO with link to upstream README.

5. **The "researcher gate" pattern (`raise NotImplementedError` with helpful message) is the right design.** All 4 of the *expected* failures (1, 2, 3a, 4) had error messages that pointed at the fix. The researcher reads the message → does the thing → re-runs. That worked.

6. **Synthetic data placeholders (like SA positions) need explicit `# PLACEHOLDER` markers.** The HLA-EMMA scaffold silently used wrong SA positions; the researcher might never realize until results are wrong. Mark placeholders distinctly from TODOs.

### Recommended v0.5 scope refinement

Original v0.5 plan: `deltasci execute` + `deltasci audit-results`.

**Revised v0.5 plan based on these findings**:

1. **`deltasci preflight <run-dir>`** (NEW, high-priority): static analysis of the notebook before executing. Counts TODOs, finds NameError-prone cross-cell references, checks file paths, surfaces all `NotImplementedError` raises with their messages. Output: a "what you need to do before running" report.

2. **`deltasci execute <run-dir>`** (the original v0.5 plan): runs the notebook, captures outputs, produces 11_results/. Useful AFTER preflight is clean.

3. **`deltasci audit-results <run-dir>`** (the original v0.5 plan): verifies results against falsifiability threshold.

4. **Pack template tightening (parallel work)**:
   - Mark placeholder data with `# PLACEHOLDER:` prefix (visually distinct from `# TODO:`)
   - Replace AI-guessed subprocess invocations with TODO + upstream-doc links
   - Declare prerequisite relationships between emitters; generator auto-inserts plumbing

The preflight tool is the missing piece — it would have caught Failure 5 without the user running anything, and it gives a clean checklist of "do these 5 things and then run".
