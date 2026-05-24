# Co-Reasoning Transcript

**Pack:** `climate`

**Idea:** Train a neural emulator on ERA5 + CMIP6 outputs to downscale precipitation extremes over the Sahel from 100km to 10km, and evaluate against in-situ rain gauge measurements during the 2003-2023 monsoon seasons.

## domain_r1 — domain_scientist

The hypothesis sits on a heavily-studied physical system — Sahel monsoon precipitation — with a known set of biases shared across coarse-resolution products.

[CLAIM type=published-evidence coverage=well-covered source="Hersbach et al 2020, QJRMS 146:1999 — ERA5"]ERA5 is the canonical fifth-generation ECMWF reanalysis, with hourly fields at ~31km resolution; precipitation specifically inherits known biases from the underlying IFS model and assimilation scheme.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Eyring et al 2016, GMD 9:1937 — CMIP6 design"]The Coupled Model Intercomparison Project Phase 6 provides standardized GCM outputs across many models and scenarios, but native resolution (typically 100-250km) under-resolves convective rainfall over the Sahel.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Stratton et al 2018, J Climate 31:3485 — CP4-Africa"]Convection-permitting (~4km) regional models reduce systematic precipitation biases over Africa relative to coarse-resolution parameterized convection, but cost is prohibitive for routine downscaling.[/CLAIM]

[CLAIM type=established-guideline coverage=well-covered source="IPCC AR6 WG1 Chapter 11 (2021)"]Heavy precipitation events over land have intensified over the late 20th and early 21st centuries with high confidence, with regional patterns including Sahel attribution complicated by dust-aerosol-monsoon coupling.[/CLAIM]

[CLAIM type=observation coverage=sparse source=""]Rain gauge density across the Sahel during 2003-2023 is extremely uneven; specific station counts I would hedge on, but it is well-known that the Western Sahel has better coverage than the Eastern Sahel, and many gauges have data gaps.[/CLAIM]

The unmet need is calibrated, verifiable downscaling of precipitation extremes over a region where conventional bias-correction fails on the tails:

[CLAIM type=observation coverage=well-covered source=""]Standard quantile-mapping bias correction performs well on the central body of the precipitation distribution but underperforms on the upper tail (extremes), which are exactly what matters for flood risk and agricultural planning.[/CLAIM]

[NOVEL_SYNTHESIS rationale="combining ERA5 dynamics with CMIP6 forcing in a single learned downscaler is not standard — most existing work uses one or the other but not both as paired inputs"]Using ERA5-derived dynamic context (low-level moisture, vertical wind shear, convective precipitation flux) AS INPUT alongside CMIP6 forcing scenario fields, with the network trained to map to gauge-observed precipitation extremes, is an unusual joint training regime not commonly seen in published downscaling work.[/NOVEL_SYNTHESIS]

[KNOWLEDGE_GAP category=lab-tribal-knowledge]Does the project have access to a curated, quality-controlled gauge network for the 2003-2023 study window, or only the publicly-available GHCN-Daily / TRMM-validated subset? Local quality control is the difference between meaningful and meaningless skill numbers.[/KNOWLEDGE_GAP]

[KNOWLEDGE_GAP category=non-english-literature]Are there French-language Sahel hydrology references (CILSS, AGRHYMET, IRD reports) that should be incorporated? Substantial gauge-network and forecast-evaluation work for West Africa is published in French and may be under-represented in my training distribution.[/KNOWLEDGE_GAP]

