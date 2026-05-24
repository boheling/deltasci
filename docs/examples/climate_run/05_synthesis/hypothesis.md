# Sahel precipitation-extreme downscaling: ERA5+CMIP6 hybrid neural emulator with water-budget regularization

> Audit summary: ✓ 6 verified

A vision-transformer neural emulator trained on ERA5 dynamics and CMIP6 forcing fields, with extreme-aware loss and a soft water-budget conservation regularizer, achieves Brier skill score > 0.15 over climatology for 95th-percentile daily Sahel precipitation 2019-2023, with 10-year return-period MAE < 30% and skill exceeding quantile-mapped ERA5. Drought-regime OOD evaluation on 1968-1990 reanalysis is reported separately as the OOD-risk benchmark.

## Domain grounding
- **mechanism**: Coarse-resolution products (ERA5, CMIP6) systematically under-resolve Sahel convective rainfall extremes; convection-permitting models reduce these biases but are too costly for routine use; a learned emulator can carry CP-class skill at coarse-model cost. ERA5 carries the dynamic context the GCM-resolution forcing fields lack.
- **unmet_need**: Calibrated, verifiable Sahel precipitation-extreme projections for flood risk + agricultural decision support, where conventional quantile-mapping fails on the upper tail.
- **expected_impact**: Decision-relevant extreme-precipitation forecasts and projections at gauge-meaningful resolution for West African meteorological offices and agricultural planners.

## Technical approach
- **core_method**: Vision-transformer (Swin-style) with per-day patch embedding over the Sahel domain; multi-channel input combining ERA5 dynamics + CMIP6 forcing + topography; extreme-aware focal MSE on log(1+P) plus soft water-budget penalty.
- **key_innovation**: Hybrid ERA5-dynamics + CMIP6-forcing input regime with explicit water-budget regularization for extremes; OOD evaluation on the 1968-1990 drought regime as a falsifiable test of generalization.
- **implementation_path**: Pangeo Zarr for ERA5 + CMIP6 → gauge QC pipeline → Sahel patch extraction → Swin transformer with multi-channel input + 3-component loss → 2003-2018 train / 2019-2023 in-distribution test / 1968-1990 OOD test → comparison vs climatology / persistence / quantile-mapping / CMIP6 mean / bilinear baselines.

## Falsifiability
- **prediction**: Neural emulator achieves higher Brier skill score on 95th-percentile daily Sahel P (2019-2023) than all baselines including quantile-mapped ERA5.
- **threshold**: Brier skill score > 0.15 over climatology baseline, AND 10-year return-period MAE < 30%, AND skill > quantile-mapped ERA5 on both metrics, AND OOD drought-regime degradation < 50%.
- **null outcome**: Brier skill < 0.05 OR worse than quantile-mapping OR OOD degradation > 70% falsifies the hypothesis.

## Feasibility scores
- **data_availability**: 3/5 — ERA5 + CMIP6 + topography are well-curated and free; gauge data for the Sahel requires institutional partnerships and language work to access West African meteorological office archives.
- **technical_feasibility**: 4/5 — Swin transformer + Pangeo + xarray are well-trodden engineering; ~3-4 weeks of focused work after data engineering.
- **physical_consistency**: 4/5 — Water-budget regularization makes the emulator physically grounded in a way pure pixel-MSE downscalers are not.
- **novelty**: 3/5 — Vision-transformer downscaling is incremental; the water-budget regularization + OOD-on-drought-regime evaluation are the contributions.
- **decision_relevance**: 4/5 — Directly addresses the decision needs of West African meteorological offices and adaptation planners, who currently rely on bias-corrected coarse-grid forecasts that miss extremes.
- **overall (weighted)**: 3.66

## Evidence trail

