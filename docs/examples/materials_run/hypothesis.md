# Multi-task GNN for spinel Li-ion cathode discovery: voltage + thermal stability co-prediction

> Audit summary: ✓ 2 verified

A multi-task graph neural network trained on Materials Project structural and computed-voltage data, with auxiliary heads for thermal decomposition temperature and energy-above-hull, will identify spinel Li-ion cathode candidates that achieve a top-20 synthesis hit-rate ≥ 30% on a closed-loop experimental validation cohort, where 'hit' means measured voltage > 4.0V AND decomposition onset > 180°C.

## Domain grounding
- **mechanism**: Spinel AB2O4 structural family is a documented Li-ion cathode workhorse; multi-task GNNs over crystal graphs achieve DFT-level accuracy at substantially lower compute; multi-task auxiliary supervision regularizes the dominant voltage-prediction task and provides synthesizability filtering at inference time.
- **unmet_need**: Cobalt-reduced cathode discovery requires voltage + thermal stability + synthesizability co-screening at scale; existing screens optimize one property at a time, and synthesizability proxies are weak.
- **expected_impact**: An auditable closed-loop screen that retires non-viable candidates before synthesis, focusing experimental effort on the highest-probability hits.

## Technical approach
- **core_method**: M3GNet-class crystal-graph encoder + 3-head MLP for voltage / decomposition temperature / hull distance, with hand-engineered Goldschmidt + Hume-Rothery features concatenated to the graph readout.
- **key_innovation**: Multi-task auxiliary supervision combined with classical empirical-rule features on a unified GNN backbone, validated on closed-loop experimental synthesis hit-rate rather than benchmark MAE.
- **implementation_path**: MP catalog filtered to spinels + spinel-adjacent → harvest decomp-temp labels → stratified-by-composition split → multi-task M3GNet training → top-K candidate selection → external synthesis + characterization → hit-rate evaluation.

## Falsifiability
- **prediction**: The multi-task GNN screen achieves a higher top-20 synthesis hit-rate on a held-out spinel discovery cohort than single-task voltage-only baselines and a hull-distance-only filter.
- **threshold**: Top-20 hit-rate >= 30% (where 'hit' = measured voltage > 4.0V AND decomp onset > 180°C), compared to baseline hit-rate that must be empirically established but is expected near 10-15% from random spinel selection.
- **null outcome**: Top-20 hit-rate < 15% falsifies the hypothesis: the multi-task screen is no better than random spinel selection from the MP catalog.

## Feasibility scores
- **data_availability**: 4/5 — MP voltage data is dense; thermal decomp labels require literature mining and are the bottleneck.
- **technical_feasibility**: 4/5 — M3GNet + multi-task heads are well-trodden engineering; ~1 week of training/eval.
- **physical_plausibility**: 4/5 — Spinel as cathode, hull-distance as synthesizability proxy, and Hume-Rothery / Goldschmidt features all have decades of physical grounding.
- **novelty**: 3/5 — Multi-task GNN for one-shot cathode property co-prediction is incremental over single-task work but not transformative.
- **synthesizability**: 2/5 — Closed-loop experimental validation is the key bottleneck — requires an experimental partner with 6-12 month synthesis turnaround on novel spinel compositions.
- **overall (weighted)**: 3.38

## Evidence trail

### AI-confident foundations (well-covered)
| # | Type | Claim | Source |
|---|------|-------|--------|
| 1 | published-evidence | The spinel AB2O4 structural family has been a workhorse for Li-ion cathode chemistry since the 1980s, with LiMn2O4 the canonical example. | Thackeray et al 1983, Mater Res Bull 18:461 — first spinel LiMn2O4 cathode |
| 2 | published-evidence | The Materials Project provides DFT-computed properties (formation energy, voltage profiles for intercalation reactions, band gaps) for >150,000 inorganic crystal structures with consistent functional choices. | Jain et al 2013, APL Materials 1:011002 — Materials Project foundational paper |
| 3 | engineering-precedent | Pymatgen is the open-source toolkit for crystal-structure manipulation, MP API access, and structural featurization at scale. | github.com/materialsproject/pymatgen |
| 4 | observation | Standard PBE DFT systematically underestimates band gaps and over-stabilizes some metallic ground states; voltage predictions inherit these biases — a 4.3V threshold predicted by PBE may correspond to a different experimental voltage. | — |
| 5 | engineering-precedent | Pymatgen provides structure parsing + Voronoi-based featurization that maps a crystal to a graph of atoms (nodes) and bonds (edges). | github.com/materialsproject/pymatgen |
| 6 | published-evidence | Crystal Graph Convolutional Neural Networks (CGCNN) demonstrated that GNNs over crystal graphs achieve DFT-level accuracy on formation energy, band gap, and other properties at substantially lower compute. | Xie & Grossman 2018, Phys Rev Lett 120:145301 — CGCNN |
| 7 | published-evidence | M3GNet extends graph networks to many-body interactions with a universal interatomic potential, enabling structural relaxation as part of the prediction pipeline. | Chen & Ong 2022, Nat Comput Sci 2:718 — M3GNet |
| 8 | engineering-precedent | MatBench provides standardized benchmark splits for materials property prediction, including hull energies and band gaps. | github.com/materialsproject/MatBench |
| 9 | observation | Single A100 sufficient. CGCNN/M3GNet-class encoders train in a few GPU-hours on MP-scale (~150K) datasets; inference over the full MP catalog is minutes. | — |
| 10 | observation | Train-test leakage in materials databases via near-duplicate structures across composition or polymorph variants is a documented failure mode for ML-on-MP work. | — |
| 11 | published-evidence | Distance-to-hull is an imperfect synthesizability proxy — meta-stable phases above the hull do get synthesized, sometimes routinely; a hard hull-distance cutoff will reject viable candidates. | Sun et al 2016, Sci Adv 2:e1600225 — synthesizability vs energy-above-hull |
| 12 | observation | A hard 4.3V threshold misses physically interesting compounds at 4.25V or 4.35V — voltage prediction has known DFT-systematic error of roughly ±0.1-0.2V depending on the redox couple. Pre-screening should use a soft margin, with the hard threshold reserved for the final candidate list. | — |
| 13 | engineering-precedent | The MatBench benchmark protocol for materials property prediction includes scaled MAE and R² but not synthesizability hit-rate, which is the metric that matters for an actionable cathode screen. | github.com/materialsproject/MatBench |
| 14 | published-evidence | The published M3GNet architecture provides the universal-potential encoder; pymatgen provides the hand-engineered features as 1-line calls. | Chen & Ong 2022, Nat Comput Sci 2:718 — M3GNet |
| 15 | observation | Single A100; ~6 hours total training. The dominant timeline cost is the experimental closed-loop validation — 6-12 months for a 10-20 candidate synthesis + characterization round. | — |

