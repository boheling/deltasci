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
