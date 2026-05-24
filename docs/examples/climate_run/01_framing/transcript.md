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
