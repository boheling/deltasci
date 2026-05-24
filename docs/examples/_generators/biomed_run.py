"""Generate the biomed example run.

This script feeds a pre-authored 4-round transcript + synthesis JSON into
deltasci's CoReasoner via MockLLM, producing the same artifacts you would
get from a live --llm anthropic run. The responses below were authored by
Claude in a Claude Code session (the same model class deltasci would have
called, just routed through scripting instead of the API). The grounding
parser, falsifiability gate, and epistemic-humility gate are exercised
identically to a live run.

Re-run: from the deltasci repo root, with the venv active:

    python docs/examples/_generators/biomed_run.py
"""

from __future__ import annotations

import json
from pathlib import Path

from deltasci import CoReasoner, Config, load_pack
from deltasci.cli import _render_hypothesis_md
from deltasci.llm.mock import MockLLM


IDEA = (
    "Predict checkpoint-immunotherapy non-response in TFE3-fusion osteosarcoma using a "
    "graph neural network over single-cell spatial transcriptomics, with CD204+ M2 "
    "macrophage neighborhood structure encoded as typed cell-cell edges."
)


DOMAIN_R1 = """\
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
"""


ENGINEER_R1 = """\
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
"""


DOMAIN_R2 = """\
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
"""


ENGINEER_R2 = """\
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
"""


SYNTHESIS_JSON = json.dumps(
    {
        "title": "Spatial CD204+ M2 macrophage neighborhood graph as a checkpoint-immunotherapy non-response predictor in TFE3-fusion osteosarcoma",
        "statement": (
            "A heterogeneous graph neural network operating on per-tumor single-cell spatial transcriptomics, "
            "with cell-type-pair typed edges (in particular, CD204+ M2 macrophage proximity to malignant cells), "
            "will predict checkpoint-immunotherapy non-response in osteosarcoma at AUROC ≥ 0.75 on held-out data, "
            "improving over a bulk IFN-γ Hallmark signature baseline by ≥ 0.07 AUROC, with calibration intercept "
            "|α| < 0.05 and slope within [0.9, 1.1]. Performance is reported stratified by TFE3 fusion status."
        ),
        "domain_grounding": {
            "mechanism": (
                "CD204+ M2-polarized macrophage dominance in the osteosarcoma TME is documented to associate "
                "with poor outcome and is mechanistically linked to T-cell suppression. Spatial proximity of "
                "M2 macrophages to malignant cells preserves geometric information that bulk RNA-seq "
                "discards. TFE3 fusion may modulate the surrounding TME via MiT-family transcriptional programs."
            ),
            "unmet_need": (
                "Patient-level checkpoint-immunotherapy response prediction in osteosarcoma. Single-agent PD-1 "
                "blockade has limited efficacy (SARC028) and there is no validated OS-specific selection biomarker; "
                "the bulk IFN-γ signature is the off-the-shelf candidate but its OS performance is unbenchmarked."
            ),
            "expected_impact": (
                "Better-calibrated patient selection for checkpoint immunotherapy at the time of treatment "
                "decision, particularly for the rare TFE3-fusion subset where stratified performance can "
                "reveal subset-specific signal lost in pooled analyses."
            ),
        },
        "technical_approach": {
            "core_method": (
                "Heterogeneous Graph Transformer (HGT) over per-tumor cell-cell spatial graph with cell-type-pair "
                "typed edges → graph readout → patient-feature concatenation (TFE3 status, prior therapy line) → "
                "MLP head producing checkpoint-response logit, trained with focal loss + calibration regularizer."
            ),
            "key_innovation": (
                "Per-tumor spatial graph with CD204+ M2-tumor cell-type-pair edge typing — to my knowledge not "
                "previously combined with HGT for IO-response prediction in osteosarcoma."
            ),
            "implementation_path": (
                "Institutional Xenium / MERFISH pretreatment-biopsy series + IO outcome linkage → squidpy spatial "
                "neighborhood graphs → PyTorch Geometric HGT + focal loss → stratified split by year + institution → "
                "external validation on second institutional cohort with cross-platform → comparison vs IFN-γ "
                "signature baseline + flat M2-density baseline + HGT-without-typed-edges ablation."
            ),
        },
        "falsifiability": {
            "prediction": (
                "The HGT-with-CD204+M2-typed-edges model achieves a higher AUROC for checkpoint-immunotherapy "
                "non-response than the bulk IFN-γ signature baseline on the external held-out OS cohort."
            ),
            "threshold": (
                "AUROC ≥ 0.75 absolute, AND AUROC improvement ≥ 0.07 over bulk IFN-γ baseline with 95% CI lower "
                "bound > IFN-γ baseline, AND calibration intercept |α| < 0.05, AND calibration slope in [0.9, 1.1]."
            ),
            "null_outcome": (
                "AUROC improvement < 0.03 over bulk IFN-γ baseline, OR calibration slope outside [0.85, 1.15], "
                "falsifies the hypothesis: the spatial-graph cell-type-pair edge typing did not add value over "
                "scalar M2 density or bulk IFN-γ score."
            ),
        },
        "feasibility_scores": {
            "data_availability": 2,
            "technical_feasibility": 4,
            "clinical_relevance": 3,
            "novelty": 4,
            "ethical_clearability": 3,
        },
        "feasibility_justifications": {
            "data_availability": (
                "Pretreatment-biopsy FFPE blocks linked to checkpoint-outcome data in OS are rare; spatial "
                "transcriptomics on existing blocks adds cost and panel-selection coordination. TFE3-fusion "
                "subset is small in any single-center series, requiring multi-center collaboration."
            ),
            "technical_feasibility": (
                "PyTorch Geometric + scanpy/squidpy provide the building blocks; HGT is a 2-layer model over "
                "mid-size per-tumor graphs; standard single-GPU training in well-trodden territory."
            ),
            "clinical_relevance": (
                "OS is rare and current checkpoint use is limited; a validated non-response biomarker would be "
                "clinically useful but the addressable patient population is small — a 3 rather than a 4."
            ),
            "novelty": (
                "Per-tumor spatial graphs with cell-type-pair typed edges have appeared in breast and melanoma; "
                "OS-specific application with TFE3-stratified reporting is, to my knowledge, novel."
            ),
            "ethical_clearability": (
                "Retrospective FFPE work is a well-trodden IRB path; multi-institutional data sharing for "
                "external validation adds 3–6 months of legal-agreement work."
            ),
        },
    },
    indent=2,
)


