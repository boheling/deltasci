# Risk register

Six risks. The dominant ones are gauge-data scarcity, OOD ambiguity on the drought regime, and the difficulty of attributing skill improvements to the water-budget regularizer specifically.

**6 risks identified.**

## R1 · data · CRITICAL

**Description.** Sahel rain-gauge density is severely uneven; the 2019-2023 evaluation period may have <50 high-quality continuous stations across the domain, with much of the eastern Sahel having no usable data.

**Likely failure mode.** Brier skill estimates have wide spatial CIs; aggregate skill numbers obscure the fact that the eastern Sahel is not actually being verified.

**Mitigation.** Report skill stratified by gauge-network density; add satellite (GPM IMERG) as a secondary spatial verification; explicitly constrain claims to where gauge density permits.

## R2 · external-validity · HIGH

**Description.** Future climate is OOD relative to 2003-2023 training; the proposed drought-regime OOD test on 1968-1990 reanalysis-back-extension uses earlier-generation reanalysis with its own biases — testing one OOD with another OOD, not a clean test.

**Likely failure mode.** OOD eval results are ambiguous; reviewers cannot distinguish reanalysis-product bias from genuine model failure.

**Mitigation.** Use multiple OOD test scenarios (drought regime + future-projection bias-corrected CMIP6); report skill degradation as a CI not a point estimate.

## R3 · method · HIGH

**Description.** Water-budget regularization couples to a quantity (aggregated ERA5 precipitation) that is itself biased; constraining the network to match a biased aggregate can encode the bias rather than physical consistency.

**Likely failure mode.** regularizer underperforms its physics-informed framing; pixel-MSE-only baseline matches it.

**Mitigation.** Ablate water-budget regularizer explicitly; report skill with and without; bias-correct the aggregated ERA5 budget before using it as a constraint.

## R4 · evaluation · HIGH

**Description.** Brier skill score on extreme thresholds derived from gauge climatology is sensitive to the threshold choice; a 90th vs 95th vs 99th percentile choice can make or break the +0.15 target.

**Likely failure mode.** result is sensitive to a hyperparameter choice that should be pre-specified.

**Mitigation.** Pre-register threshold choices; report skill across 90/95/99th to expose sensitivity.

## R5 · confounding · MEDIUM

**Description.** Gauge-data improvement over time (more stations 2010s vs 2000s) confounds the 2003-2018 train vs 2019-2023 test split: the test set is a higher-quality period than parts of the training set.

**Likely failure mode.** test-set skill is artificially high; not generalizable to historical periods with sparser gauge coverage.

**Mitigation.** Stratify train/test by gauge-density era; report cross-era skill explicitly.

## R6 · incentive-or-process · MEDIUM

**Description.** Engagement with West African meteorological offices (ASECNA, national met services) is essential for both the gauge data and the decision-relevance framing; without their input the project is academic.

**Likely failure mode.** paper publishes; outputs are not used by the operational forecasting community.

**Mitigation.** Co-design evaluation metrics with at least one West African operational forecaster from project start.
