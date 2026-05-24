# DeltaScience

> **Two perspectives, one hypothesis.**
> A domain scientist and an ML engineer talk through your AI4Science research idea in 4 structured rounds, producing a grounded, falsifiable hypothesis with a citation trail.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#)

---

## What is DeltaScience?

DeltaScience is a small, focused tool for the AI4Science community. It runs a structured **two-perspective co-reasoning dialogue** — alternating between a domain expert (parameterized by a *domain pack*) and an ML engineer — and produces a hypothesis you can defend in front of a PI or a grant reviewer.

It ships in two form factors:

1. **`pip install deltasci`** — a Python CLI + library.
2. **A Claude Code skill** — drop the `skill/` directory into `~/.claude/skills/deltasci/` and invoke it from inside Claude Code.

Both share the same domain packs (biomed, materials, climate, plus your own).

## Why two perspectives?

Free-form chatbot brainstorming gives plausible-sounding research ideas with no grounding. Single-prompt "be a scientist" approaches collapse two distinct expertises (domain mechanism, ML feasibility) into one voice and produce mush. DeltaScience keeps them separate:

```
Round 1  Domain Scientist  → mechanism, unmet need, prior evidence, constraints
Round 2  ML Engineer       → data representation, method, precedents, risks
Round 3  Domain Scientist  → refinement, evaluation realism, falsifiable prediction
Round 4  ML Engineer       → revised plan, formulas, implementation, expected outcomes
                ↓
            Synthesis: a grounded, falsifiable hypothesis with citation trail
```

A complete deltasci run produces six artifacts: hypothesis, experiment protocol, risk register, adversarial challenger findings, citation audit, and a transcript of the dialogue that produced them — all auditable, all in one navigable run directory.

Six things make it different from "just prompting an LLM":

| | DeltaScience | Free-form LLM |
|--|--|--|
| **Grounding** | Every claim tagged with type, source, AND AI's training-coverage self-assessment (`well-covered` / `sparse`) | Untagged; mixes facts and vibes |
| **Honest about AI's edges** | Material outside training distribution is emitted as `[KNOWLEDGE_GAP]` for the researcher, not fabricated | Confabulates citations to fill gaps |
| **Falsifiability gate** | Synthesis refuses to emit a hypothesis without a measurable threshold | "It might work!" |
| **Epistemic humility gate** | Synthesis refuses if zero `KNOWLEDGE_GAP` and zero `NOVEL_SYNTHESIS` across the dialogue (a complete-certainty transcript is itself a hallucination signal) | No such check |
| **Citation audit pillar** | Every PMID/DOI/arXiv ID/GitHub repo/GEO accession in a CLAIM is verified against the real PubMed/Crossref/OpenAlex/GitHub record; metadata mismatches surface as a prominent "FAILED AUDIT" section (this catches the BioIntel-style failure where a fabricated PMID got a green checkmark) | "I checked it" with no actual fetch |
| **Adversarial challenger** | A second-opinion model (optionally a different provider via `--challenger-llm`) tries to break the hypothesis; its findings are first-class output and its own citations get audited too | None |
| **Structured protocol + risks** | Hypothesis ships with a concrete 6-step experiment plan and a ranked risk register; both flow through the same audit pillar | Hypothesis text only |
| **Domain awareness** | Pluggable domain packs parameterize the expert lens | Generic "be a scientist" |

### The three first-class tags

```
[CLAIM type=<TYPE> coverage=<COVERAGE> source="<CITATION>"]<text>[/CLAIM]
[KNOWLEDGE_GAP category=<CATEGORY>]<question for the researcher>[/KNOWLEDGE_GAP]
[NOVEL_SYNTHESIS rationale="<one-line>"]<the connection you're proposing>[/NOVEL_SYNTHESIS]
```

