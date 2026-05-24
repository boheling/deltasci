"""Biomed-serology notebook scaffold (v0.4.0).

Canonical emitters for HLA-serology / Luminex / virtual-crossmatch workflows.
Routes step names to step-specific code:

- MARCo / extraction         → pandas + requests + BeautifulSoup scraper scaffold
- IMGT / FASTA / sequence    → Biopython FASTA parser
- HATS / featurization       → subprocess Perl wrapper + CSV parse + per-pair features
- HLA-EMMA / mismatch        → sequence-diff + SA-position table integration
- HLAMatchmaker / PIRCHE / eplet → institutional-access guidance + TODO
- feature assembly / split   → pandas + GroupKFold
- train / regressor / xgboost → XGBoost with sample-weighted MSE
- evaluat / spearman / platform → scipy.stats.spearmanr + per-locus + discrepant subset

Generic stub fallback for unmatched step names.
"""

from __future__ import annotations

from deltasci.hypothesis import GroundedHypothesis
from deltasci.notebook.cells import code_cell, markdown_cell
from deltasci.protocol import ExperimentPlan, ProtocolStep


def build_cells(hypothesis: GroundedHypothesis, plan: ExperimentPlan) -> list[dict]:
    cells: list[dict] = []

    cells.append(markdown_cell(
        f"# {hypothesis.title}\n"
        f"\n_HLA-serology notebook scaffold. Canonical workflow code is real; "
        f"`# TODO` markers indicate where substantive customization is required._\n"
        f"_See `README.md` for orientation._\n"
    ))

    cells.append(markdown_cell(
        "## Hypothesis\n\n"
        f"{hypothesis.statement}\n\n"
        "### Falsifiability\n"
        f"- **Prediction:** {hypothesis.falsifiability.prediction}\n"
        f"- **Threshold:** {hypothesis.falsifiability.threshold}\n"
        f"- **Null outcome:** {hypothesis.falsifiability.null_outcome}\n"
    ))

    cells.append(code_cell(_imports_cell()))
    cells.append(markdown_cell(_data_acquisition_md(plan)))
    cells.append(code_cell(_data_acquisition_code(plan)))

    for step in plan.steps:
        cells.append(_step_markdown(step))
        cells.append(code_cell(_route_step_code(step)))

    cells.append(markdown_cell("## Falsifiability check\n"))
    cells.append(code_cell(_falsifiability_code(plan)))

    cells.append(markdown_cell(
        "## Notes\n\n"
        "When the falsifiability check passes:\n\n"
        "1. Re-audit with `deltasci audit <run-dir> --write` to re-verify any new\n"
        "   citations or repos you wired in.\n"
        "2. Consider iterating: `deltasci run --iterate-on <this-run-dir>` archives\n"
        "   the current run and lets you refine the hypothesis with new evidence.\n"
    ))

    return cells


def _imports_cell() -> str:
    return (
        "# === Imports — HLA serology + tabular ML stack ===\n"
        "import os\n"
        "import subprocess\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "\n"
        "from Bio import SeqIO\n"
        "from scipy.stats import spearmanr\n"
        "from sklearn.model_selection import GroupKFold\n"
        "from sklearn.metrics import mean_absolute_error, r2_score\n"
        "import xgboost as xgb\n"
        "\n"
        "# Optional: web acquisition for MARCo / IPD-IMGT/HLA scraping\n"
        "# import requests\n"
        "# from bs4 import BeautifulSoup\n"
        "\n"
        "RANDOM_SEED = 0\n"
        "np.random.seed(RANDOM_SEED)\n"
    )


def _data_acquisition_md(plan: ExperimentPlan) -> str:
    return (
        "## Data acquisition\n\n"
        f"- **Primary dataset:** {plan.data_acquisition.primary_dataset or '(not specified)'}\n"
        f"- **Accession / URL:** `{plan.data_acquisition.accession_or_url or '—'}`\n"
        f"- **Access constraints:** {plan.data_acquisition.access_constraints or '—'}\n"
    )


