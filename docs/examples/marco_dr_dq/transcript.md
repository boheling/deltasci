# Co-Reasoning Transcript

**Pack:** `biomed-serology`

**Idea:** Predict empirical anti-HLA Class II (DR / DQ heterodimer / DPA1+DPB1) antibody cross-reactivity — operationalized as the MFI Spearman correlation between allele pairs in the public MARCo dataset (marco.igen.org.br) — using a learned model over HATS key-residue + HLA-EMMA solvent-accessible mismatch features with chain-aware encoding for heterodimers. The model must be platform-agnostic across Immucor/Werfen and One Lambda/Thermo Fisher LSA assays, evaluated specifically on the platform-discrepant allele-pair subset where the two manufacturers disagree.

## domain_r1 — domain_scientist

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

### Evidence collected
- **[published-evidence · well-covered]** De novo donor-specific anti-HLA Class II antibodies (with anti-DQ predominating) drive the majority of antibody-mediated rejection events in modern kidney transplantation and are mechanistically linked to graft loss. — _Wiebe et al 2017, Am J Transplant 17:3050_
- **[published-evidence · well-covered]** The Sensitization in Transplantation: Assessment of Risk (STAR) working group documented that LSA-based virtual crossmatch interpretation is non-trivially platform-dependent: Immucor and One Lambda assays disagree on certain MFI thresholds and on bead-specific reactivities. This is the central practical motivation for a platform-agnostic predictor. — _Tambur et al 2018, Am J Transplant 18:1604 — STAR consensus_
- **[published-evidence · well-covered]** HLA-EMMA produces a per-position amino-acid mismatch profile between any two HLA alleles, with solvent-accessible (SA) positions explicitly flagged — these positions are the primary candidates for antibody-recognized epitopes. — _Kramer et al 2020, HLA 96:43 — HLA-EMMA_
- **[published-evidence · well-covered]** The HATS classifier assigns HLA alleles to broad serological types using a systematic key-residue-position rule that covers Class I (A/B/C) and Class II (DRB1/3/4/5, DQA1, DQB1, DPA1). — _Osoegawa et al 2024, HLA 104:e15702 — HATS_
- **[engineering-precedent · well-covered]** A reference Perl implementation of HATS is publicly available; it consumes IPD-IMGT/HLA protein FASTA and emits per-allele key-residue tables consumable from any language. — _github.com/kosoegawa/HATS_
- **[observation · well-covered]** MARCo (marco.igen.org.br) is a public Brazilian-cohort tool that produces, for each pair of HLA alleles queried, the empirical Spearman correlation, R², regression coefficients, manufacturer-stratified sample counts, discordance rates, and HATS+HLA-EMMA annotations — across 1,000+ sera, with filters by transfusion / transplant / pregnancy history. — _—_
- **[observation · sparse]** The MARCo manufacturer dropdown supports Immucor/Werfen and One Lambda/Thermo Fisher (with the OL ExPlex extended panel as a sub-category); per-pair counts on each platform vary, with some pairs covered on only one platform — the exact distribution would require systematic extraction across all DR/DQ pairs. — _—_
- **[published-evidence · well-covered]** DQ-DSA dominates Class II-DSA in modern dnDSA cohorts; eplet-based DQ matching has improved donor-recipient pair selection but remains rule-based and platform-naive. — _Wiebe & Nickerson 2018, Curr Opin Organ Transplant 23:399_
- **[established-guideline · well-covered]** Calibration (intercept, slope) is a required deliverable for any prognostic / classification tool the transplant community would adopt; pure discrimination metrics are insufficient. — _STAR 2018 + TRIPOD 2015 reporting_

