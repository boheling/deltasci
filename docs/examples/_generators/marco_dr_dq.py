"""Generate the MARCo DR/DQ Class II HLA antibody cross-reactivity example run.

Same hand-authored pattern as biomed_run.py / materials_run.py / climate_run.py:
4 rounds + synthesis + protocol + risks + challenger JSON, fed through MockLLM.
Audit pillar runs live against PubMed / Crossref / GitHub / GEO.

Hypothesis target: predict empirical anti-HLA Class II (DR/DQ-focused) antibody
cross-reactivity (MFI Spearman ρ between allele pairs) using HATS key-residue
+ HLA-EMMA SA-mismatch + chain-aware features, with platform-agnostic
calibration across Immucor/Werfen and One Lambda/Thermo Fisher LSA assays.
"""

from __future__ import annotations

import json
from pathlib import Path

from deltasci import CoReasoner, Config, load_pack
from deltasci.cli import _write_outputs_staged
from deltasci.llm.mock import MockLLM


IDEA = (
    "Predict empirical anti-HLA Class II (DR / DQ heterodimer / DPA1+DPB1) antibody "
    "cross-reactivity — operationalized as the MFI Spearman correlation between allele "
    "pairs in the public MARCo dataset (marco.igen.org.br) — using a learned model over "
    "HATS key-residue + HLA-EMMA solvent-accessible mismatch features with chain-aware "
    "encoding for heterodimers. The model must be platform-agnostic across Immucor/Werfen "
    "and One Lambda/Thermo Fisher LSA assays, evaluated specifically on the platform-"
    "discrepant allele-pair subset where the two manufacturers disagree."
)


DOMAIN_R1 = """\
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
"""


ENGINEER_R1 = """\
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
"""


DOMAIN_R2 = """\
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
"""


ENGINEER_R2 = """\
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
"""


