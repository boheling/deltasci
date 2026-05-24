"""Climate notebook scaffold (v0.3.1 — canonical code, keyword-routed)."""

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
        "# === Imports — climate / earth-system stack ===\n"
        "import numpy as np\n"
        "import pandas as pd\n"
        "import xarray as xr\n"
        "import matplotlib.pyplot as plt\n"
        "# import cartopy.crs as ccrs\n"
        "# import dask.array as da\n"
        "\n"
        "import torch\n"
        "import torch.nn as nn\n"
        "from torch.utils.data import Dataset, DataLoader\n"
        "\n"
        "from sklearn.metrics import mean_absolute_error, brier_score_loss\n"
        "\n"
        "RANDOM_SEED = 0\n"
        "np.random.seed(RANDOM_SEED)\n"
        "torch.manual_seed(RANDOM_SEED)\n"
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
        "# === Data acquisition (Pangeo / xarray canonical pattern) ===\n"
        f"PRIMARY_DATASET = {accession!r}\n"
        "\n"
        "# Pangeo-hosted ARCO-ERA5 (public, anonymous-readable):\n"
        "# ERA5_URL = 'gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3'\n"
        "ERA5_URL = None  # TODO: set to the Pangeo ERA5 Zarr URL or your local path\n"
        "GAUGE_CSV = None  # TODO: set path to GHCN-Daily / institutional gauge CSV\n"
        "\n"
        "if ERA5_URL is None:\n"
        "    raise NotImplementedError(\n"
        "        f'Set ERA5_URL before continuing. Reference: {PRIMARY_DATASET}'\n"
        "    )\n"
        "\n"
        "ds = xr.open_zarr(ERA5_URL, chunks={'time': 240}, consolidated=True)\n"
        "print(f'opened: {ds.sizes}')\n"
        "print(f'variables: {list(ds.data_vars)[:8]} ...')\n"
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
    if any(k in name for k in ("data acquisition", "tiling", "tile", "subset", "patch")):
        return _step_subset(step)
    if any(k in name for k in ("gauge", "qc pipeline", "ghcn", "station")):
        return _step_gauges(step)
    if any(k in name for k in ("architect", "loss", "swin", "vit", "transformer", "model")):
        return _step_arch(step)
    if any(k in name for k in ("train", "fit", "validate", "ood")):
        return _step_train(step)
    if any(k in name for k in ("baseline",)):
        return _step_baselines(step)
    if any(k in name for k in ("report", "evaluat", "skill", "decision", "metric", "brier")):
        return _step_evaluate(step)
    return _step_generic(step)


def _step_subset(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Spatial + temporal subset of the ERA5 dataset (canonical xarray pattern).\n"
        "\n"
        "# Sahel domain — TODO: tune for your region of interest.\n"
        "LAT_BOUNDS = (5.0, 25.0)\n"
        "LON_BOUNDS = (-30.0, 30.0)\n"
        "TIME_BOUNDS = ('2003-01-01', '2023-12-31')  # TODO: align with study period\n"
        "VARIABLES = ['total_precipitation']  # TODO: add specific_humidity, u_wind, v_wind, etc.\n"
        "\n"
        "lat_var = 'latitude' if 'latitude' in ds.dims else 'lat'\n"
        "lon_var = 'longitude' if 'longitude' in ds.dims else 'lon'\n"
        "\n"
        "ds_sub = (\n"
        "    ds[VARIABLES]\n"
        "    .sel({lat_var: slice(*LAT_BOUNDS), lon_var: slice(*LON_BOUNDS)})\n"
        "    .sel(time=slice(*TIME_BOUNDS))\n"
        ")\n"
        "print(f'subset: {ds_sub.sizes}')\n"
        "\n"
        "# Temporal aggregation (hourly → daily).\n"
        "if 'precipitation' in VARIABLES[0]:\n"
        "    ds_daily = ds_sub.resample(time='1D').sum()\n"
        "else:\n"
        "    ds_daily = ds_sub.resample(time='1D').mean()\n"
        "print(f'daily aggregated: {ds_daily.sizes}')\n"
    )