### Knowledge gaps flagged for researcher
- (unpublished-or-pilot-data) Does the lab have access to a paired-platform institutional cohort (Immucor + One Lambda LSA on the same sera) for an external validation arm beyond MARCo? This is the difference between a benchmark model and a clinically deployable tool.
- (non-english-literature) Brazilian transplant cohort literature, especially from MARCo's contributing institutions, may carry context on cohort sensitization-route distribution and population-genetic structure that I would underweight from English-only references.
- (patent-or-clinical-practice) Whether MARCo exposes a bulk-download / API endpoint for systematic per-pair extraction across all DR/DQ pairs (~10,000+ pairs) is unclear from the public-facing UI; respectful scraping vs institutional contact may both be required.

### Novel syntheses proposed
- Combining MARCo's population-MFI ground truth with HATS key-residue features and HLA-EMMA SA-position features in a single supervised regression task, with platform-id auxiliary features for cross-platform calibration, is the conceptual leap. — _treating MARCo's per-allele-pair empirical Spearman ρ as a regression target — with HATS key-residue + HLA-EMMA SA-position features and chain-aware encoding for DQ/DP heterodimers — has not, to my knowledge, been published; the existing tools are rule-based and platform-specific_

## engineer_r1 — ml_engineer

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

### Evidence collected
- **[engineering-precedent · well-covered]** The IPD-IMGT/HLA Database is mirrored on GitHub at ANHIG/IMGTHLA, providing FASTA + version-controlled allele protein sequences for all HLA loci. — _github.com/ANHIG/IMGTHLA_
- **[published-evidence · well-covered]** The IPD-IMGT/HLA Database is the canonical reference for HLA nomenclature and sequence; the most recently published comprehensive description appeared in Nucleic Acids Research. — _Robinson et al 2020, Nucleic Acids Res 48:D948 — IPD-IMGT/HLA Database_
- **[engineering-precedent · well-covered]** Biopython provides robust FASTA parsing and per-allele sequence indexing. — _github.com/biopython/biopython_
- **[engineering-precedent · well-covered]** XGBoost is the canonical gradient-boosted regressor for tabular feature-engineering tasks at this scale; native feature-importance interpretation supports the post-hoc analysis. — _github.com/dmlc/xgboost_
- **[engineering-precedent · well-covered]** scikit-learn provides RandomForestRegressor, GroupKFold, and the suite of evaluation metrics needed for cross-validated regression with leakage protection. — _github.com/scikit-learn/scikit-learn_
- **[observation · sparse]** I would hedge on whether XGBoost outperforms LightGBM or a small neural net at this data scale; the choice depends on the realized N (number of allele pairs) which I do not know without MARCo extraction. — _—_
- **[observation · well-covered]** Trivial — single CPU, ~1 hour training. The bottleneck is data acquisition: MARCo extraction + IPD-IMGT/HLA download + HATS Perl run + HLA-EMMA processing — all together likely 1-2 weeks of analyst time depending on whether MARCo exposes a bulk-download endpoint. — _—_
- **[published-evidence · well-covered]** Eplet / key-residue definitions are version-dependent; retrospective reanalysis with newer HLAMatchmaker versions has produced different results — same caution applies to HATS revisions. — _Tambur et al 2018, Am J Transplant 18:1604_
- **[observation · well-covered]** Cross-locus pairs (DR vs DQ, DQ vs DP) shouldn't show structural antibody cross-reactivity — antibodies are locus-specific by physical-recognition argument — but the dataset has them by combinatorial enumeration. Explicit within-locus filter required. — _—_
- **[observation · sparse]** Imbalanced sample sizes per allele pair (some N>1000, some N<50) mean the empirical Spearman ρ uncertainty differs across pairs. Sample-size-weighted MSE loss handles this; without weighting, the model fits the noise of small-N pairs. — _—_

### Knowledge gaps flagged for researcher
- (niche-subfield) Are there published learned (non-rule-based) cross-reactivity prediction models for HLA Class II using empirical MFI as a target? I can recall HLAMatchmaker / PIRCHE-II / HLA-EMMA as rule-based tools and Tambur's STAR working-group platform-comparison work, but not an empirical-MFI-target learned regressor.

