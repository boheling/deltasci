# Co-Reasoning Transcript

**Pack:** `biomed`

**Idea:** Predict checkpoint-immunotherapy non-response in TFE3-fusion osteosarcoma using a graph neural network over single-cell spatial transcriptomics, with CD204+ M2 macrophage neighborhood structure encoded as typed cell-cell edges.

## domain_r1 — domain_scientist

The hypothesis sits on a documented but rapidly-evolving immunological substrate: the osteosarcoma tumor microenvironment is heavily infiltrated by CD204+ M2-polarized macrophages, and that polarization is mechanistically linked to checkpoint-inhibitor non-response.

[CLAIM type=published-evidence coverage=well-covered source="Komohara et al 2014, Cancer Sci 105:1–8"]CD204+ M2-polarized tumor-associated macrophage density in osteosarcoma is associated with shorter metastasis-free survival in retrospective IHC cohorts.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Buddingh et al 2011, Clin Cancer Res 17:2110"]M2-skewed macrophage infiltrate in pretreatment osteosarcoma biopsies has been linked to reduced overall survival in pediatric and AYA cohorts.[/CLAIM]

[CLAIM type=published-evidence coverage=sparse source="GEO accession GSE152048 (osteosarcoma scRNA-seq atlas); precise paper-level citation hedged"]The public single-cell RNA-seq atlas at GEO GSE152048 characterizes osteosarcoma myeloid, lymphoid, stromal, and malignant compartments at cell resolution and is widely used as a reference for OS TME analysis. The accession itself is verifiable, but I should hedge on the exact paper-level metadata (authors, journal, year) that accompanies it.[/CLAIM]

[KNOWLEDGE_GAP category=niche-subfield]The exact paper-level citation that accompanies the GSE152048 osteosarcoma scRNA-seq atlas — please supply the verified PMID/DOI so the audit pass can confirm authors and journal. The training-recall version of this citation failed PubMed audit on a previous run.[/KNOWLEDGE_GAP]

The unmet need is patient-level prediction of checkpoint-inhibitor non-response — checkpoint efficacy in osteosarcoma is heterogeneous and overall low:

[CLAIM type=published-evidence coverage=well-covered source="Tawbi et al 2017, Lancet Oncology 18:1493 — SARC028 pembrolizumab in advanced sarcoma"]Single-agent PD-1 blockade in advanced bone and soft-tissue sarcomas (SARC028) showed objective response in only a minority of osteosarcoma patients, with no validated patient-selection biomarker.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Ayers et al 2017, J Clin Invest 127:2930 — IFN-γ signature"]A bulk-RNA-seq IFN-γ-response gene signature predicts pembrolizumab response across multiple solid-tumor histologies, but its performance in osteosarcoma specifically has not been systematically benchmarked.[/CLAIM]

[CLAIM type=observation coverage=sparse source=""]I am not aware of a published, externally-validated, OS-specific checkpoint-response biomarker — bulk IFN-γ is the closest off-the-shelf candidate but its OS performance I would hedge on.[/CLAIM]

[NOVEL_SYNTHESIS rationale="combines two well-established ideas — CD204+ M2 dominance as an OS-specific suppressive feature and spatial cell-cell graph representation — into a single per-patient prediction graph, which I cannot find written down for OS checkpoint response"]Building a per-tumor cell-cell spatial graph with CD204+ M2 macrophage proximity to malignant cells encoded as a typed edge, then predicting checkpoint non-response from the graph, is an architecture I cannot find published for osteosarcoma.[/NOVEL_SYNTHESIS]

Constraints worth flagging:

[CLAIM type=established-guideline coverage=well-covered source="HHS 45 CFR 46 + institutional IRB review for retrospective tissue research"]Retrospective use of FFPE blocks linked to outcome data requires IRB approval and either consent waiver or banked-consent coverage; spatial-transcriptomics on patient material does not change the regulatory category but extends the data minimization conversation.[/CLAIM]

[KNOWLEDGE_GAP category=unpublished-or-pilot-data]Does the candidate cohort have FFPE blocks of pretreatment biopsies AND linked checkpoint-inhibitor outcome data (best response by RECIST or PFS)? Spatial transcriptomics requires intact tissue; pretreatment-only is the relevant window.[/KNOWLEDGE_GAP]

