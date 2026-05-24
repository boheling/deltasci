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