def _data_acquisition_code(plan: ExperimentPlan) -> str:
    accession = plan.data_acquisition.accession_or_url or ""
    return (
        "# === Data acquisition entry point ===\n"
        "# This cell sets up paths and verifies that the reference data is present.\n"
        "# Each downstream step assumes these are populated.\n"
        "\n"
        f"PRIMARY_REFERENCE = {accession!r}\n"
        "DATA_DIR = 'data'\n"
        "TOOLS_DIR = 'tools'\n"
        "os.makedirs(DATA_DIR, exist_ok=True)\n"
        "os.makedirs(TOOLS_DIR, exist_ok=True)\n"
        "\n"
        "MARCO_PAIRS_CSV = os.path.join(DATA_DIR, 'marco_pairs.csv')         # populated by step 1\n"
        "IMGT_FASTA = os.path.join(DATA_DIR, 'hla_prot.fasta')               # populated by step 2\n"
        "HATS_OUTPUT_CSV = os.path.join(DATA_DIR, 'hats_per_allele.csv')     # populated by step 3\n"
        "FEATURES_CSV = os.path.join(DATA_DIR, 'allele_pair_features.csv')   # populated by step 5\n"
        "\n"
        "print(f'data dir:  {DATA_DIR}')\n"
        "print(f'tools dir: {TOOLS_DIR}')\n"
    )


def _step_markdown(step: ProtocolStep) -> dict:
    parts = [f"## Step {step.order}: {step.name}"]
    if step.description:
        parts.extend(["", step.description])
    if step.inputs:
        parts.extend(["", f"**Inputs:** {', '.join(step.inputs)}"])
    if step.outputs:
        parts.append(f"**Outputs:** {', '.join(step.outputs)}")
    if step.method_citations:
        parts.extend(["", "**Methods cited:**"])
        for c in step.method_citations:
            parts.append(f"- {c}")
    return markdown_cell("\n".join(parts) + "\n")


def _route_step_code(step: ProtocolStep) -> str:
    """Route on `step.name` only (not description) to avoid keyword collisions
    from prose descriptions. Order = most-specific-tool-name first."""

    name = step.name.lower()

    # Specific tool / dataset names first — these are unambiguous
    if "hats" in name:
        return _step_hats(step)
    if "emma" in name or "hla-emma" in name:
        return _step_emma(step)
    if "matchmaker" in name or "pirche" in name or "eplet" in name:
        return _step_eplet_baselines(step)
    if "imgt" in name or "fasta" in name:
        return _step_imgt_fasta(step)
    if "marco" in name:
        return _step_marco_extraction(step)

    # Phase keywords — broader, ordered to disambiguate
    if any(k in name for k in ("feature assembly", "train/test split", "groupkfold")):
        return _step_feature_assembly(step)
    if any(k in name for k in ("xgboost", "regressor", "train ", "model fit")):
        return _step_train(step)
    if any(k in name for k in ("evaluat", "per-locus", "spearman", "platform-stratified", "platform-discrepant")):
        return _step_evaluate(step)

    # Generic data acquisition fallback
    if any(k in name for k in ("extraction", "data acquisition", "scraping")):
        return _step_marco_extraction(step)

    return _step_generic(step)


