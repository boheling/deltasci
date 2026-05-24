# Multi-locus Class II HLA antibody cross-reactivity prediction with platform-agnostic calibration: MARCo + HATS + HLA-EMMA

> Audit summary: ✓ 5 verified

A gradient-boosted regression model trained on MARCo empirical anti-HLA Class II (DR / DQ heterodimer / DP heterodimer) cross-reactivity data, with HATS key-residue + HLA-EMMA solvent-accessible mismatch features, chain-aware DQ/DP heterodimer encoding, and platform-id auxiliary features, will predict held-out allele-pair MFI Spearman correlations with pooled ρ ≥ 0.85, exceeding the strongest rule-based baseline (HLAMatchmaker eplet count or HLA-EMMA SA-mismatch) by ≥ 0.07. The model also produces a platform-agnostic predicted ρ that recovers cross-platform consensus on Immucor/OL-discrepant allele pairs with Spearman ρ vs consensus ≥ 0.7.

## Domain grounding
- **mechanism**: Anti-HLA Class II antibodies recognize residue-level epitopes; HATS key-residue rules capture serotype-level groupings; HLA-EMMA flags solvent-accessible (eplet-relevant) positions. MARCo provides empirical population-MFI cross-reactivity at allele-pair resolution across 1000+ sera. Combining residue-level features with empirical cross-reactivity ground truth gives a calibration-friendly surrogate for virtual crossmatch that the rule-based tradition does not produce.
- **unmet_need**: Platform-agnostic, per-locus, residue-resolution learned virtual crossmatch for Class II HLA antibodies, with explicit handling of Immucor/OL platform discrepancy. Existing tools (HLAMatchmaker, PIRCHE-II, HLA-EMMA) are rule-based; HATS gives serotype but not cross-reactivity. No public learned model exists with empirical MFI as the supervised target.
- **expected_impact**: Better-calibrated virtual crossmatch decisions, especially for DQ-heterodimer pairs; reduced inter-platform interpretation disagreement; baseline benchmark on the public MARCo cohort for the broader transplant immunogenetics community.

## Technical approach
- **core_method**: XGBoost regressor with HATS key-residue mismatch + HLA-EMMA SA-mismatch + per-position indicator + HLAMatchmaker eplet count + PIRCHE-II indirect-recognition + locus + platform + log(sample_count) features, predicting MFI Spearman ρ with sample-size-weighted MSE loss. Chain-aware concatenated features for DQ/DP heterodimers. 5-fold GroupKFold by allele identity, plus held-one-allele-entirely-out evaluation for stricter leakage control.
- **key_innovation**: (a) MARCo empirical MFI ρ as the regression target — first public Class II ML benchmark of this kind; (b) chain-aware DQ/DP heterodimer encoding; (c) explicit platform-discrepant-subset evaluation as a primary clinical-actionability deliverable.
- **implementation_path**: MARCo extraction (API / scraping) → IPD-IMGT/HLA FASTA → HATS Perl → HLA-EMMA mismatch profiling → HLAMatchmaker + PIRCHE-II bulk pipeline → allele-pair feature assembly → XGBoost with sample-size-weighted MSE → 5-fold GroupKFold + held-one-allele-out → per-locus + platform-stratified + platform-discrepant-subset evaluation → external validation on institutional paired-platform cohort.

## Falsifiability
- **prediction**: On held-out 20% allele-pair test set, the XGBoost model achieves higher Spearman correlation between predicted and observed MFI ρ than each of the rule-based baselines (naive Hamming, HATS-shares, HLA-EMMA-SA, HLAMatchmaker eplet count, PIRCHE-II), AND maintains comparable lift on the platform-discrepant subset.
- **threshold**: Pooled Spearman ρ ≥ 0.85 AND ≥ 0.07 absolute lift over the best of {naive Hamming, HATS-shares, HLA-EMMA-SA, HLAMatchmaker eplet count, PIRCHE-II indirect-recognition}, AND per-locus lift ≥ 0.05 in ≥ 4/5 stratification groups, AND platform-discrepant-pair subset Spearman ρ vs cross-platform consensus ≥ 0.7.
- **null outcome**: Pooled lift < 0.03 OR DQ-heterodimer lift < 0.05 OR platform-discrepant-pair correlation vs consensus < 0.5 falsifies the hypothesis: rule-based baselines suffice, OR heterodimer encoding does not add value, OR the model cannot recover cross-platform consensus.