def _step_gauges(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Gauge data QC + station-to-grid matching (canonical pattern).\n"
        "\n"
        "if GAUGE_CSV is None:\n"
        "    raise NotImplementedError('Set GAUGE_CSV (GHCN-Daily download or institutional file).')\n"
        "\n"
        "gauges = pd.read_csv(GAUGE_CSV, parse_dates=['date'])\n"
        "print(f'raw gauges: {len(gauges)} obs across {gauges[\"station_id\"].nunique()} stations')\n"
        "\n"
        "# Drop obvious flags. TODO: extend per your QC standards.\n"
        "valid = (gauges['precip_mm'] >= 0) & (gauges['precip_mm'] < 1000)\n"
        "gauges = gauges[valid].copy()\n"
        "\n"
        "# Require continuous coverage to avoid stations with massive gaps biasing the eval.\n"
        "MIN_DAYS_PER_STATION = 365 * 5\n"
        "counts = gauges.groupby('station_id').size()\n"
        "good_stations = counts[counts >= MIN_DAYS_PER_STATION].index\n"
        "gauges = gauges[gauges['station_id'].isin(good_stations)]\n"
        "print(f'after QC: {len(gauges)} obs across {gauges[\"station_id\"].nunique()} stations')\n"
        "\n"
        "# Station → grid-cell mapping (nearest-neighbor in lat/lon). TODO: assign each\n"
        "# station to its enclosing ds_daily grid cell using xr.DataArray.sel(method='nearest').\n"
        "station_meta = gauges.groupby('station_id')[['lat', 'lon']].first().reset_index()\n"
    )


def _step_arch(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Vision-CNN downscaler skeleton — real forward pass, real PixelShuffle upsample.\n"
        "# TODO: swap to a Swin transformer or U-Net per your hypothesis.\n"
        "\n"
        "HIDDEN_DIM = 64\n"
        "OUTPUT_RES_RATIO = 10  # 100km → 10km\n"
        "\n"
        "class Downscaler(nn.Module):\n"
        "    def __init__(self, in_channels, out_channels=1, hidden=HIDDEN_DIM):\n"
        "        super().__init__()\n"
        "        self.enc = nn.Sequential(\n"
        "            nn.Conv2d(in_channels, hidden, 3, padding=1), nn.ReLU(),\n"
        "            nn.Conv2d(hidden, hidden * 2, 3, padding=1), nn.ReLU(),\n"
        "            nn.Conv2d(hidden * 2, hidden * 4, 3, padding=1), nn.ReLU(),\n"
        "        )\n"
        "        self.dec = nn.Sequential(\n"
        "            nn.Conv2d(hidden * 4, out_channels * OUTPUT_RES_RATIO ** 2, 3, padding=1),\n"
        "            nn.PixelShuffle(OUTPUT_RES_RATIO),\n"
        "        )\n"
        "\n"
        "    def forward(self, x):\n"
        "        return self.dec(self.enc(x))\n"
        "\n"
        "def extreme_focal_mse(pred, target, threshold_per_pixel):\n"
        "    base = (pred - target) ** 2\n"
        "    extreme_mask = (target > threshold_per_pixel).float()\n"
        "    return (base * (1 + 2 * extreme_mask)).mean()\n"
    )


def _step_train(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Training loop — split by year (no time leakage), extreme-aware loss.\n"
        "\n"
        "TRAIN_YEARS = list(range(2003, 2019))\n"
        "VAL_YEARS = list(range(2019, 2024))\n"
        "OOD_YEARS = list(range(1968, 1991))  # drought regime\n"
        "\n"
        "EPOCHS = 20\n"
        "BATCH_SIZE = 8\n"
        "LR = 1e-3\n"
        "\n"
        "input_vars = ['total_precipitation']  # TODO: extend with dynamics + topography\n"
        "X_train = ds_daily[input_vars].sel(time=ds_daily.time.dt.year.isin(TRAIN_YEARS))\n"
        "X_val   = ds_daily[input_vars].sel(time=ds_daily.time.dt.year.isin(VAL_YEARS))\n"
        "print(f'train days: {X_train.sizes[\"time\"]}; val days: {X_val.sizes[\"time\"]}')\n"
        "\n"
        "model = Downscaler(in_channels=len(input_vars))\n"
        "optimizer = torch.optim.Adam(model.parameters(), lr=LR)\n"
        "\n"
        "# TODO: wire xarray patches → torch DataLoader with your tensor conversion strategy.\n"
        "raise NotImplementedError(\n"
        "    'Wire xarray patches → torch DataLoader. Loss + optimizer above are real; '\n"
        "    'the dataset-class plumbing depends on your patch-extraction strategy.'\n"
        ")\n"
    )