PROTOCOL_JSON = json.dumps({
    "title": "Spatial CD204+ M2 macrophage neighborhood graph for OS checkpoint-immunotherapy non-response prediction",
    "summary": "Per-tumor spatial transcriptomics over Xenium fields; cell-type-typed cell-cell graph with CD204+ M2-malignant edges; HGT encoder; calibrated AUROC for non-response, stratified by TFE3-fusion status, evaluated against bulk IFN-γ Hallmark signature baseline.",
    "data_acquisition": {
        "primary_dataset": "Institutional pretreatment FFPE OS biopsy cohort with linked PD-1 / PD-L1 inhibitor RECIST outcomes; Xenium 10x in-situ panel.",
        "accession_or_url": "(institutional cohort — DUA + IRB required; reference OS scRNA-seq atlas at GEO GSE152048 for cell-type marker priors)",
        "access_constraints": "IRB approval, FFPE block availability, RECIST adjudication, multi-site DUA for external validation",
        "fallback_datasets": ["public GSE152048 for marker priors", "Vizgen MERFISH OS panel if Xenium unavailable"],
    },
    "steps": [
        {"order": 1, "name": "Cohort assembly", "description": "Pretreatment FFPE biopsies with linked best-RECIST-response and TFE3-fusion status.",
         "inputs": ["FFPE blocks", "clinical chart"], "outputs": ["cohort manifest"],
         "method_citations": ["RECIST 1.1, Eisenhauer 2009"]},
        {"order": 2, "name": "Spatial transcriptomics + QC", "description": "Run Xenium panel; QC per cell, per FOV, per sample.",
         "inputs": ["FFPE sections"], "outputs": ["per-cell expression matrices"],
         "method_citations": ["github.com/scverse/scanpy", "github.com/scverse/squidpy"]},
        {"order": 3, "name": "Cell-type annotation", "description": "Reference-mapped annotation against OS scRNA-seq atlas; tag CD204+ M2, malignant, T-cell, fibroblast.",
         "inputs": ["per-cell expression"], "outputs": ["typed cells"],
         "method_citations": ["GEO GSE152048 marker panel"]},
        {"order": 4, "name": "Spatial graph construction", "description": "k-NN in physical-µm with edge type = cell-type pair (M2-malignant, M2-T, T-malignant, ...).",
         "inputs": ["typed cells", "x/y coords"], "outputs": ["per-tumor heterogeneous graph"],
         "method_citations": ["github.com/pyg-team/pytorch_geometric"]},
        {"order": 5, "name": "HGT encoder + survival head", "description": "Heterogeneous Graph Transformer (Hu et al 2020) → graph readout → MLP head; multitask loss.",
         "inputs": ["graphs", "outcomes"], "outputs": ["trained model", "predictions"],
         "method_citations": ["Hu et al 2020 WWW HGT"]},
        {"order": 6, "name": "Evaluation + calibration", "description": "AUROC + AUPRC + decision-curve analysis vs IFN-γ Hallmark baseline; stratified by TFE3 status.",
         "inputs": ["predictions"], "outputs": ["metrics", "figures"],
         "method_citations": ["TRIPOD 2015"]},
    ],
    "primary_metric": "AUROC for predicting checkpoint-inhibitor non-response (best RECIST = PD)",
    "success_threshold": "AUROC ≥ 0.75 absolute AND ≥ 0.07 above bulk IFN-γ baseline AUROC, with calibration intercept |α| < 0.05 and slope ∈ [0.9, 1.1]",
    "null_outcome": "AUROC improvement < 0.02 over bulk IFN-γ baseline, OR calibration slope outside [0.85, 1.15], OR no detectable signal in TFE3-fusion stratum",
    "baselines": ["bulk IFN-γ Hallmark signature", "TIL count from H&E", "M2/M1 ratio bulk", "logistic regression on simple panel"],
    "compute": {"hardware": "1× A100 (24GB sufficient for per-tumor graphs)", "estimated_runtime": "8-12h training",
                "storage": "~500GB Xenium raw + 50GB processed", "cost_estimate": "low (~$50 GPU)"},
    "timeline_estimate": "12-16 weeks: cohort assembly + IRB (4-6w), Xenium runs (4w), modeling + writing (6w)",
    "sample_size_justification": "Power calculation TBD; expect ~60-100 OS pretreatment biopsies with linked outcomes — likely underpowered for stratified TFE3 analysis without multi-site collaboration."
}, indent=2)


