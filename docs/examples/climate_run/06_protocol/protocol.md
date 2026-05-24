# Experiment plan — Sahel extreme-P downscaler: ERA5+CMIP6 Swin transformer with water-budget regularization

Train Swin-style ViT to downscale Sahel daily P from coarse-grid (ERA5 ~31km, CMIP6 ~100-250km) to 10km, evaluated against gauge data (2019-2023 in-distribution + 1968-1990 OOD) using extreme-focused metrics.

## Data acquisition
- **Primary dataset**: ERA5 hourly + CMIP6 historical/SSP for Sahel domain via Pangeo Zarr; GHCN-Daily for gauge data; West African meteorological office archives for supplementary gauge data.
- **Accession / URL**: https://pangeo.io ; https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily
- **Access constraints**: ERA5 + GHCN free; CMIP6 free via Earth System Grid; West African office data requires institutional MOU.
- **Fallback datasets**: NOAA 20CRv3 reanalysis for OOD drought-regime extension, TRMM/GPM satellite precipitation for spatial verification

## Steps

### 1. Data acquisition + tiling
Pull ERA5 + CMIP6 + topography from Pangeo; tile to per-day Sahel patches.
- **Inputs**: Pangeo Zarr
- **Outputs**: patch tensors
- **Methods cited**: github.com/pydata/xarray, https://pangeo.io

### 2. Gauge QC pipeline
GHCN-Daily QC, station-matching to grid cells, supplement with West African office archives.
- **Inputs**: GHCN-Daily, office archives
- **Outputs**: QC'd gauge timeseries

### 3. Architecture + losses
Swin transformer with multi-channel input; 3-component loss (pixel MSE on log(1+P) + extreme focal + water-budget penalty).
- **Inputs**: patches, gauge labels
- **Outputs**: model
- **Methods cited**: Pathak et al 2022, arXiv 2202.11214 — FourCastNet, Nguyen et al 2023, arXiv 2301.10343 — ClimaX

### 4. Train / in-dist eval / OOD eval
Train 2003-2018; eval 2019-2023; OOD eval on 1968-1990 reanalysis-back-extension.
- **Inputs**: model
- **Outputs**: metrics

### 5. Baselines
Climatology, persistence, quantile-mapped ERA5, CMIP6 ensemble mean, bilinear ERA5 interpolation.
- **Inputs**: data
- **Outputs**: baseline metrics

### 6. Reporting + decision-relevance
Brier skill score + 10-year return-period MAE + spatial skill maps; compare vs all baselines stratified by season + station density.
- **Inputs**: metrics
- **Outputs**: paper, skill maps
- **Methods cited**: IPCC AR6 WG1 Chapter 11

## Evaluation
- **Primary metric**: Brier skill score for 95th-percentile daily P (2019-2023 in-distribution; gauge-defined thresholds)
- **Success threshold**: Brier skill score > 0.15 over climatology baseline AND 10-year return-period MAE < 30% AND skill > quantile-mapped ERA5 baseline AND OOD drought-regime skill degradation < 50%
- **Null outcome**: Brier skill < 0.05 OR worse than quantile-mapping OR OOD degradation > 70% falsifies
- **Baselines**: climatology-by-month, persistence-by-day, quantile-mapped ERA5, CMIP6 ensemble mean, bilinear ERA5 interpolation

## Compute
- **Hardware**: 1× A100 (40GB)
- **Estimated runtime**: 1-3 days per ensemble member
- **Storage**: ~5TB ERA5 + 2TB CMIP6 (cached on Pangeo)
- **Cost estimate**: ~$300 GPU + Pangeo cloud egress

## Timeline
Data engineering 4-6 weeks (mostly gauge QC + West African office MOU). Modeling + eval 4-6 weeks.

## Sample-size justification
20 years × 365 days × ~600×400 grid points = ~1.7B training pixels per channel. Effective sample size for extremes is much smaller (~365 × 20 × 5% = 3650 days with extreme events somewhere in the patch); sufficient for the proposed Brier skill targets at gauge density.