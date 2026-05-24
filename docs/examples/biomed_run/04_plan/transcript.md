Adopting the domain refinements. Three pivots that change the design materially: (a) bulk IFN-γ signature as the explicit baseline to beat; (b) TFE3-stratified evaluation with optional TFE3-specific head; (c) calibration as a first-class metric.

**Architecture (revised).**

Per-tumor heterogeneous spatial graph G = (V, E):
- V = {tumor cell, CD204+ M2 macrophage, CD68+ macrophage (other), T cell, NK cell, fibroblast, endothelial} — node type from canonical-marker assignment on the Xenium panel
- E = typed edges {tumor↔M2_CD204+, tumor↔M2_CD204−, tumor↔T, M2↔T, T↔T, ...} where the underlying edge-construction rule is k=10 nearest neighbors in physical µm space

Each node carries one-hot cell-type identity + a learned embedding lookup + the pseudo-bulk expression of the small marker panel (CD204, CD68, CD163, MSR1, MARCO, CD3, CD8, MKI67, plus the 18-gene IFN-γ panel restricted to whichever genes are on the Xenium kit).

Encoder: 2-layer Heterogeneous Graph Transformer (HGT, hidden_dim=64) → per-node attention pooling → per-tumor graph readout → concatenated with patient-level features (age, prior chemotherapy line count, TFE3 fusion status as categorical) → 2-layer MLP head producing checkpoint-response logit.

**Loss.**

Binary cross-entropy with focal loss to handle the responder-rarity imbalance:

    L = L_focal(γ=2, α=0.25) + λ_cal · L_calib

with λ_cal ≈ 0.1; L_calib = expected calibration error (ECE) computed on a per-mini-batch isotonic recalibrator output. Post-hoc temperature scaling on the validation fold for final calibration.

**Training plan.**

1. Source cohort: institutional pretreatment-biopsy series, all-comer adult OS treated with anti-PD-1 / anti-PD-L1 monotherapy or combination, with linked best-response and PFS data. Realistic n: 30–60 patients across the largest available series, with ~10–20% responders.
2. Two arms: TFE3-fusion patients (likely n < 10 in any single-center series) and TFE3-wild-type, with stratified reporting.
3. Stratified split by treatment year and institution. No time-leakage.
4. External validation: a second institutional cohort, ideally with a different spatial-transcriptomics platform (Xenium vs MERFISH) to test platform-shift robustness.
5. Baselines: bulk IFN-γ Hallmark signature score (the bar to clear); CD204+ M2 density alone (a non-relational baseline isolating the spatial contribution); HGT without M2-edge typing (an ablation isolating the typed-edge contribution); flat MLP on the same per-tumor feature vector.

**Expected outcomes.**

[CLAIM type=observation coverage=sparse source=""]Realistic AUROC ceiling for checkpoint non-response prediction in OS with multimodal spatial features is plausibly 0.70–0.82; the IFN-γ baseline plausibly 0.60–0.68. The ≥ 0.07 improvement is a defensible target but not data-anchored without the pilot.[/CLAIM]

Anticipated lift from the spatial-graph representation over flat M2-density features: +0.03 to +0.10 AUROC, with the upper end requiring at least 50 patients with adequate spatial coverage. Below +0.03 means the typed-edge framing did not add value over scalar M2 density → hypothesis falsified.

[KNOWLEDGE_GAP category=unpublished-or-pilot-data]The effect size on the user's pilot cohort (any small case series with even 5–10 patients having paired spatial transcriptomics + IO response) would inform power calculations and the realism of the +0.07 falsifiability threshold; without it the threshold is a defensible prior but not data-anchored.[/KNOWLEDGE_GAP]

**Compute & timeline.**

[CLAIM type=observation coverage=well-covered source=""]Single 24GB GPU; ~4–6 hour training run per fold; 6–10 weeks of analyst time including IRB / tissue procurement / panel selection coordination, plus the external-validation arm.[/CLAIM]
