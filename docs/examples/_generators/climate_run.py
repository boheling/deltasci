"""Generate the climate example run."""

from __future__ import annotations

import json
from pathlib import Path

from deltasci import CoReasoner, Config, load_pack
from deltasci.cli import _write_outputs_staged
from deltasci.llm.mock import MockLLM


IDEA = (
    "Train a neural emulator on ERA5 + CMIP6 outputs to downscale precipitation "
    "extremes over the Sahel from 100km to 10km, and evaluate against in-situ rain "
    "gauge measurements during the 2003-2023 monsoon seasons."
)


DOMAIN_R1 = """\
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
"""


ENGINEER_R1 = """\
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
"""


DOMAIN_R2 = """\
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
"""


ENGINEER_R2 = """\
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
"""


SYNTHESIS_JSON = json.dumps({
    "title": "Sahel precipitation-extreme downscaling: ERA5+CMIP6 hybrid neural emulator with water-budget regularization",
    "statement": (
        "A vision-transformer neural emulator trained on ERA5 dynamics and CMIP6 forcing fields, with extreme-aware "
        "loss and a soft water-budget conservation regularizer, achieves Brier skill score > 0.15 over climatology "
        "for 95th-percentile daily Sahel precipitation 2019-2023, with 10-year return-period MAE < 30% and skill "
        "exceeding quantile-mapped ERA5. Drought-regime OOD evaluation on 1968-1990 reanalysis is reported "
        "separately as the OOD-risk benchmark."
    ),
    "domain_grounding": {
        "mechanism": "Coarse-resolution products (ERA5, CMIP6) systematically under-resolve Sahel convective rainfall extremes; convection-permitting models reduce these biases but are too costly for routine use; a learned emulator can carry CP-class skill at coarse-model cost. ERA5 carries the dynamic context the GCM-resolution forcing fields lack.",
        "unmet_need": "Calibrated, verifiable Sahel precipitation-extreme projections for flood risk + agricultural decision support, where conventional quantile-mapping fails on the upper tail.",
        "expected_impact": "Decision-relevant extreme-precipitation forecasts and projections at gauge-meaningful resolution for West African meteorological offices and agricultural planners."
    },
    "technical_approach": {
        "core_method": "Vision-transformer (Swin-style) with per-day patch embedding over the Sahel domain; multi-channel input combining ERA5 dynamics + CMIP6 forcing + topography; extreme-aware focal MSE on log(1+P) plus soft water-budget penalty.",
        "key_innovation": "Hybrid ERA5-dynamics + CMIP6-forcing input regime with explicit water-budget regularization for extremes; OOD evaluation on the 1968-1990 drought regime as a falsifiable test of generalization.",
        "implementation_path": "Pangeo Zarr for ERA5 + CMIP6 → gauge QC pipeline → Sahel patch extraction → Swin transformer with multi-channel input + 3-component loss → 2003-2018 train / 2019-2023 in-distribution test / 1968-1990 OOD test → comparison vs climatology / persistence / quantile-mapping / CMIP6 mean / bilinear baselines."
    },
    "falsifiability": {
        "prediction": "Neural emulator achieves higher Brier skill score on 95th-percentile daily Sahel P (2019-2023) than all baselines including quantile-mapped ERA5.",
        "threshold": "Brier skill score > 0.15 over climatology baseline, AND 10-year return-period MAE < 30%, AND skill > quantile-mapped ERA5 on both metrics, AND OOD drought-regime degradation < 50%.",
        "null_outcome": "Brier skill < 0.05 OR worse than quantile-mapping OR OOD degradation > 70% falsifies the hypothesis."
    },
    "feasibility_scores": {
        "data_availability": 3,
        "technical_feasibility": 4,
        "physical_consistency": 4,
        "novelty": 3,
        "decision_relevance": 4
    },
    "feasibility_justifications": {
        "data_availability": "ERA5 + CMIP6 + topography are well-curated and free; gauge data for the Sahel requires institutional partnerships and language work to access West African meteorological office archives.",
        "technical_feasibility": "Swin transformer + Pangeo + xarray are well-trodden engineering; ~3-4 weeks of focused work after data engineering.",
        "physical_consistency": "Water-budget regularization makes the emulator physically grounded in a way pure pixel-MSE downscalers are not.",
        "novelty": "Vision-transformer downscaling is incremental; the water-budget regularization + OOD-on-drought-regime evaluation are the contributions.",
        "decision_relevance": "Directly addresses the decision needs of West African meteorological offices and adaptation planners, who currently rely on bias-corrected coarse-grid forecasts that miss extremes."
    }
}, indent=2)


