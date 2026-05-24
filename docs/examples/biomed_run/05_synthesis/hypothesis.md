# Spatial CD204+ M2 macrophage neighborhood graph as a checkpoint-immunotherapy non-response predictor in TFE3-fusion osteosarcoma

> Audit summary: ✓ 7 verified

A heterogeneous graph neural network operating on per-tumor single-cell spatial transcriptomics, with cell-type-pair typed edges (in particular, CD204+ M2 macrophage proximity to malignant cells), will predict checkpoint-immunotherapy non-response in osteosarcoma at AUROC ≥ 0.75 on held-out data, improving over a bulk IFN-γ Hallmark signature baseline by ≥ 0.07 AUROC, with calibration intercept |α| < 0.05 and slope within [0.9, 1.1]. Performance is reported stratified by TFE3 fusion status.

## Domain grounding
- **mechanism**: CD204+ M2-polarized macrophage dominance in the osteosarcoma TME is documented to associate with poor outcome and is mechanistically linked to T-cell suppression. Spatial proximity of M2 macrophages to malignant cells preserves geometric information that bulk RNA-seq discards. TFE3 fusion may modulate the surrounding TME via MiT-family transcriptional programs.
- **unmet_need**: Patient-level checkpoint-immunotherapy response prediction in osteosarcoma. Single-agent PD-1 blockade has limited efficacy (SARC028) and there is no validated OS-specific selection biomarker; the bulk IFN-γ signature is the off-the-shelf candidate but its OS performance is unbenchmarked.
- **expected_impact**: Better-calibrated patient selection for checkpoint immunotherapy at the time of treatment decision, particularly for the rare TFE3-fusion subset where stratified performance can reveal subset-specific signal lost in pooled analyses.

## Technical approach
- **core_method**: Heterogeneous Graph Transformer (HGT) over per-tumor cell-cell spatial graph with cell-type-pair typed edges → graph readout → patient-feature concatenation (TFE3 status, prior therapy line) → MLP head producing checkpoint-response logit, trained with focal loss + calibration regularizer.
- **key_innovation**: Per-tumor spatial graph with CD204+ M2-tumor cell-type-pair edge typing — to my knowledge not previously combined with HGT for IO-response prediction in osteosarcoma.
- **implementation_path**: Institutional Xenium / MERFISH pretreatment-biopsy series + IO outcome linkage → squidpy spatial neighborhood graphs → PyTorch Geometric HGT + focal loss → stratified split by year + institution → external validation on second institutional cohort with cross-platform → comparison vs IFN-γ signature baseline + flat M2-density baseline + HGT-without-typed-edges ablation.

## Falsifiability
- **prediction**: The HGT-with-CD204+M2-typed-edges model achieves a higher AUROC for checkpoint-immunotherapy non-response than the bulk IFN-γ signature baseline on the external held-out OS cohort.
- **threshold**: AUROC ≥ 0.75 absolute, AND AUROC improvement ≥ 0.07 over bulk IFN-γ baseline with 95% CI lower bound > IFN-γ baseline, AND calibration intercept |α| < 0.05, AND calibration slope in [0.9, 1.1].
- **null outcome**: AUROC improvement < 0.03 over bulk IFN-γ baseline, OR calibration slope outside [0.85, 1.15], falsifies the hypothesis: the spatial-graph cell-type-pair edge typing did not add value over scalar M2 density or bulk IFN-γ score.

## Feasibility scores
- **data_availability**: 2/5 — Pretreatment-biopsy FFPE blocks linked to checkpoint-outcome data in OS are rare; spatial transcriptomics on existing blocks adds cost and panel-selection coordination. TFE3-fusion subset is small in any single-center series, requiring multi-center collaboration.
- **technical_feasibility**: 4/5 — PyTorch Geometric + scanpy/squidpy provide the building blocks; HGT is a 2-layer model over mid-size per-tumor graphs; standard single-GPU training in well-trodden territory.
- **clinical_relevance**: 3/5 — OS is rare and current checkpoint use is limited; a validated non-response biomarker would be clinically useful but the addressable patient population is small — a 3 rather than a 4.
- **novelty**: 4/5 — Per-tumor spatial graphs with cell-type-pair typed edges have appeared in breast and melanoma; OS-specific application with TFE3-stratified reporting is, to my knowledge, novel.
- **ethical_clearability**: 3/5 — Retrospective FFPE work is a well-trodden IRB path; multi-institutional data sharing for external validation adds 3–6 months of legal-agreement work.
- **overall (weighted)**: 3.18

## Evidence trail