### Likely-reliable, please verify (sparse coverage)
| # | Type | Claim | Source |
|---|------|-------|--------|
| 1 | published-evidence | Cobalt-free and reduced-cobalt cathode chemistry is an active push driven by supply-chain concerns; spinel structures are attractive because of the 3D Li-diffusion network and the structural robustness across charge states. | Whittingham 2014, Chem Rev 114:11414 — cathode review; specific recent thermal-decomposition benchmarks I'd hedge on |
| 2 | observation | Combining a multi-task GNN with hull-energy filtering for synthesizability has appeared in recent preprints but I would hedge on specific 2024+ citations. | — |
| 3 | observation | Decomposition-temperature labels are sparser and noisier than voltage labels. Class-imbalance in 'thermally-stable above 200°C' may degrade the corresponding head; specific dataset sizes I'd hedge on. | — |
| 4 | published-evidence | Synthesizability prediction has progressed beyond hull-distance to multi-feature classification; any new screen should compare against this stronger baseline. | Aykol et al 2018, Sci Adv 4:eaaq0148 — synthesizability prediction; specific result numbers I'd hedge on |
| 5 | observation | Realistic top-20 synthesis hit-rate for a well-tuned multi-task screen is plausibly 25-40% on a focused spinel test cohort; below 15% means the screen is no better than randomly picking from the MP spinel set. | — |

### Researcher knowledge required

**Knowledge gaps the AI flagged for researcher input:**

1. _(unpublished-or-pilot-data)_ Does the lab have synthesis attempts for any of the candidate compositions, with measured voltage and thermal stability? This anchors the falsifiability threshold.
2. _(niche-subfield)_ How many spinel-family entries in MP currently carry experimentally-measured voltage labels at sufficient sample size for training (vs purely DFT-computed)? This determines whether the hypothesis is supervised or active-learning-driven.
3. _(niche-subfield)_ Has multi-task GNN voltage + decomposition co-prediction been published for Li-ion cathodes specifically? I can recall single-task cathode GNN screens but no multi-task pipeline.
4. _(lab-tribal-knowledge)_ Is there an experimental partner who can synthesize and characterize the top-K candidates from the screen? Without this, the falsifiability prediction is computational only and the hypothesis collapses to a benchmark exercise.
5. _(niche-subfield)_ The current canonical maintained M3GNet implementation (the materialsvirtuallab fork or the newer matgl combined library — please supply the correct verified GitHub URL).
6. _(unpublished-or-pilot-data)_ Pilot synthesis attempts on the top-3 candidates from a baseline single-task screen would calibrate the hit-rate threshold and inform the +0.3V tolerance band on the 4.3V target.

**Novel syntheses the AI is proposing (not stated by any single source):**

1. A multi-task GNN that predicts voltage AND decomposition temperature AND distance-to-hull jointly, then filters by all three thresholds, is the conceptual leap the hypothesis is making. — _combining hull-energy synthesizability filter + voltage prediction + thermal decomposition prediction in one pipeline is not standard practice — most existing GNN work targets one property at a time_
2. Adding Goldschmidt tolerance factor, ionic-radius mismatch, and Hume-Rothery rules as auxiliary input features alongside the learned graph embedding lets the model exploit hard-won materials-science priors that pure GNN features may not recover from data alone. — _combining classical empirical rules with learned features in a single pipeline is not standard — most GNN cathode work uses pure structural features_
3. The right held-out test is not 'predict the test-set MP voltage' — it is 'pick top-K candidates from outside MP, attempt synthesis, measure properties, compute hit-rate against the predicted thresholds.' This is a closed-loop evaluation, more demanding than benchmark MAE. — _connecting GNN screen output to experimental synthesizability validation has been done individually but not as a held-out evaluation regime_

## Citation audit

### ✓ Verified (2)
| Auditor | AI claim | Verified record |
|---------|----------|-----------------|
| github | github.com/materialsproject/pymatgen | materialsproject/pymatgen — https://github.com/materialsproject/pymatgen |
| github | github.com/materialsproject/MatBench | materialsproject/matbench — https://github.com/materialsproject/matbench |

## Epistemic summary
- well-covered claims: **15**
- sparse-coverage claims: **5**
- knowledge gaps flagged: **6**
- novel syntheses proposed: **3**

_Generated by DeltaScience 0.3.0 :: pack materials v0.1.0 :: mockllm/mock-llm-v1_