PROTOCOL_JSON = json.dumps({
    "title": "Sahel extreme-P downscaler: ERA5+CMIP6 Swin transformer with water-budget regularization",
    "summary": "Train Swin-style ViT to downscale Sahel daily P from coarse-grid (ERA5 ~31km, CMIP6 ~100-250km) to 10km, evaluated against gauge data (2019-2023 in-distribution + 1968-1990 OOD) using extreme-focused metrics.",
    "data_acquisition": {
        "primary_dataset": "ERA5 hourly + CMIP6 historical/SSP for Sahel domain via Pangeo Zarr; GHCN-Daily for gauge data; West African meteorological office archives for supplementary gauge data.",
        "accession_or_url": "https://pangeo.io ; https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily",
        "access_constraints": "ERA5 + GHCN free; CMIP6 free via Earth System Grid; West African office data requires institutional MOU.",
        "fallback_datasets": ["NOAA 20CRv3 reanalysis for OOD drought-regime extension", "TRMM/GPM satellite precipitation for spatial verification"]
    },
    "steps": [
        {"order": 1, "name": "Data acquisition + tiling", "description": "Pull ERA5 + CMIP6 + topography from Pangeo; tile to per-day Sahel patches.",
         "inputs": ["Pangeo Zarr"], "outputs": ["patch tensors"],
         "method_citations": ["github.com/pydata/xarray", "https://pangeo.io"]},
        {"order": 2, "name": "Gauge QC pipeline", "description": "GHCN-Daily QC, station-matching to grid cells, supplement with West African office archives.",
         "inputs": ["GHCN-Daily", "office archives"], "outputs": ["QC'd gauge timeseries"],
         "method_citations": []},
        {"order": 3, "name": "Architecture + losses", "description": "Swin transformer with multi-channel input; 3-component loss (pixel MSE on log(1+P) + extreme focal + water-budget penalty).",
         "inputs": ["patches", "gauge labels"], "outputs": ["model"],
         "method_citations": ["Pathak et al 2022, arXiv 2202.11214 — FourCastNet", "Nguyen et al 2023, arXiv 2301.10343 — ClimaX"]},
        {"order": 4, "name": "Train / in-dist eval / OOD eval", "description": "Train 2003-2018; eval 2019-2023; OOD eval on 1968-1990 reanalysis-back-extension.",
         "inputs": ["model"], "outputs": ["metrics"],
         "method_citations": []},
        {"order": 5, "name": "Baselines", "description": "Climatology, persistence, quantile-mapped ERA5, CMIP6 ensemble mean, bilinear ERA5 interpolation.",
         "inputs": ["data"], "outputs": ["baseline metrics"],
         "method_citations": []},
        {"order": 6, "name": "Reporting + decision-relevance", "description": "Brier skill score + 10-year return-period MAE + spatial skill maps; compare vs all baselines stratified by season + station density.",
         "inputs": ["metrics"], "outputs": ["paper", "skill maps"],
         "method_citations": ["IPCC AR6 WG1 Chapter 11"]}
    ],
    "primary_metric": "Brier skill score for 95th-percentile daily P (2019-2023 in-distribution; gauge-defined thresholds)",
    "success_threshold": "Brier skill score > 0.15 over climatology baseline AND 10-year return-period MAE < 30% AND skill > quantile-mapped ERA5 baseline AND OOD drought-regime skill degradation < 50%",
    "null_outcome": "Brier skill < 0.05 OR worse than quantile-mapping OR OOD degradation > 70% falsifies",
    "baselines": ["climatology-by-month", "persistence-by-day", "quantile-mapped ERA5", "CMIP6 ensemble mean", "bilinear ERA5 interpolation"],
    "compute": {"hardware": "1× A100 (40GB)", "estimated_runtime": "1-3 days per ensemble member", "storage": "~5TB ERA5 + 2TB CMIP6 (cached on Pangeo)", "cost_estimate": "~$300 GPU + Pangeo cloud egress"},
    "timeline_estimate": "Data engineering 4-6 weeks (mostly gauge QC + West African office MOU). Modeling + eval 4-6 weeks.",
    "sample_size_justification": "20 years × 365 days × ~600×400 grid points = ~1.7B training pixels per channel. Effective sample size for extremes is much smaller (~365 × 20 × 5% = 3650 days with extreme events somewhere in the patch); sufficient for the proposed Brier skill targets at gauge density."
}, indent=2)


