The neural-emulator family has matured rapidly in the last 3 years; the engineering question is which architecture and which physics-informed losses to combine.

**Data representation.**

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/pydata/xarray"]xarray is the canonical Python library for labeled multi-dimensional climate data; combined with dask it scales to ERA5-class workflows.[/CLAIM]

[CLAIM type=engineering-precedent coverage=well-covered source="https://pangeo.io and github.com/pangeo-data"]Pangeo provides cloud-hosted analysis-ready ERA5 and CMIP6 data on Zarr with consistent geospatial conventions.[/CLAIM]

A natural construction: per-day patch over the Sahel domain (~30°W-30°E, 5°N-25°N), with ERA5 dynamics + CMIP6 forcing + topography + month/year embedding stacked as channels; output is a 10km-resolution precipitation field over the same patch.

**ML paradigm.**

[CLAIM type=published-evidence coverage=sparse source="Pathak et al 2022, arXiv 2202.11214 — FourCastNet; Nguyen et al 2023, arXiv 2301.10343 — ClimaX"]Vision-transformer and Fourier-neural-operator architectures have demonstrated competitive global weather/climate emulation, with FourCastNet and ClimaX as canonical recent examples — though I would hedge on which specific architectures dominate the regional-downscaling benchmarks.[/CLAIM]

[CLAIM type=published-evidence coverage=sparse source="Vandal et al 2017, KDD — DeepSD; Baño-Medina et al 2020, GMD 13:2109 — DL statistical downscaling"]Earlier deep-learning downscaling work (DeepSD-style super-resolution networks; Baño-Medina convolutional approaches) demonstrated that simple architectures already outperform classical statistical downscaling for the central distribution, but extremes remained underperformed.[/CLAIM]

**Existing implementations.**

[KNOWLEDGE_GAP category=niche-subfield]Are there published neural emulators specifically for Sahel precipitation extremes I should be aware of? I can recall global emulators and other-region downscalers but no Sahel-specific architecture.[/KNOWLEDGE_GAP]

**Compute.**

[CLAIM type=observation coverage=well-covered source=""]Per-day Sahel patch is ~600x400 grid points at 10km — small. Per-day forward pass is sub-second on a single A100. Training over 20 years of daily data with multiple ensemble members of CMIP6 forcing fits on a single A100 in days, not weeks.[/CLAIM]

**Top three risks.**

1. [CLAIM type=observation coverage=well-covered source=""]Out-of-distribution risk — future climate is, by definition, OOD relative to ERA5 training. The model's behavior on the tail of the future distribution is the key open question and cannot be benchmark-validated within the historical record.[/CLAIM]

2. [CLAIM type=observation coverage=sparse source=""]Skill on extremes is hard to verify with sparse rain gauges. Per-station verification has wide CIs; aggregating across stations introduces spatial autocorrelation that benchmarks rarely handle correctly.[/CLAIM]

3. [CLAIM type=observation coverage=well-covered source=""]Apparent skill that is in fact climatology / persistence skill is a documented failure mode of climate ML papers; baselines must include 'climatological mean precipitation by month' and 'previous-day persistence'.[/CLAIM]

[NOVEL_SYNTHESIS rationale="physics-informed losses for water-budget consistency at downscaled resolution is not standard practice in current downscaling DL — most use pure pixel-MSE or distribution-matching"]Adding a soft water-budget conservation loss (P - E - dS/dt = R, where the network's downscaled P must be consistent with the coarse-scale water balance from ERA5) regularizes against physically-implausible artifacts, particularly in the extremes the hypothesis cares about.[/NOVEL_SYNTHESIS]