def _step_marco_extraction(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# MARCo bulk extraction. The public site at marco.igen.org.br is JS-rendered\n"
        "# and (as of writing) does not expose a documented bulk-download API.\n"
        "# Two options:\n"
        "#   (A) Institutional access via contato@igen.org.br for the underlying CSV matrix\n"
        "#   (B) Browser-driven scraping (Playwright / Selenium) per allele pair\n"
        "#\n"
        "# This scaffold assumes option A produced a CSV at MARCO_PAIRS_CSV with columns:\n"
        "#   locus, allele1, allele2, n_pooled, n_immucor, n_ol,\n"
        "#   rho_pooled, rho_immucor, rho_ol, r2,\n"
        "#   discordance_pos_neg_a1, discordance_pos_neg_a2,\n"
        "#   hats_shares_serotype, hla_emma_sa_count\n"
        "\n"
        "if not os.path.exists(MARCO_PAIRS_CSV):\n"
        "    raise NotImplementedError(\n"
        "        'MARCo bulk data not present. Either contact contato@igen.org.br for the '\n"
        "        'institutional CSV matrix, or implement a Playwright-driven per-pair scraper. '\n"
        "        f'Place result at: {MARCO_PAIRS_CSV}'\n"
        "    )\n"
        "\n"
        "marco_df = pd.read_csv(MARCO_PAIRS_CSV)\n"
        "print(f'MARCo pairs:        {len(marco_df)}')\n"
        "print(f'distinct alleles:   {pd.concat([marco_df[\"allele1\"], marco_df[\"allele2\"]]).nunique()}')\n"
        "print(f'loci covered:       {sorted(marco_df[\"locus\"].unique())}')\n"
        "print(f'pooled-rho range:   {marco_df[\"rho_pooled\"].min():.3f} – {marco_df[\"rho_pooled\"].max():.3f}')\n"
        "\n"
        "# Filter to within-locus pairs (cross-locus structural cross-reactivity is ~0)\n"
        "marco_df = marco_df[marco_df['allele1'].str.split(r'[*]', n=1).str[0] ==\n"
        "                    marco_df['allele2'].str.split(r'[*]', n=1).str[0]].copy()\n"
        "print(f'within-locus pairs: {len(marco_df)}')\n"
        "\n"
        "# TODO: filter to your locus subset (e.g., DRB1 + DQA1 + DQB1 for the DR/DQ study)\n"
        "TARGET_LOCI = ['DRB1', 'DRB3', 'DRB4', 'DRB5', 'DQA1', 'DQB1']\n"
        "marco_df = marco_df[marco_df['locus'].isin(TARGET_LOCI)].copy()\n"
        "print(f'after locus filter: {len(marco_df)} pairs')\n"
    )


def _step_imgt_fasta(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# IPD-IMGT/HLA protein FASTA — Biopython parse + per-allele indexing.\n"
        "# Mirror at github.com/ANHIG/IMGTHLA; download fasta/hla_prot.fasta from the Latest branch.\n"
        "\n"
        "if not os.path.exists(IMGT_FASTA):\n"
        "    raise NotImplementedError(\n"
        "        f'IPD-IMGT/HLA FASTA missing. Download from:\\n'\n"
        "        f'  https://raw.githubusercontent.com/ANHIG/IMGTHLA/Latest/fasta/hla_prot.fasta\\n'\n"
        "        f'and place at {IMGT_FASTA}'\n"
        "    )\n"
        "\n"
        "allele_sequences: dict[str, str] = {}\n"
        "for record in SeqIO.parse(IMGT_FASTA, 'fasta'):\n"
        "    # FASTA header format: 'HLA:HLA00001 A*01:01:01:01 1098 bp'\n"
        "    parts = record.description.split()\n"
        "    if len(parts) >= 2:\n"
        "        allele_name = parts[1]                 # e.g., 'A*01:01:01:01'\n"
        "        # Truncate to 2-field allele (the resolution MARCo uses): 'A*01:01'\n"
        "        two_field = ':'.join(allele_name.split(':')[:2])\n"
        "        if two_field not in allele_sequences:\n"
        "            allele_sequences[two_field] = str(record.seq)\n"
        "\n"
        "print(f'parsed: {len(allele_sequences)} 2-field HLA alleles')\n"
        "\n"
        "# Sanity-check: confirm MARCo alleles have sequences\n"
        "marco_alleles = set(marco_df['allele1']) | set(marco_df['allele2'])\n"
        "missing = marco_alleles - set(allele_sequences)\n"
        "if missing:\n"
        "    print(f'WARNING: {len(missing)} MARCo alleles have no sequence (e.g., {list(missing)[:5]})')\n"
        "    marco_df = marco_df[marco_df['allele1'].isin(allele_sequences) &\n"
        "                        marco_df['allele2'].isin(allele_sequences)].copy()\n"
        "    print(f'after sequence-coverage filter: {len(marco_df)} pairs')\n"
    )