### Novel syntheses proposed
- Chain-aware encoding for DQ and DP heterodimers — concatenating features from both α-chain and β-chain pairs into a single feature vector — is an architectural choice that should be ablated; the literature usually reduces to β-chain mismatches alone. — _explicit α+β-chain concatenated featurization for DQ/DP heterodimers (vs single-chain features) is rarely framed in the LSA-virtual-crossmatch literature, which tends to focus on β-chain alone for DR matching_

## domain_r2 — domain_scientist

The ML framing is reasonable. Two adjustments before this is clinically defensible.

**1. Platform discrepancy is the primary deliverable, not an auxiliary concern.**

[CLAIM type=published-evidence coverage=well-covered source="Tambur et al 2018, Am J Transplant 18:1604 — STAR"]Platform discrepancy between Immucor and One Lambda LSA assays is a documented, ongoing clinical headache: same patient sera, same allele pair, can yield disagreeing positivity calls at common MFI thresholds. This is *the* reason a single-platform model is clinically less actionable than a platform-agnostic one.[/CLAIM]

The right framing: train on the union of Immucor + OL data with platform-id as a feature, then evaluate stratified by platform AND specifically on the platform-discrepant allele-pair subset (pairs where the two manufacturers' Spearman ρ differ by some pre-specified margin). The deliverable is "platform-agnostic predicted ρ that recovers the consensus when the platforms agree, and produces calibrated uncertainty when they don't."

[NOVEL_SYNTHESIS rationale="explicit platform-discrepant subset analysis as a primary deliverable for a learned LSA model is, to my knowledge, not standard practice in the published HLA-prediction literature"]The discrepant-subset evaluation — does the model's predicted ρ correlate with the cross-platform consensus on disagreement pairs — is the clinically actionable falsifiability that distinguishes this work from a benchmark exercise.[/NOVEL_SYNTHESIS]

**2. Per-locus stratified evaluation, with DQ heterodimer prioritized.**

[CLAIM type=published-evidence coverage=well-covered source="Wiebe & Nickerson 2018, Curr Opin Organ Transplant 23:399"]DQ-DSA is the dominant Class II-DSA in modern dnDSA cohorts; DR-DSA matters but DQ matters more for kidney outcomes — and DQ is heterodimeric, which is exactly where chain-aware encoding earns its keep.[/CLAIM]

Reporting median lift across {DRB1, DRB3/4/5, DQA1+DQB1 heterodimer, DPA1+DPB1 heterodimer} with the stricter requirement that DQ-heterodimer alone shows measurable lift (≥ 0.05 over best baseline) is the clinically defensible falsifiability framing. DRB1 likely has the largest pair count; DQ heterodimer is the clinically dominant target.

**3. Stronger baselines.**

[CLAIM type=observation coverage=well-covered source=""]The proposed baselines (naive Hamming, HATS-shares, HLA-EMMA SA-count) are weak. The clinical reference for virtual crossmatch is HLAMatchmaker eplet-mismatch count and PIRCHE-II indirect-recognition score. Beating naive Hamming and binary HATS-shares is a low bar.[/CLAIM]

[KNOWLEDGE_GAP category=patent-or-clinical-practice]HLAMatchmaker eplet count and PIRCHE-II indirect-recognition score should be added as required baselines. Both have publicly-callable web interfaces but bulk programmatic access varies; this is a 1-2 week pipeline-engineering investment.[/KNOWLEDGE_GAP]

**4. The falsifiable prediction.**

The hypothesis commits to: a learned XGBoost model trained on MARCo Class II (DR/DQ-focused, DPA1+DPB1 secondary) with platform-id and chain-aware features, achieves on a held-out 20% allele-pair test set:
- Pooled Spearman ρ (predicted vs observed MFI ρ) ≥ 0.85
- ≥ 0.07 absolute lift over best of the rule-based baselines (HATS-shares, HLA-EMMA-SA, naive Hamming, HLAMatchmaker eplet-count, PIRCHE-II indirect-recognition)
- Per-locus lift ≥ 0.05 in ≥ 4/5 stratification groups
- Platform-discrepant-pair subset Spearman ρ vs consensus ≥ 0.7

Null outcome: pooled lift < 0.03 OR DQ-heterodimer lift < 0.05 OR platform-discrepant correlation < 0.5 falsifies the hypothesis.

[KNOWLEDGE_GAP category=unpublished-or-pilot-data]Does the lab have access to a paired-platform institutional cohort beyond MARCo for external validation? Without it, the model is a benchmark; with it, the model becomes a clinically deployable tool.[/KNOWLEDGE_GAP]

### Evidence collected
- **[published-evidence · well-covered]** Platform discrepancy between Immucor and One Lambda LSA assays is a documented, ongoing clinical headache: same patient sera, same allele pair, can yield disagreeing positivity calls at common MFI thresholds. This is *the* reason a single-platform model is clinically less actionable than a platform-agnostic one. — _Tambur et al 2018, Am J Transplant 18:1604 — STAR_
- **[published-evidence · well-covered]** DQ-DSA is the dominant Class II-DSA in modern dnDSA cohorts; DR-DSA matters but DQ matters more for kidney outcomes — and DQ is heterodimeric, which is exactly where chain-aware encoding earns its keep. — _Wiebe & Nickerson 2018, Curr Opin Organ Transplant 23:399_
- **[observation · well-covered]** The proposed baselines (naive Hamming, HATS-shares, HLA-EMMA SA-count) are weak. The clinical reference for virtual crossmatch is HLAMatchmaker eplet-mismatch count and PIRCHE-II indirect-recognition score. Beating naive Hamming and binary HATS-shares is a low bar. — _—_

### Knowledge gaps flagged for researcher
- (patent-or-clinical-practice) HLAMatchmaker eplet count and PIRCHE-II indirect-recognition score should be added as required baselines. Both have publicly-callable web interfaces but bulk programmatic access varies; this is a 1-2 week pipeline-engineering investment.
- (unpublished-or-pilot-data) Does the lab have access to a paired-platform institutional cohort beyond MARCo for external validation? Without it, the model is a benchmark; with it, the model becomes a clinically deployable tool.

### Novel syntheses proposed
- The discrepant-subset evaluation — does the model's predicted ρ correlate with the cross-platform consensus on disagreement pairs — is the clinically actionable falsifiability that distinguishes this work from a benchmark exercise. — _explicit platform-discrepant subset analysis as a primary deliverable for a learned LSA model is, to my knowledge, not standard practice in the published HLA-prediction literature_

## engineer_r2 — ml_engineer

Adopting the domain refinements. Two pivots that materially change the design: platform-agnostic predicted ρ as a primary deliverable (with explicit discrepant-subset evaluation), and per-locus evaluation with DQ-heterodimer prioritization. Adding HLAMatchmaker eplet count and PIRCHE-II indirect-recognition score as required baselines.

**Architecture.**

Input: per-allele-pair feature vector — ~25 features for single-chain pairs (DRB1, DRB3/4/5), ~50 features for heterodimer pairs (DQA1+DQB1, DPA1+DPB1):
- HATS shares-serotype binary
- HATS key-residue Hamming distance
- HLA-EMMA SA-mismatch count
- HLA-EMMA total mismatch count
- Per-position binary indicators at the locus's top-10 most variable positions
- HLAMatchmaker eplet-mismatch count
- PIRCHE-II indirect-recognition score
- Locus 5-way one-hot
- Platform 2-way one-hot
- log(n_samples_pooled), log(n_immucor), log(n_ol)
- Mean MFI on each platform (for the positive-pair subset)

For DQ/DP heterodimers: concatenate α-chain pair features and β-chain pair features (handles the heterodimer correctly).

Output: predicted Spearman ρ ∈ [-1, 1].

**Loss.**

Sample-size-weighted MSE on the predicted vs observed Spearman ρ:

```
L = (1/Σw_i) · Σ w_i · (predicted_ρ_i - observed_ρ_i)²
```

where w_i = log(n_samples_i + 1) so high-N pairs carry more weight without dominating.

Optional: predict log(uncertainty) and use Gaussian negative log-likelihood for calibrated prediction intervals — the discrepant-subset evaluation depends on uncertainty being well-calibrated.

**Training plan.**

1. MARCo extraction: full DR/DQ matrix via API (if available) or respectful scraping; output is per-pair {a1, a2, locus, n_pooled, n_immucor, n_ol, ρ_pooled, ρ_immucor, ρ_ol, R², discordance counts, HATS shares-serotype, HLA-EMMA SA-mismatch count}.
2. IPD-IMGT/HLA: download protein FASTA, parse with Biopython, build per-allele indexed sequences.
3. HATS: run Perl on the FASTA, parse outputs to per-allele key-residue feature vectors; compute per-pair HATS key-residue Hamming.
4. HLA-EMMA: run distance tables on each MARCo allele pair to extract SA + total mismatch counts.
5. HLAMatchmaker + PIRCHE-II: bulk eplet-count + indirect-recognition score per pair (1-2 weeks of pipeline integration).
6. Stratified split by allele identity (5-fold GroupKFold + a stricter "hold out one allele entirely" eval that catches the residual leakage).
7. Train XGBoost with sample-size-weighted MSE; tune via CV.
8. Per-locus + platform-stratified + platform-discrepant-subset evaluation.
9. External validation: institutional paired-platform cohort if available.

**Expected outcomes.**

[CLAIM type=observation coverage=sparse source=""]Realistic Spearman ρ ceiling for the proposed model on held-out pairs is plausibly 0.85-0.92; HLA-EMMA-SA baseline is plausibly 0.75-0.82 (a strong baseline by Class II's antibody-recognition biology); HLAMatchmaker eplet-count plausibly 0.78-0.85; the +0.07 lift over the strongest baseline is defensible but not data-anchored without pilot extraction.[/CLAIM]

[KNOWLEDGE_GAP category=unpublished-or-pilot-data]The exact MARCo data extraction mechanism (web scraping, API, downloadable matrix) needs to be confirmed against the live site; the methods plan above assumes one of these is feasible, which is not yet validated.[/KNOWLEDGE_GAP]

**Compute & timeline.**

[CLAIM type=observation coverage=well-covered source=""]Single CPU, ~1 hour training. Most time is data acquisition + HLAMatchmaker/PIRCHE-II pipeline integration: 2-3 weeks total. External-validation arm adds 1-2 months for institutional cohort assembly.[/CLAIM]

### Evidence collected
- **[observation · sparse]** Realistic Spearman ρ ceiling for the proposed model on held-out pairs is plausibly 0.85-0.92; HLA-EMMA-SA baseline is plausibly 0.75-0.82 (a strong baseline by Class II's antibody-recognition biology); HLAMatchmaker eplet-count plausibly 0.78-0.85; the +0.07 lift over the strongest baseline is defensible but not data-anchored without pilot extraction. — _—_
- **[observation · well-covered]** Single CPU, ~1 hour training. Most time is data acquisition + HLAMatchmaker/PIRCHE-II pipeline integration: 2-3 weeks total. External-validation arm adds 1-2 months for institutional cohort assembly. — _—_

### Knowledge gaps flagged for researcher
- (unpublished-or-pilot-data) The exact MARCo data extraction mechanism (web scraping, API, downloadable matrix) needs to be confirmed against the live site; the methods plan above assumes one of these is feasible, which is not yet validated.
