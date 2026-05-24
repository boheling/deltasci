---
name: Domain pack proposal
about: Propose a new built-in domain pack (neuroscience, chemistry, ecology, etc.)
title: "[pack] propose: <domain>"
labels: domain-pack, enhancement
---

## Domain

What scientific domain does this pack target? (e.g., "neuroscience — systems and computational neuro, with an emphasis on Neuropixels-era multi-region recording")

## Target user

Who would use this pack? (PhD student, postdoc, PI, role)

## Datasets and benchmarks the lens names

List the canonical datasets / benchmarks / repositories this domain expects. We use these to anchor the lens.

- Dataset 1:
- Benchmark 1:
- Reference repo 1:

## Proposed scoring rubric axes

3-5 axes that matter most for evaluating ideas in this domain. Each will get a 1-5 score in the synthesized hypothesis. Examples:

- `data_availability`
- `technical_feasibility`
- `<domain-specific axis>`
- `novelty`
- `<domain-specific axis>`

## Common pitfalls in this domain

What apparent-but-fake results does this domain see often? What confounds, distribution shifts, or evaluation traps do experts immediately spot?

## Draft files (if you have them)

Paste your draft `pack.toml` and `lens.md` here, or link to a fork. We'll iterate together.

## Validation

Have you run `deltasci validate-pack` on it? Have you run `deltasci demo --pack` against it with `--llm mock`?

- [ ] `validate-pack` passes
- [ ] `demo --llm mock` runs end-to-end
- [ ] One real-LLM run attached as a transcript