### Evidence collected
- **[published-evidence · well-covered]** ERA5 is the canonical fifth-generation ECMWF reanalysis, with hourly fields at ~31km resolution; precipitation specifically inherits known biases from the underlying IFS model and assimilation scheme. — _Hersbach et al 2020, QJRMS 146:1999 — ERA5_
- **[published-evidence · well-covered]** The Coupled Model Intercomparison Project Phase 6 provides standardized GCM outputs across many models and scenarios, but native resolution (typically 100-250km) under-resolves convective rainfall over the Sahel. — _Eyring et al 2016, GMD 9:1937 — CMIP6 design_
- **[published-evidence · well-covered]** Convection-permitting (~4km) regional models reduce systematic precipitation biases over Africa relative to coarse-resolution parameterized convection, but cost is prohibitive for routine downscaling. — _Stratton et al 2018, J Climate 31:3485 — CP4-Africa_
- **[established-guideline · well-covered]** Heavy precipitation events over land have intensified over the late 20th and early 21st centuries with high confidence, with regional patterns including Sahel attribution complicated by dust-aerosol-monsoon coupling. — _IPCC AR6 WG1 Chapter 11 (2021)_
- **[observation · sparse]** Rain gauge density across the Sahel during 2003-2023 is extremely uneven; specific station counts I would hedge on, but it is well-known that the Western Sahel has better coverage than the Eastern Sahel, and many gauges have data gaps. — _—_
- **[observation · well-covered]** Standard quantile-mapping bias correction performs well on the central body of the precipitation distribution but underperforms on the upper tail (extremes), which are exactly what matters for flood risk and agricultural planning. — _—_

### Knowledge gaps flagged for researcher
- (lab-tribal-knowledge) Does the project have access to a curated, quality-controlled gauge network for the 2003-2023 study window, or only the publicly-available GHCN-Daily / TRMM-validated subset? Local quality control is the difference between meaningful and meaningless skill numbers.
- (non-english-literature) Are there French-language Sahel hydrology references (CILSS, AGRHYMET, IRD reports) that should be incorporated? Substantial gauge-network and forecast-evaluation work for West Africa is published in French and may be under-represented in my training distribution.

### Novel syntheses proposed
- Using ERA5-derived dynamic context (low-level moisture, vertical wind shear, convective precipitation flux) AS INPUT alongside CMIP6 forcing scenario fields, with the network trained to map to gauge-observed precipitation extremes, is an unusual joint training regime not commonly seen in published downscaling work. — _combining ERA5 dynamics with CMIP6 forcing in a single learned downscaler is not standard — most existing work uses one or the other but not both as paired inputs_

## engineer_r1 — ml_engineer

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

### Evidence collected
- **[engineering-precedent · well-covered]** xarray is the canonical Python library for labeled multi-dimensional climate data; combined with dask it scales to ERA5-class workflows. — _github.com/pydata/xarray_
- **[engineering-precedent · well-covered]** Pangeo provides cloud-hosted analysis-ready ERA5 and CMIP6 data on Zarr with consistent geospatial conventions. — _https://pangeo.io and github.com/pangeo-data_
- **[published-evidence · sparse]** Vision-transformer and Fourier-neural-operator architectures have demonstrated competitive global weather/climate emulation, with FourCastNet and ClimaX as canonical recent examples — though I would hedge on which specific architectures dominate the regional-downscaling benchmarks. — _Pathak et al 2022, arXiv 2202.11214 — FourCastNet; Nguyen et al 2023, arXiv 2301.10343 — ClimaX_
- **[published-evidence · sparse]** Earlier deep-learning downscaling work (DeepSD-style super-resolution networks; Baño-Medina convolutional approaches) demonstrated that simple architectures already outperform classical statistical downscaling for the central distribution, but extremes remained underperformed. — _Vandal et al 2017, KDD — DeepSD; Baño-Medina et al 2020, GMD 13:2109 — DL statistical downscaling_
- **[observation · well-covered]** Per-day Sahel patch is ~600x400 grid points at 10km — small. Per-day forward pass is sub-second on a single A100. Training over 20 years of daily data with multiple ensemble members of CMIP6 forcing fits on a single A100 in days, not weeks. — _—_
- **[observation · well-covered]** Out-of-distribution risk — future climate is, by definition, OOD relative to ERA5 training. The model's behavior on the tail of the future distribution is the key open question and cannot be benchmark-validated within the historical record. — _—_
- **[observation · sparse]** Skill on extremes is hard to verify with sparse rain gauges. Per-station verification has wide CIs; aggregating across stations introduces spatial autocorrelation that benchmarks rarely handle correctly. — _—_
- **[observation · well-covered]** Apparent skill that is in fact climatology / persistence skill is a documented failure mode of climate ML papers; baselines must include 'climatological mean precipitation by month' and 'previous-day persistence'. — _—_

### Knowledge gaps flagged for researcher
- (niche-subfield) Are there published neural emulators specifically for Sahel precipitation extremes I should be aware of? I can recall global emulators and other-region downscalers but no Sahel-specific architecture.

