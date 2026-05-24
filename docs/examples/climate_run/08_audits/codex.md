# Challenge report

_Challenger: mockllm/mock-llm-v1_

Four findings. The hypothesis frames the contribution as the architecture, but the architecture is incremental; the real contribution is the OOD evaluation regime, which is also the weakest experimental element. The water-budget regularizer is doing more inferential work than the framing acknowledges.

**4 findings.**

## C1 · novelty-overstated · MEDIUM

**Description.** Vision-transformer architectures for weather/climate emulation are now common (FourCastNet, ClimaX, Pangu-Weather, GraphCast). The Sahel-specific architectural contribution is small; the real contribution is the evaluation regime.

**Evidence cited:**
- Pathak et al 2022, arXiv 2202.11214

**Suggested response.** Frame the contribution as 'rigorous extreme-focused evaluation including OOD drought regime' rather than as a new architecture.

## C2 · wrong-metric · HIGH

**Description.** Brier skill score requires probabilistic forecasts. The proposed deterministic emulator either needs to add ensemble generation (expensive) or be evaluated with a deterministic-friendly extreme metric (e.g., 95th percentile bias, spatial CRPS via random-time-permutation ensemble).

**Suggested response.** Either add ensemble dropout / VAE component for probabilistic forecasts, or replace Brier skill with a deterministic-compatible extreme metric pre-specified upfront.

## C3 · data-leakage-risk · HIGH

**Description.** ERA5 itself assimilates gauge data over the Sahel — using ERA5 as input AND gauge data as label means the network can shortcut by extracting the assimilated gauge signal from ERA5. This is a well-known failure mode of ERA5-as-input downscalers.

**Suggested response.** Test for the shortcut: train a model with ERA5-only inputs and check whether it already achieves high skill at gauge stations; report 'lift over ERA5-only baseline' as the headline metric.

## C4 · feasibility-overstated · MEDIUM

**Description.** Engagement with West African meteorological offices for gauge data and decision-relevance framing is described as a step but is realistically 6-12 months of relationship-building, not a workstream you can compress into the timeline.

**Suggested response.** Either start with publicly-available gauge data only and explicitly defer the operational-decision-relevance claim, or budget 6-12 months for the partnerships before the modeling timeline begins.