RISKS_JSON = json.dumps({
    "summary": "Six risks. The dominant ones are gauge-data scarcity, OOD ambiguity on the drought regime, and the difficulty of attributing skill improvements to the water-budget regularizer specifically.",
    "items": [
        {"id": "R1", "category": "data", "severity": "critical",
         "description": "Sahel rain-gauge density is severely uneven; the 2019-2023 evaluation period may have <50 high-quality continuous stations across the domain, with much of the eastern Sahel having no usable data.",
         "likely_failure_mode": "Brier skill estimates have wide spatial CIs; aggregate skill numbers obscure the fact that the eastern Sahel is not actually being verified.",
         "mitigation": "Report skill stratified by gauge-network density; add satellite (GPM IMERG) as a secondary spatial verification; explicitly constrain claims to where gauge density permits.",
         "counter_evidence_citations": []},
        {"id": "R2", "category": "external-validity", "severity": "high",
         "description": "Future climate is OOD relative to 2003-2023 training; the proposed drought-regime OOD test on 1968-1990 reanalysis-back-extension uses earlier-generation reanalysis with its own biases — testing one OOD with another OOD, not a clean test.",
         "likely_failure_mode": "OOD eval results are ambiguous; reviewers cannot distinguish reanalysis-product bias from genuine model failure.",
         "mitigation": "Use multiple OOD test scenarios (drought regime + future-projection bias-corrected CMIP6); report skill degradation as a CI not a point estimate.",
         "counter_evidence_citations": []},
        {"id": "R3", "category": "method", "severity": "high",
         "description": "Water-budget regularization couples to a quantity (aggregated ERA5 precipitation) that is itself biased; constraining the network to match a biased aggregate can encode the bias rather than physical consistency.",
         "likely_failure_mode": "regularizer underperforms its physics-informed framing; pixel-MSE-only baseline matches it.",
         "mitigation": "Ablate water-budget regularizer explicitly; report skill with and without; bias-correct the aggregated ERA5 budget before using it as a constraint.",
         "counter_evidence_citations": []},
        {"id": "R4", "category": "evaluation", "severity": "high",
         "description": "Brier skill score on extreme thresholds derived from gauge climatology is sensitive to the threshold choice; a 90th vs 95th vs 99th percentile choice can make or break the +0.15 target.",
         "likely_failure_mode": "result is sensitive to a hyperparameter choice that should be pre-specified.",
         "mitigation": "Pre-register threshold choices; report skill across 90/95/99th to expose sensitivity.",
         "counter_evidence_citations": []},
        {"id": "R5", "category": "confounding", "severity": "medium",
         "description": "Gauge-data improvement over time (more stations 2010s vs 2000s) confounds the 2003-2018 train vs 2019-2023 test split: the test set is a higher-quality period than parts of the training set.",
         "likely_failure_mode": "test-set skill is artificially high; not generalizable to historical periods with sparser gauge coverage.",
         "mitigation": "Stratify train/test by gauge-density era; report cross-era skill explicitly.",
         "counter_evidence_citations": []},
        {"id": "R6", "category": "incentive-or-process", "severity": "medium",
         "description": "Engagement with West African meteorological offices (ASECNA, national met services) is essential for both the gauge data and the decision-relevance framing; without their input the project is academic.",
         "likely_failure_mode": "paper publishes; outputs are not used by the operational forecasting community.",
         "mitigation": "Co-design evaluation metrics with at least one West African operational forecaster from project start.",
         "counter_evidence_citations": []}
    ]
}, indent=2)


