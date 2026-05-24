"""Materials notebook scaffold (v0.3.1 — canonical code, keyword-routed)."""

from __future__ import annotations

from deltasci.hypothesis import GroundedHypothesis
from deltasci.notebook.cells import code_cell, markdown_cell
from deltasci.protocol import ExperimentPlan, ProtocolStep


def build_cells(hypothesis: GroundedHypothesis, plan: ExperimentPlan) -> list[dict]:
    cells: list[dict] = []

    cells.append(markdown_cell(
        f"# {hypothesis.title}\n"
        f"\n_Canonical workflow code is real; `# TODO` markers indicate where customization is required._\n"
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

    return cells


def _imports_cell() -> str:
    return (
        "# === Imports — materials informatics stack ===\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import matplotlib.pyplot as plt\n"
        "\n"
        "from pymatgen.core import Structure, Composition\n"
        "from pymatgen.ext.matproj import MPRester\n"
        "# from matminer.featurizers.composition import ElementProperty\n"
        "# from matminer.featurizers.structure import SiteStatsFingerprint\n"
        "\n"
        "from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier\n"
        "from sklearn.metrics import mean_absolute_error, r2_score, top_k_accuracy_score\n"
        "from sklearn.model_selection import KFold\n"
        "\n"
        "import torch\n"
        "import torch.nn as nn\n"
        "# import torch_geometric as pyg\n"
        "\n"
        "RANDOM_SEED = 0\n"
        "np.random.seed(RANDOM_SEED)\n"
        "torch.manual_seed(RANDOM_SEED)\n"
        "\n"
        "MP_API_KEY = None  # TODO: set your https://materialsproject.org API key\n"
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
        "# === Data acquisition (Materials Project canonical pattern) ===\n"
        f"PRIMARY_REFERENCE = {accession!r}\n"
        "\n"
        "if MP_API_KEY is None:\n"
        "    raise NotImplementedError(\n"
        "        f'Set MP_API_KEY before continuing. Reference: {PRIMARY_REFERENCE}'\n"
        "    )\n"
        "\n"
        "# TODO: tune the search criteria for your hypothesis. Spinel example:\n"
        "FORMULA_PATTERN = '*Mn2O4'  # TODO: replace with your composition family\n"
        "FIELDS = [\n"
        "    'material_id', 'formula_pretty', 'structure',\n"
        "    'formation_energy_per_atom', 'energy_above_hull',\n"
        "    'band_gap', 'is_stable', 'theoretical',\n"
        "]\n"
        "\n"
        "with MPRester(MP_API_KEY) as mpr:\n"
        "    docs = mpr.summary.search(formula=FORMULA_PATTERN, fields=FIELDS)\n"
        "\n"
        "df = pd.DataFrame([{f: getattr(d, f, None) for f in FIELDS} for d in docs])\n"
        "print(f'queried: {len(df)} candidates matching {FORMULA_PATTERN!r}')\n"
        "print(df[['formula_pretty', 'energy_above_hull', 'band_gap', 'is_stable']].head())\n"
    )


def _step_markdown(step: ProtocolStep) -> dict:
    parts = [f"## Step {step.order}: {step.name}"]
    if step.description:
        parts.extend(["", step.description])
    if step.method_citations:
        parts.extend(["", "**Methods cited:**"])
        for c in step.method_citations:
            parts.append(f"- {c}")
    return markdown_cell("\n".join(parts) + "\n")


def _route_step_code(step: ProtocolStep) -> str:
    name = (step.name + " " + (step.description or "")).lower()
    if any(k in name for k in ("spinel", "subset", "extraction", "filter")):
        return _step_subset(step)
    if any(k in name for k in ("featuriz", "feature", "encod")):
        return _step_features(step)
    if any(k in name for k in ("label", "harvest", "decomp")):
        return _step_labels(step)
    if any(k in name for k in ("train", "model", "fit", "gnn", "cgcnn", "m3gnet")):
        return _step_train(step)
    if any(k in name for k in ("rank", "candidate", "screen")):
        return _step_rank(step)
    if any(k in name for k in ("evaluat", "metric", "synth", "closed-loop", "validation")):
        return _step_evaluate(step)
    return _step_generic(step)


def _step_subset(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Filter the queried set to your structural family of interest.\n"
        "\n"
        "MAX_HULL_DISTANCE_EV = 0.05  # TODO: tune; 0 = thermodynamically stable, 0.1 = mildly metastable\n"
        "REQUIRE_STABLE = False        # TODO: True for stable-only, False to include metastables\n"
        "\n"
        "df_filt = df.copy()\n"
        "df_filt = df_filt[df_filt['energy_above_hull'].fillna(99) <= MAX_HULL_DISTANCE_EV]\n"
        "if REQUIRE_STABLE:\n"
        "    df_filt = df_filt[df_filt['is_stable'].fillna(False)]\n"
        "print(f'after stability filter: {len(df_filt)}/{len(df)} retained')\n"
        "\n"
        "# TODO: add structure-prototype filter for your topology (e.g., spinel space group Fd-3m)\n"
        "# from pymatgen.symmetry.analyzer import SpacegroupAnalyzer\n"
        "# df_filt['spacegroup'] = df_filt['structure'].apply(\n"
        "#     lambda s: SpacegroupAnalyzer(s).get_space_group_symbol() if s else None\n"
        "# )\n"
        "# df_filt = df_filt[df_filt['spacegroup'] == 'Fd-3m']\n"
    )


def _step_features(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Canonical matminer featurization: composition-level descriptors.\n"
        "from matminer.featurizers.composition import ElementProperty\n"
        "\n"
        "ep = ElementProperty.from_preset('magpie')\n"
        "df_filt['composition'] = df_filt['formula_pretty'].apply(Composition)\n"
        "feat = ep.featurize_dataframe(df_filt, col_id='composition', ignore_errors=True)\n"
        "feature_cols = [c for c in feat.columns if c.startswith('MagpieData')]\n"
        "X = feat[feature_cols].fillna(0).values\n"
        "print(f'featurized: X shape = {X.shape}')\n"
        "\n"
        "# TODO: add classical empirical-rule features alongside Magpie:\n"
        "# - Goldschmidt tolerance factor for perovskite/spinel topologies\n"
        "# - Hume-Rothery ionic-size mismatch\n"
        "# - mean electronegativity difference\n"
    )


def _step_labels(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Harvest decomposition / voltage / other property labels.\n"
        "\n"
        "# Voltage labels via MP intercalation electrode endpoints (canonical pattern):\n"
        "# with MPRester(MP_API_KEY) as mpr:\n"
        "#     batt = mpr.materials.insertion_electrodes.search(\n"
        "#         working_ion='Li', formula='*Mn2O4',\n"
        "#         fields=['battery_id', 'average_voltage', 'energy_grav', 'capacity_grav'],\n"
        "#     )\n"
        "\n"
        "# TODO: harvest decomposition-temperature labels from open thermochemistry\n"
        "# tables (NIST WebBook) or DFT-MD literature. This is the bottleneck data step.\n"
        "decomp_temps = pd.DataFrame()  # TODO: populate with material_id → decomp_C\n"
        "if decomp_temps.empty:\n"
        "    raise NotImplementedError(\n"
        "        'Populate decomp_temps with experimental or DFT-MD decomposition labels.'\n"
        "    )\n"
        "\n"
        "df_filt = df_filt.merge(decomp_temps, on='material_id', how='left')\n"
        "print(f'labeled: {df_filt[\"decomp_C\"].notna().sum()}/{len(df_filt)} have decomp temps')\n"
    )


def _step_train(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Multi-task regression baseline: random-forest per target, then upgrade to GNN.\n"
        "\n"
        "from sklearn.ensemble import RandomForestRegressor\n"
        "\n"
        "y_voltage = df_filt.get('average_voltage', pd.Series([np.nan] * len(df_filt))).values\n"
        "y_decomp  = df_filt.get('decomp_C', pd.Series([np.nan] * len(df_filt))).values\n"
        "y_hull    = df_filt['energy_above_hull'].values\n"
        "\n"
        "mask_v = ~np.isnan(y_voltage)\n"
        "mask_d = ~np.isnan(y_decomp)\n"
        "\n"
        "models = {}\n"
        "if mask_v.sum() > 20:\n"
        "    models['voltage'] = RandomForestRegressor(n_estimators=200, random_state=RANDOM_SEED).fit(X[mask_v], y_voltage[mask_v])\n"
        "    print(f'voltage model trained on {mask_v.sum()} samples')\n"
        "if mask_d.sum() > 20:\n"
        "    models['decomp'] = RandomForestRegressor(n_estimators=200, random_state=RANDOM_SEED).fit(X[mask_d], y_decomp[mask_d])\n"
        "    print(f'decomp model trained on {mask_d.sum()} samples')\n"
        "models['hull'] = RandomForestRegressor(n_estimators=200, random_state=RANDOM_SEED).fit(X, y_hull)\n"
        "print(f'hull model trained on {len(X)} samples')\n"
        "\n"
        "# TODO: upgrade to a GNN once the RF baseline is established.\n"
        "# class CrystalGNN(nn.Module):\n"
        "#     def __init__(self, ...): ...  # TODO: wire CGCNN or M3GNet-class encoder\n"
    )


def _step_rank(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Rank candidates by joint posterior over voltage / decomp / hull thresholds.\n"
        "\n"
        "VOLTAGE_TARGET = 4.3   # TODO: tune to your hypothesis\n"
        "DECOMP_TARGET = 200.0  # °C\n"
        "TOP_K = 20\n"
        "\n"
        "preds = pd.DataFrame({'material_id': df_filt['material_id'].values})\n"
        "if 'voltage' in models:\n"
        "    preds['pred_voltage'] = models['voltage'].predict(X)\n"
        "if 'decomp' in models:\n"
        "    preds['pred_decomp'] = models['decomp'].predict(X)\n"
        "preds['pred_hull'] = models['hull'].predict(X)\n"
        "\n"
        "# Composite score: voltage above target AND decomp above target AND hull below cutoff.\n"
        "preds['score'] = (\n"
        "    (preds.get('pred_voltage', 0) - VOLTAGE_TARGET).clip(lower=-1) +\n"
        "    (preds.get('pred_decomp', 0) - DECOMP_TARGET).clip(lower=-50) / 50.0 -\n"
        "    preds['pred_hull']\n"
        ")\n"
        "top = preds.nlargest(TOP_K, 'score')\n"
        "print(top.head(10))\n"
    )


def _step_evaluate(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Closed-loop evaluation: top-K synthesis hit-rate vs random selection.\n"
        "\n"
        "# Provide measured outcomes for the top-K candidates after synthesis.\n"
        "# TODO: replace with your real measured properties.\n"
        "measured = pd.DataFrame()  # columns: material_id, measured_voltage, measured_decomp_C\n"
        "if measured.empty:\n"
        "    raise NotImplementedError(\n"
        "        'Populate `measured` with synthesized + characterized candidates from the top-K list.'\n"
        "    )\n"
        "\n"
        "VOLTAGE_HIT = 4.0  # TODO: align with falsifiability tolerance band\n"
        "DECOMP_HIT = 180.0\n"
        "\n"
        "measured['hit'] = (\n"
        "    (measured['measured_voltage'] >= VOLTAGE_HIT)\n"
        "    & (measured['measured_decomp_C'] >= DECOMP_HIT)\n"
        ")\n"
        "model_hit_rate = measured['hit'].mean()\n"
        "print(f'top-{len(measured)} synthesis hit-rate: {model_hit_rate:.1%}')\n"
        "\n"
        "# Random-baseline hit rate from the unranked spinel set, for comparison.\n"
        "BASELINE_HIT_RATE = 0.15  # TODO: empirically establish or assume from literature\n"
        "print(f'baseline hit-rate (random selection): {BASELINE_HIT_RATE:.1%}')\n"
        "print(f'lift: {model_hit_rate - BASELINE_HIT_RATE:+.2%}')\n"
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
        "    model_metric_value = float(model_hit_rate)\n"
        "    baseline_metric_value = float(BASELINE_HIT_RATE)\n"
        "except NameError:\n"
        "    model_metric_value = None\n"
        "    baseline_metric_value = None\n"
        "\n"
        "if model_metric_value is None or baseline_metric_value is None:\n"
        "    raise NotImplementedError('Run the evaluation step first, or set values manually.')\n"
        "\n"
        "lift = model_metric_value - baseline_metric_value\n"
        "print(f'metric (model):    {model_metric_value:.4f}')\n"
        "print(f'metric (baseline): {baseline_metric_value:.4f}')\n"
        "print(f'lift:              {lift:+.4f}')\n"
        "\n"
        "MIN_LIFT_FOR_HYPOTHESIS = 0.15  # TODO: align with falsifiability threshold\n"
        "assert lift >= MIN_LIFT_FOR_HYPOTHESIS, (\n"
        "    f'Lift {lift:+.4f} below threshold {MIN_LIFT_FOR_HYPOTHESIS} — hypothesis falsified.'\n"
        ")\n"
        "print('falsifiability check PASSED')\n"
    )
