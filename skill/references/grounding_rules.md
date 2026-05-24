# Grounding Rules

DeltaScience is built on the principle that AI4Science hypotheses are only useful when the AI is honest about three things:

1. What it knows reliably (cite confidently).
2. What it knows but might confabulate the specifics on (hedge, ask the researcher to verify).
3. What it does not know because the material is outside its training distribution (defer to the researcher).

The training distribution of every web-trained LLM systematically under-represents:

- Paywalled / subscription-journal literature.
- Non-English literature.
- Lab tribal knowledge ("everyone in this lab does X but it's never been written up").
- Niche subfields with thin online citation density.
- Patents, conference posters, clinical practice that hasn't been published.
- The researcher's own pilot data.
- Cross-disciplinary connections that have not been written down.

A hypothesis tool that pretends the AI knows everything will hallucinate exactly where the researcher's expertise is most valuable. DeltaScience instead makes the AI's epistemic boundary explicit.

## The three tags

### `[CLAIM type=<TYPE> coverage=<COVERAGE> source="<CITATION>"]<text>[/CLAIM]`

Use for any factual claim you are willing to assert.

`coverage` ∈ `{well-covered, sparse}`.

- `well-covered`: You can recall this from multiple independent textbook / review-level sources. Cite confidently.
- `sparse`: You have signal but might confabulate dates, names, or specific numbers. Hedge specifics. Cite only verbatim.

`coverage=uncovered` is **not allowed** on a CLAIM. Use a KNOWLEDGE_GAP instead.

### `[KNOWLEDGE_GAP category=<CATEGORY>]<question>[/KNOWLEDGE_GAP]`

Use whenever you would otherwise be tempted to fabricate.

`category` ∈ `{lab-tribal-knowledge, paywalled-or-non-OA, non-english-literature, niche-subfield, unpublished-or-pilot-data, patent-or-clinical-practice, novel-cross-disciplinary-connection, other}`.

The researcher fills these in.

### `[NOVEL_SYNTHESIS rationale="<one-line>"]<connection>[/NOVEL_SYNTHESIS]`

Use when you are *making a leap* — combining well-covered facts into a hypothesis or connection no source explicitly states. This is the creative step at the heart of hypothesis generation. It is *good*. But it must be marked, not dressed up as a citation.

## What counts as a violation

- A factual claim outside any tag.
- A CLAIM with no `coverage`, or with `coverage=uncovered`.
- A KNOWLEDGE_GAP with an unknown category.
- A `published-evidence` / `established-guideline` / `engineering-precedent` CLAIM with empty `source`.
- A pack-specific source-pattern mismatch (e.g., biomed requires a 4-digit year).

## What to do on a violation

1. Redo the round once with the violations described.
2. If they persist, leave them in but record them in the grounding summary.
3. **Never fabricate a citation to clear a violation.** Tag the claim as a KNOWLEDGE_GAP instead.

## Why a transcript with zero gaps and zero syntheses is suspect

If the AI emits zero KNOWLEDGE_GAPs and zero NOVEL_SYNTHESES across an entire 4-round dialogue, it is claiming complete certainty about every aspect of a research idea. That is statistically implausible — *every* AI4Science research idea has training-distribution edges and creative leaps. Synthesis refuses by default. Bypass with `--allow-no-epistemic-gaps` only if you've reviewed the transcript and confirmed it.