`coverage` ∈ `{well-covered, sparse}`. Material the AI thinks is `uncovered` (lab-tribal, paywalled, niche, non-English, the researcher's pilot data, etc.) is **never** allowed as a CLAIM — it must be a `KNOWLEDGE_GAP`. Connections the AI is *making* (not citing) are `NOVEL_SYNTHESIS`. This is exactly the line between "AI knows what's well-discussed online" and "the researcher knows what's at the frontier of their field" — DeltaScience surfaces it instead of papering over it.

## Install

```bash
pip install deltasci                    # core (CLI + library)
pip install "deltasci[anthropic]"       # + Anthropic adapter
pip install "deltasci[openai]"          # + OpenAI adapter
pip install "deltasci[all]"             # both
```

Provider keys are read from the environment (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`).

## Quick start

### One-liner (Materials)

```bash
export ANTHROPIC_API_KEY=...
deltasci run \
  --pack materials \
  --idea "Train a graph neural network on the Materials Project to identify Li-ion cathode candidates in the spinel family with predicted voltage > 4.3V."
```

Outputs go to `./deltasci-output/<timestamp>_<slug>/` in a numbered staged layout:

```
00_idea.md
01_framing/      02_engineering/    03_refinement/    04_plan/      (per-round transcripts)
05_synthesis/    hypothesis.md + summary.json (three-section evidence trail + falsifiability)
06_protocol/     protocol.md + experiment_plan.json (concrete, execution-ready plan)
07_risks/        risks.md + risk_register.json (5–10 ranked failure modes + mitigations)
08_audits/       citations.json + codex.md (citation audit + adversarial challenger)
manifest.json    (run-level metadata)
```

The web UI at `deltasci view <run-dir>` (auto-launched at the end of `deltasci run` unless you pass `--no-view`) renders all of this with the audit results, including any `FAILED AUDIT` section showing both what the AI claimed and what was actually at the cited identifier.

### Try it without an API key

```bash
deltasci demo --pack biomed --llm mock
```

This runs a deterministic mock LLM end-to-end so you can see the output shape.

### Inside Claude Code

```bash
git clone https://github.com/deltasci/deltasci
cd deltasci && bash skill/install.sh
```

Then in Claude Code:

> *"Use deltasci with the climate pack to generate a hypothesis for: train a neural emulator on ERA5 to downscale Sahel precipitation."*

## Built-in domain packs

| Pack | Display name | What it lenses |
|------|--------------|----------------|
| `biomed` | Biomedical Sciences | mechanism, patient framing, evidence base, IRB / regulatory pathway, translational realism |
| `materials` | Materials Science | first principles, composition/structure space, DFT bias, synthesizability, validation pathway |
| `climate` | Climate & Earth Sciences | physical conservation, observational data ecosystem, statistical regime, decision relevance |

List them: `deltasci list-packs`. Inspect one: `deltasci show-pack biomed`.

## Author your own domain pack

A domain pack is **two files** in a directory:

```
my_pack/
├── pack.toml      # metadata + evidence rules + scoring rubric
└── lens.md        # the domain expert's reasoning lens (markdown)
```

Scaffold one:

```bash
deltasci init-pack neuroscience
# ... edit pack.toml and lens.md ...
deltasci validate-pack ./packs/neuroscience
deltasci run --pack ./packs/neuroscience --idea "..."
```

See [`docs/AUTHORING_DOMAIN_PACKS.md`](docs/AUTHORING_DOMAIN_PACKS.md) for the full guide.

## Comparison

| Tool | Scope | Open source | License | Domain-pluggable | Falsifiability gate |
|------|-------|-------------|---------|------------------|---------------------|
| **DeltaScience** | Hypothesis ideation | ✅ | **MIT** | ✅ packs | ✅ hard requirement |
| ChatGPT / Claude direct | Generic chat | n/a | n/a | manual prompts | ❌ |
| AI Scientist (Sakana) | Full paper generation | ✅ | Apache 2.0 | partial | ❌ |
| Coscientist (CMU) | Chemistry experiment design | partial | research | locked | partial |
| Galactica / scite / Elicit | Literature retrieval | ✅/❌ | mixed | n/a | n/a |

DeltaScience deliberately occupies a small niche: *get to a defensible hypothesis*. It hands off to your favourite paper-writing or experiment-design tool downstream.

## Library API

```python
from deltasci import CoReasoner, Config, load_pack
from deltasci.llm import get_adapter

pack = load_pack("biomed")
llm = get_adapter("anthropic")
reasoner = CoReasoner(pack=pack, llm=llm, config=Config(num_rounds=4))

result = reasoner.run(idea="Predict checkpoint-immunotherapy non-response in TFE3-fusion osteosarcoma from spatial transcriptomics.")
print(result.hypothesis.title)
print(result.hypothesis.falsifiability.threshold)
print(result.hypothesis.feasibility_scores.overall)
```

The full hypothesis schema is documented in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Configuration

Environment variables:

| Variable | Default | Notes |
|----------|---------|-------|
| `DELTASCI_LLM_PROVIDER` | auto | `anthropic`, `openai`, `mock`, or `auto` |
| `DELTASCI_MODEL` | provider default | model id override |
| `DELTASCI_OUTPUT_DIR` | `./deltasci-output` | where outputs are written |
| `ANTHROPIC_API_KEY` | — | required for `--llm anthropic` |
| `OPENAI_API_KEY` | — | required for `--llm openai` |

CLI flags override env vars (`--llm`, `--model`, `--out`).

## Privacy & ethics

DeltaScience runs locally and does not phone home. The only outbound traffic is to whatever LLM provider you choose. No telemetry, no user accounts, no server.

If you use it for clinical, regulatory, or high-stakes research work, **the falsifiability gate is not a substitute for IRB review, regulatory pathway analysis, or clinical validation.** The tool is an ideation aid, not a decision-maker.

## Citation

If DeltaScience helps your research, citing it as:

```bibtex
@software{deltascience2026,
  title  = {DeltaScience: Two-Perspective Co-Reasoning for AI4Science Hypothesis Generation},
  author = {{DeltaScience contributors}},
  year   = {2026},
  url    = {https://github.com/deltasci/deltasci},
  note   = {Version 0.1.0}
}
```

## Contributing

Contributions welcome — especially **new domain packs**. See [`CONTRIBUTING.md`](CONTRIBUTING.md). The fastest path:

1. Open a [domain pack proposal issue](.github/ISSUE_TEMPLATE/domain_pack_proposal.md).
2. Author the pack (≈50 LOC of TOML + 1 markdown file).
3. Open a PR with `validate-pack` output and one example transcript.

## License

MIT — see [`LICENSE`](LICENSE).