SYNTHESIS_JSON = json.dumps({
    "title": "Multi-locus Class II HLA antibody cross-reactivity prediction with platform-agnostic calibration: MARCo + HATS + HLA-EMMA",
    "statement": (
        "A gradient-boosted regression model trained on MARCo empirical anti-HLA Class II "
        "(DR / DQ heterodimer / DP heterodimer) cross-reactivity data, with HATS key-residue + "
        "HLA-EMMA solvent-accessible mismatch features, chain-aware DQ/DP heterodimer encoding, "
        "and platform-id auxiliary features, will predict held-out allele-pair MFI Spearman "
        "correlations with pooled ρ ≥ 0.85, exceeding the strongest rule-based baseline "
        "(HLAMatchmaker eplet count or HLA-EMMA SA-mismatch) by ≥ 0.07. The model also produces "
        "a platform-agnostic predicted ρ that recovers cross-platform consensus on Immucor/OL-"
        "discrepant allele pairs with Spearman ρ vs consensus ≥ 0.7."
    ),
    "domain_grounding": {
        "mechanism": (
            "Anti-HLA Class II antibodies recognize residue-level epitopes; HATS key-residue rules "
            "capture serotype-level groupings; HLA-EMMA flags solvent-accessible (eplet-relevant) "
            "positions. MARCo provides empirical population-MFI cross-reactivity at allele-pair "
            "resolution across 1000+ sera. Combining residue-level features with empirical "
            "cross-reactivity ground truth gives a calibration-friendly surrogate for virtual "
            "crossmatch that the rule-based tradition does not produce."
        ),
        "unmet_need": (
            "Platform-agnostic, per-locus, residue-resolution learned virtual crossmatch for Class II "
            "HLA antibodies, with explicit handling of Immucor/OL platform discrepancy. Existing tools "
            "(HLAMatchmaker, PIRCHE-II, HLA-EMMA) are rule-based; HATS gives serotype but not cross-"
            "reactivity. No public learned model exists with empirical MFI as the supervised target."
        ),
        "expected_impact": (
            "Better-calibrated virtual crossmatch decisions, especially for DQ-heterodimer pairs; "
            "reduced inter-platform interpretation disagreement; baseline benchmark on the public "
            "MARCo cohort for the broader transplant immunogenetics community."
        ),
    },
    "technical_approach": {
        "core_method": (
            "XGBoost regressor with HATS key-residue mismatch + HLA-EMMA SA-mismatch + per-position "
            "indicator + HLAMatchmaker eplet count + PIRCHE-II indirect-recognition + locus + platform "
            "+ log(sample_count) features, predicting MFI Spearman ρ with sample-size-weighted MSE loss. "
            "Chain-aware concatenated features for DQ/DP heterodimers. 5-fold GroupKFold by allele "
            "identity, plus held-one-allele-entirely-out evaluation for stricter leakage control."
        ),
        "key_innovation": (
            "(a) MARCo empirical MFI ρ as the regression target — first public Class II ML benchmark "
            "of this kind; (b) chain-aware DQ/DP heterodimer encoding; (c) explicit platform-discrepant-"
            "subset evaluation as a primary clinical-actionability deliverable."
        ),
        "implementation_path": (
            "MARCo extraction (API / scraping) → IPD-IMGT/HLA FASTA → HATS Perl → HLA-EMMA mismatch "
            "profiling → HLAMatchmaker + PIRCHE-II bulk pipeline → allele-pair feature assembly → "
            "XGBoost with sample-size-weighted MSE → 5-fold GroupKFold + held-one-allele-out → "
            "per-locus + platform-stratified + platform-discrepant-subset evaluation → external "
            "validation on institutional paired-platform cohort."
        ),
    },
    "falsifiability": {
        "prediction": (
            "On held-out 20% allele-pair test set, the XGBoost model achieves higher Spearman "
            "correlation between predicted and observed MFI ρ than each of the rule-based baselines "
            "(naive Hamming, HATS-shares, HLA-EMMA-SA, HLAMatchmaker eplet count, PIRCHE-II), AND "
            "maintains comparable lift on the platform-discrepant subset."
        ),
        "threshold": (
            "Pooled Spearman ρ ≥ 0.85 AND ≥ 0.07 absolute lift over the best of {naive Hamming, "
            "HATS-shares, HLA-EMMA-SA, HLAMatchmaker eplet count, PIRCHE-II indirect-recognition}, "
            "AND per-locus lift ≥ 0.05 in ≥ 4/5 stratification groups, AND platform-discrepant-pair "
            "subset Spearman ρ vs cross-platform consensus ≥ 0.7."
        ),
        "null_outcome": (
            "Pooled lift < 0.03 OR DQ-heterodimer lift < 0.05 OR platform-discrepant-pair correlation "
            "vs consensus < 0.5 falsifies the hypothesis: rule-based baselines suffice, OR heterodimer "
            "encoding does not add value, OR the model cannot recover cross-platform consensus."
        ),
    },
    "feasibility_scores": {
        "data_availability": 4,
        "technical_feasibility": 5,
        "clinical_relevance": 4,
        "novelty": 3,
        "ethical_clearability": 5,
    },
    "feasibility_justifications": {
        "data_availability": "MARCo public via web; IPD-IMGT/HLA public; HATS public; HLA-EMMA public. Friction: HLAMatchmaker / PIRCHE-II bulk programmatic access and the institutional paired-platform external-validation cohort.",
        "technical_feasibility": "Tabular feature engineering + XGBoost is well-trodden. Single-CPU training in ~1 hour. The pipeline-engineering portion (HATS Perl + HLAMatchmaker + PIRCHE-II batch) is the dominant time cost, not modeling.",
        "clinical_relevance": "DQ-DSA dominates AMR; platform-agnostic prediction resolves a known clinical headache; transplant labs would adopt a tool that consistently bridged the Immucor / OL interpretation gap.",
        "novelty": "Methodology is incremental over rule-based eplet matching (the 3-rating). Distinctive contributions: empirical-MFI target on the public MARCo cohort + explicit platform-discrepant-subset deliverable.",
        "ethical_clearability": "No new human-subjects research; uses public LSA cross-reactivity data (MARCo) and public reference databases (IPD-IMGT/HLA, HATS, HLA-EMMA). External-validation cohort would require institutional IRB but is a separate work package."
    }
}, indent=2)


