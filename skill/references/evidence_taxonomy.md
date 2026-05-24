# Evidence Taxonomy

A more granular guide to choosing the right evidence type for a claim.

## published-evidence

Use when:
- The claim is supported by a specific paper or preprint you can name.
- The reference exists and is verifiable (the user can search for it).
- You can give first-author surname + year + venue (or DOI).

Do **not** use when:
- You vaguely remember "there's a paper on this somewhere" — that's an `observation`.
- The reference is hallucinated or imagined.

Examples:
- `[CLAIM type=published-evidence source="Goyal et al 2022, Nature Methods 19:1108"]Variant graph genome representations improve mapping accuracy by 4-7% over linear references.[/CLAIM]`

## established-guideline

Use when:
- A recognized body has issued a formal recommendation.
- The claim is normative ("you should do X") with institutional backing.

Examples:
- `[CLAIM type=established-guideline source="ICH-E9, Statistical Principles for Clinical Trials (1998)"]Pre-specified primary endpoints are required for confirmatory trials.[/CLAIM]`
- `[CLAIM type=established-guideline source="IPCC AR6 WG1, Chapter 11 (2021)"]Heavy precipitation events have intensified over most land regions with high confidence.[/CLAIM]`

## engineering-precedent

Use when:
- A public artifact (repo, model, benchmark) demonstrates the method works.
- The user could clone/download the artifact today.

Examples:
- `[CLAIM type=engineering-precedent source="github.com/MaterialsProject/pymatgen"]A mature open-source toolkit exists for crystal structure manipulation and Materials Project integration.[/CLAIM]`
- `[CLAIM type=engineering-precedent source="huggingface.co/microsoft/biogpt"]Open biomedical language models with billion-parameter scale exist for fine-tuning.[/CLAIM]`

## observation

Use when:
- The claim is your own reasoning, lab experience, or established field
  intuition that doesn't trace to a single citable source.
- The claim is a domain truism that experts share but isn't formally cited
  (e.g., "DFT systematically underestimates band gaps").

Examples:
- `[CLAIM type=observation source=""]Class-imbalanced losses tend to underperform when the rare class has both small support AND high label noise — both conditions are common in clinical mortality prediction.[/CLAIM]`

## Decision tree

```
Can you name a specific paper / preprint / DOI?
  yes -> published-evidence
  no  -> Is it from a guideline body / standards org / regulator?
           yes -> established-guideline
           no  -> Is there a public repo / benchmark / model that proves it?
                    yes -> engineering-precedent
                    no  -> observation (with empty source)
```

When in doubt, prefer `observation` over inventing a source.