### AI-confident foundations (well-covered)
| # | Type | Claim | Source |
|---|------|-------|--------|
| 1 | published-evidence | CD204+ M2-polarized tumor-associated macrophage density in osteosarcoma is associated with shorter metastasis-free survival in retrospective IHC cohorts. | Komohara et al 2014, Cancer Sci 105:1–8 |
| 2 | published-evidence | M2-skewed macrophage infiltrate in pretreatment osteosarcoma biopsies has been linked to reduced overall survival in pediatric and AYA cohorts. | Buddingh et al 2011, Clin Cancer Res 17:2110 |
| 3 | published-evidence | Single-agent PD-1 blockade in advanced bone and soft-tissue sarcomas (SARC028) showed objective response in only a minority of osteosarcoma patients, with no validated patient-selection biomarker. | Tawbi et al 2017, Lancet Oncology 18:1493 — SARC028 pembrolizumab in advanced sarcoma |
| 4 | published-evidence | A bulk-RNA-seq IFN-γ-response gene signature predicts pembrolizumab response across multiple solid-tumor histologies, but its performance in osteosarcoma specifically has not been systematically benchmarked. | Ayers et al 2017, J Clin Invest 127:2930 — IFN-γ signature |
| 5 | established-guideline | Retrospective use of FFPE blocks linked to outcome data requires IRB approval and either consent waiver or banked-consent coverage; spatial-transcriptomics on patient material does not change the regulatory category but extends the data minimization conversation. | HHS 45 CFR 46 + institutional IRB review for retrospective tissue research |
| 6 | engineering-precedent | PyTorch Geometric provides production-grade implementations of message-passing GNNs (GAT, GraphSAGE, Heterogeneous Graph Transformer) with first-class support for typed nodes and edges and per-graph readouts. | github.com/pyg-team/pytorch_geometric |
| 7 | published-evidence | Heterogeneous Graph Transformers handle typed nodes and typed edges with parametric attention, fitting the multi-cell-type spatial-graph use case better than plain GCN. | Hu et al 2020, WWW — Heterogeneous Graph Transformer (HGT) |
| 8 | engineering-precedent | scanpy + squidpy together cover the cell-typing, spatial-neighborhood-graph construction, and per-cell feature extraction needed to translate Xenium per-tumor fields into per-tumor graph objects. | github.com/scverse/scanpy + github.com/scverse/squidpy |
| 9 | observation | Per-tumor spatial graphs are mid-size (tens of thousands of cells per Xenium field), so per-tumor forward passes fit on a single 24GB GPU with subgraph sampling. Cohort size (likely 30–80 OS patients across the largest available institutional series) is the bottleneck, not compute. | — |
| 10 | published-evidence | Xenium and MERFISH panels are limited (~300–500 genes); cell-type assignment relies on canonical markers being present in the panel, which constrains downstream feature richness compared to full scRNA-seq. | 10x Genomics Xenium technical brief 2024 + Janesick et al 2023, Nat Commun 14:8353 |
| 11 | observation | Distribution shift between technical platforms (Xenium vs MERFISH vs CosMx) and between institutions (FFPE fixation protocols, panel choice) is real; an external-cohort generalization arm is essential. | — |
| 12 | published-evidence | The 18-gene IFN-γ-response signature is the most-validated bulk-RNA-seq checkpoint-response biomarker across solid tumors and is computable from FFPE-derived RNA at clinical-lab scale. | Ayers et al 2017, J Clin Invest 127:2930 |
| 13 | published-evidence | TFE3-rearranged osteosarcoma is a rare molecular subset; MiT-family transcription factors are documented to modulate lysosomal and immune-related gene programs, which could affect TME composition relative to TFE3-wild-type OS. | Argani et al 2020, Genes Chromosomes Cancer 59:367 — MiT family translocation tumors |
| 14 | established-guideline | Calibration (calibration-in-the-large, calibration slope) is required alongside discrimination for any prediction model intended to inform treatment decisions. | TRIPOD 2015 reporting guideline |
| 15 | observation | Decision-curve analysis at the clinically meaningful threshold (the cost of giving immunotherapy to a non-responder vs withholding it from a responder) is more informative than raw AUROC for whether the model would change practice. | — |
| 16 | observation | Single 24GB GPU; ~4–6 hour training run per fold; 6–10 weeks of analyst time including IRB / tissue procurement / panel selection coordination, plus the external-validation arm. | — |

### Likely-reliable, please verify (sparse coverage)
| # | Type | Claim | Source |
|---|------|-------|--------|
| 1 | published-evidence | The public single-cell RNA-seq atlas at GEO GSE152048 characterizes osteosarcoma myeloid, lymphoid, stromal, and malignant compartments at cell resolution and is widely used as a reference for OS TME analysis. The accession itself is verifiable, but I should hedge on the exact paper-level metadata (authors, journal, year) that accompanies it. | GEO accession GSE152048 (osteosarcoma scRNA-seq atlas); precise paper-level citation hedged |
| 2 | observation | I am not aware of a published, externally-validated, OS-specific checkpoint-response biomarker — bulk IFN-γ is the closest off-the-shelf candidate but its OS performance I would hedge on. | — |
| 3 | observation | Combining HGT-style attention with cell-type-pair edge typing for IO-response prediction in spatial transcriptomics has appeared in breast and melanoma preprints; OS-specific GNN-on-spatial-transcriptomics for IO response, I am less certain has been published. | — |
| 4 | observation | Cohort imbalance: in adult OS, checkpoint responders are likely <20% of treated patients — naive cross-entropy will collapse to majority-class non-response without explicit handling. Specific response rates I'd hedge on per cohort. | — |
| 5 | observation | On osteosarcoma specifically, my training does not contain a definitive numerical AUROC for the IFN-γ signature applied to checkpoint response — I'd hedge that it is plausibly 0.60–0.68 based on transferred pan-cancer performance, but this needs cohort-specific verification. | — |
| 6 | observation | Realistic AUROC ceiling for checkpoint non-response prediction in OS with multimodal spatial features is plausibly 0.70–0.82; the IFN-γ baseline plausibly 0.60–0.68. The ≥ 0.07 improvement is a defensible target but not data-anchored without the pilot. | — |