RISKS_JSON = json.dumps({
    "summary": "Six risks ranked by their potential to falsely produce or hide a positive result.",
    "items": [
        {"id": "R1", "category": "data", "severity": "critical",
         "description": "Pretreatment FFPE OS biopsy cohorts with linked checkpoint-inhibitor outcomes are very small (likely <100 patients, often <50 with high-quality Xenium); single-site cohorts will be severely underpowered for stratified TFE3-fusion analysis.",
         "likely_failure_mode": "wide AUROC confidence intervals overlapping the IFN-γ baseline, false negative on the +0.07 falsifiability threshold even if true effect exists.",
         "mitigation": "Multi-site cohort assembly via SARC consortium or COG before commencing; pre-register sample-size requirements.",
         "counter_evidence_citations": []},
        {"id": "R2", "category": "evaluation", "severity": "high",
         "description": "AUROC may not reflect the clinically actionable improvement at the offer-acceptance decision threshold; non-response is the rare class, so AUPRC and net benefit at the relevant decision point matter more than AUROC.",
         "likely_failure_mode": "model achieves AUROC > 0.75 but decision-curve analysis shows no benefit over standard of care.",
         "mitigation": "Pre-specify AUPRC + DCA at clinically meaningful threshold as co-primary endpoints.",
         "counter_evidence_citations": ["Vickers & Elkin 2006 Med Decis Making 26:565"]},
        {"id": "R3", "category": "method", "severity": "high",
         "description": "Cell-type annotation noise — CD204 / CD68 / CD163 panels in Xenium can confuse M2 macrophages with osteoclast-like cells abundant in OS — would propagate into spurious graph edges.",
         "likely_failure_mode": "model learns osteoclast spatial signal, not M2 polarization; effect disappears in external validation.",
         "mitigation": "Add osteoclast markers (TRAP, CTSK) to panel; require dual-positive CD204+CD68+CD163+ for M2 calls; sensitivity-test with leave-one-marker-out.",
         "counter_evidence_citations": []},
        {"id": "R4", "category": "confounding", "severity": "high",
         "description": "TFE3-fusion status may be confounded with cohort-source — TFE3-positive cases concentrate at large referral centers — making the TFE3-stratified evaluation a site effect rather than a biology effect.",
         "likely_failure_mode": "stratified TFE3 result reproduces site demographics, not the proposed biological signal.",
         "mitigation": "Multi-site cohort with matched TFE3 distributions across sites; site-as-confound sensitivity analysis.",
         "counter_evidence_citations": []},
        {"id": "R5", "category": "novelty-overstated", "severity": "medium",
         "description": "Spatial graph approaches to immunotherapy response prediction in melanoma and breast cancer are increasingly common; the OS-specific contribution may be smaller than framed if the architecture itself is borrowed.",
         "likely_failure_mode": "reviewers note that the OS application is straightforward transfer of existing methods.",
         "mitigation": "Position the contribution as the OS-specific cell-type panel + TFE3-stratified evaluation, not the architecture; cite the prior melanoma/breast spatial-graph IO work directly.",
         "counter_evidence_citations": []},
        {"id": "R6", "category": "ethics-or-governance", "severity": "medium",
         "description": "Multi-site DUA + IRB for federated training of a clinical-decision-support tool is non-trivial; privacy-preserving federated learning has its own failure modes.",
         "likely_failure_mode": "project stalls at 6 months in legal review; or, simpler federated approach has unexpected accuracy hit.",
         "mitigation": "Begin DUA discussions in week 1 of project, before any modeling; plan for centralized vs federated decision early.",
         "counter_evidence_citations": []},
    ],
}, indent=2)


