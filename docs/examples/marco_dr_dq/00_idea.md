# Research idea

Predict empirical anti-HLA Class II (DR / DQ heterodimer / DPA1+DPB1) antibody cross-reactivity — operationalized as the MFI Spearman correlation between allele pairs in the public MARCo dataset (marco.igen.org.br) — using a learned model over HATS key-residue + HLA-EMMA solvent-accessible mismatch features with chain-aware encoding for heterodimers. The model must be platform-agnostic across Immucor/Werfen and One Lambda/Thermo Fisher LSA assays, evaluated specifically on the platform-discrepant allele-pair subset where the two manufacturers disagree.
