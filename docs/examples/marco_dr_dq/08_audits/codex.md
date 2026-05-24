# Challenge report

_Challenger: mockllm/mock-llm-v1_

Five concrete challenges. The hypothesis is well-grounded but has three soft spots: (a) HLA-EMMA SA-mismatch + HLAMatchmaker eplet count are baselines that may already saturate the Class II signal, making +0.07 lift unrealistic; (b) the platform-discrepant subset analysis assumes paired data that MARCo may not provide for many pairs; (c) the GroupKFold split has residual allele-pair leakage that hides the true generalization gap.

**5 findings.**

## C1 · feasibility-overstated · HIGH

**Description.** The +0.07 absolute Spearman ρ lift over HLA-EMMA SA-mismatch / HLAMatchmaker eplet count on held-out Class II allele pairs is more aggressive than the published Class II ML literature suggests is achievable. SA positions ARE the antibody-recognized epitopes by construction; HLA-EMMA already captures most of the signal. Realistic learned-model lift over the strongest rule-based baseline is probably +0.03-0.05.

**Evidence cited:**
- Kramer et al 2020, HLA 96:43

**Suggested response.** Pre-specify +0.04 as the falsifiability threshold; treat +0.07 as the stretch goal. Report effect size with bootstrap CI rather than as a binary pass/fail.

## C2 · data-leakage-risk · HIGH

**Description.** GroupKFold by allele identity does not eliminate allele-pair leakage: a test pair (a1, a3) where (a1, a2) was in training shares half its features with a training example. The model can interpolate. The realistic-generalization metric is held-one-allele-entirely-out, which produces a materially lower number.

**Suggested response.** Report BOTH split strategies as primary outcomes. Be explicit that the GroupKFold number overestimates real-world generalization. The held-one-allele-out number is the one to compare against the falsifiability threshold.

## C3 · missing-baseline · HIGH

**Description.** The proposed baseline set (naive Hamming, HATS-shares, HLA-EMMA-SA, HLAMatchmaker eplet count, PIRCHE-II) is reasonable but missing one critical comparator: a learned model trained on a SINGLE platform's data (e.g., One Lambda only) evaluated on the other (Immucor). If single-platform-trained models generalize across platforms with comparable lift, the platform-id auxiliary feature was unnecessary and the platform-agnostic framing collapses.

**Suggested response.** Add 'OL-trained XGBoost evaluated on Immucor pairs' and 'Immucor-trained XGBoost evaluated on OL pairs' as required cross-platform-generalization baselines. The platform-id-feature model must beat these in addition to the rule-based baselines.

## C4 · data-leakage-risk · MEDIUM

**Description.** The MARCo per-pair Spearman ρ is itself estimated from a finite sample; pairs with N<100 sera have high uncertainty in the target ρ. Training a model to predict noisy targets and evaluating with Spearman ρ between predicted and observed values rewards the model for matching the noise, not the signal. The sample-size-weighted MSE loss helps but does not fully solve this.

**Suggested response.** Report results separately for high-N pairs (n_samples > 200) and low-N pairs. Treat low-N pair results as exploratory. Consider a Bayesian formulation that propagates target uncertainty into the loss.

## C5 · novelty-overstated · MEDIUM

**Description.** The contribution is framed as 'first ML on empirical MFI for Class II'. The Tambur STAR working group has published platform-comparison work; PIRCHE-II is itself learned (HLA-peptide-binding component). Multi-task ML for HLA antibody prediction has appeared in preprint space. The distinctive contribution is the public-MARCo-cohort + platform-agnostic framing, not the methodology.

**Evidence cited:**
- Tambur et al 2018, Am J Transplant 18:1604

**Suggested response.** Frame as 'first public Class II benchmark using MARCo + first explicit platform-discrepant-subset evaluation' rather than as 'first learned cross-reactivity model'. Cite Tambur STAR work directly as platform-comparison precedent.