PROTOCOL_JSON = json.dumps({
    "title": "MARCo + HATS + HLA-EMMA Class II HLA cross-reactivity ML pipeline with platform-agnostic calibration",
    "summary": "Multi-stage pipeline: extract MARCo per-pair MFI ρ for Class II → IPD-IMGT/HLA sequence retrieval → HATS featurization → HLA-EMMA mismatch profiling → HLAMatchmaker + PIRCHE-II bulk pipeline → assemble allele-pair features → train XGBoost with sample-size-weighted MSE → evaluate per-locus + platform-stratified + on the platform-discrepant subset.",
    "data_acquisition": {
        "primary_dataset": "MARCo Class II allele-pair MFI ρ data (DRB1, DRB3/4/5, DQA1+DQB1, DPA1+DPB1)",
        "accession_or_url": "https://marco.igen.org.br/",
        "access_constraints": "public web; bulk download mechanism unconfirmed; institutional contact via contato@igen.org.br for downloadable matrix",
        "fallback_datasets": [
            "IPD-IMGT/HLA protein FASTA (https://www.ebi.ac.uk/ipd/imgt/hla/)",
            "HATS Perl reference implementation (github.com/kosoegawa/HATS)",
            "HLA-EMMA mismatch profiling (Kramer 2020)",
            "Institutional paired-platform LSA cohort for external validation"
        ]
    },
    "steps": [
        {"order": 1, "name": "MARCo data extraction",
         "description": "Extract per-allele-pair Spearman ρ, R², regression coefficients, manufacturer-stratified sample counts, discordance counts, HATS+HLA-EMMA annotations from MARCo for Class II loci (DRB1, DRB3/4/5, DQA1+DQB1, DPA1+DPB1).",
         "inputs": ["MARCo URL"], "outputs": ["pair-level CSV: a1, a2, locus, n_pooled, n_immucor, n_ol, rho_pooled, rho_immucor, rho_ol, r2, hats_shares, hla_emma_sa_count"],
         "method_citations": ["https://marco.igen.org.br/"]},
        {"order": 2, "name": "IPD-IMGT/HLA sequence retrieval",
         "description": "Download protein FASTA for Class II loci; parse via Biopython; build per-allele indexed sequences for HATS / HLA-EMMA / HLAMatchmaker / PIRCHE-II downstream pipelines.",
         "inputs": ["IPD-IMGT/HLA FASTA"],
         "outputs": ["per-allele protein-sequence index"],
         "method_citations": ["https://www.ebi.ac.uk/ipd/imgt/hla/", "github.com/biopython/biopython"]},
        {"order": 3, "name": "HATS featurization",
         "description": "Run HATS Perl on IPD-IMGT/HLA FASTA; parse per-allele key-residue tables; compute per-MARCo-pair shares-serotype binary AND key-residue Hamming distance per locus.",
         "inputs": ["IPD-IMGT/HLA FASTA", "HATS Perl"],
         "outputs": ["per-pair HATS feature vectors"],
         "method_citations": ["github.com/kosoegawa/HATS", "Osoegawa et al 2024, HLA 104:e15702"]},
        {"order": 4, "name": "HLA-EMMA mismatch profiling",
         "description": "Run HLA-EMMA on each MARCo allele pair to produce per-position mismatch profile with SA flagging; aggregate to SA-mismatch count + total-mismatch count features.",
         "inputs": ["per-allele sequences", "HLA-EMMA distance tables"],
         "outputs": ["per-pair SA + total mismatch counts"],
         "method_citations": ["Kramer et al 2020, HLA 96:43"]},
        {"order": 5, "name": "HLAMatchmaker + PIRCHE-II bulk pipeline",
         "description": "Add HLAMatchmaker eplet-mismatch count and PIRCHE-II indirect-recognition score per MARCo pair as required strong baselines; this is the 1-2 week pipeline-engineering investment.",
         "inputs": ["per-allele sequences"],
         "outputs": ["per-pair HLAMatchmaker + PIRCHE-II features"],
         "method_citations": ["Duquesnoy 2002, Hum Immunol 63:339", "Geneugelijk & Spierings 2020 PIRCHE-II review"]},
        {"order": 6, "name": "Feature assembly + train/test split",
         "description": "Concatenate HATS + HLA-EMMA + HLAMatchmaker + PIRCHE-II + locus + platform features into the per-pair feature matrix; assemble sample-size weights; produce 5-fold GroupKFold splits by allele identity plus a hold-one-allele-entirely-out evaluation. (This step was added v0.5 after the case study found that omitting it left the train step with NameError on undefined X/y.)",
         "inputs": ["all per-pair feature columns from steps 3-5"],
         "outputs": ["X, y, sample_weight, fold_indices, FEATURE_COLS"],
         "method_citations": ["github.com/scikit-learn/scikit-learn"]},
        {"order": 7, "name": "Train XGBoost regressor",
         "description": "XGBoost with sample-size-weighted MSE loss (w_i = log(n_samples_i + 1)); cross-validated training on the 5-fold GroupKFold splits from step 6; final production model on all data for feature-importance interpretation.",
         "inputs": ["X, y, sample_weight, fold_indices from step 6"],
         "outputs": ["trained XGBoost model + cross-validated metrics"],
         "method_citations": ["github.com/dmlc/xgboost"]},
        {"order": 8, "name": "Evaluate per-locus + platform-stratified + platform-discrepant",
         "description": "Held-out test (20% pairs by stratified split): pooled Spearman ρ; per-locus Spearman ρ for {DRB1, DRB3/4/5, DQ heterodimer, DP heterodimer}; platform-stratified eval (Immucor-only, OL-only, pooled); platform-discrepant-subset analysis (pairs where |ρ_immucor - ρ_ol| > 0.15) — does the model recover the consensus?",
         "inputs": ["model predictions on held-out test"],
         "outputs": ["per-locus Spearman ρ, platform-stratified ρ, discrepant-pair correlation vs consensus"],
         "method_citations": ["TRIPOD 2015 reporting"]}
    ],
    "primary_metric": "Spearman correlation between predicted and observed MFI cross-reactivity (Spearman ρ) at held-out allele pairs, pooled and per-locus",
    "success_threshold": "Pooled Spearman ρ ≥ 0.85 AND ≥ 0.07 absolute lift over best of {naive Hamming, HATS-shares, HLA-EMMA-SA, HLAMatchmaker eplet count, PIRCHE-II indirect-recognition} AND per-locus lift ≥ 0.05 in ≥ 4/5 stratification groups AND platform-discrepant-pair Spearman ρ vs consensus ≥ 0.7",
    "null_outcome": "Pooled lift < 0.03 OR DQ-heterodimer lift < 0.05 OR platform-discrepant-pair correlation < 0.5 falsifies",
    "baselines": [
        "naive AA Hamming distance (regression)",
        "HATS shares-serotype binary (regression)",
        "HLA-EMMA SA-mismatch count (regression)",
        "HLAMatchmaker eplet-mismatch count (regression)",
        "PIRCHE-II indirect-recognition score (regression)",
        "Single-platform-trained XGBoost evaluated on the other platform (cross-platform generalization baseline)"
    ],
    "compute": {
        "hardware": "Single CPU (no GPU needed)",
        "estimated_runtime": "~1h training + ~1-2 weeks data + pipeline acquisition",
        "storage": "~2GB IPD-IMGT/HLA FASTA + extracted MARCo data + intermediate feature tables",
        "cost_estimate": "$0 (all data sources public; HLAMatchmaker / PIRCHE-II web tools free for academic use)"
    },
    "timeline_estimate": "3-4 weeks total: 2 weeks data + pipeline (MARCo extraction, HLAMatchmaker / PIRCHE-II bulk integration); 1 week modeling + cross-validation + per-locus stratified eval; 1 week external-validation arm if institutional paired-platform cohort is available.",
    "sample_size_justification": "MARCo has 1000+ sera; thousands of within-locus DR/DQ allele pairs (DRB1 alone likely 5000-10000 pairs given allele-frequency-weighted enumeration; DQ heterodimer likely 1000-3000 pairs). Sufficient for tabular regression with ~50 features. Per-locus stratified analysis: DRB1 well-powered; DRB3/4/5 + DP exploratory; DQ heterodimer is the clinically dominant target with adequate N for the +0.05 lift detection."
}, indent=2)


