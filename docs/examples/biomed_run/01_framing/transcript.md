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