def _step_baselines(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Non-negotiable baselines: climatology, persistence, quantile-mapped ERA5.\n"
        "\n"
        "X_train = ds_daily[input_vars].sel(time=ds_daily.time.dt.year.isin(TRAIN_YEARS))\n"
        "\n"
        "climatology = X_train.groupby('time.month').mean()\n"
        "X_val_pred_clim = climatology.sel(month=ds_daily.time.dt.month).sel(\n"
        "    time=ds_daily.time.dt.year.isin(VAL_YEARS)\n"
        ")\n"
        "\n"
        "X_val_pred_persist = ds_daily[input_vars].shift(time=1).sel(\n"
        "    time=ds_daily.time.dt.year.isin(VAL_YEARS)\n"
        ")\n"
        "\n"
        "# Quantile-mapped ERA5 baseline — per-station quantile mapping at the gauge match.\n"
        "# TODO: implement\n"
        "# def quantile_map(era5_train_hist, gauge_train_hist, era5_test): ...\n"
        "\n"
        "print('baselines computed: climatology, persistence; quantile-mapping is TODO')\n"
    )


def _step_evaluate(step: ProtocolStep) -> str:
    return (
        f"# === Step {step.order}: {step.name} ===\n"
        "# Brier skill score on extreme thresholds + return-period MAE + lift over baselines.\n"
        "\n"
        "EXTREME_PCTILE = 95\n"
        "\n"
        "# TODO: replace with your model's predictions vs gauge truth.\n"
        "y_true = None        # binary: precip > station's 95th-pctile climatology threshold\n"
        "y_pred_model = None  # model's predicted exceedance probability\n"
        "y_pred_clim = None   # climatology baseline's predicted exceedance probability\n"
        "\n"
        "if y_true is None or y_pred_model is None or y_pred_clim is None:\n"
        "    raise NotImplementedError('Compute exceedance probabilities for held-out gauge stations.')\n"
        "\n"
        "brier_model = brier_score_loss(y_true, y_pred_model)\n"
        "brier_clim = brier_score_loss(y_true, y_pred_clim)\n"
        "brier_skill = 1 - brier_model / brier_clim\n"
        "print(f'Brier model: {brier_model:.4f}')\n"
        "print(f'Brier clim:  {brier_clim:.4f}')\n"
        "print(f'Brier skill score (vs climatology): {brier_skill:+.4f}')\n"
        "\n"
        "# 10-year return-period MAE — fit GEV per station, compare to model prediction. TODO.\n"
        "rp10_mae = None\n"
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
        "    model_metric_value = float(brier_skill)\n"
        "    baseline_metric_value = 0.0  # climatology baseline by construction\n"
        "except NameError:\n"
        "    model_metric_value = None\n"
        "    baseline_metric_value = None\n"
        "\n"
        "if model_metric_value is None or baseline_metric_value is None:\n"
        "    raise NotImplementedError('Run the evaluation step first.')\n"
        "\n"
        "lift = model_metric_value - baseline_metric_value\n"
        "print(f'Brier skill (model vs climatology): {model_metric_value:+.4f}')\n"
        "print(f'lift over climatology:              {lift:+.4f}')\n"
        "\n"
        "MIN_BRIER_SKILL = 0.15  # TODO: align with falsifiability threshold\n"
        "assert lift >= MIN_BRIER_SKILL, (\n"
        "    f'Brier skill {lift:+.4f} below threshold {MIN_BRIER_SKILL} — hypothesis falsified.'\n"
        ")\n"
        "print('falsifiability check PASSED')\n"
    )