### Novel syntheses proposed
- Adding a soft water-budget conservation loss (P - E - dS/dt = R, where the network's downscaled P must be consistent with the coarse-scale water balance from ERA5) regularizes against physically-implausible artifacts, particularly in the extremes the hypothesis cares about. — _physics-informed losses for water-budget consistency at downscaled resolution is not standard practice in current downscaling DL — most use pure pixel-MSE or distribution-matching_

## domain_r2 — domain_scientist

The architecture sketch is reasonable. Three adjustments before this is a defensible hypothesis.

**1. The right outcome and the right baseline.**

[CLAIM type=observation coverage=well-covered source=""]Mean precipitation skill (correlation, RMSE) is the wrong target — the hypothesis cares about extremes. The right metrics are: 95th and 99th percentile bias, return-period (10-year, 20-year) bias, and exceedance-frequency accuracy at gauge-defined thresholds.[/CLAIM]

[CLAIM type=observation coverage=well-covered source=""]Climatology-by-month and persistence-by-day are the non-negotiable baselines. 'Quantile-mapped ERA5' is the strong baseline that bias-correction-based methods set; 'CMIP6 ensemble mean' is the GCM baseline.[/CLAIM]

**2. Stationarity and OOD.**

[CLAIM type=published-evidence coverage=sparse source="Nicholson 2013, ISRN Meteorology — Sahel hydroclimate review; specific recent attribution papers I'd hedge on"]Sahel rainfall is non-stationary on multi-decadal timescales, with the 1968-1990 drought followed by partial recovery. Training on the 2003-2023 monsoon window captures only the post-recovery regime; extrapolation to drought-regime climates is OOD.[/CLAIM]

[NOVEL_SYNTHESIS rationale="explicit OOD evaluation as a separate experimental arm is not standard in downscaling DL — most papers report single-period skill"]Reserving 1968-1990 drought-regime ERA5 reanalysis (which exists, derived from earlier 5-rean products) as a held-out OOD test cohort makes the OOD risk falsifiable instead of hand-waved away.[/NOVEL_SYNTHESIS]

**3. The falsifiable prediction.**

The hypothesis should commit to: a neural emulator trained on 2003-2018 ERA5 + CMIP6 + topography, evaluated on 2019-2023 gauge data, achieves Brier skill score > 0.15 (over climatology baseline) for 95th-percentile daily precipitation events, AND mean absolute error on 10-year return-period magnitude < 30%, AND demonstrably better than quantile-mapped ERA5 baseline on the same metrics. Brier skill < 0.05 OR worse than quantile-mapping falsifies it.

[KNOWLEDGE_GAP category=lab-tribal-knowledge]Is the gauge dataset for 2019-2023 already QC'd and station-matched to coarse-grid centers, or does that pipeline still need building? This is 1-3 months of data engineering on the critical path.[/KNOWLEDGE_GAP]

[KNOWLEDGE_GAP category=non-english-literature]Are there West African meteorological office reports (ASECNA, Direction Nationale de la Météorologie de Mali/Niger/etc.) with gauge data that should be incorporated alongside or instead of GHCN-Daily?[/KNOWLEDGE_GAP]

### Evidence collected
- **[observation · well-covered]** Mean precipitation skill (correlation, RMSE) is the wrong target — the hypothesis cares about extremes. The right metrics are: 95th and 99th percentile bias, return-period (10-year, 20-year) bias, and exceedance-frequency accuracy at gauge-defined thresholds. — _—_
- **[observation · well-covered]** Climatology-by-month and persistence-by-day are the non-negotiable baselines. 'Quantile-mapped ERA5' is the strong baseline that bias-correction-based methods set; 'CMIP6 ensemble mean' is the GCM baseline. — _—_
- **[published-evidence · sparse]** Sahel rainfall is non-stationary on multi-decadal timescales, with the 1968-1990 drought followed by partial recovery. Training on the 2003-2023 monsoon window captures only the post-recovery regime; extrapolation to drought-regime climates is OOD. — _Nicholson 2013, ISRN Meteorology — Sahel hydroclimate review; specific recent attribution papers I'd hedge on_

### Knowledge gaps flagged for researcher
- (lab-tribal-knowledge) Is the gauge dataset for 2019-2023 already QC'd and station-matched to coarse-grid centers, or does that pipeline still need building? This is 1-3 months of data engineering on the critical path.
- (non-english-literature) Are there West African meteorological office reports (ASECNA, Direction Nationale de la Météorologie de Mali/Niger/etc.) with gauge data that should be incorporated alongside or instead of GHCN-Daily?

### Novel syntheses proposed
- Reserving 1968-1990 drought-regime ERA5 reanalysis (which exists, derived from earlier 5-rean products) as a held-out OOD test cohort makes the OOD risk falsifiable instead of hand-waved away. — _explicit OOD evaluation as a separate experimental arm is not standard in downscaling DL — most papers report single-period skill_

## engineer_r2 — ml_engineer

Adopting the domain refinements. The pivot: extremes-focused metrics + drought-regime OOD evaluation. This changes the loss function and the data split materially.

**Architecture.**

Input: per-day patch [time, channel, H, W] = [365, ~12 channels, 600, 400] where channels are {ERA5 total precip, ERA5 850hPa moisture, ERA5 wind shear, ERA5 convective precip, CMIP6 forcing field for matching SSP, topography elevation, topography slope, climatological-monthly-mean P, day-of-year sin/cos, year-relative-to-1998}.

Output: per-day downscaled precipitation field at 10km, same H/W footprint.

Encoder: Vision-Transformer / Swin-style hierarchical attention with patch embedding at 4-pixel patches; 4 transformer stages; output head a 1×1 conv to single-channel precipitation rate.

Loss:
- L_pixel = MSE on log(1 + P) (variance-stabilizing transform standard in precipitation work)
- L_extreme = focal-style upweighting of pixels above the 95th percentile (per-grid-cell threshold from training-set climatology)
- L_water_budget = soft penalty on |sum(downscaled_P) - aggregated_ERA5_P| over each patch (water-budget consistency)
- L_total = λ_p · L_pixel + λ_e · L_extreme + λ_w · L_water_budget, with λ_p=1, λ_e=2, λ_w=0.3

**Training plan.**

1. Source: ERA5 hourly aggregated to daily, 2003-2023, Sahel domain. CMIP6 historical + SSP forcing for the same period from a multi-model ensemble. Pangeo-hosted Zarr.
2. Gauge data: GHCN-Daily for the in-domain stations, supplemented with West African office data where accessible.
3. Train: 2003-2018. Validate: 2019-2023 in-distribution. OOD test: 1968-1990 from earlier reanalysis (ERA5-back-extension or NOAA 20CRv3).
4. Baselines: climatology-by-month, persistence-by-day, quantile-mapped ERA5, CMIP6 ensemble mean, simple bilinear interpolation of ERA5 to 10km.

**Expected outcomes.**

[CLAIM type=observation coverage=sparse source=""]Realistic Brier skill score for 95th-percentile daily P over rain-gauge networks for a well-tuned downscaler is plausibly 0.15-0.30 over climatology; below 0.10 would be disappointing. Specific recent benchmark numbers I'd hedge on.[/CLAIM]

[KNOWLEDGE_GAP category=unpublished-or-pilot-data]Have prior runs over the Sahel been done at the same lab? Pilot effect-size estimates would calibrate the realistic-vs-aspirational framing of the 0.15 Brier-skill threshold.[/KNOWLEDGE_GAP]

**Compute & timeline.**

[CLAIM type=observation coverage=well-covered source=""]Single A100; ~1-3 days of training per ensemble member. ~2-3 weeks of analyst time after the gauge data engineering pipeline is built.[/CLAIM]

### Evidence collected
- **[observation · sparse]** Realistic Brier skill score for 95th-percentile daily P over rain-gauge networks for a well-tuned downscaler is plausibly 0.15-0.30 over climatology; below 0.10 would be disappointing. Specific recent benchmark numbers I'd hedge on. — _—_
- **[observation · well-covered]** Single A100; ~1-3 days of training per ensemble member. ~2-3 weeks of analyst time after the gauge data engineering pipeline is built. — _—_

### Knowledge gaps flagged for researcher
- (unpublished-or-pilot-data) Have prior runs over the Sahel been done at the same lab? Pilot effect-size estimates would calibrate the realistic-vs-aspirational framing of the 0.15 Brier-skill threshold.