def _step_hats(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# HATS featurization. The 2026-05-02 deltasci case study found that an earlier\n"
        "# AI-generated invocation here was structurally wrong (no `HATS.pl`; HATS is\n"
        "# per-locus Perl scripts; output goes to RESIDUES/ + TWORESULTS/ with `Protein`\n"
        "# / `Associated` columns, not a single CSV with `allele` / `serotype`).\n"
        "# This step now points you at upstream docs instead of guessing the invocation.\n"
        "#\n"
        "# Real HATS workflow (per https://github.com/kosoegawa/HATS#usage):\n"
        "#   1. cd tools/HATS && mkdir -p input output\n"
        "#   2. cp data/hla_prot.fasta input/hla_prot.fasta.<release-version>\n"
        "#      (e.g., hla_prot.fasta.3.54.0 — the version suffix matters)\n"
        "#   3. touch hla_prot.fasta.<release-version>  (empty marker file)\n"
        "#   4. perl runDRB1.pl  (then runDRB3/4/5.pl, runDQA1.pl, runDQB1.pl, ...)\n"
        "#   5. Outputs: RESIDUES/<LOCUS>_DEP_<version>_<date>.csv  (key residues per allele)\n"
        "#               TWORESULTS/<LOCUS>_Protein_Antigen_Table_*.csv  (allele → serotype)\n"
        "#\n"
        "# Bridge script that the deltasci case study used to merge per-locus outputs into\n"
        "# the (allele, serotype, key_residue_columns...) schema this notebook expects:\n"
        "#\n"
        "#   import glob\n"
        "#   loci = ['DRB1', 'DRB3', 'DRB4', 'DQA1', 'DQB1']\n"
        "#   combined = []\n"
        "#   for locus in loci:\n"
        "#       res = pd.read_csv(\n"
        "#           glob.glob(f'{HATS_DIR}/RESIDUES/{locus}_DEP_*.csv')[0]\n"
        "#       ).rename(columns={'Protein': 'allele'})\n"
        "#       sero = pd.read_csv(\n"
        "#           glob.glob(f'{HATS_DIR}/TWORESULTS/{locus}_Protein_Antigen_Table_*.csv')[0],\n"
        "#           on_bad_lines='skip',\n"
        "#       ).rename(columns={'Protein': 'allele', 'Associated': 'serotype'})\n"
        "#       combined.append(res.merge(sero[['allele', 'serotype']], on='allele', how='left'))\n"
        "#   pd.concat(combined, ignore_index=True).to_csv(HATS_OUTPUT_CSV, index=False)\n"
        "\n"
        "HATS_DIR = os.path.join(TOOLS_DIR, 'HATS')\n"
        "if not os.path.isdir(HATS_DIR):\n"
        "    raise NotImplementedError(\n"
        "        f'HATS not cloned. Run: git clone https://github.com/kosoegawa/HATS.git {HATS_DIR}'\n"
        "    )\n"
        "\n"
        "if not os.path.exists(HATS_OUTPUT_CSV):\n"
        "    raise NotImplementedError(\n"
        "        f'HATS output not yet produced. Run the real per-locus pipeline (see comment '\n"
        "        f'block above) and bridge its outputs to {HATS_OUTPUT_CSV} with columns: '\n"
        "        f'allele, serotype, plus numeric position columns from the RESIDUES table.'\n"
        "    )\n"
        "\n"
        "hats_df = pd.read_csv(HATS_OUTPUT_CSV)\n"
        "print(f'HATS bridged output: {len(hats_df)} alleles × {len(hats_df.columns)} columns')\n"
        "\n"
        "# Per-pair HATS features. Key-residue columns in the bridged schema are numeric.\n"
        "hats_by_allele = hats_df.set_index('allele').to_dict('index')\n"
        "key_residue_cols = [c for c in hats_df.columns if str(c).isdigit()]\n"
        "\n"
        "def hats_pair_features(a1: str, a2: str) -> dict:\n"
        "    r1 = hats_by_allele.get(a1)\n"
        "    r2 = hats_by_allele.get(a2)\n"
        "    if not r1 or not r2:\n"
        "        return {'hats_shares_serotype': 0, 'hats_key_residue_hamming': -1}\n"
        "    return {\n"
        "        'hats_shares_serotype': int(r1.get('serotype') == r2.get('serotype')),\n"
        "        'hats_key_residue_hamming': sum(1 for c in key_residue_cols if r1[c] != r2[c]),\n"
        "    }\n"
        "\n"
        "hats_feats = marco_df.apply(\n"
        "    lambda r: hats_pair_features(r['allele1'], r['allele2']), axis=1, result_type='expand',\n"
        ")\n"
        "marco_df = pd.concat([marco_df, hats_feats], axis=1)\n"
        "print(f'HATS features added.')\n"
    )