## Feasibility scores
- **data_availability**: 4/5 — MARCo public via web; IPD-IMGT/HLA public; HATS public; HLA-EMMA public. Friction: HLAMatchmaker / PIRCHE-II bulk programmatic access and the institutional paired-platform external-validation cohort.
- **technical_feasibility**: 5/5 — Tabular feature engineering + XGBoost is well-trodden. Single-CPU training in ~1 hour. The pipeline-engineering portion (HATS Perl + HLAMatchmaker + PIRCHE-II batch) is the dominant time cost, not modeling.
- **clinical_relevance**: 4/5 — DQ-DSA dominates AMR; platform-agnostic prediction resolves a known clinical headache; transplant labs would adopt a tool that consistently bridged the Immucor / OL interpretation gap.
- **novelty**: 3/5 — Methodology is incremental over rule-based eplet matching (the 3-rating). Distinctive contributions: empirical-MFI target on the public MARCo cohort + explicit platform-discrepant-subset deliverable.
- **ethical_clearability**: 5/5 — No new human-subjects research; uses public LSA cross-reactivity data (MARCo) and public reference databases (IPD-IMGT/HLA, HATS, HLA-EMMA). External-validation cohort would require institutional IRB but is a separate work package.
- **overall (weighted)**: 4.21

## Evidence trail