[KNOWLEDGE_GAP category=patent-or-clinical-practice]How is "non-response" being operationalized — RECIST progressive disease at first restaging, no PFS benefit vs historical control, or a composite? OS checkpoint trials have used different endpoints.[/KNOWLEDGE_GAP]

### Evidence collected
- **[published-evidence · well-covered]** CD204+ M2-polarized tumor-associated macrophage density in osteosarcoma is associated with shorter metastasis-free survival in retrospective IHC cohorts. — _Komohara et al 2014, Cancer Sci 105:1–8_
- **[published-evidence · well-covered]** M2-skewed macrophage infiltrate in pretreatment osteosarcoma biopsies has been linked to reduced overall survival in pediatric and AYA cohorts. — _Buddingh et al 2011, Clin Cancer Res 17:2110_
- **[published-evidence · sparse]** The public single-cell RNA-seq atlas at GEO GSE152048 characterizes osteosarcoma myeloid, lymphoid, stromal, and malignant compartments at cell resolution and is widely used as a reference for OS TME analysis. The accession itself is verifiable, but I should hedge on the exact paper-level metadata (authors, journal, year) that accompanies it. — _GEO accession GSE152048 (osteosarcoma scRNA-seq atlas); precise paper-level citation hedged_
- **[published-evidence · well-covered]** Single-agent PD-1 blockade in advanced bone and soft-tissue sarcomas (SARC028) showed objective response in only a minority of osteosarcoma patients, with no validated patient-selection biomarker. — _Tawbi et al 2017, Lancet Oncology 18:1493 — SARC028 pembrolizumab in advanced sarcoma_
- **[published-evidence · well-covered]** A bulk-RNA-seq IFN-γ-response gene signature predicts pembrolizumab response across multiple solid-tumor histologies, but its performance in osteosarcoma specifically has not been systematically benchmarked. — _Ayers et al 2017, J Clin Invest 127:2930 — IFN-γ signature_
- **[observation · sparse]** I am not aware of a published, externally-validated, OS-specific checkpoint-response biomarker — bulk IFN-γ is the closest off-the-shelf candidate but its OS performance I would hedge on. — _—_
- **[established-guideline · well-covered]** Retrospective use of FFPE blocks linked to outcome data requires IRB approval and either consent waiver or banked-consent coverage; spatial-transcriptomics on patient material does not change the regulatory category but extends the data minimization conversation. — _HHS 45 CFR 46 + institutional IRB review for retrospective tissue research_

### Knowledge gaps flagged for researcher
- (niche-subfield) The exact paper-level citation that accompanies the GSE152048 osteosarcoma scRNA-seq atlas — please supply the verified PMID/DOI so the audit pass can confirm authors and journal. The training-recall version of this citation failed PubMed audit on a previous run.
- (unpublished-or-pilot-data) Does the candidate cohort have FFPE blocks of pretreatment biopsies AND linked checkpoint-inhibitor outcome data (best response by RECIST or PFS)? Spatial transcriptomics requires intact tissue; pretreatment-only is the relevant window.
- (patent-or-clinical-practice) How is "non-response" being operationalized — RECIST progressive disease at first restaging, no PFS benefit vs historical control, or a composite? OS checkpoint trials have used different endpoints.

### Novel syntheses proposed
- Building a per-tumor cell-cell spatial graph with CD204+ M2 macrophage proximity to malignant cells encoded as a typed edge, then predicting checkpoint non-response from the graph, is an architecture I cannot find published for osteosarcoma. — _combines two well-established ideas — CD204+ M2 dominance as an OS-specific suppressive feature and spatial cell-cell graph representation — into a single per-patient prediction graph, which I cannot find written down for OS checkpoint response_

## engineer_r1 — ml_engineer

The spatial-graph framing is a natural fit for heterogeneous graph neural networks. Concretely:

**Data representation.**

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/pyg-team/pytorch_geometric"]PyTorch Geometric provides production-grade implementations of message-passing GNNs (GAT, GraphSAGE, Heterogeneous Graph Transformer) with first-class support for typed nodes and edges and per-graph readouts.[/CLAIM]

A natural construction: each cell from a Xenium / MERFISH per-tumor field becomes a node, with cell-type embedding derived from a reference-mapped scRNA-seq label (canonical-marker score-gene assignment, the same approach standard in scanpy). Edges are k-nearest-neighbor in physical-µm space with edge type = cell-type pair (tumor↔M2, tumor↔T-cell, M2↔T-cell, etc.). Per-cell features carry the pseudo-bulk expression of a small marker panel (CD204/MSR1, CD68, CD163, CD3, CD8, MKI67, plus IFN-γ-pathway genes from Ayers).