### AI-confident foundations (well-covered)
| # | Type | Claim | Source |
|---|------|-------|--------|
| 1 | published-evidence | ERA5 is the canonical fifth-generation ECMWF reanalysis, with hourly fields at ~31km resolution; precipitation specifically inherits known biases from the underlying IFS model and assimilation scheme. | Hersbach et al 2020, QJRMS 146:1999 — ERA5 |
| 2 | published-evidence | The Coupled Model Intercomparison Project Phase 6 provides standardized GCM outputs across many models and scenarios, but native resolution (typically 100-250km) under-resolves convective rainfall over the Sahel. | Eyring et al 2016, GMD 9:1937 — CMIP6 design |
| 3 | published-evidence | Convection-permitting (~4km) regional models reduce systematic precipitation biases over Africa relative to coarse-resolution parameterized convection, but cost is prohibitive for routine downscaling. | Stratton et al 2018, J Climate 31:3485 — CP4-Africa |
| 4 | established-guideline | Heavy precipitation events over land have intensified over the late 20th and early 21st centuries with high confidence, with regional patterns including Sahel attribution complicated by dust-aerosol-monsoon coupling. | IPCC AR6 WG1 Chapter 11 (2021) |
| 5 | observation | Standard quantile-mapping bias correction performs well on the central body of the precipitation distribution but underperforms on the upper tail (extremes), which are exactly what matters for flood risk and agricultural planning. | — |
| 6 | engineering-precedent | xarray is the canonical Python library for labeled multi-dimensional climate data; combined with dask it scales to ERA5-class workflows. | github.com/pydata/xarray |
| 7 | engineering-precedent | Pangeo provides cloud-hosted analysis-ready ERA5 and CMIP6 data on Zarr with consistent geospatial conventions. | https://pangeo.io and github.com/pangeo-data |
| 8 | observation | Per-day Sahel patch is ~600x400 grid points at 10km — small. Per-day forward pass is sub-second on a single A100. Training over 20 years of daily data with multiple ensemble members of CMIP6 forcing fits on a single A100 in days, not weeks. | — |
| 9 | observation | Out-of-distribution risk — future climate is, by definition, OOD relative to ERA5 training. The model's behavior on the tail of the future distribution is the key open question and cannot be benchmark-validated within the historical record. | — |
| 10 | observation | Apparent skill that is in fact climatology / persistence skill is a documented failure mode of climate ML papers; baselines must include 'climatological mean precipitation by month' and 'previous-day persistence'. | — |
| 11 | observation | Mean precipitation skill (correlation, RMSE) is the wrong target — the hypothesis cares about extremes. The right metrics are: 95th and 99th percentile bias, return-period (10-year, 20-year) bias, and exceedance-frequency accuracy at gauge-defined thresholds. | — |
| 12 | observation | Climatology-by-month and persistence-by-day are the non-negotiable baselines. 'Quantile-mapped ERA5' is the strong baseline that bias-correction-based methods set; 'CMIP6 ensemble mean' is the GCM baseline. | — |
| 13 | observation | Single A100; ~1-3 days of training per ensemble member. ~2-3 weeks of analyst time after the gauge data engineering pipeline is built. | — |

### Likely-reliable, please verify (sparse coverage)
| # | Type | Claim | Source |
|---|------|-------|--------|
| 1 | observation | Rain gauge density across the Sahel during 2003-2023 is extremely uneven; specific station counts I would hedge on, but it is well-known that the Western Sahel has better coverage than the Eastern Sahel, and many gauges have data gaps. | — |
| 2 | published-evidence | Vision-transformer and Fourier-neural-operator architectures have demonstrated competitive global weather/climate emulation, with FourCastNet and ClimaX as canonical recent examples — though I would hedge on which specific architectures dominate the regional-downscaling benchmarks. | Pathak et al 2022, arXiv 2202.11214 — FourCastNet; Nguyen et al 2023, arXiv 2301.10343 — ClimaX |
| 3 | published-evidence | Earlier deep-learning downscaling work (DeepSD-style super-resolution networks; Baño-Medina convolutional approaches) demonstrated that simple architectures already outperform classical statistical downscaling for the central distribution, but extremes remained underperformed. | Vandal et al 2017, KDD — DeepSD; Baño-Medina et al 2020, GMD 13:2109 — DL statistical downscaling |
| 4 | observation | Skill on extremes is hard to verify with sparse rain gauges. Per-station verification has wide CIs; aggregating across stations introduces spatial autocorrelation that benchmarks rarely handle correctly. | — |
| 5 | published-evidence | Sahel rainfall is non-stationary on multi-decadal timescales, with the 1968-1990 drought followed by partial recovery. Training on the 2003-2023 monsoon window captures only the post-recovery regime; extrapolation to drought-regime climates is OOD. | Nicholson 2013, ISRN Meteorology — Sahel hydroclimate review; specific recent attribution papers I'd hedge on |
| 6 | observation | Realistic Brier skill score for 95th-percentile daily P over rain-gauge networks for a well-tuned downscaler is plausibly 0.15-0.30 over climatology; below 0.10 would be disappointing. Specific recent benchmark numbers I'd hedge on. | — |

