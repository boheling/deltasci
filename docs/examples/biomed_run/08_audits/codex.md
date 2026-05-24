# Challenge report

_Challenger: mockllm/mock-llm-v1_

Five concrete challenges. The hypothesis is plausible but the falsifiability threshold (+0.07 AUROC over IFN-γ) is more aggressive than the cohort size will support, the cell-type annotation step is doing more inferential work than the framing acknowledges, and the comparison to a bulk RNA-seq baseline conflates two evaluation regimes.

**5 findings.**

## C1 · feasibility-overstated · HIGH

**Description.** The +0.07 absolute AUROC lift over bulk IFN-γ baseline at n≈60-100 pretreatment OS biopsies is unlikely to be detectable with statistical confidence. Effect-size calculations for AUROC differences at this sample size place the minimum detectable lift well above 0.07.

**Evidence cited:**
- Hanley & McNeil 1982 Radiology 143:29 — AUC variance estimator

**Suggested response.** Pre-register an interim analysis at n=40 with go/no-go thresholds; downgrade the falsifiability target to a calibration-focused metric if AUROC differences are not powered.

## C2 · wrong-metric · HIGH

**Description.** AUROC for a class-imbalanced outcome (non-response is ~30-40% in OS checkpoint trials) is dominated by the negatives. AUPRC and decision-curve net benefit at clinically meaningful threshold (e.g., 'would you take this kidney offer / start this treatment') are more informative and the hypothesis should commit to one.

**Evidence cited:**
- Vickers et al 2008 BMJ 336:1170 — DCA for clinical models

**Suggested response.** Add AUPRC (target >0.55) and DCA (target net benefit > standard-of-care across threshold range 10-40%) as co-primary endpoints.

## C3 · data-leakage-risk · HIGH

**Description.** Cell-type annotation is performed by reference-mapping against an external scRNA-seq atlas (GSE152048). If the reference and the test cohort overlap (institutional sample sharing), or if the annotator is trained on the same cohort being used for test, the spatial graph features inherit leakage.

**Suggested response.** Hold out annotation training data by patient AND by site; use only patient IDs disjoint from atlas contributors; report annotation-pipeline cross-validation separately.

## C4 · missing-baseline · MEDIUM

**Description.** The proposed baseline (bulk IFN-γ Hallmark) is a soft target. Stronger comparisons that the model must beat: (a) TIL density from H&E (free, used clinically), (b) PD-L1 IHC tumor proportion score (FDA-validated companion diagnostic for some indications), (c) simple M2/M1 ratio from the same Xenium panel without spatial structure.

**Suggested response.** Add (a)+(b)+(c) as required baselines; if the spatial-graph model does not beat the simple M2/M1 ratio, the spatial framing was unnecessary.

## C5 · novelty-overstated · MEDIUM

**Description.** Spatial-graph IO response prediction is now common in melanoma (Schurch et al 2020, Cell), breast cancer (Wang et al 2024), and triple-negative breast (Keren et al 2018). The OS-specific contribution is the cell-type panel + TFE3 stratification, not the architecture itself.

**Evidence cited:**
- Schurch et al 2020, Cell 182:1341
- Keren et al 2018, Cell 174:1373

**Suggested response.** Frame the OS-specific contribution explicitly; do not claim novelty for HGT or spatial-graph IO prediction in general.