**ML paradigm.**

[CLAIM type=published-evidence coverage=well-covered source="Hu et al 2020, WWW — Heterogeneous Graph Transformer (HGT)"]Heterogeneous Graph Transformers handle typed nodes and typed edges with parametric attention, fitting the multi-cell-type spatial-graph use case better than plain GCN.[/CLAIM]

For the response head:

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/scverse/scanpy + github.com/scverse/squidpy"]scanpy + squidpy together cover the cell-typing, spatial-neighborhood-graph construction, and per-cell feature extraction needed to translate Xenium per-tumor fields into per-tumor graph objects.[/CLAIM]

[CLAIM type=observation coverage=sparse source=""]Combining HGT-style attention with cell-type-pair edge typing for IO-response prediction in spatial transcriptomics has appeared in breast and melanoma preprints; OS-specific GNN-on-spatial-transcriptomics for IO response, I am less certain has been published.[/CLAIM]

**Existing implementations of the exact idea.**

[KNOWLEDGE_GAP category=niche-subfield]Are there published GNN-on-spatial-transcriptomics models for IO response prediction in any sarcoma histology I should be aware of? I can recall efforts in melanoma and breast but no sarcoma-specific spatial-GNN IO biomarker work.[/KNOWLEDGE_GAP]

**Compute.**

[CLAIM type=observation coverage=well-covered source=""]Per-tumor spatial graphs are mid-size (tens of thousands of cells per Xenium field), so per-tumor forward passes fit on a single 24GB GPU with subgraph sampling. Cohort size (likely 30–80 OS patients across the largest available institutional series) is the bottleneck, not compute.[/CLAIM]

**Top three technical risks.**

1. [CLAIM type=published-evidence coverage=well-covered source="10x Genomics Xenium technical brief 2024 + Janesick et al 2023, Nat Commun 14:8353"]Xenium and MERFISH panels are limited (~300–500 genes); cell-type assignment relies on canonical markers being present in the panel, which constrains downstream feature richness compared to full scRNA-seq.[/CLAIM]

2. [CLAIM type=observation coverage=sparse source=""]Cohort imbalance: in adult OS, checkpoint responders are likely <20% of treated patients — naive cross-entropy will collapse to majority-class non-response without explicit handling. Specific response rates I'd hedge on per cohort.[/CLAIM]

3. [CLAIM type=observation coverage=well-covered source=""]Distribution shift between technical platforms (Xenium vs MERFISH vs CosMx) and between institutions (FFPE fixation protocols, panel choice) is real; an external-cohort generalization arm is essential.[/CLAIM]

[NOVEL_SYNTHESIS rationale="HGT cell-type-pair edge tokens make M2-tumor-proximity weighting learnable rather than hand-coded as a fixed M2-density feature — this combination doesn't appear in OS literature I'm aware of"]Using HGT cell-type-pair edge tokens lets the model learn that, for example, the M2↔tumor edge weight matters more than the M2↔fibroblast edge weight, without manual neighborhood-density feature engineering.[/NOVEL_SYNTHESIS]