def _step_emma(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Per-pair residue mismatches + DSSP-style solvent-accessible (SA) mask.\n"
        "#\n"
        "# Earlier scaffolds named these features `emma_*` and embedded a hand-coded\n"
        "# placeholder SA-position dict. v0.7.2 swaps in `dssp_sa_mismatch_count` —\n"
        "# the SA mask is computed by `deltasci compute-sa-positions` from public\n"
        "# PDB structures via Biopython's Shrake-Rupley SASA, threshold rel SASA\n"
        "# ≥ 0.20, β1-domain only. This is a reproducible *DSSP-style proxy* and\n"
        "# is NOT the HLA-EMMA mask (HLA-EMMA itself is gated behind a non-\n"
        "# commercial license at hla-emma.com). Document this distinction in any\n"
        "# write-up — feature comparability with HLA-EMMA-validated literature is\n"
        "# limited.\n"
        "\n"
        "from deltasci.structural import load_sa_positions\n"
        "_SA_PAYLOAD = load_sa_positions()\n"
        "SA_POSITIONS_PER_LOCUS = {\n"
        "    locus: payload['positions']\n"
        "    for locus, payload in _SA_PAYLOAD.items() if locus != 'metadata'\n"
        "}\n"
        "print(f'loaded DSSP SA positions: {len(SA_POSITIONS_PER_LOCUS)} loci '\n"
        "      f'(threshold rel SASA ≥ {_SA_PAYLOAD[\"metadata\"][\"threshold_rel_sasa\"]}, '\n"
        "      f'reference PDBs in metadata)')\n"
        "\n"
        "def residue_mismatch_features(a1: str, a2: str, locus: str) -> dict:\n"
        "    seq1 = allele_sequences.get(a1)\n"
        "    seq2 = allele_sequences.get(a2)\n"
        "    if not seq1 or not seq2:\n"
        "        return {'total_residue_mismatches': -1, 'dssp_sa_mismatch_count': -1}\n"
        "    L = min(len(seq1), len(seq2))\n"
        "    total_mm = sum(1 for i in range(L) if seq1[i] != seq2[i])\n"
        "    sa_positions = SA_POSITIONS_PER_LOCUS.get(locus, [])\n"
        "    sa_mm = sum(1 for p in sa_positions if (p - 1) < L and seq1[p - 1] != seq2[p - 1])\n"
        "    return {'total_residue_mismatches': total_mm, 'dssp_sa_mismatch_count': sa_mm}\n"
        "\n"
        "feats = marco_df.apply(\n"
        "    lambda r: residue_mismatch_features(r['allele1'], r['allele2'], r['locus']),\n"
        "    axis=1, result_type='expand',\n"
        ")\n"
        "marco_df = pd.concat([marco_df, feats], axis=1)\n"
        "print('residue-mismatch features added; DSSP SA-mismatch distribution:')\n"
        "print(marco_df['dssp_sa_mismatch_count'].describe())\n"
    )


