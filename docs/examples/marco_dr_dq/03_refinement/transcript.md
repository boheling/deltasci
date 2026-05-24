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