### AI-confident foundations (well-covered)
| # | Type | Claim | Source |
|---|------|-------|--------|
| 1 | published-evidence | De novo donor-specific anti-HLA Class II antibodies (with anti-DQ predominating) drive the majority of antibody-mediated rejection events in modern kidney transplantation and are mechanistically linked to graft loss. | Wiebe et al 2017, Am J Transplant 17:3050 |
| 2 | published-evidence | The Sensitization in Transplantation: Assessment of Risk (STAR) working group documented that LSA-based virtual crossmatch interpretation is non-trivially platform-dependent: Immucor and One Lambda assays disagree on certain MFI thresholds and on bead-specific reactivities. This is the central practical motivation for a platform-agnostic predictor. | Tambur et al 2018, Am J Transplant 18:1604 — STAR consensus |
| 3 | published-evidence | HLA-EMMA produces a per-position amino-acid mismatch profile between any two HLA alleles, with solvent-accessible (SA) positions explicitly flagged — these positions are the primary candidates for antibody-recognized epitopes. | Kramer et al 2020, HLA 96:43 — HLA-EMMA |
| 4 | published-evidence | The HATS classifier assigns HLA alleles to broad serological types using a systematic key-residue-position rule that covers Class I (A/B/C) and Class II (DRB1/3/4/5, DQA1, DQB1, DPA1). | Osoegawa et al 2024, HLA 104:e15702 — HATS |
| 5 | engineering-precedent | A reference Perl implementation of HATS is publicly available; it consumes IPD-IMGT/HLA protein FASTA and emits per-allele key-residue tables consumable from any language. | github.com/kosoegawa/HATS |
| 6 | observation | MARCo (marco.igen.org.br) is a public Brazilian-cohort tool that produces, for each pair of HLA alleles queried, the empirical Spearman correlation, R², regression coefficients, manufacturer-stratified sample counts, discordance rates, and HATS+HLA-EMMA annotations — across 1,000+ sera, with filters by transfusion / transplant / pregnancy history. | — |
| 7 | published-evidence | DQ-DSA dominates Class II-DSA in modern dnDSA cohorts; eplet-based DQ matching has improved donor-recipient pair selection but remains rule-based and platform-naive. | Wiebe & Nickerson 2018, Curr Opin Organ Transplant 23:399 |
| 8 | established-guideline | Calibration (intercept, slope) is a required deliverable for any prognostic / classification tool the transplant community would adopt; pure discrimination metrics are insufficient. | STAR 2018 + TRIPOD 2015 reporting |
| 9 | engineering-precedent | The IPD-IMGT/HLA Database is mirrored on GitHub at ANHIG/IMGTHLA, providing FASTA + version-controlled allele protein sequences for all HLA loci. | github.com/ANHIG/IMGTHLA |
| 10 | published-evidence | The IPD-IMGT/HLA Database is the canonical reference for HLA nomenclature and sequence; the most recently published comprehensive description appeared in Nucleic Acids Research. | Robinson et al 2020, Nucleic Acids Res 48:D948 — IPD-IMGT/HLA Database |
| 11 | engineering-precedent | Biopython provides robust FASTA parsing and per-allele sequence indexing. | github.com/biopython/biopython |
| 12 | engineering-precedent | XGBoost is the canonical gradient-boosted regressor for tabular feature-engineering tasks at this scale; native feature-importance interpretation supports the post-hoc analysis. | github.com/dmlc/xgboost |
| 13 | engineering-precedent | scikit-learn provides RandomForestRegressor, GroupKFold, and the suite of evaluation metrics needed for cross-validated regression with leakage protection. | github.com/scikit-learn/scikit-learn |
| 14 | observation | Trivial — single CPU, ~1 hour training. The bottleneck is data acquisition: MARCo extraction + IPD-IMGT/HLA download + HATS Perl run + HLA-EMMA processing — all together likely 1-2 weeks of analyst time depending on whether MARCo exposes a bulk-download endpoint. | — |
| 15 | published-evidence | Eplet / key-residue definitions are version-dependent; retrospective reanalysis with newer HLAMatchmaker versions has produced different results — same caution applies to HATS revisions. | Tambur et al 2018, Am J Transplant 18:1604 |
| 16 | observation | Cross-locus pairs (DR vs DQ, DQ vs DP) shouldn't show structural antibody cross-reactivity — antibodies are locus-specific by physical-recognition argument — but the dataset has them by combinatorial enumeration. Explicit within-locus filter required. | — |
| 17 | published-evidence | Platform discrepancy between Immucor and One Lambda LSA assays is a documented, ongoing clinical headache: same patient sera, same allele pair, can yield disagreeing positivity calls at common MFI thresholds. This is *the* reason a single-platform model is clinically less actionable than a platform-agnostic one. | Tambur et al 2018, Am J Transplant 18:1604 — STAR |
| 18 | published-evidence | DQ-DSA is the dominant Class II-DSA in modern dnDSA cohorts; DR-DSA matters but DQ matters more for kidney outcomes — and DQ is heterodimeric, which is exactly where chain-aware encoding earns its keep. | Wiebe & Nickerson 2018, Curr Opin Organ Transplant 23:399 |
| 19 | observation | The proposed baselines (naive Hamming, HATS-shares, HLA-EMMA SA-count) are weak. The clinical reference for virtual crossmatch is HLAMatchmaker eplet-mismatch count and PIRCHE-II indirect-recognition score. Beating naive Hamming and binary HATS-shares is a low bar. | — |
| 20 | observation | Single CPU, ~1 hour training. Most time is data acquisition + HLAMatchmaker/PIRCHE-II pipeline integration: 2-3 weeks total. External-validation arm adds 1-2 months for institutional cohort assembly. | — |

