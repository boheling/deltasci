# Risk register

Six risks ranked by their potential to falsely produce or hide a positive result.

**6 risks identified.**

## R1 · data · CRITICAL

**Description.** Pretreatment FFPE OS biopsy cohorts with linked checkpoint-inhibitor outcomes are very small (likely <100 patients, often <50 with high-quality Xenium); single-site cohorts will be severely underpowered for stratified TFE3-fusion analysis.

**Likely failure mode.** wide AUROC confidence intervals overlapping the IFN-γ baseline, false negative on the +0.07 falsifiability threshold even if true effect exists.

**Mitigation.** Multi-site cohort assembly via SARC consortium or COG before commencing; pre-register sample-size requirements.

## R2 · evaluation · HIGH

**Description.** AUROC may not reflect the clinically actionable improvement at the offer-acceptance decision threshold; non-response is the rare class, so AUPRC and net benefit at the relevant decision point matter more than AUROC.

**Likely failure mode.** model achieves AUROC > 0.75 but decision-curve analysis shows no benefit over standard of care.

**Mitigation.** Pre-specify AUPRC + DCA at clinically meaningful threshold as co-primary endpoints.

**Counter-evidence cited:**
- Vickers & Elkin 2006 Med Decis Making 26:565

## R3 · method · HIGH

**Description.** Cell-type annotation noise — CD204 / CD68 / CD163 panels in Xenium can confuse M2 macrophages with osteoclast-like cells abundant in OS — would propagate into spurious graph edges.

**Likely failure mode.** model learns osteoclast spatial signal, not M2 polarization; effect disappears in external validation.

**Mitigation.** Add osteoclast markers (TRAP, CTSK) to panel; require dual-positive CD204+CD68+CD163+ for M2 calls; sensitivity-test with leave-one-marker-out.

## R4 · confounding · HIGH

**Description.** TFE3-fusion status may be confounded with cohort-source — TFE3-positive cases concentrate at large referral centers — making the TFE3-stratified evaluation a site effect rather than a biology effect.

**Likely failure mode.** stratified TFE3 result reproduces site demographics, not the proposed biological signal.

**Mitigation.** Multi-site cohort with matched TFE3 distributions across sites; site-as-confound sensitivity analysis.

## R5 · novelty-overstated · MEDIUM

**Description.** Spatial graph approaches to immunotherapy response prediction in melanoma and breast cancer are increasingly common; the OS-specific contribution may be smaller than framed if the architecture itself is borrowed.

**Likely failure mode.** reviewers note that the OS application is straightforward transfer of existing methods.

**Mitigation.** Position the contribution as the OS-specific cell-type panel + TFE3-stratified evaluation, not the architecture; cite the prior melanoma/breast spatial-graph IO work directly.

## R6 · ethics-or-governance · MEDIUM

**Description.** Multi-site DUA + IRB for federated training of a clinical-decision-support tool is non-trivial; privacy-preserving federated learning has its own failure modes.

**Likely failure mode.** project stalls at 6 months in legal review; or, simpler federated approach has unexpected accuracy hit.

**Mitigation.** Begin DUA discussions in week 1 of project, before any modeling; plan for centralized vs federated decision early.
