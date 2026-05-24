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