RISKS_JSON = json.dumps({
    "summary": "Six risks. Dominant ones: MARCo bulk-extraction feasibility, the strong-baseline issue (HLA-EMMA-SA + HLAMatchmaker eplet count are tough to beat by +0.07 on Class II), and platform-discrepancy ambiguity (paired Immucor+OL data per pair varies; the 'discrepant subset' analysis assumes paired data that may not exist for all pairs).",
    "items": [
        {"id": "R1", "category": "data", "severity": "critical",
         "description": "MARCo bulk-extraction feasibility is unconfirmed. With ~10,000+ Class II pairs, programmatic per-pair extraction may take weeks if no API exists, and may trigger rate-limiting / institutional pushback.",
         "likely_failure_mode": "extraction takes 2+ months instead of 1-2 weeks; partial coverage forces the analysis to subset, undermining per-locus claims.",
         "mitigation": "Contact MARCo developers (contato@igen.org.br) early for bulk-download or institutional MOU; in parallel build a respectful rate-limited scraper; pre-register data-completeness criteria for inclusion.",
         "counter_evidence_citations": []},
        {"id": "R2", "category": "method", "severity": "high",
         "description": "HLA-EMMA SA-mismatch is a deceptively strong Class II baseline by construction (SA positions are the antibody-recognized epitopes). HLAMatchmaker eplet count is similarly strong as the de-facto clinical reference. The +0.07 lift over the best baseline is more aggressive than typical Class II ML-vs-rule-based literature suggests.",
         "likely_failure_mode": "learned model achieves +0.02-0.04 lift, which is statistically detectable but clinically marginal; reviewers ask whether the engineering complexity is justified.",
         "mitigation": "Pre-specify +0.04 as the alternative threshold and treat +0.07 as a stretch goal; report effect size with bootstrap CI; provide ablations identifying which features add value beyond HLA-EMMA + HLAMatchmaker.",
         "counter_evidence_citations": ["Kramer et al 2020, HLA 96:43"]},
        {"id": "R3", "category": "data", "severity": "high",
         "description": "Per-locus sample imbalance: DRB1 likely has 5000+ pairs; DRB3/4/5 may have <1000 each; DPA1/B1 heterodimer pairs likely much fewer. The +0.05 per-locus-lift threshold is harder to detect at small N with statistical confidence.",
         "likely_failure_mode": "model meets pooled threshold but DRB3/4/5 and DP show no statistically meaningful lift; clinical adoption stratified by locus becomes muddied.",
         "mitigation": "Pre-register that DRB1 + DQ-heterodimer are the primary endpoints; treat DRB3/4/5 and DP as exploratory with appropriately wider CIs; report power analysis upfront.",
         "counter_evidence_citations": []},
        {"id": "R4", "category": "data", "severity": "high",
         "description": "Platform-discrepancy analysis assumes paired Immucor+OL data per allele pair, but MARCo's manufacturer-stratified counts vary; for many pairs only one platform is represented. The 'discrepant subset' may be too small for stable conclusions.",
         "likely_failure_mode": "discrepant-subset Spearman ρ vs consensus has wide CI; the platform-agnostic claim is statistically not supported.",
         "mitigation": "Pre-register the minimum N per pair on each platform required for inclusion in the discrepant analysis; if MARCo coverage is insufficient, shift the discrepant analysis to the institutional external-validation cohort.",
         "counter_evidence_citations": []},
        {"id": "R5", "category": "evaluation", "severity": "high",
         "description": "GroupKFold by allele identity is a partial leakage guard, but allele PAIRS in MARCo overlap heavily within locus (e.g., DRB1*15:01 appears in pairs with thousands of other DRB1 alleles). Many test pairs share one allele with training pairs, creating residual leakage.",
         "likely_failure_mode": "evaluation metrics are inflated by leakage; held-out lift on truly novel allele pairs is materially lower.",
         "mitigation": "Add a stricter 'hold one allele entirely out' eval: pick e.g. DRB1*15:01, drop ALL its pairs from training, evaluate on those pairs only. Compare against GroupKFold-by-allele-id; report both. Be honest about the gap.",
         "counter_evidence_citations": []},
        {"id": "R6", "category": "external-validity", "severity": "medium",
         "description": "MARCo's cohort is Brazilian; the Brazilian transplant population has distinctive HLA frequency distributions (admixed European-Indigenous-African ancestry); model may not generalize to North American or East Asian cohorts where allele-frequency-weighted pair coverage is different.",
         "likely_failure_mode": "single-cohort model trained; reviewers question generalization; clinical adoption stalls outside Brazil.",
         "mitigation": "Frame as 'first public Class II benchmark using MARCo' with explicit cross-cohort external validation as future work; partner with international groups for replication.",
         "counter_evidence_citations": []}
    ]
}, indent=2)