### Researcher knowledge required

**Knowledge gaps the AI flagged for researcher input:**

1. _(niche-subfield)_ The exact paper-level citation that accompanies the GSE152048 osteosarcoma scRNA-seq atlas — please supply the verified PMID/DOI so the audit pass can confirm authors and journal. The training-recall version of this citation failed PubMed audit on a previous run.
2. _(unpublished-or-pilot-data)_ Does the candidate cohort have FFPE blocks of pretreatment biopsies AND linked checkpoint-inhibitor outcome data (best response by RECIST or PFS)? Spatial transcriptomics requires intact tissue; pretreatment-only is the relevant window.
3. _(patent-or-clinical-practice)_ How is "non-response" being operationalized — RECIST progressive disease at first restaging, no PFS benefit vs historical control, or a composite? OS checkpoint trials have used different endpoints.
4. _(niche-subfield)_ Are there published GNN-on-spatial-transcriptomics models for IO response prediction in any sarcoma histology I should be aware of? I can recall efforts in melanoma and breast but no sarcoma-specific spatial-GNN IO biomarker work.
5. _(lab-tribal-knowledge)_ Is there an annotated cohort where TFE3 fusion status, pretreatment-biopsy spatial transcriptomics, and checkpoint-inhibitor response are linked at the patient level? OS is rare; this triangulation may not exist outside specialized sarcoma centers.
6. _(non-english-literature)_ Are there Japanese or Chinese OS spatial-transcriptomics cohorts with checkpoint outcome data that should inform external validation? Asian OS series have meaningfully different demographics and TME composition that I have weak training coverage on.
7. _(unpublished-or-pilot-data)_ The effect size on the user's pilot cohort (any small case series with even 5–10 patients having paired spatial transcriptomics + IO response) would inform power calculations and the realism of the +0.07 falsifiability threshold; without it the threshold is a defensible prior but not data-anchored.

**Novel syntheses the AI is proposing (not stated by any single source):**

1. Building a per-tumor cell-cell spatial graph with CD204+ M2 macrophage proximity to malignant cells encoded as a typed edge, then predicting checkpoint non-response from the graph, is an architecture I cannot find published for osteosarcoma. — _combines two well-established ideas — CD204+ M2 dominance as an OS-specific suppressive feature and spatial cell-cell graph representation — into a single per-patient prediction graph, which I cannot find written down for OS checkpoint response_
2. Using HGT cell-type-pair edge tokens lets the model learn that, for example, the M2↔tumor edge weight matters more than the M2↔fibroblast edge weight, without manual neighborhood-density feature engineering. — _HGT cell-type-pair edge tokens make M2-tumor-proximity weighting learnable rather than hand-coded as a fixed M2-density feature — this combination doesn't appear in OS literature I'm aware of_
3. Training the model on a pan-OS cohort but reporting performance separately on TFE3-fusion patients (and ideally training a TFE3-specific head) would be the honest framing — pooled training, stratified evaluation. — _if TFE3 fusion modifies macrophage polarization or IFN-γ-response programs, the model must be trained or evaluated stratified by fusion status — otherwise the TFE3 subset's signal is averaged into the larger TFE3-wild-type pool and may be missed_

## Citation audit

### ✓ Verified (7)
| Auditor | AI claim | Verified record |
|---------|----------|-----------------|
| geo | GEO GSE152048 marker panel | GSE152048 — https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE152048 |
| github | github.com/pyg-team/pytorch_geometric | pyg-team/pytorch_geometric — https://github.com/pyg-team/pytorch_geometric |
| github | github.com/scverse/scanpy | scverse/scanpy — https://github.com/scverse/scanpy |
| github | github.com/scverse/squidpy | scverse/squidpy — https://github.com/scverse/squidpy |
| github | github.com/scverse/scanpy | scverse/scanpy — https://github.com/scverse/scanpy |
| github | github.com/scverse/squidpy | scverse/squidpy — https://github.com/scverse/squidpy |
| geo | GEO GSE152048 marker panel | GSE152048 — https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE152048 |

## Epistemic summary
- well-covered claims: **16**
- sparse-coverage claims: **6**
- knowledge gaps flagged: **7**
- novel syntheses proposed: **3**

_Generated by DeltaScience 0.3.0 :: pack biomed v0.1.0 :: mockllm/mock-llm-v1_