### Researcher knowledge required

**Knowledge gaps the AI flagged for researcher input:**

1. _(lab-tribal-knowledge)_ Does the project have access to a curated, quality-controlled gauge network for the 2003-2023 study window, or only the publicly-available GHCN-Daily / TRMM-validated subset? Local quality control is the difference between meaningful and meaningless skill numbers.
2. _(non-english-literature)_ Are there French-language Sahel hydrology references (CILSS, AGRHYMET, IRD reports) that should be incorporated? Substantial gauge-network and forecast-evaluation work for West Africa is published in French and may be under-represented in my training distribution.
3. _(niche-subfield)_ Are there published neural emulators specifically for Sahel precipitation extremes I should be aware of? I can recall global emulators and other-region downscalers but no Sahel-specific architecture.
4. _(lab-tribal-knowledge)_ Is the gauge dataset for 2019-2023 already QC'd and station-matched to coarse-grid centers, or does that pipeline still need building? This is 1-3 months of data engineering on the critical path.
5. _(non-english-literature)_ Are there West African meteorological office reports (ASECNA, Direction Nationale de la Météorologie de Mali/Niger/etc.) with gauge data that should be incorporated alongside or instead of GHCN-Daily?
6. _(unpublished-or-pilot-data)_ Have prior runs over the Sahel been done at the same lab? Pilot effect-size estimates would calibrate the realistic-vs-aspirational framing of the 0.15 Brier-skill threshold.

**Novel syntheses the AI is proposing (not stated by any single source):**

1. Using ERA5-derived dynamic context (low-level moisture, vertical wind shear, convective precipitation flux) AS INPUT alongside CMIP6 forcing scenario fields, with the network trained to map to gauge-observed precipitation extremes, is an unusual joint training regime not commonly seen in published downscaling work. — _combining ERA5 dynamics with CMIP6 forcing in a single learned downscaler is not standard — most existing work uses one or the other but not both as paired inputs_
2. Adding a soft water-budget conservation loss (P - E - dS/dt = R, where the network's downscaled P must be consistent with the coarse-scale water balance from ERA5) regularizes against physically-implausible artifacts, particularly in the extremes the hypothesis cares about. — _physics-informed losses for water-budget consistency at downscaled resolution is not standard practice in current downscaling DL — most use pure pixel-MSE or distribution-matching_
3. Reserving 1968-1990 drought-regime ERA5 reanalysis (which exists, derived from earlier 5-rean products) as a held-out OOD test cohort makes the OOD risk falsifiable instead of hand-waved away. — _explicit OOD evaluation as a separate experimental arm is not standard in downscaling DL — most papers report single-period skill_

## Citation audit

### ✓ Verified (6)
| Auditor | AI claim | Verified record |
|---------|----------|-----------------|
| github | github.com/pydata/xarray | pydata/xarray — https://github.com/pydata/xarray |
| arxiv | Pathak et al 2022, arXiv 2202.11214 | FourCastNet: A Global Data-driven High-resolution Weather Model using Adaptive Fourier Neural Operators — https://arxiv.org/abs/2202.11214 |
| arxiv | Nguyen et al 2023, arXiv 2301.10343 — ClimaX | ClimaX: A foundation model for weather and climate — https://arxiv.org/abs/2301.10343 |
| arxiv | Pathak et al 2022, arXiv 2202.11214 | FourCastNet: A Global Data-driven High-resolution Weather Model using Adaptive Fourier Neural Operators — https://arxiv.org/abs/2202.11214 |
| arxiv | Nguyen et al 2023, arXiv 2301.10343 — ClimaX | ClimaX: A foundation model for weather and climate — https://arxiv.org/abs/2301.10343 |
| arxiv | Pathak et al 2022, arXiv 2202.11214 | FourCastNet: A Global Data-driven High-resolution Weather Model using Adaptive Fourier Neural Operators — https://arxiv.org/abs/2202.11214 |

## Epistemic summary
- well-covered claims: **13**
- sparse-coverage claims: **6**
- knowledge gaps flagged: **6**
- novel syntheses proposed: **3**

_Generated by DeltaScience 0.3.0 :: pack climate v0.1.0 :: mockllm/mock-llm-v1_