CHALLENGE_JSON = json.dumps({
    "summary": "Five concrete challenges. The hypothesis is well-grounded but has three soft spots: (a) HLA-EMMA SA-mismatch + HLAMatchmaker eplet count are baselines that may already saturate the Class II signal, making +0.07 lift unrealistic; (b) the platform-discrepant subset analysis assumes paired data that MARCo may not provide for many pairs; (c) the GroupKFold split has residual allele-pair leakage that hides the true generalization gap.",
    "findings": [
        {"id": "C1", "kind": "feasibility-overstated", "severity": "high",
         "description": "The +0.07 absolute Spearman ρ lift over HLA-EMMA SA-mismatch / HLAMatchmaker eplet count on held-out Class II allele pairs is more aggressive than the published Class II ML literature suggests is achievable. SA positions ARE the antibody-recognized epitopes by construction; HLA-EMMA already captures most of the signal. Realistic learned-model lift over the strongest rule-based baseline is probably +0.03-0.05.",
         "evidence_citations": ["Kramer et al 2020, HLA 96:43"],
         "suggested_response": "Pre-specify +0.04 as the falsifiability threshold; treat +0.07 as the stretch goal. Report effect size with bootstrap CI rather than as a binary pass/fail."},
        {"id": "C2", "kind": "data-leakage-risk", "severity": "high",
         "description": "GroupKFold by allele identity does not eliminate allele-pair leakage: a test pair (a1, a3) where (a1, a2) was in training shares half its features with a training example. The model can interpolate. The realistic-generalization metric is held-one-allele-entirely-out, which produces a materially lower number.",
         "evidence_citations": [],
         "suggested_response": "Report BOTH split strategies as primary outcomes. Be explicit that the GroupKFold number overestimates real-world generalization. The held-one-allele-out number is the one to compare against the falsifiability threshold."},
        {"id": "C3", "kind": "missing-baseline", "severity": "high",
         "description": "The proposed baseline set (naive Hamming, HATS-shares, HLA-EMMA-SA, HLAMatchmaker eplet count, PIRCHE-II) is reasonable but missing one critical comparator: a learned model trained on a SINGLE platform's data (e.g., One Lambda only) evaluated on the other (Immucor). If single-platform-trained models generalize across platforms with comparable lift, the platform-id auxiliary feature was unnecessary and the platform-agnostic framing collapses.",
         "evidence_citations": [],
         "suggested_response": "Add 'OL-trained XGBoost evaluated on Immucor pairs' and 'Immucor-trained XGBoost evaluated on OL pairs' as required cross-platform-generalization baselines. The platform-id-feature model must beat these in addition to the rule-based baselines."},
        {"id": "C4", "kind": "data-leakage-risk", "severity": "medium",
         "description": "The MARCo per-pair Spearman ρ is itself estimated from a finite sample; pairs with N<100 sera have high uncertainty in the target ρ. Training a model to predict noisy targets and evaluating with Spearman ρ between predicted and observed values rewards the model for matching the noise, not the signal. The sample-size-weighted MSE loss helps but does not fully solve this.",
         "evidence_citations": [],
         "suggested_response": "Report results separately for high-N pairs (n_samples > 200) and low-N pairs. Treat low-N pair results as exploratory. Consider a Bayesian formulation that propagates target uncertainty into the loss."},
        {"id": "C5", "kind": "novelty-overstated", "severity": "medium",
         "description": "The contribution is framed as 'first ML on empirical MFI for Class II'. The Tambur STAR working group has published platform-comparison work; PIRCHE-II is itself learned (HLA-peptide-binding component). Multi-task ML for HLA antibody prediction has appeared in preprint space. The distinctive contribution is the public-MARCo-cohort + platform-agnostic framing, not the methodology.",
         "evidence_citations": ["Tambur et al 2018, Am J Transplant 18:1604"],
         "suggested_response": "Frame as 'first public Class II benchmark using MARCo + first explicit platform-discrepant-subset evaluation' rather than as 'first learned cross-reactivity model'. Cite Tambur STAR work directly as platform-comparison precedent."}
    ]
}, indent=2)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    out_dir = repo_root / "examples" / "marco_dr_dq"
    out_dir.mkdir(parents=True, exist_ok=True)

    pack = load_pack("biomed-serology")
    llm = MockLLM(responses=[
        DOMAIN_R1, ENGINEER_R1, DOMAIN_R2, ENGINEER_R2,
        SYNTHESIS_JSON, PROTOCOL_JSON, RISKS_JSON, CHALLENGE_JSON,
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
    _write_outputs_staged(result, out_dir, IDEA, pack=pack, generate_notebook=True)

    es = result.hypothesis.epistemic_summary
    audit = result.audit_report
    print(f"marco_dr_dq (v0.3.1) generated:")
    print(f"  well-covered: {es.well_covered_count} · sparse: {es.sparse_count} · gaps: {es.knowledge_gap_count} · syntheses: {es.novel_synthesis_count}")
    print(f"  protocol steps: {len(result.plan.steps)} · risks: {len(result.risks.items)} · challenge findings: {len(result.challenge.findings)}")
    print(f"  audit: {audit.banner()}")
    if audit.mismatch_count:
        print()
        for f in audit.findings:
            if f.status != "mismatch":
                continue
            print(f"  ✗ [{f.auditor_name}] AI claimed: {f.target_summary[:120]}")
            for r in f.mismatch_reasons:
                print(f"      → {r}")
    print(f"  outputs in {out_dir}")


if __name__ == "__main__":
    main()
