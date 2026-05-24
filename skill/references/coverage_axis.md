# The Coverage Axis: Why It's Not About Recency

DeltaScience asks the AI to self-classify each claim's `coverage` — `well-covered` or `sparse` — or, for material outside its training distribution, to emit a `KNOWLEDGE_GAP` instead of fabricating.

A common temptation is to treat this as "recent vs old literature." That is the wrong axis. Recency is a weak proxy at best.

## What coverage actually depends on

LLMs are trained on the open web. Web visibility — not publication date — determines what's in the training distribution.

A 2024 ML preprint that has been on Twitter and discussed in dozens of blog posts is **well-covered**. A 2008 paper in a regional journal that was never properly digitized is **uncovered**. Date does not predict it.

Web visibility is shaped by:

- **Open-access vs paywalled** publishing. Subscription-journal results have weaker training-data signal.
- **English vs non-English**. Significant work in Chinese, German, Spanish, Korean, etc. communities is systematically under-represented.
- **Citation density online**. Repos that get linked, papers that get blogged. A niche subfield can publish actively but produce thin training signal.
- **Publication form**. Patents, conference posters, clinical practice notes, lab protocols — under-indexed corpora.
- **Privacy of the source**. The researcher's pilot data, internal lab notebooks, unpublished findings — never on the web at all.

## Two distinct AI failure modes

The coverage axis addresses one failure mode (missing facts). There is a second failure mode the `NOVEL_SYNTHESIS` tag addresses:

- **Missing facts**: The fact isn't in training data. AI confabulates a citation. → KNOWLEDGE_GAP.
- **Missing connections**: Both endpoint facts are in training, but the *connection* between them was never explicitly written. AI either invents a citation that "establishes" the connection, or pretends the connection is well-established. → NOVEL_SYNTHESIS.

Both are where the researcher's expertise is most valuable. Both are where AI hallucinates most.

## Heuristic decision tree (for the AI to apply to itself)

```
Is this claim a leap I am making (no source explicitly states it)?
   yes → [NOVEL_SYNTHESIS]

Is this claim's source plausibly outside my training distribution?
   - lab-tribal? → [KNOWLEDGE_GAP category=lab-tribal-knowledge]
   - paywalled? → [KNOWLEDGE_GAP category=paywalled-or-non-OA]
   - non-English literature? → [KNOWLEDGE_GAP category=non-english-literature]
   - niche journal, rarely cited online? → [KNOWLEDGE_GAP category=niche-subfield]
   - unpublished / researcher's data? → [KNOWLEDGE_GAP category=unpublished-or-pilot-data]
   - patent or clinical practice? → [KNOWLEDGE_GAP category=patent-or-clinical-practice]
   yes → KNOWLEDGE_GAP

Can I recall this from MULTIPLE independent textbook/review-level sources?
   yes → [CLAIM coverage=well-covered]
   no  → [CLAIM coverage=sparse]   (and hedge specifics)
```

## Why this changes hallucination rates structurally

In a generic chatbot, the prompt asks "what is the answer?" and the AI is forced to provide one. Hallucination is the rational behavior under that prompt.

In DeltaScience, the AI has three honest options: cite (well-covered), hedge (sparse), or defer (KNOWLEDGE_GAP). Fabrication isn't the path of least resistance any more — deferring is.

The synthesis stage's epistemic-humility gate (refuse if zero gaps and zero syntheses across the transcript) closes the remaining loophole: an AI that confidently asserts everything is suspect even if every individual claim looks well-formed.