### Likely-reliable, please verify (sparse coverage)
| # | Type | Claim | Source |
|---|------|-------|--------|
| 1 | observation | The MARCo manufacturer dropdown supports Immucor/Werfen and One Lambda/Thermo Fisher (with the OL ExPlex extended panel as a sub-category); per-pair counts on each platform vary, with some pairs covered on only one platform — the exact distribution would require systematic extraction across all DR/DQ pairs. | — |
| 2 | observation | I would hedge on whether XGBoost outperforms LightGBM or a small neural net at this data scale; the choice depends on the realized N (number of allele pairs) which I do not know without MARCo extraction. | — |
| 3 | observation | Imbalanced sample sizes per allele pair (some N>1000, some N<50) mean the empirical Spearman ρ uncertainty differs across pairs. Sample-size-weighted MSE loss handles this; without weighting, the model fits the noise of small-N pairs. | — |
| 4 | observation | Realistic Spearman ρ ceiling for the proposed model on held-out pairs is plausibly 0.85-0.92; HLA-EMMA-SA baseline is plausibly 0.75-0.82 (a strong baseline by Class II's antibody-recognition biology); HLAMatchmaker eplet-count plausibly 0.78-0.85; the +0.07 lift over the strongest baseline is defensible but not data-anchored without pilot extraction. | — |

### Researcher knowledge required

**Knowledge gaps the AI flagged for researcher input:**

1. _(unpublished-or-pilot-data)_ Does the lab have access to a paired-platform institutional cohort (Immucor + One Lambda LSA on the same sera) for an external validation arm beyond MARCo? This is the difference between a benchmark model and a clinically deployable tool.
2. _(non-english-literature)_ Brazilian transplant cohort literature, especially from MARCo's contributing institutions, may carry context on cohort sensitization-route distribution and population-genetic structure that I would underweight from English-only references.
3. _(patent-or-clinical-practice)_ Whether MARCo exposes a bulk-download / API endpoint for systematic per-pair extraction across all DR/DQ pairs (~10,000+ pairs) is unclear from the public-facing UI; respectful scraping vs institutional contact may both be required.
4. _(niche-subfield)_ Are there published learned (non-rule-based) cross-reactivity prediction models for HLA Class II using empirical MFI as a target? I can recall HLAMatchmaker / PIRCHE-II / HLA-EMMA as rule-based tools and Tambur's STAR working-group platform-comparison work, but not an empirical-MFI-target learned regressor.
5. _(patent-or-clinical-practice)_ HLAMatchmaker eplet count and PIRCHE-II indirect-recognition score should be added as required baselines. Both have publicly-callable web interfaces but bulk programmatic access varies; this is a 1-2 week pipeline-engineering investment.
6. _(unpublished-or-pilot-data)_ Does the lab have access to a paired-platform institutional cohort beyond MARCo for external validation? Without it, the model is a benchmark; with it, the model becomes a clinically deployable tool.
7. _(unpublished-or-pilot-data)_ The exact MARCo data extraction mechanism (web scraping, API, downloadable matrix) needs to be confirmed against the live site; the methods plan above assumes one of these is feasible, which is not yet validated.

**Novel syntheses the AI is proposing (not stated by any single source):**

1. Combining MARCo's population-MFI ground truth with HATS key-residue features and HLA-EMMA SA-position features in a single supervised regression task, with platform-id auxiliary features for cross-platform calibration, is the conceptual leap. — _treating MARCo's per-allele-pair empirical Spearman ρ as a regression target — with HATS key-residue + HLA-EMMA SA-position features and chain-aware encoding for DQ/DP heterodimers — has not, to my knowledge, been published; the existing tools are rule-based and platform-specific_
2. Chain-aware encoding for DQ and DP heterodimers — concatenating features from both α-chain and β-chain pairs into a single feature vector — is an architectural choice that should be ablated; the literature usually reduces to β-chain mismatches alone. — _explicit α+β-chain concatenated featurization for DQ/DP heterodimers (vs single-chain features) is rarely framed in the LSA-virtual-crossmatch literature, which tends to focus on β-chain alone for DR matching_
3. The discrepant-subset evaluation — does the model's predicted ρ correlate with the cross-platform consensus on disagreement pairs — is the clinically actionable falsifiability that distinguishes this work from a benchmark exercise. — _explicit platform-discrepant subset analysis as a primary deliverable for a learned LSA model is, to my knowledge, not standard practice in the published HLA-prediction literature_

## Citation audit

### ✓ Verified (5)
| Auditor | AI claim | Verified record |
|---------|----------|-----------------|
| github | github.com/kosoegawa/HATS | kosoegawa/HATS — https://github.com/kosoegawa/HATS |
| github | github.com/dmlc/xgboost | dmlc/xgboost — https://github.com/dmlc/xgboost |
| github | github.com/ANHIG/IMGTHLA | ANHIG/IMGTHLA — https://github.com/ANHIG/IMGTHLA |
| github | github.com/biopython/biopython | biopython/biopython — https://github.com/biopython/biopython |
| github | github.com/scikit-learn/scikit-learn | scikit-learn/scikit-learn — https://github.com/scikit-learn/scikit-learn |

## Epistemic summary
- well-covered claims: **20**
- sparse-coverage claims: **4**
- knowledge gaps flagged: **7**
- novel syntheses proposed: **3**

_Generated by DeltaScience 0.4.0 :: pack biomed-serology v0.1.0 :: mockllm/mock-llm-v1_