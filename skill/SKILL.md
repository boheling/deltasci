---
name: deltasci
description: >
  Two-perspective co-reasoning for AI4Science hypothesis generation. Runs a structured
  4-round dialogue between a domain scientist (parameterized by a domain pack) and an
  ML engineer, producing a grounded, falsifiable research hypothesis that is honest
  about the AI's training-distribution edges. Domain-agnostic via pluggable packs
  (biomed, materials, climate, or your own). Use when a researcher has a vague idea
  and wants to turn it into a defensible, evaluable hypothesis with explicit handoffs
  for the things only the researcher can know.
---

# DeltaScience: Two-Perspective Co-Reasoning

## Purpose

Generate AI4Science research hypotheses that are:

1. **Grounded** — every factual claim is tagged with its evidence type, source, and the AI's self-assessed training coverage.
2. **Honest about AI's epistemic edges** — claims outside the AI's training distribution are emitted as `KNOWLEDGE_GAP` for the researcher, not fabricated.
3. **Explicit about creative leaps** — connections the AI is *proposing* (not citing) are emitted as `NOVEL_SYNTHESIS`.
4. **Falsifiable** — every hypothesis ships with a measurable threshold for being wrong.
5. **Domain-aware** — uses a pluggable lens specific to the scientific field.
6. **Two-perspective** — alternates between domain expert and ML engineer.

This is the Claude Code skill version of the `deltasci` Python package. They share the same domain packs and grounding rules.

## The three first-class tags

```
[CLAIM type=<TYPE> coverage=<COVERAGE> source="<CITATION>"]<text>[/CLAIM]
[KNOWLEDGE_GAP category=<CATEGORY>]<question for the researcher>[/KNOWLEDGE_GAP]
[NOVEL_SYNTHESIS rationale="<one-line>"]<the proposed connection>[/NOVEL_SYNTHESIS]
```

`coverage` ∈ `{well-covered, sparse}`. `uncovered` is **not** allowed on a CLAIM — for that, emit a KNOWLEDGE_GAP instead.

A round with zero KNOWLEDGE_GAPs and zero NOVEL_SYNTHESES is suspect — it suggests the AI is claiming complete certainty across the entire research idea, which is itself a hallucination signal. Synthesis refuses by default.

## Inputs

| Parameter | Required | Description |
|-----------|----------|-------------|
| `idea` | Yes | The raw research idea. |
| `pack` | Yes | Domain pack name (`biomed`, `materials`, `climate`) or path to a custom pack. |
| `context_dir` | No | Directory of background papers/notes. |
| `out_dir` | No | Where to write outputs. Default: `./deltasci-output/`. |

## Outputs

| File | Description |
|------|-------------|
| `transcript.md` | Full 4-round dialogue with all three tag types. |
| `hypothesis.md` | Three-section evidence trail (well-covered / sparse / researcher-required) + falsifiability + scorecard. |
| `summary.json` | Machine-readable hypothesis schema + epistemic summary. |

## Step-by-Step Procedure

### Step 1 — Identify the domain pack

Read `<pack_dir>/pack.toml` and `<pack_dir>/lens.md`. If the user's request doesn't name a pack and the domain is unambiguous, pick one without asking.

### Step 2 — Run the 4-round dialogue

Follow the prompts in `prompts/`. The flow is:

```
Round 1  Domain Scientist  (mechanism, unmet need, prior work, constraints)
Round 2  ML Engineer       (data representation, method, precedents, risks)
Round 3  Domain Scientist  (refinement, evaluation realism, falsifiable prediction)
Round 4  ML Engineer       (revised plan, math, implementation, expected outcomes)
```

In **every round**, every factual statement must be one of the three tags. See `references/grounding_rules.md` and `references/coverage_axis.md` for the rationale.

After each round, scan the output. If you find untagged factual claims, redo that round (one repair attempt). If a round has zero KNOWLEDGE_GAPs *and* zero NOVEL_SYNTHESES, prompt yourself: "Am I being honest about my training-distribution edges? Am I being honest about which connections are leaps vs cited?" — and rewrite if needed.

### Step 3 — Write the transcript

Write to `<out_dir>/transcript.md` with each round labeled and all three tag types preserved.

### Step 4 — Synthesize the grounded hypothesis

Follow `prompts/synthesis_round.md`. Produce JSON with:
- `title`, `statement`
- `domain_grounding`, `technical_approach`
- `falsifiability` (prediction + threshold + null_outcome — all required)
- `feasibility_scores`, `feasibility_justifications`

The CLAIMs, KNOWLEDGE_GAPs, and NOVEL_SYNTHESES are **collected automatically from the transcript** — do NOT re-emit them in the synthesis JSON.

**Hard rules**:
- No falsifiable threshold → refuse, output `{"error": "no_falsifiable_clause", "reason": "..."}`.
- Across all rounds, zero KNOWLEDGE_GAPs and zero NOVEL_SYNTHESES → refuse, output `{"error": "no_epistemic_humility", "reason": "..."}`.

### Step 5 — Render the hypothesis

The final `hypothesis.md` has THREE evidence sections, in this order:

1. **AI-confident foundations** (well-covered claims with citations)
2. **Likely-reliable, please verify** (sparse-coverage claims — cite carefully)
3. **Researcher knowledge required** — KNOWLEDGE_GAPs + NOVEL_SYNTHESES

Plus an **Epistemic summary** with counts of each tag type and any warnings (e.g., "sparse claims outnumber well-covered ones").

### Step 6 — Report

Tell the user:
- The hypothesis title
- Overall feasibility score
- Counts: well-covered / sparse / knowledge gaps / novel syntheses
- The falsifiability threshold
- Any epistemic warnings
- Where output files are

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `num_rounds` | 4 | Total dialogue rounds (must be even). |
| `grounding_strictness` | `high` | Reject tagless claims with one repair attempt. |
| `require_falsifiability` | `true` | Refuse to emit a hypothesis without a falsifiability clause. |
| `require_epistemic_humility` | `true` | Refuse to emit a hypothesis when no KNOWLEDGE_GAPs and no NOVEL_SYNTHESES were emitted across the transcript. |

## Rules

- **Never invent citations.** If you can't name a real reference, either tag the claim `coverage=sparse` and use the most-honest source you have, or emit a KNOWLEDGE_GAP.
- **Never use `coverage=uncovered` on a CLAIM.** Uncovered material goes in a KNOWLEDGE_GAP.
- **Mark your leaps as NOVEL_SYNTHESIS.** Combining two well-covered facts into a hypothesis nobody has written down is *good* — it's the point. But say so explicitly.
- **Skip the falsifiability gate is not allowed.** A hypothesis without a measurable threshold is a wish.
- **The pack lens is read literally.** It parameterizes how the domain expert reasons.

## Checklist

- [ ] Domain pack identified and lens loaded.
- [ ] 4 rounds completed with proper CLAIM / KNOWLEDGE_GAP / NOVEL_SYNTHESIS tags.
- [ ] At least one KNOWLEDGE_GAP and at least one NOVEL_SYNTHESIS across the transcript.
- [ ] Synthesis produced valid JSON matching the schema.
- [ ] Falsifiability clause has prediction + threshold + null_outcome.
- [ ] Hypothesis.md has all three evidence sections.
- [ ] Outputs written: transcript.md, hypothesis.md, summary.json.
