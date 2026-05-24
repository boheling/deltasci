The data + ML stack is straightforward; the engineering questions are feature engineering for Class II heterodimers and platform-discrepancy handling.

**Data representation.**

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/ANHIG/IMGTHLA"]The IPD-IMGT/HLA Database is mirrored on GitHub at ANHIG/IMGTHLA, providing FASTA + version-controlled allele protein sequences for all HLA loci.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Robinson et al 2020, Nucleic Acids Res 48:D948 — IPD-IMGT/HLA Database"]The IPD-IMGT/HLA Database is the canonical reference for HLA nomenclature and sequence; the most recently published comprehensive description appeared in Nucleic Acids Research.[/CLAIM]

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/biopython/biopython"]Biopython provides robust FASTA parsing and per-allele sequence indexing.[/CLAIM]

For each MARCo allele pair (a1, a2), the feature vector is:
- HATS shares-serotype: binary indicator (do a1 and a2 share serotype per HATS rules?)
- HATS key-residue Hamming: count of mismatches at HATS key positions for the locus
- HLA-EMMA SA-mismatch count: count of mismatches at solvent-accessible positions
- HLA-EMMA total mismatch count: count of all amino-acid mismatches
- Per-position one-hot indicators at the locus's top-10 most variable positions
- Locus indicator: 5-way one-hot for {DRB1, DRB3/4/5 grouped, DQA1, DQB1, DQ-heterodimer, DP-heterodimer}
- Platform indicator: 2-way one-hot {Immucor, OL}
- Sample-count features: log(n_samples), n_immucor, n_ol

For DQ heterodimer pairs, the feature vector concatenates α-chain (DQA1) AND β-chain (DQB1) features — handling the heterodimer correctly without forcing a single-chain abstraction.

Output: predicted Spearman ρ ∈ [-1, 1] (regression).

**ML paradigm.**

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/dmlc/xgboost"]XGBoost is the canonical gradient-boosted regressor for tabular feature-engineering tasks at this scale; native feature-importance interpretation supports the post-hoc analysis.[/CLAIM]

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/scikit-learn/scikit-learn"]scikit-learn provides RandomForestRegressor, GroupKFold, and the suite of evaluation metrics needed for cross-validated regression with leakage protection.[/CLAIM]

A 4-way structured comparison on held-out allele pairs:
1. Naive AA Hamming distance (count of mismatched positions across the mature protein)
2. HATS shares-serotype binary
3. HLA-EMMA SA-mismatch count
4. XGBoost on all features (proposed)

[CLAIM type=observation coverage=sparse source=""]I would hedge on whether XGBoost outperforms LightGBM or a small neural net at this data scale; the choice depends on the realized N (number of allele pairs) which I do not know without MARCo extraction.[/CLAIM]

**Existing implementations of the exact idea.**

[KNOWLEDGE_GAP category=niche-subfield]Are there published learned (non-rule-based) cross-reactivity prediction models for HLA Class II using empirical MFI as a target? I can recall HLAMatchmaker / PIRCHE-II / HLA-EMMA as rule-based tools and Tambur's STAR working-group platform-comparison work, but not an empirical-MFI-target learned regressor.[/KNOWLEDGE_GAP]

**Compute.**

[CLAIM type=observation coverage=well-covered source=""]Trivial — single CPU, ~1 hour training. The bottleneck is data acquisition: MARCo extraction + IPD-IMGT/HLA download + HATS Perl run + HLA-EMMA processing — all together likely 1-2 weeks of analyst time depending on whether MARCo exposes a bulk-download endpoint.[/CLAIM]

**Top three risks.**

1. [CLAIM type=published-evidence coverage=well-covered source="Tambur et al 2018, Am J Transplant 18:1604"]Eplet / key-residue definitions are version-dependent; retrospective reanalysis with newer HLAMatchmaker versions has produced different results — same caution applies to HATS revisions.[/CLAIM]

2. [CLAIM type=observation coverage=well-covered source=""]Cross-locus pairs (DR vs DQ, DQ vs DP) shouldn't show structural antibody cross-reactivity — antibodies are locus-specific by physical-recognition argument — but the dataset has them by combinatorial enumeration. Explicit within-locus filter required.[/CLAIM]

3. [CLAIM type=observation coverage=sparse source=""]Imbalanced sample sizes per allele pair (some N>1000, some N<50) mean the empirical Spearman ρ uncertainty differs across pairs. Sample-size-weighted MSE loss handles this; without weighting, the model fits the noise of small-N pairs.[/CLAIM]

[NOVEL_SYNTHESIS rationale="explicit α+β-chain concatenated featurization for DQ/DP heterodimers (vs single-chain features) is rarely framed in the LSA-virtual-crossmatch literature, which tends to focus on β-chain alone for DR matching"]Chain-aware encoding for DQ and DP heterodimers — concatenating features from both α-chain and β-chain pairs into a single feature vector — is an architectural choice that should be ablated; the literature usually reduces to β-chain mismatches alone.[/NOVEL_SYNTHESIS]