def _step_eplet_baselines(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# HLAMatchmaker eplet count + PIRCHE-II indirect-recognition score.\n"
        "# Both tools have web interfaces; programmatic batch access varies by tool/version.\n"
        "\n"
        "# Three integration paths in order of preference:\n"
        "#   (A) Institutional access via the tool maintainers (HLAMatchmaker: Duquesnoy lab;\n"
        "#       PIRCHE-II: PIRCHE.com / UMC Utrecht). Email + research agreement → batch CSV.\n"
        "#   (B) Public Eplet Registry (https://www.epregistry.com.br/) — gives eplet definitions\n"
        "#       per allele; you compute the count yourself from registry tables.\n"
        "#   (C) Single-allele-pair web scraping (fragile; rate-limited; not viable at scale).\n"
        "#\n"
        "# This scaffold leaves the integration as a TODO with explicit guidance.\n"
        "\n"
        "EPLET_FEATURES_CSV = os.path.join(DATA_DIR, 'eplet_features.csv')\n"
        "if not os.path.exists(EPLET_FEATURES_CSV):\n"
        "    raise NotImplementedError(\n"
        "        'HLAMatchmaker + PIRCHE-II features missing. Recommended path:\\n'\n"
        "        '  1) Email HLAMatchmaker maintainer for batch eplet count CSV\\n'\n"
        "        '  2) Email PIRCHE-II maintainer for batch indirect-recognition CSV\\n'\n"
        "        '  3) Or compute eplet counts yourself from the public Eplet Registry tables\\n'\n"
        "        f'Output expected at {EPLET_FEATURES_CSV} with columns:\\n'\n"
        "        '     allele1, allele2, hlamatchmaker_eplet_count, pirche_ii_score'\n"
        "    )\n"
        "\n"
        "eplet_df = pd.read_csv(EPLET_FEATURES_CSV)\n"
        "marco_df = marco_df.merge(eplet_df, on=['allele1', 'allele2'], how='left')\n"
        "print(f'eplet features merged; missing values: {marco_df[\"hlamatchmaker_eplet_count\"].isna().sum()}/{len(marco_df)}')\n"
    )


def _step_feature_assembly(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Assemble the final feature matrix and stratified train/test splits.\n"
        "\n"
        "marco_df = marco_df.dropna(subset=['rho_pooled']).copy()\n"
        "marco_df['log_n_samples'] = np.log1p(marco_df['n_pooled'])\n"
        "marco_df['log_n_immucor'] = np.log1p(marco_df['n_immucor'].fillna(0))\n"
        "marco_df['log_n_ol'] = np.log1p(marco_df['n_ol'].fillna(0))\n"
        "\n"
        "# Locus one-hot encoding\n"
        "for locus in TARGET_LOCI:\n"
        "    marco_df[f'locus_{locus}'] = (marco_df['locus'] == locus).astype(int)\n"
        "\n"
        "FEATURE_COLS = [\n"
        "    'hats_shares_serotype', 'hats_key_residue_hamming',\n"
        "    'emma_total_mm', 'emma_sa_mm',\n"
        "    'hlamatchmaker_eplet_count', 'pirche_ii_score',\n"
        "    'log_n_samples', 'log_n_immucor', 'log_n_ol',\n"
        "] + [f'locus_{loc}' for loc in TARGET_LOCI]\n"
        "\n"
        "X = marco_df[FEATURE_COLS].fillna(0).values\n"
        "y = marco_df['rho_pooled'].values\n"
        "sample_weight = np.log1p(marco_df['n_pooled'].clip(lower=1)).values\n"
        "\n"
        "# GroupKFold by allele identity — partial leakage protection\n"
        "groups = marco_df['allele1'].values\n"
        "gkf = GroupKFold(n_splits=5)\n"
        "fold_indices = list(gkf.split(X, y, groups))\n"
        "for fold, (train_idx, test_idx) in enumerate(fold_indices):\n"
        "    print(f'fold {fold}: {len(train_idx)} train + {len(test_idx)} test')\n"
        "\n"
        "# Stricter held-one-allele-out evaluation: pick a target allele, remove ALL its pairs.\n"
        "HELD_OUT_ALLELE = 'DRB1*15:01'  # TODO: pick a clinically important allele to hold out\n"
        "is_holdout = (marco_df['allele1'] == HELD_OUT_ALLELE) | (marco_df['allele2'] == HELD_OUT_ALLELE)\n"
        "print(f'held-out allele {HELD_OUT_ALLELE}: {is_holdout.sum()} pairs')\n"
        "X_strict_train, X_strict_test = X[~is_holdout], X[is_holdout]\n"
        "y_strict_train, y_strict_test = y[~is_holdout], y[is_holdout]\n"
        "w_strict_train = sample_weight[~is_holdout]\n"
    )


