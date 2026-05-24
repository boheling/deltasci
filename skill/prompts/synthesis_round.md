# Synthesis Round

You synthesize the full 4-round transcript into a single grounded hypothesis.

## Output format

Produce a single JSON object — no commentary, no markdown fences, just JSON.

The object MUST have these top-level fields:

```json
{
  "title": "...",
  "statement": "one paragraph",
  "domain_grounding": {
    "mechanism": "...",
    "unmet_need": "...",
    "expected_impact": "..."
  },
  "technical_approach": {
    "core_method": "...",
    "key_innovation": "...",
    "implementation_path": "..."
  },
  "falsifiability": {
    "prediction": "...",
    "threshold": "MEASURABLE — e.g., AUC >= 0.85, Δμ > 2σ, p < 0.01",
    "null_outcome": "what observation would falsify the hypothesis"
  },
  "feasibility_scores": {
    "<axis_1>": <int 1-5>,
    "<axis_2>": <int 1-5>,
    ...
  },
  "feasibility_justifications": {
    "<axis_1>": "one sentence",
    ...
  }
}
```

Use the rubric axes defined in the active domain pack's `pack.toml` under
`[scoring_rubric].axes`.

## Hard rules

1. **Falsifiability is required**. If the transcript does not support a
   prediction with a measurable threshold and a clear null outcome, output
   exactly this object instead:

   ```json
   {"error": "no_falsifiable_clause", "reason": "<one sentence>"}
   ```

2. **Epistemic humility is required**. If the transcript has zero
   KNOWLEDGE_GAPs *and* zero NOVEL_SYNTHESES across all rounds, that is a
   hallucination signal — the AI is claiming complete certainty across the
   entire research idea. Output exactly this object instead:

   ```json
   {"error": "no_epistemic_humility", "reason": "<one sentence>"}
   ```

3. **No invented citations**. The CLAIM, KNOWLEDGE_GAP, and NOVEL_SYNTHESIS
   items are aggregated from the transcript automatically — do not re-emit them
   in this JSON.

4. **The threshold must be operationalizable**. "Improves performance" is not
   a threshold. "AUROC ≥ 0.85 with 95% CI lower bound > 0.80 on the held-out
   external cohort" is a threshold.

5. **Match the rubric**. Provide exactly one integer score per rubric axis,
   in [1, 5].