### Evidence collected
- **[engineering-precedent · well-covered]** PyTorch Geometric provides production-grade implementations of message-passing GNNs (GAT, GraphSAGE, Heterogeneous Graph Transformer) with first-class support for typed nodes and edges and per-graph readouts. — _github.com/pyg-team/pytorch_geometric_
- **[published-evidence · well-covered]** Heterogeneous Graph Transformers handle typed nodes and typed edges with parametric attention, fitting the multi-cell-type spatial-graph use case better than plain GCN. — _Hu et al 2020, WWW — Heterogeneous Graph Transformer (HGT)_
- **[engineering-precedent · well-covered]** scanpy + squidpy together cover the cell-typing, spatial-neighborhood-graph construction, and per-cell feature extraction needed to translate Xenium per-tumor fields into per-tumor graph objects. — _github.com/scverse/scanpy + github.com/scverse/squidpy_
- **[observation · sparse]** Combining HGT-style attention with cell-type-pair edge typing for IO-response prediction in spatial transcriptomics has appeared in breast and melanoma preprints; OS-specific GNN-on-spatial-transcriptomics for IO response, I am less certain has been published. — _—_
- **[observation · well-covered]** Per-tumor spatial graphs are mid-size (tens of thousands of cells per Xenium field), so per-tumor forward passes fit on a single 24GB GPU with subgraph sampling. Cohort size (likely 30–80 OS patients across the largest available institutional series) is the bottleneck, not compute. — _—_
- **[published-evidence · well-covered]** Xenium and MERFISH panels are limited (~300–500 genes); cell-type assignment relies on canonical markers being present in the panel, which constrains downstream feature richness compared to full scRNA-seq. — _10x Genomics Xenium technical brief 2024 + Janesick et al 2023, Nat Commun 14:8353_
- **[observation · sparse]** Cohort imbalance: in adult OS, checkpoint responders are likely <20% of treated patients — naive cross-entropy will collapse to majority-class non-response without explicit handling. Specific response rates I'd hedge on per cohort. — _—_
- **[observation · well-covered]** Distribution shift between technical platforms (Xenium vs MERFISH vs CosMx) and between institutions (FFPE fixation protocols, panel choice) is real; an external-cohort generalization arm is essential. — _—_

### Knowledge gaps flagged for researcher
- (niche-subfield) Are there published GNN-on-spatial-transcriptomics models for IO response prediction in any sarcoma histology I should be aware of? I can recall efforts in melanoma and breast but no sarcoma-specific spatial-GNN IO biomarker work.

### Novel syntheses proposed
- Using HGT cell-type-pair edge tokens lets the model learn that, for example, the M2↔tumor edge weight matters more than the M2↔fibroblast edge weight, without manual neighborhood-density feature engineering. — _HGT cell-type-pair edge tokens make M2-tumor-proximity weighting learnable rather than hand-coded as a fixed M2-density feature — this combination doesn't appear in OS literature I'm aware of_

## domain_r2 — domain_scientist

The architecture is reasonable, but two things need adjusting before it's clinically actionable.

**1. The right outcome and the right baseline.**

The bulk IFN-γ signature is the clinical-grade baseline you must beat — anything below that performance is not adoptable.

[CLAIM type=published-evidence coverage=well-covered source="Ayers et al 2017, J Clin Invest 127:2930"]The 18-gene IFN-γ-response signature is the most-validated bulk-RNA-seq checkpoint-response biomarker across solid tumors and is computable from FFPE-derived RNA at clinical-lab scale.[/CLAIM]

[CLAIM type=observation coverage=sparse source=""]On osteosarcoma specifically, my training does not contain a definitive numerical AUROC for the IFN-γ signature applied to checkpoint response — I'd hedge that it is plausibly 0.60–0.68 based on transferred pan-cancer performance, but this needs cohort-specific verification.[/CLAIM]

**2. Patient stratification by TFE3 status.**

[CLAIM type=published-evidence coverage=well-covered source="Argani et al 2020, Genes Chromosomes Cancer 59:367 — MiT family translocation tumors"]TFE3-rearranged osteosarcoma is a rare molecular subset; MiT-family transcription factors are documented to modulate lysosomal and immune-related gene programs, which could affect TME composition relative to TFE3-wild-type OS.[/CLAIM]

[NOVEL_SYNTHESIS rationale="if TFE3 fusion modifies macrophage polarization or IFN-γ-response programs, the model must be trained or evaluated stratified by fusion status — otherwise the TFE3 subset's signal is averaged into the larger TFE3-wild-type pool and may be missed"]Training the model on a pan-OS cohort but reporting performance separately on TFE3-fusion patients (and ideally training a TFE3-specific head) would be the honest framing — pooled training, stratified evaluation.[/NOVEL_SYNTHESIS]

**3. Clinically meaningful evaluation.**

[CLAIM type=established-guideline coverage=well-covered source="TRIPOD 2015 reporting guideline"]Calibration (calibration-in-the-large, calibration slope) is required alongside discrimination for any prediction model intended to inform treatment decisions.[/CLAIM]

[CLAIM type=observation coverage=well-covered source=""]Decision-curve analysis at the clinically meaningful threshold (the cost of giving immunotherapy to a non-responder vs withholding it from a responder) is more informative than raw AUROC for whether the model would change practice.[/CLAIM]

**4. The falsifiable prediction.**