def _step_train(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# XGBoost regression with sample-size-weighted MSE loss.\n"
        "\n"
        "XGB_PARAMS = dict(\n"
        "    n_estimators=500,\n"
        "    max_depth=6,\n"
        "    learning_rate=0.05,\n"
        "    subsample=0.8,\n"
        "    colsample_bytree=0.8,\n"
        "    reg_alpha=0.1,\n"
        "    reg_lambda=1.0,\n"
        "    random_state=RANDOM_SEED,\n"
        "    objective='reg:squarederror',\n"
        ")\n"
        "\n"
        "# Cross-validated training over GroupKFold splits\n"
        "cv_predictions = np.zeros_like(y, dtype=float)\n"
        "for fold, (train_idx, test_idx) in enumerate(fold_indices):\n"
        "    model_cv = xgb.XGBRegressor(**XGB_PARAMS)\n"
        "    model_cv.fit(X[train_idx], y[train_idx], sample_weight=sample_weight[train_idx])\n"
        "    cv_predictions[test_idx] = model_cv.predict(X[test_idx])\n"
        "    fold_rho, _ = spearmanr(cv_predictions[test_idx], y[test_idx])\n"
        "    print(f'fold {fold}: held-out Spearman ρ = {fold_rho:.4f}')\n"
        "\n"
        "# Final production model on all data (for feature-importance interpretation)\n"
        "model = xgb.XGBRegressor(**XGB_PARAMS)\n"
        "model.fit(X, y, sample_weight=sample_weight)\n"
        "\n"
        "importances = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)\n"
        "print('\\nTop-10 feature importances:')\n"
        "print(importances.head(10))\n"
    )


