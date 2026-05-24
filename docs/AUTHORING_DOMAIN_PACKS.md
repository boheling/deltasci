# Authoring a Domain Pack

A domain pack is **the entire personality of the domain expert** in a DeltaScience session. It's two files:

```
my_pack/
├── pack.toml
└── lens.md
```

The bar to add one is intentionally low: ~50 LOC of TOML + one markdown lens file. No Python required.

## Step 1 — scaffold

```bash
deltasci init-pack neuroscience
```

This creates `./packs/neuroscience/pack.toml` and `./packs/neuroscience/lens.md` with sensible defaults.

## Step 2 — fill in `pack.toml`

```toml
[meta]
name = "neuroscience"
display_name = "Neuroscience"
version = "0.1.0"
description = "Systems, cognitive, computational, and clinical neuroscience — covers neural recording, imaging, behavior."
example_idea = "Use a transformer encoder over multi-region Neuropixels recordings to predict trial-by-trial decision boundaries during a 2AFC task in mice."

[[evidence_rules]]
type = "published-evidence"
source_pattern = "\\d{4}"          # require a year in citations

[[evidence_rules]]
type = "engineering-precedent"
source_pattern = "(github\\.com|huggingface\\.co|datalad|openneuro|dandi)"

[scoring_rubric]
axes = ["data_availability", "technical_feasibility", "biological_plausibility", "novelty", "translational_potential"]
weights = [1.0, 1.0, 1.5, 1.0, 1.2]
```

### Field reference

| Field | Required | Notes |
|-------|----------|-------|
| `[meta].name` | yes | snake_case identifier |
| `[meta].display_name` | yes | human-readable name shown to LLM |
| `[meta].version` | yes | SemVer string |
| `[meta].description` | yes | one-paragraph scope |
| `[meta].example_idea` | recommended | enables `deltasci demo --pack <name>` |
| `[[evidence_rules]]` | optional | per-type source-pattern regex enforcement |
| `[scoring_rubric].axes` | yes | the feasibility scorecard axes |
| `[scoring_rubric].weights` | yes | one float per axis |

## Step 3 — write `lens.md`

The lens is the prompt fragment that turns the LLM into your domain expert. The format is open — markdown — but we recommend 4-6 sections with bullet questions:

1. **Mechanism / first principles** — what underlying processes govern this domain?
2. **Data ecosystem** — canonical datasets, biases, gaps.
3. **Methodology realism** — non-negotiable baselines, sample sizes, effect sizes.
4. **Validation pathway** — what end-to-end success looks like.
5. **Things to flag explicitly** — common pitfalls a generalist LLM would miss.

Look at `src/deltasci/packs/biomed/lens.md`, `materials/lens.md`, and `climate/lens.md` for working examples.

### What makes a good lens

- **Specific to the domain.** "Be a careful scientist" is useless. "DFT systematically underestimates band gaps" is useful.
- **Names canonical artifacts.** Datasets, benchmarks, repos that domain experts would recognize.
- **Lists pitfalls.** Apparent-but-fake results, confounds, distribution shifts that this domain has learned to be paranoid about.
- **Names the domain's epistemic edges explicitly.** Where does training data thin out for *this* field? Subfields published mostly in non-English journals, lab-tribal protocol knowledge, paywalled instrument manuals, the researcher's own pilot data — list these so the AI knows where it should be emitting `KNOWLEDGE_GAP`s instead of guessing.
- **Stays under ~2,000 words.** This goes into every prompt; longer = more cost.

## Step 4 — validate

```bash
deltasci validate-pack ./packs/neuroscience
```

This loads the pack and surfaces any structural problems.

## Step 5 — try it

```bash
# Smoke test with mock LLM
deltasci demo --pack ./packs/neuroscience --llm mock

# Real run with your LLM
deltasci run --pack ./packs/neuroscience --idea "your idea here"
```

## Step 6 — contribute it back

If your pack is broadly useful, [open a domain pack proposal issue](../.github/ISSUE_TEMPLATE/domain_pack_proposal.md) on the DeltaScience repo. Include:

1. The two pack files.
2. One example transcript + hypothesis from a real run (anonymized as needed).
3. A one-paragraph note on the target user (which subdomain, which datasets, which kind of researcher).

We merge community packs into `src/deltasci/packs/` after a brief review. Pack authors are credited in the changelog.

## Tips

- **Score axes are a design choice.** Pick 3-5 that matter for your domain. For climate, `decision_relevance` matters; for materials, `synthesizability` matters; for biomed, `ethical_clearability` matters.
- **Source patterns are advisory.** They're regexes that filter out obviously-fake citations (e.g., requiring a 4-digit year). Don't make them so strict that real citations get rejected.
- **Test with `--llm mock` first.** It's free and fast.
- **The lens is read literally.** If you write "respond in haiku," the LLM will respond in haiku. Be deliberate.
