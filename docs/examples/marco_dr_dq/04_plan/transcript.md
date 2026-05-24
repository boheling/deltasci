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
