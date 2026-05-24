# Challenge report

_Challenger: mockllm/mock-llm-v1_

Four findings. The hypothesis frames the multi-task GNN approach as the novel contribution, but the harder unsolved problem is the decomp-temp data scarcity. The 30% hit-rate threshold is loose given measurement noise. The hull-distance synthesizability filter is doing more inferential work than the framing acknowledges.

**4 findings.**

## C1 · feasibility-overstated · HIGH

**Description.** The 30% top-20 hit-rate threshold at n=20 has a wide binomial CI (~[12%, 54%]). A baseline screen at hit-rate 15% has CI ~[3%, 38%]. The two CIs overlap substantially, so a measured 30% vs 15% point estimate is not a definitive falsifiability test at this sample size.

**Suggested response.** Pre-specify n=40 or report Bayesian posterior on hit-rate; treat the threshold as a Bayesian prior, not a frequentist gate.

## C2 · novelty-overstated · MEDIUM

**Description.** Multi-task GNNs for materials property co-prediction have appeared in the recent literature. The OS-specific contribution is the spinel + decomp-temp + closed-loop angle, not the multi-task GNN itself.

**Evidence cited:**
- Chen & Ong 2022, Nat Comput Sci 2:718

**Suggested response.** Frame the contribution as the spinel + closed-loop synthesis evaluation, not the architecture.

## C3 · missing-baseline · HIGH

**Description.** Hull-distance-only filter is too easy a baseline. Stronger baselines: (a) Aykol synthesizability classifier with hull as one feature, (b) bandit-style active learning that picks batch candidates rather than top-K static, (c) random forest on the same hand-engineered features without GNN.

**Evidence cited:**
- Aykol et al 2018, Sci Adv 4:eaaq0148

**Suggested response.** Add (a)-(c) as required baselines; if multi-task GNN does not beat random forest on the same features, the GNN was unnecessary.

## C4 · data-leakage-risk · MEDIUM

**Description.** Stratified-by-composition split helps but does not eliminate near-duplicate-structure leakage when the same composition has multiple polymorphs in MP. Polymorph-aware split is needed.

**Suggested response.** Split by reduced-formula AND prototype-structure tag jointly; report the training-set leak rate explicitly.
