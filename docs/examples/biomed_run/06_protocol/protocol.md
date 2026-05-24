# Experiment plan — Spatial CD204+ M2 macrophage neighborhood graph for OS checkpoint-immunotherapy non-response prediction

Per-tumor spatial transcriptomics over Xenium fields; cell-type-typed cell-cell graph with CD204+ M2-malignant edges; HGT encoder; calibrated AUROC for non-response, stratified by TFE3-fusion status, evaluated against bulk IFN-γ Hallmark signature baseline.

## Data acquisition
- **Primary dataset**: Institutional pretreatment FFPE OS biopsy cohort with linked PD-1 / PD-L1 inhibitor RECIST outcomes; Xenium 10x in-situ panel.
- **Accession / URL**: (institutional cohort — DUA + IRB required; reference OS scRNA-seq atlas at GEO GSE152048 for cell-type marker priors)
- **Access constraints**: IRB approval, FFPE block availability, RECIST adjudication, multi-site DUA for external validation
- **Fallback datasets**: public GSE152048 for marker priors, Vizgen MERFISH OS panel if Xenium unavailable

## Steps

### 1. Cohort assembly
Pretreatment FFPE biopsies with linked best-RECIST-response and TFE3-fusion status.
- **Inputs**: FFPE blocks, clinical chart
- **Outputs**: cohort manifest
- **Methods cited**: RECIST 1.1, Eisenhauer 2009

### 2. Spatial transcriptomics + QC
Run Xenium panel; QC per cell, per FOV, per sample.
- **Inputs**: FFPE sections
- **Outputs**: per-cell expression matrices
- **Methods cited**: github.com/scverse/scanpy, github.com/scverse/squidpy

### 3. Cell-type annotation
Reference-mapped annotation against OS scRNA-seq atlas; tag CD204+ M2, malignant, T-cell, fibroblast.
- **Inputs**: per-cell expression
- **Outputs**: typed cells
- **Methods cited**: GEO GSE152048 marker panel

### 4. Spatial graph construction
k-NN in physical-µm with edge type = cell-type pair (M2-malignant, M2-T, T-malignant, ...).
- **Inputs**: typed cells, x/y coords
- **Outputs**: per-tumor heterogeneous graph
- **Methods cited**: github.com/pyg-team/pytorch_geometric

### 5. HGT encoder + survival head
Heterogeneous Graph Transformer (Hu et al 2020) → graph readout → MLP head; multitask loss.
- **Inputs**: graphs, outcomes
- **Outputs**: trained model, predictions
- **Methods cited**: Hu et al 2020 WWW HGT

### 6. Evaluation + calibration
AUROC + AUPRC + decision-curve analysis vs IFN-γ Hallmark baseline; stratified by TFE3 status.
- **Inputs**: predictions
- **Outputs**: metrics, figures
- **Methods cited**: TRIPOD 2015

## Evaluation
- **Primary metric**: AUROC for predicting checkpoint-inhibitor non-response (best RECIST = PD)
- **Success threshold**: AUROC ≥ 0.75 absolute AND ≥ 0.07 above bulk IFN-γ baseline AUROC, with calibration intercept |α| < 0.05 and slope ∈ [0.9, 1.1]
- **Null outcome**: AUROC improvement < 0.02 over bulk IFN-γ baseline, OR calibration slope outside [0.85, 1.15], OR no detectable signal in TFE3-fusion stratum
- **Baselines**: bulk IFN-γ Hallmark signature, TIL count from H&E, M2/M1 ratio bulk, logistic regression on simple panel

## Compute
- **Hardware**: 1× A100 (24GB sufficient for per-tumor graphs)
- **Estimated runtime**: 8-12h training
- **Storage**: ~500GB Xenium raw + 50GB processed
- **Cost estimate**: low (~$50 GPU)

## Timeline
12-16 weeks: cohort assembly + IRB (4-6w), Xenium runs (4w), modeling + writing (6w)

## Sample-size justification
Power calculation TBD; expect ~60-100 OS pretreatment biopsies with linked outcomes — likely underpowered for stratified TFE3 analysis without multi-site collaboration.