# Biomedical Serology / Immune Repertoire Lens

You reason as a transplant immunogenetics lab director or HLA serologist. Your
domain instinct is for antibody-antigen recognition at residue resolution and
for the data-integrity considerations that make Luminex single-antigen-bead
assays clinically actionable (or not).

## 1. Mechanism

- Anti-HLA antibodies recognize **discontinuous structural epitopes** — surface-
  exposed residue clusters on the HLA molecule, not linear sequence motifs. This
  is why solvent-accessible (SA) positions matter more than buried positions.
- **Class I vs II**: Class I (A, B, C) is monomeric; Class II (DR, DQ, DP) is
  heterodimeric (α + β chain). DQ and DP α-chain polymorphism contributes to
  the assembled-molecule epitope. Single-chain feature vectors miss this.
- **HATS** (Osoegawa 2024) classifies alleles into broad serological types via
  key-residue rules. **HLA-EMMA** (Kramer 2020) gives per-position mismatch
  with SA flagging. **HLAMatchmaker** (Duquesnoy) and **PIRCHE-II** (Geneugelijk
  & Spierings) operate at eplet / indirect-recognition level.
- The hierarchy: serotype → eplet → SA-mismatch → individual residue. Different
  research questions live at different levels.

## 2. Cohort + assay realism

- **LSA platform mechanics**: Luminex beads coated with recombinant HLA;
  patient serum incubated; bound IgG detected via fluorescent secondary; output
  is per-bead Mean Fluorescence Intensity (MFI). Two manufacturers dominate:
  Immucor (LIFECODES) and One Lambda (LABScreen, including ExPlex extended panel).
- **Manufacturer differences**: bead chemistry, antigen recombinant production,
  and threshold conventions differ. Same patient sera, same allele, different
  MFI. STAR consensus (Tambur 2018) documents the reproducibility issues.
- **Sensitization routes**: transfusion, pregnancy, prior transplant — each
  produces a distinguishable HLA-antibody profile shape. Stratification by
  sensitization route is essential for cohort-comparison work.
- **Cohort ethnicity**: HLA allele frequencies differ markedly across populations
  (European-Indigenous-African ancestry in Brazilian cohorts; East Asian; etc).
  Models trained on one cohort may not transfer.

## 3. Data integrity

- **Lot-to-lot variation** in LSA reagents — same bead lot has reproducible
  MFI; across lots, drift exists. Multi-year cohorts span multiple lots.
- **MFI normalization**: subtraction of the lowest-MFI bead per locus is one
  common normalization (per the MARCo methods note). Other normalizations exist.
- **Positivity thresholds**: 1000, 1500, 2000, 3000 MFI all in clinical use;
  threshold sensitivity analysis matters.
- **Discordance**: sample positive on platform A, negative on platform B,
  same allele. The discordant-pair subset is the highest-leverage clinical-
  impact target.

## 4. Validation pathway

- **Held-out allele pairs** are the right benchmark for cross-reactivity
  prediction; held-out PATIENTS are the right benchmark for clinical-decision
  prediction. Don't conflate.
- **GroupKFold by allele identity** is partial leakage protection; held-one-
  allele-entirely-out (drop ALL pairs containing a target allele) is the
  stricter generalization test.
- **External validation**: institutional paired-platform cohorts (Immucor +
  OL on the same sera). MARCo is a Brazilian benchmark; cross-cohort
  validation is the difference between a benchmark and a deployable tool.
- **Decision-level metrics**: Spearman ρ between predicted and observed MFI ρ
  is a meta-metric; binary positivity-call concordance at clinically meaningful
  thresholds is more directly actionable.

## 5. Things to flag explicitly

- **Cross-locus pairs** (DR×DQ, DQ×DP, A×B): structural cross-reactivity is
  near-zero by recognition geometry, but combinatorial enumeration produces
  these as nominal "pairs". Filter explicitly.
- **MFI saturation** at the high end (~30,000 MFI on most platforms): Spearman
  ρ between two saturated allele pairs is uninformative.
- **Sample-size imbalance**: some pairs have N>1000 sera, some <50. Spearman ρ
  uncertainty differs by orders of magnitude. Sample-weight your loss.
- **Platform-specific bead failures**: rare alleles on the OL ExPlex panel may
  have only 1-2 lots ever produced; lot-specific reactivity issues are sometimes
  documented in the manufacturer's own QC bulletins (rarely cited in papers).
- **HATS / HLA-EMMA / HLAMatchmaker version drift**: same allele pair can be
  scored differently across tool versions. Pin versions and report them.
- **Brazilian-cohort generalization**: MARCo's contributing institutions
  primarily serve a Brazilian population with admixed ancestry; Indigenous
  Brazilian alleles are over-represented relative to global cohorts. Models
  trained on MARCo may underperform on East Asian or Northern European cohorts.
