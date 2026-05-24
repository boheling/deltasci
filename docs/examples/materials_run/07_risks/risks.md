# Risk register

Five risks. The dominant ones are decomp-temp data sparsity, weak synthesizability proxy, and the closed-loop experimental partnership being on the critical path.

**5 risks identified.**

## R1 · data · HIGH

**Description.** Decomposition-temperature labels are sparse (likely <500 across all spinels) and noisy (different DSC/TGA protocols, atmospheres). The decomp head will struggle.

**Likely failure mode.** decomp-temp predictions have high variance; the joint hit-rate metric is dominated by decomp filter mistakes.

**Mitigation.** Begin with a binary 'thermally stable above 200°C: yes/no' classification head if regression is too sparse; consider DFT-MD as label augmentation.

## R2 · method · HIGH

**Description.** Distance-to-hull is a documented imperfect synthesizability proxy. Real synthesizability depends on kinetics, precursor availability, and reaction pathways the GNN cannot see.

**Likely failure mode.** model rejects synthesizable meta-stable spinels; alternatively keeps thermodynamically stable but kinetically inaccessible structures.

**Mitigation.** Use Aykol et al 2018 multi-feature synthesizability classifier as a secondary filter; relax hull-distance cutoff and rely on closed-loop feedback.

**Counter-evidence cited:**
- Sun et al 2016, Sci Adv 2:e1600225
- Aykol et al 2018, Sci Adv 4:eaaq0148

## R3 · evaluation · HIGH

**Description.** Top-20 hit-rate is a small-N metric (n=20). Statistical significance of a 30% vs 15% hit-rate at n=20 has wide CIs (binomial CI ~[12, 54%] vs [3, 38%]) — overlapping intervals are likely.

**Likely failure mode.** model achieves hit-rate that visually exceeds baseline but does not reach statistical significance.

**Mitigation.** Pre-register a second screen at n=40 if first screen is ambiguous; report Bayesian posterior on hit-rate, not binary success.

## R4 · external-validity · MEDIUM

**Description.** Held-out cohort selected from compositions adjacent to MP training set may share local structural patterns; performance on truly novel compositions may degrade.

**Likely failure mode.** model performs well on near-training-distribution candidates but poorly on out-of-distribution proposals.

**Mitigation.** Compose held-out set from intentionally distant compositions; report performance stratified by Tanimoto-distance to nearest training neighbor.

## R5 · incentive-or-process · MEDIUM

**Description.** Closed-loop synthesis partnership is on the critical path. If the experimental partner deprioritizes the project, the falsifiability evaluation cannot complete.

**Likely failure mode.** ML model trained but never validated experimentally; the project produces a benchmark paper, not a hypothesis test.

**Mitigation.** Lock in experimental partner with explicit milestone agreement before commencing modeling.
