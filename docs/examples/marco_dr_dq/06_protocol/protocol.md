# Experiment plan — MARCo + HATS + HLA-EMMA Class II HLA cross-reactivity ML pipeline with platform-agnostic calibration

Multi-stage pipeline: extract MARCo per-pair MFI ρ for Class II → IPD-IMGT/HLA sequence retrieval → HATS featurization → HLA-EMMA mismatch profiling → HLAMatchmaker + PIRCHE-II bulk pipeline → assemble allele-pair features → train XGBoost with sample-size-weighted MSE → evaluate per-locus + platform-stratified + on the platform-discrepant subset.

## Data acquisition
- **Primary dataset**: MARCo Class II allele-pair MFI ρ data (DRB1, DRB3/4/5, DQA1+DQB1, DPA1+DPB1)
- **Accession / URL**: https://marco.igen.org.br/
- **Access constraints**: public web; bulk download mechanism unconfirmed; institutional contact via contato@igen.org.br for downloadable matrix
- **Fallback datasets**: IPD-IMGT/HLA protein FASTA (https://www.ebi.ac.uk/ipd/imgt/hla/), HATS Perl reference implementation (github.com/kosoegawa/HATS), HLA-EMMA mismatch profiling (Kramer 2020), Institutional paired-platform LSA cohort for external validation

## Steps

### 1. MARCo data extraction
Extract per-allele-pair Spearman ρ, R², regression coefficients, manufacturer-stratified sample counts, discordance counts, HATS+HLA-EMMA annotations from MARCo for Class II loci (DRB1, DRB3/4/5, DQA1+DQB1, DPA1+DPB1).
- **Inputs**: MARCo URL
- **Outputs**: pair-level CSV: a1, a2, locus, n_pooled, n_immucor, n_ol, rho_pooled, rho_immucor, rho_ol, r2, hats_shares, hla_emma_sa_count
- **Methods cited**: https://marco.igen.org.br/

### 2. IPD-IMGT/HLA sequence retrieval
Download protein FASTA for Class II loci; parse via Biopython; build per-allele indexed sequences for HATS / HLA-EMMA / HLAMatchmaker / PIRCHE-II downstream pipelines.
- **Inputs**: IPD-IMGT/HLA FASTA
- **Outputs**: per-allele protein-sequence index
- **Methods cited**: https://www.ebi.ac.uk/ipd/imgt/hla/, github.com/biopython/biopython

### 3. HATS featurization
Run HATS Perl on IPD-IMGT/HLA FASTA; parse per-allele key-residue tables; compute per-MARCo-pair shares-serotype binary AND key-residue Hamming distance per locus.
- **Inputs**: IPD-IMGT/HLA FASTA, HATS Perl
- **Outputs**: per-pair HATS feature vectors
- **Methods cited**: github.com/kosoegawa/HATS, Osoegawa et al 2024, HLA 104:e15702

### 4. HLA-EMMA mismatch profiling
Run HLA-EMMA on each MARCo allele pair to produce per-position mismatch profile with SA flagging; aggregate to SA-mismatch count + total-mismatch count features.
- **Inputs**: per-allele sequences, HLA-EMMA distance tables
- **Outputs**: per-pair SA + total mismatch counts
- **Methods cited**: Kramer et al 2020, HLA 96:43

### 5. HLAMatchmaker + PIRCHE-II bulk pipeline
Add HLAMatchmaker eplet-mismatch count and PIRCHE-II indirect-recognition score per MARCo pair as required strong baselines; this is the 1-2 week pipeline-engineering investment.
- **Inputs**: per-allele sequences
- **Outputs**: per-pair HLAMatchmaker + PIRCHE-II features
- **Methods cited**: Duquesnoy 2002, Hum Immunol 63:339, Geneugelijk & Spierings 2020 PIRCHE-II review

### 6. Feature assembly + train/test split
Concatenate HATS + HLA-EMMA + HLAMatchmaker + PIRCHE-II + locus + platform features into the per-pair feature matrix; assemble sample-size weights; produce 5-fold GroupKFold splits by allele identity plus a hold-one-allele-entirely-out evaluation. (This step was added v0.5 after the case study found that omitting it left the train step with NameError on undefined X/y.)
- **Inputs**: all per-pair feature columns from steps 3-5
- **Outputs**: X, y, sample_weight, fold_indices, FEATURE_COLS
- **Methods cited**: github.com/scikit-learn/scikit-learn

### 7. Train XGBoost regressor
XGBoost with sample-size-weighted MSE loss (w_i = log(n_samples_i + 1)); cross-validated training on the 5-fold GroupKFold splits from step 6; final production model on all data for feature-importance interpretation.
- **Inputs**: X, y, sample_weight, fold_indices from step 6
- **Outputs**: trained XGBoost model + cross-validated metrics
- **Methods cited**: github.com/dmlc/xgboost

### 8. Evaluate per-locus + platform-stratified + platform-discrepant
Held-out test (20% pairs by stratified split): pooled Spearman ρ; per-locus Spearman ρ for {DRB1, DRB3/4/5, DQ heterodimer, DP heterodimer}; platform-stratified eval (Immucor-only, OL-only, pooled); platform-discrepant-subset analysis (pairs where |ρ_immucor - ρ_ol| > 0.15) — does the model recover the consensus?
- **Inputs**: model predictions on held-out test
- **Outputs**: per-locus Spearman ρ, platform-stratified ρ, discrepant-pair correlation vs consensus
- **Methods cited**: TRIPOD 2015 reporting

## Evaluation
- **Primary metric**: Spearman correlation between predicted and observed MFI cross-reactivity (Spearman ρ) at held-out allele pairs, pooled and per-locus
- **Success threshold**: Pooled Spearman ρ ≥ 0.85 AND ≥ 0.07 absolute lift over best of {naive Hamming, HATS-shares, HLA-EMMA-SA, HLAMatchmaker eplet count, PIRCHE-II indirect-recognition} AND per-locus lift ≥ 0.05 in ≥ 4/5 stratification groups AND platform-discrepant-pair Spearman ρ vs consensus ≥ 0.7
- **Null outcome**: Pooled lift < 0.03 OR DQ-heterodimer lift < 0.05 OR platform-discrepant-pair correlation < 0.5 falsifies
- **Baselines**: naive AA Hamming distance (regression), HATS shares-serotype binary (regression), HLA-EMMA SA-mismatch count (regression), HLAMatchmaker eplet-mismatch count (regression), PIRCHE-II indirect-recognition score (regression), Single-platform-trained XGBoost evaluated on the other platform (cross-platform generalization baseline)

## Compute
- **Hardware**: Single CPU (no GPU needed)
- **Estimated runtime**: ~1h training + ~1-2 weeks data + pipeline acquisition
- **Storage**: ~2GB IPD-IMGT/HLA FASTA + extracted MARCo data + intermediate feature tables
- **Cost estimate**: $0 (all data sources public; HLAMatchmaker / PIRCHE-II web tools free for academic use)

## Timeline
3-4 weeks total: 2 weeks data + pipeline (MARCo extraction, HLAMatchmaker / PIRCHE-II bulk integration); 1 week modeling + cross-validation + per-locus stratified eval; 1 week external-validation arm if institutional paired-platform cohort is available.

## Sample-size justification
MARCo has 1000+ sera; thousands of within-locus DR/DQ allele pairs (DRB1 alone likely 5000-10000 pairs given allele-frequency-weighted enumeration; DQ heterodimer likely 1000-3000 pairs). Sufficient for tabular regression with ~50 features. Per-locus stratified analysis: DRB1 well-powered; DRB3/4/5 + DP exploratory; DQ heterodimer is the clinically dominant target with adequate N for the +0.05 lift detection.