The hypothesis should commit to: GNN-with-CD204+M2-typed-edges achieves AUROC ≥ 0.75 on the held-out cohort for checkpoint non-response (RECIST PD at first restaging or no PFS benefit at 6 months), improves over the bulk IFN-γ signature baseline by ≥ 0.07 AUROC with 95% CI lower bound > IFN-γ baseline, with calibration intercept |α| < 0.05 and slope in [0.9, 1.1]. Improvement < 0.03 AUROC, OR calibration slope outside [0.85, 1.15], falsifies it.

[KNOWLEDGE_GAP category=lab-tribal-knowledge]Is there an annotated cohort where TFE3 fusion status, pretreatment-biopsy spatial transcriptomics, and checkpoint-inhibitor response are linked at the patient level? OS is rare; this triangulation may not exist outside specialized sarcoma centers.[/KNOWLEDGE_GAP]

[KNOWLEDGE_GAP category=non-english-literature]Are there Japanese or Chinese OS spatial-transcriptomics cohorts with checkpoint outcome data that should inform external validation? Asian OS series have meaningfully different demographics and TME composition that I have weak training coverage on.[/KNOWLEDGE_GAP]

### Evidence collected
- **[published-evidence · well-covered]** The 18-gene IFN-γ-response signature is the most-validated bulk-RNA-seq checkpoint-response biomarker across solid tumors and is computable from FFPE-derived RNA at clinical-lab scale. — _Ayers et al 2017, J Clin Invest 127:2930_
- **[observation · sparse]** On osteosarcoma specifically, my training does not contain a definitive numerical AUROC for the IFN-γ signature applied to checkpoint response — I'd hedge that it is plausibly 0.60–0.68 based on transferred pan-cancer performance, but this needs cohort-specific verification. — _—_
- **[published-evidence · well-covered]** TFE3-rearranged osteosarcoma is a rare molecular subset; MiT-family transcription factors are documented to modulate lysosomal and immune-related gene programs, which could affect TME composition relative to TFE3-wild-type OS. — _Argani et al 2020, Genes Chromosomes Cancer 59:367 — MiT family translocation tumors_
- **[established-guideline · well-covered]** Calibration (calibration-in-the-large, calibration slope) is required alongside discrimination for any prediction model intended to inform treatment decisions. — _TRIPOD 2015 reporting guideline_
- **[observation · well-covered]** Decision-curve analysis at the clinically meaningful threshold (the cost of giving immunotherapy to a non-responder vs withholding it from a responder) is more informative than raw AUROC for whether the model would change practice. — _—_

### Knowledge gaps flagged for researcher
- (lab-tribal-knowledge) Is there an annotated cohort where TFE3 fusion status, pretreatment-biopsy spatial transcriptomics, and checkpoint-inhibitor response are linked at the patient level? OS is rare; this triangulation may not exist outside specialized sarcoma centers.
- (non-english-literature) Are there Japanese or Chinese OS spatial-transcriptomics cohorts with checkpoint outcome data that should inform external validation? Asian OS series have meaningfully different demographics and TME composition that I have weak training coverage on.

### Novel syntheses proposed
- Training the model on a pan-OS cohort but reporting performance separately on TFE3-fusion patients (and ideally training a TFE3-specific head) would be the honest framing — pooled training, stratified evaluation. — _if TFE3 fusion modifies macrophage polarization or IFN-γ-response programs, the model must be trained or evaluated stratified by fusion status — otherwise the TFE3 subset's signal is averaged into the larger TFE3-wild-type pool and may be missed_

## engineer_r2 — ml_engineer

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

### Evidence collected
- **[observation · sparse]** Realistic AUROC ceiling for checkpoint non-response prediction in OS with multimodal spatial features is plausibly 0.70–0.82; the IFN-γ baseline plausibly 0.60–0.68. The ≥ 0.07 improvement is a defensible target but not data-anchored without the pilot. — _—_
- **[observation · well-covered]** Single 24GB GPU; ~4–6 hour training run per fold; 6–10 weeks of analyst time including IRB / tissue procurement / panel selection coordination, plus the external-validation arm. — _—_

### Knowledge gaps flagged for researcher
- (unpublished-or-pilot-data) The effect size on the user's pilot cohort (any small case series with even 5–10 patients having paired spatial transcriptomics + IO response) would inform power calculations and the realism of the +0.07 falsifiability threshold; without it the threshold is a defensible prior but not data-anchored.
