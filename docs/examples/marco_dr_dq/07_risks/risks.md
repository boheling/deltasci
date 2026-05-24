# Risk register

Six risks. Dominant ones: MARCo bulk-extraction feasibility, the strong-baseline issue (HLA-EMMA-SA + HLAMatchmaker eplet count are tough to beat by +0.07 on Class II), and platform-discrepancy ambiguity (paired Immucor+OL data per pair varies; the 'discrepant subset' analysis assumes paired data that may not exist for all pairs).

**6 risks identified.**

## R1 · data · CRITICAL · ✅ resolved

**Description.** MARCo bulk-extraction feasibility is unconfirmed. With ~10,000+ Class II pairs, programmatic per-pair extraction may take weeks if no API exists, and may trigger rate-limiting / institutional pushback.

**Likely failure mode.** extraction takes 2+ months instead of 1-2 weeks; partial coverage forces the analysis to subset, undermining per-locus claims.

**Mitigation.** Contact MARCo developers (contato@igen.org.br) early for bulk-download or institutional MOU; in parallel build a respectful rate-limited scraper; pre-register data-completeness criteria for inclusion.

## R2 · method · HIGH · ✅ resolved

**Description.** HLA-EMMA SA-mismatch is a deceptively strong Class II baseline by construction (SA positions are the antibody-recognized epitopes). HLAMatchmaker eplet count is similarly strong as the de-facto clinical reference. The +0.07 lift over the best baseline is more aggressive than typical Class II ML-vs-rule-based literature suggests.

**Likely failure mode.** learned model achieves +0.02-0.04 lift, which is statistically detectable but clinically marginal; reviewers ask whether the engineering complexity is justified.

**Mitigation.** Pre-specify +0.04 as the alternative threshold and treat +0.07 as a stretch goal; report effect size with bootstrap CI; provide ablations identifying which features add value beyond HLA-EMMA + HLAMatchmaker.

**Counter-evidence cited:**
- Kramer et al 2020, HLA 96:43

## R3 · data · HIGH · 🔴 confirmed

**Description.** Per-locus sample imbalance: DRB1 likely has 5000+ pairs; DRB3/4/5 may have <1000 each; DPA1/B1 heterodimer pairs likely much fewer. The +0.05 per-locus-lift threshold is harder to detect at small N with statistical confidence.

**Likely failure mode.** model meets pooled threshold but DRB3/4/5 and DP show no statistically meaningful lift; clinical adoption stratified by locus becomes muddied.

**Mitigation.** Pre-register that DRB1 + DQ-heterodimer are the primary endpoints; treat DRB3/4/5 and DP as exploratory with appropriately wider CIs; report power analysis upfront.

## R4 · data · HIGH · 🟡 still open

**Description.** Platform-discrepancy analysis assumes paired Immucor+OL data per allele pair, but MARCo's manufacturer-stratified counts vary; for many pairs only one platform is represented. The 'discrepant subset' may be too small for stable conclusions.

**Likely failure mode.** discrepant-subset Spearman ρ vs consensus has wide CI; the platform-agnostic claim is statistically not supported.

**Mitigation.** Pre-register the minimum N per pair on each platform required for inclusion in the discrepant analysis; if MARCo coverage is insufficient, shift the discrepant analysis to the institutional external-validation cohort.

## R5 · evaluation · HIGH · 🟡 still open

**Description.** GroupKFold by allele identity is a partial leakage guard, but allele PAIRS in MARCo overlap heavily within locus (e.g., DRB1*15:01 appears in pairs with thousands of other DRB1 alleles). Many test pairs share one allele with training pairs, creating residual leakage.

**Likely failure mode.** evaluation metrics are inflated by leakage; held-out lift on truly novel allele pairs is materially lower.

**Mitigation.** Add a stricter 'hold one allele entirely out' eval: pick e.g. DRB1*15:01, drop ALL its pairs from training, evaluate on those pairs only. Compare against GroupKFold-by-allele-id; report both. Be honest about the gap.

## R6 · external-validity · MEDIUM · 🟡 still open

**Description.** MARCo's cohort is Brazilian; the Brazilian transplant population has distinctive HLA frequency distributions (admixed European-Indigenous-African ancestry); model may not generalize to North American or East Asian cohorts where allele-frequency-weighted pair coverage is different.

**Likely failure mode.** single-cohort model trained; reviewers question generalization; clinical adoption stalls outside Brazil.

**Mitigation.** Frame as 'first public Class II benchmark using MARCo' with explicit cross-cohort external validation as future work; partner with international groups for replication.