CHALLENGE_JSON = json.dumps({
    "summary": "Five concrete challenges. The hypothesis is plausible but the falsifiability threshold (+0.07 AUROC over IFN-γ) is more aggressive than the cohort size will support, the cell-type annotation step is doing more inferential work than the framing acknowledges, and the comparison to a bulk RNA-seq baseline conflates two evaluation regimes.",
    "findings": [
        {"id": "C1", "kind": "feasibility-overstated", "severity": "high",
         "description": "The +0.07 absolute AUROC lift over bulk IFN-γ baseline at n≈60-100 pretreatment OS biopsies is unlikely to be detectable with statistical confidence. Effect-size calculations for AUROC differences at this sample size place the minimum detectable lift well above 0.07.",
         "evidence_citations": ["Hanley & McNeil 1982 Radiology 143:29 — AUC variance estimator"],
         "suggested_response": "Pre-register an interim analysis at n=40 with go/no-go thresholds; downgrade the falsifiability target to a calibration-focused metric if AUROC differences are not powered."},
        {"id": "C2", "kind": "wrong-metric", "severity": "high",
         "description": "AUROC for a class-imbalanced outcome (non-response is ~30-40% in OS checkpoint trials) is dominated by the negatives. AUPRC and decision-curve net benefit at clinically meaningful threshold (e.g., 'would you take this kidney offer / start this treatment') are more informative and the hypothesis should commit to one.",
         "evidence_citations": ["Vickers et al 2008 BMJ 336:1170 — DCA for clinical models"],
         "suggested_response": "Add AUPRC (target >0.55) and DCA (target net benefit > standard-of-care across threshold range 10-40%) as co-primary endpoints."},
        {"id": "C3", "kind": "data-leakage-risk", "severity": "high",
         "description": "Cell-type annotation is performed by reference-mapping against an external scRNA-seq atlas (GSE152048). If the reference and the test cohort overlap (institutional sample sharing), or if the annotator is trained on the same cohort being used for test, the spatial graph features inherit leakage.",
         "evidence_citations": [],
         "suggested_response": "Hold out annotation training data by patient AND by site; use only patient IDs disjoint from atlas contributors; report annotation-pipeline cross-validation separately."},
        {"id": "C4", "kind": "missing-baseline", "severity": "medium",
         "description": "The proposed baseline (bulk IFN-γ Hallmark) is a soft target. Stronger comparisons that the model must beat: (a) TIL density from H&E (free, used clinically), (b) PD-L1 IHC tumor proportion score (FDA-validated companion diagnostic for some indications), (c) simple M2/M1 ratio from the same Xenium panel without spatial structure.",
         "evidence_citations": [],
         "suggested_response": "Add (a)+(b)+(c) as required baselines; if the spatial-graph model does not beat the simple M2/M1 ratio, the spatial framing was unnecessary."},
        {"id": "C5", "kind": "novelty-overstated", "severity": "medium",
         "description": "Spatial-graph IO response prediction is now common in melanoma (Schurch et al 2020, Cell), breast cancer (Wang et al 2024), and triple-negative breast (Keren et al 2018). The OS-specific contribution is the cell-type panel + TFE3 stratification, not the architecture itself.",
         "evidence_citations": ["Schurch et al 2020, Cell 182:1341", "Keren et al 2018, Cell 174:1373"],
         "suggested_response": "Frame the OS-specific contribution explicitly; do not claim novelty for HGT or spatial-graph IO prediction in general."},
    ],
}, indent=2)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "examples" / "biomed_run"
    out_dir.mkdir(parents=True, exist_ok=True)

    pack = load_pack("biomed")
    llm = MockLLM(responses=[
        DOMAIN_R1, ENGINEER_R1, DOMAIN_R2, ENGINEER_R2,
        SYNTHESIS_JSON,
        PROTOCOL_JSON,
        RISKS_JSON,
        CHALLENGE_JSON,
    ])
    config = Config(
        num_rounds=4,
        grounding_strictness="high",
        require_falsifiability=True,
        require_epistemic_humility=True,
        generate_protocol=True,
        generate_risks=True,
        run_challenge=True,
        auto_view=False,
        output_dir=out_dir,
    )
    reasoner = CoReasoner(pack=pack, llm=llm, config=config)
    result = reasoner.run(idea=IDEA)

    # Use the staged-layout writer (v0.2.0 default; v0.3.0 adds 10_notebook/).
    from deltasci.cli import _write_outputs_staged
    _write_outputs_staged(result, out_dir, IDEA, pack=pack, generate_notebook=True)

    es = result.hypothesis.epistemic_summary
    audit = result.audit_report
    print(f"biomed_run (v0.2.0) generated:")
    print(f"  well-covered claims:    {es.well_covered_count}")
    print(f"  sparse-coverage claims: {es.sparse_count}")
    print(f"  knowledge gaps:         {es.knowledge_gap_count}")
    print(f"  novel syntheses:        {es.novel_synthesis_count}")
    print(f"  protocol steps:         {len(result.plan.steps) if result.plan else 0}")
    print(f"  risks identified:       {len(result.risks.items) if result.risks else 0}")
    print(f"  challenger findings:    {len(result.challenge.findings) if result.challenge else 0}")
    print(f"  audit:                  {audit.banner()}")
    if audit.mismatch_count:
        print()
        print("FAILED AUDIT details:")
        for f in audit.findings:
            if f.status != "mismatch":
                continue
            print(f"  ✗ [{f.auditor_name}] AI claimed: {f.target_summary[:100]}")
            for r in f.mismatch_reasons:
                print(f"      → {r}")
    print(f"  outputs in {out_dir}")


if __name__ == "__main__":
    main()
