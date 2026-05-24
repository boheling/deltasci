# biomed_run — example DeltaScience output

This directory contains the artifacts of one full DeltaScience run on the `biomed` pack's example research idea:

> *Predict checkpoint-immunotherapy non-response in TFE3-fusion osteosarcoma using a graph neural network over single-cell spatial transcriptomics, with CD204+ M2 macrophage neighborhood structure encoded as typed cell-cell edges.*

## What's here

- **`transcript.md`** — the full 4-round dialogue (Domain Scientist ↔ ML Engineer) with every CLAIM, KNOWLEDGE_GAP, and NOVEL_SYNTHESIS tag preserved.
- **`hypothesis.md`** — the synthesized grounded hypothesis. Note the **three-section evidence trail**:
  1. *AI-confident foundations* — claims the AI cited from well-covered training (textbook / multi-source).
  2. *Likely-reliable, please verify* — claims with sparser training coverage; specifics should be checked.
  3. *Researcher knowledge required* — `KNOWLEDGE_GAP`s the AI explicitly deferred on, and `NOVEL_SYNTHESIS` leaps the AI is proposing rather than citing.
- **`summary.json`** — machine-readable hypothesis schema + epistemic summary.

## How this run was produced

The 4 round responses and the synthesis JSON were authored by Claude (the same model class deltasci would have called against the Anthropic API), then fed into DeltaScience's `CoReasoner` via the `MockLLM` scripted-response adapter. Every part of the engine — grounding tag parser, per-pack source-pattern rules, falsifiability gate, epistemic-humility gate, three-section evidence renderer — ran identically to a live `--llm anthropic` run. The only difference is *how the LLM responses arrived* (scripted from this session vs streamed from the API).

To reproduce or modify:

```bash
cd <deltasci repo root>
python docs/examples/_generators/biomed_run.py
```

The generator script with all 5 canned responses inline is at [`../_generators/biomed_run.py`](../_generators/biomed_run.py). Edit the responses and re-run to see the engine respond.

## What this run demonstrates

| Tag | Count | Interpretation |
|-----|-------|----------------|
| `CLAIM coverage=well-covered` | 17 | Documented OS biology (CD204+ M2 prognostic role, GSE152048 atlas, IFN-γ signature, HGT, scanpy/squidpy) — citations confidently asserted. |
| `CLAIM coverage=sparse` | 5 | OS-specific IFN-γ baseline AUROC, OS-specific spatial-GNN IO precedent, responder rate, realistic ceiling — hedged. |
| `KNOWLEDGE_GAP` | 6 | Researcher's pretreatment-biopsy + outcome linkage, response definition, sarcoma spatial-GNN literature, TFE3-stratified annotated cohort, Asian-cohort generalization, pilot effect size — explicitly handed back to the researcher. |
| `NOVEL_SYNTHESIS` | 3 | Per-tumor cell-cell graph with M2-tumor typed edges, HGT cell-type-pair edge tokens for learnable spatial weighting, TFE3-stratified evaluation framing — the AI is *proposing* these, not citing them. |
| Falsifiability clause | required | AUROC ≥ 0.75 absolute + ≥ 0.07 over IFN-γ baseline + calibration intercept |α| < 0.05 + slope ∈ [0.9, 1.1]. Null outcome explicitly stated. |

A free-form chatbot run on the same idea would produce text that reads similarly but flatten everything into a single confident voice — no distinction between what's textbook, what's the AI's leap, and what the *researcher* knows that the AI cannot.

## What a launch reader should take away

- A real DeltaScience output is a **division of labor**: the AI handles what's well-discussed online, the researcher handles what isn't (pilot data, niche subfields, non-English work, lab-tribal knowledge, novel cross-disciplinary connections). The three-section evidence trail surfaces that division explicitly.
- The **falsifiability clause** turns a "this might work" research idea into a "we will believe it when X is observed" hypothesis you can defend at a lab meeting or in a grant proposal.
- The **epistemic-humility gate** (synthesis refuses if zero gaps and zero syntheses across the transcript) makes a "complete-certainty" output a structural impossibility — which is what you want from a tool meant for hypothesis generation rather than confident-sounding text.

## Next steps for the launch

Once this example is reviewed and merged, the same generator pattern should be applied to `materials_run/` and `climate_run/` using each pack's `example_idea`. Together, three runs across three packs will give launch readers a strong sense of how DeltaScience adapts to different scientific domains.