def _step_evaluate(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Per-locus + platform-stratified + platform-discrepant evaluation.\n"
        "\n"
        "# Pooled cross-validated Spearman ρ\n"
        "pooled_rho, _ = spearmanr(cv_predictions, y)\n"
        "print(f'POOLED held-out Spearman ρ:        {pooled_rho:.4f}')\n"
        "\n"
        "# Per-locus stratified evaluation\n"
        "print('\\nPer-locus Spearman ρ:')\n"
        "for locus in TARGET_LOCI:\n"
        "    mask = marco_df['locus'] == locus\n"
        "    if mask.sum() < 20:\n"
        "        print(f'  {locus:7s}: n={mask.sum()} (too small for stable ρ; skipped)')\n"
        "        continue\n"
        "    locus_rho, _ = spearmanr(cv_predictions[mask], y[mask])\n"
        "    print(f'  {locus:7s}: n={mask.sum():4d}, ρ = {locus_rho:.4f}')\n"
        "\n"
        "# Baselines (each evaluated on the same CV folds)\n"
        "print('\\nBaseline cross-validated Spearman ρ:')\n"
        "BASELINES = {\n"
        "    'naive_hamming':         marco_df['emma_total_mm'].values,\n"
        "    'hats_shares_serotype':  marco_df['hats_shares_serotype'].values,\n"
        "    'hla_emma_sa':           marco_df['emma_sa_mm'].values,\n"
        "    'hlamatchmaker_eplet':   marco_df['hlamatchmaker_eplet_count'].fillna(0).values,\n"
        "    'pirche_ii':             marco_df['pirche_ii_score'].fillna(0).values,\n"
        "}\n"
        "best_baseline_rho = -1\n"
        "best_baseline_name = ''\n"
        "for name, baseline_pred in BASELINES.items():\n"
        "    # Note: rule-based baselines predict mismatch counts (higher = more different\n"
        "    # = lower expected ρ), so the correlation with ρ is *negative* before sign-flip.\n"
        "    rho, _ = spearmanr(-baseline_pred, y)\n"
        "    print(f'  {name:25s}: ρ = {rho:.4f}')\n"
        "    if rho > best_baseline_rho:\n"
        "        best_baseline_rho = rho\n"
        "        best_baseline_name = name\n"
        "\n"
        "print(f'\\nBest baseline: {best_baseline_name} (ρ = {best_baseline_rho:.4f})')\n"
        "print(f'Model lift over best baseline: {pooled_rho - best_baseline_rho:+.4f}')\n"
        "\n"
        "# Platform-discrepant subset analysis\n"
        "marco_df['platform_disagreement'] = (marco_df['rho_immucor'] - marco_df['rho_ol']).abs()\n"
        "discrepant_mask = marco_df['platform_disagreement'] > 0.15\n"
        "print(f'\\nPlatform-discrepant pairs (|ρ_imm - ρ_ol| > 0.15): {discrepant_mask.sum()}')\n"
        "if discrepant_mask.sum() > 10:\n"
        "    consensus = (marco_df.loc[discrepant_mask, 'rho_immucor'] +\n"
        "                 marco_df.loc[discrepant_mask, 'rho_ol']) / 2\n"
        "    discrepant_pred = cv_predictions[discrepant_mask]\n"
        "    discrepant_rho, _ = spearmanr(discrepant_pred, consensus)\n"
        "    print(f'  Predicted ρ vs cross-platform consensus: ρ = {discrepant_rho:.4f}')\n"
    )


def _step_generic(step: ProtocolStep) -> str:
    slug = "_".join(step.name.lower().split())[:32]
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        f"# No canonical pattern matched. Implement directly.\n"
        f"\n"
        f"def step_{step.order:02d}_{slug}():\n"
        f"    \"\"\"{step.description or step.name}\"\"\"\n"
        f"    raise NotImplementedError('TODO: implement step {step.order}')\n"
    )


def _falsifiability_code(plan: ExperimentPlan) -> str:
    return (
        "# === Falsifiability check ===\n"
        f"# Primary metric: {plan.primary_metric}\n"
        f"# Success threshold: {plan.success_threshold}\n"
        f"# Null outcome:     {plan.null_outcome}\n"
        "\n"
        "try:\n"
        "    model_pooled_rho = float(pooled_rho)\n"
        "    baseline_pooled_rho = float(best_baseline_rho)\n"
        "except NameError:\n"
        "    model_pooled_rho = None\n"
        "    baseline_pooled_rho = None\n"
        "\n"
        "if model_pooled_rho is None or baseline_pooled_rho is None:\n"
        "    raise NotImplementedError('Run the evaluation step first.')\n"
        "\n"
        "lift = model_pooled_rho - baseline_pooled_rho\n"
        "print(f'pooled Spearman ρ (model):    {model_pooled_rho:.4f}')\n"
        "print(f'pooled Spearman ρ (baseline): {baseline_pooled_rho:.4f}')\n"
        "print(f'lift over best baseline:      {lift:+.4f}')\n"
        "\n"
        "MIN_LIFT_FOR_HYPOTHESIS = 0.07  # TODO: align with falsifiability threshold above\n"
        "assert lift >= MIN_LIFT_FOR_HYPOTHESIS, (\n"
        "    f'Lift {lift:+.4f} below threshold {MIN_LIFT_FOR_HYPOTHESIS} — hypothesis falsified.'\n"
        ")\n"
        "print('falsifiability check PASSED')\n"
    )
