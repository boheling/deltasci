The hypothesis sits at the intersection of three converging substrates: (a) anti-HLA Class II antibodies, especially anti-DQ, dominate antibody-mediated rejection in modern kidney and lung transplantation; (b) MARCo provides population-scale empirical MFI cross-reactivity at allele-pair resolution, publicly; and (c) two complementary residue-level tools — HATS for serotype assignment and HLA-EMMA for amino-acid mismatch profiling — give clean feature inputs.

[CLAIM type=published-evidence coverage=well-covered source="Wiebe et al 2017, Am J Transplant 17:3050"]De novo donor-specific anti-HLA Class II antibodies (with anti-DQ predominating) drive the majority of antibody-mediated rejection events in modern kidney transplantation and are mechanistically linked to graft loss.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Tambur et al 2018, Am J Transplant 18:1604 — STAR consensus"]The Sensitization in Transplantation: Assessment of Risk (STAR) working group documented that LSA-based virtual crossmatch interpretation is non-trivially platform-dependent: Immucor and One Lambda assays disagree on certain MFI thresholds and on bead-specific reactivities. This is the central practical motivation for a platform-agnostic predictor.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Kramer et al 2020, HLA 96:43 — HLA-EMMA"]HLA-EMMA produces a per-position amino-acid mismatch profile between any two HLA alleles, with solvent-accessible (SA) positions explicitly flagged — these positions are the primary candidates for antibody-recognized epitopes.[/CLAIM]

[CLAIM type=published-evidence coverage=well-covered source="Osoegawa et al 2024, HLA 104:e15702 — HATS"]The HATS classifier assigns HLA alleles to broad serological types using a systematic key-residue-position rule that covers Class I (A/B/C) and Class II (DRB1/3/4/5, DQA1, DQB1, DPA1).[/CLAIM]

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/kosoegawa/HATS"]A reference Perl implementation of HATS is publicly available; it consumes IPD-IMGT/HLA protein FASTA and emits per-allele key-residue tables consumable from any language.[/CLAIM]

[CLAIM type=observation coverage=well-covered source=""]MARCo (marco.igen.org.br) is a public Brazilian-cohort tool that produces, for each pair of HLA alleles queried, the empirical Spearman correlation, R², regression coefficients, manufacturer-stratified sample counts, discordance rates, and HATS+HLA-EMMA annotations — across 1,000+ sera, with filters by transfusion / transplant / pregnancy history.[/CLAIM]

[CLAIM type=observation coverage=sparse source=""]The MARCo manufacturer dropdown supports Immucor/Werfen and One Lambda/Thermo Fisher (with the OL ExPlex extended panel as a sub-category); per-pair counts on each platform vary, with some pairs covered on only one platform — the exact distribution would require systematic extraction across all DR/DQ pairs.[/CLAIM]

The unmet need is a calibrated, platform-agnostic, residue-resolution predictor for Class II HLA antibody cross-reactivity that beats both rule-based virtual-crossmatch heuristics and single-platform learned models:

[CLAIM type=published-evidence coverage=well-covered source="Wiebe & Nickerson 2018, Curr Opin Organ Transplant 23:399"]DQ-DSA dominates Class II-DSA in modern dnDSA cohorts; eplet-based DQ matching has improved donor-recipient pair selection but remains rule-based and platform-naive.[/CLAIM]

[NOVEL_SYNTHESIS rationale="treating MARCo's per-allele-pair empirical Spearman ρ as a regression target — with HATS key-residue + HLA-EMMA SA-position features and chain-aware encoding for DQ/DP heterodimers — has not, to my knowledge, been published; the existing tools are rule-based and platform-specific"]Combining MARCo's population-MFI ground truth with HATS key-residue features and HLA-EMMA SA-position features in a single supervised regression task, with platform-id auxiliary features for cross-platform calibration, is the conceptual leap.[/NOVEL_SYNTHESIS]

Constraints worth flagging:

[CLAIM type=established-guideline coverage=well-covered source="STAR 2018 + TRIPOD 2015 reporting"]Calibration (intercept, slope) is a required deliverable for any prognostic / classification tool the transplant community would adopt; pure discrimination metrics are insufficient.[/CLAIM]

[KNOWLEDGE_GAP category=unpublished-or-pilot-data]Does the lab have access to a paired-platform institutional cohort (Immucor + One Lambda LSA on the same sera) for an external validation arm beyond MARCo? This is the difference between a benchmark model and a clinically deployable tool.[/KNOWLEDGE_GAP]

[KNOWLEDGE_GAP category=non-english-literature]Brazilian transplant cohort literature, especially from MARCo's contributing institutions, may carry context on cohort sensitization-route distribution and population-genetic structure that I would underweight from English-only references.[/KNOWLEDGE_GAP]

[KNOWLEDGE_GAP category=patent-or-clinical-practice]Whether MARCo exposes a bulk-download / API endpoint for systematic per-pair extraction across all DR/DQ pairs (~10,000+ pairs) is unclear from the public-facing UI; respectful scraping vs institutional contact may both be required.[/KNOWLEDGE_GAP]