CHALLENGE_JSON = json.dumps({
    "summary": "Four findings. The hypothesis frames the contribution as the architecture, but the architecture is incremental; the real contribution is the OOD evaluation regime, which is also the weakest experimental element. The water-budget regularizer is doing more inferential work than the framing acknowledges.",
    "findings": [
        {"id": "C1", "kind": "novelty-overstated", "severity": "medium",
         "description": "Vision-transformer architectures for weather/climate emulation are now common (FourCastNet, ClimaX, Pangu-Weather, GraphCast). The Sahel-specific architectural contribution is small; the real contribution is the evaluation regime.",
         "evidence_citations": ["Pathak et al 2022, arXiv 2202.11214"],
         "suggested_response": "Frame the contribution as 'rigorous extreme-focused evaluation including OOD drought regime' rather than as a new architecture."},
        {"id": "C2", "kind": "wrong-metric", "severity": "high",
         "description": "Brier skill score requires probabilistic forecasts. The proposed deterministic emulator either needs to add ensemble generation (expensive) or be evaluated with a deterministic-friendly extreme metric (e.g., 95th percentile bias, spatial CRPS via random-time-permutation ensemble).",
         "evidence_citations": [],
         "suggested_response": "Either add ensemble dropout / VAE component for probabilistic forecasts, or replace Brier skill with a deterministic-compatible extreme metric pre-specified upfront."},
        {"id": "C3", "kind": "data-leakage-risk", "severity": "high",
         "description": "ERA5 itself assimilates gauge data over the Sahel — using ERA5 as input AND gauge data as label means the network can shortcut by extracting the assimilated gauge signal from ERA5. This is a well-known failure mode of ERA5-as-input downscalers.",
         "evidence_citations": [],
         "suggested_response": "Test for the shortcut: train a model with ERA5-only inputs and check whether it already achieves high skill at gauge stations; report 'lift over ERA5-only baseline' as the headline metric."},
        {"id": "C4", "kind": "feasibility-overstated", "severity": "medium",
         "description": "Engagement with West African meteorological offices for gauge data and decision-relevance framing is described as a step but is realistically 6-12 months of relationship-building, not a workstream you can compress into the timeline.",
         "evidence_citations": [],
         "suggested_response": "Either start with publicly-available gauge data only and explicitly defer the operational-decision-relevance claim, or budget 6-12 months for the partnerships before the modeling timeline begins."}
    ]
}, indent=2)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "examples" / "climate_run"
    out_dir.mkdir(parents=True, exist_ok=True)

    pack = load_pack("climate")
    llm = MockLLM(responses=[
        DOMAIN_R1, ENGINEER_R1, DOMAIN_R2, ENGINEER_R2,
        SYNTHESIS_JSON, PROTOCOL_JSON, RISKS_JSON, CHALLENGE_JSON,
    ])
    config = Config(
        num_rounds=4,
        grounding_strictness="high",
        require_falsifiability=True,
        require_epistemic_humility=True,
        generate_protocol=True,
        generate_risks=True,
        run_challenge=True,
        auto_view=False,
        output_dir=out_dir,
    )
    reasoner = CoReasoner(pack=pack, llm=llm, config=config)
    result = reasoner.run(idea=IDEA)
    _write_outputs_staged(result, out_dir, IDEA, pack=pack, generate_notebook=True)

    es = result.hypothesis.epistemic_summary
    audit = result.audit_report
    print(f"climate_run (v0.2.0) generated:")
    print(f"  well-covered: {es.well_covered_count} · sparse: {es.sparse_count} · gaps: {es.knowledge_gap_count} · syntheses: {es.novel_synthesis_count}")
    print(f"  protocol steps: {len(result.plan.steps)} · risks: {len(result.risks.items)} · challenge findings: {len(result.challenge.findings)}")
    print(f"  audit: {audit.banner()}")
    if audit.mismatch_count:
        print()
        for f in audit.findings:
            if f.status != "mismatch":
                continue
            print(f"  ✗ [{f.auditor_name}] AI claimed: {f.target_summary[:100]}")
            for r in f.mismatch_reasons:
                print(f"      → {r}")
    print(f"  outputs in {out_dir}")


if __name__ == "__main__":
    main()
