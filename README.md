# DeltaScience

> **A verification layer for scientific work.**
> Paste any scientific text — or a whole PDF — and every PMID, DOI, arXiv ID and GitHub repo is checked against the real record: does it exist, does its metadata match, does the cited paper support the claim? Fabricated and mis-cited references are flagged. Deterministic, no API key.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](#)
[![Live demo](https://img.shields.io/badge/demo-boheling.github.io%2Fdeltasci-2f6f5b)](https://boheling.github.io/deltasci)

**▶ [Live demo & interactive verifier](https://boheling.github.io/deltasci)** — paste a paragraph, watch it catch a fabricated or mis-cited reference.

---

## What is DeltaScience?

DeltaScience checks the citations in scientific writing against the real record — whether you drafted the text yourself or with an AI. Its core is a **citation verifier**: paste a paragraph, a hypothesis, or a whole paper, and every identifier is checked against PubMed / Crossref / OpenAlex / arXiv / DataCite / GitHub — does it exist, does its metadata match, and does the cited paper actually support the claim? It is **deterministic** (real lookups + string matching, no LLM in the trust path), so it runs with **no API key**.

Around that trust path it adds the **discovery** layer: **`scan`** (retrieve the closest real prior work) and **`gap`** (a coverage-honest read of how crowded an area is) — plus a workflow layer that runs the right ones for your goal (`grant`, `paper`, `review`, `ideate`). The principle is **no LLM in the *trust path***, not "no LLM anywhere": `verify` must be deterministic, but discovery is better with intelligence. So `scan`/`gap` run keyless out of the box (deterministic term-overlap retrieval), and get sharper when an agent drives them — pass your own queries with `scan --query "…"`, or let the [`deltasci-ground` skill](#inside-claude-code) write the queries and reason over the results. A weak discovery pass can only make you *miss* prior art; it can never corrupt a verdict.

It also includes the **two-perspective co-reasoning mode** it grew out of — a domain scientist and an ML engineer talk an idea through in structured rounds (`deltasci run`, needs an LLM), documented below. The verifier is the part that stands on its own.

It ships in two form factors:

1. **`pip install deltasci`** — a Python CLI + library.
2. **Claude Code skills** — install `skill/` for the two-perspective hypothesis mode (`deltasci`), and/or `skill-ground/` for the **grounding layer** (`deltasci-ground`), where the agent drives scan → gap and calls the deterministic engine to verify.

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
git clone https://github.com/boheling/deltasci
cd deltasci
bash skill/install.sh         # deltasci — two-perspective hypothesis mode
bash skill-ground/install.sh  # deltasci-ground — the scan → gap → verify grounding layer
```

Then in Claude Code, for the grounding layer (the agent writes the queries and reasons; `verify` stays deterministic — no key):

> *"Ground this idea: an experience-learning framework with RL for LLM-agent skill evolution."*
> *"Verify the citations in paper.pdf."*

…or for the hypothesis mode:

> *"Use deltasci with the climate pack to generate a hypothesis for: train a neural emulator on ERA5 to downscale Sahel precipitation."*

## Verify citations in *any* text (no run required)

DeltaScience's citation-audit pillar also ships as a standalone verifier you can point at **any** LLM-generated scientific text — a pasted related-work section, a JSON list of claims, or a `.bib` file. It checks that each cited PMID / DOI / arXiv / GitHub identifier exists, that its metadata matches, and (by default) that the cited paper actually *supports* the claim — catching the "real paper, wrong citation" failure that plagues autonomous AI-scientist pipelines. **No provider API key required.**

```bash
deltasci verify --file related_work.md          # untagged prose
echo "X drives Y (PMID 35562209)." | deltasci verify --file -
deltasci verify --text '…' --json               # machine output; exit code 2 on any failed audit
```

Each claim gets a verdict: `PASS` / `FABRICATED` / `METADATA-MISMATCH` / `UNSUPPORTED` / `UNVERIFIABLE` / `SKIPPED`.

### As an MCP server

Verify generated citations from inside any MCP client (Claude Code/Desktop, Cursor) or AI-scientist pipeline — without forking anything:

```bash
pip install "deltasci[mcp]"
claude mcp add deltasci-verify -- deltasci-mcp
```

It exposes one tool, `verify_scientific_claims(text, format, check_support)`, returning the same per-claim verdicts.

### Verify a whole paper (PDF)

Real papers cite by number, with the references in a bibliography at the bottom — so a pasted paragraph only has `[12]`, nothing to resolve. Paper mode ingests the whole document: it parses the bibliography, **resolves every reference to a real record** (embedded DOI/PMID/arXiv, or a Crossref title lookup), links each in-text marker to its reference, and checks each citation **in the context of the sentence that cites it**.

```bash
pip install "deltasci[pdf]"
deltasci verify --pdf paper.pdf                 # verify every numbered citation in context
deltasci verify --pdf paper.pdf --max-references 30   # fast first pass on a big bibliography
deltasci verify --paper --file paper.txt        # pasted full text (body + references)
deltasci verify --pdf paper.pdf --llm anthropic # LLM fallback for author-year / messy bibliographies
```

The web UI (`/verify`) also accepts a PDF upload and shows one card per citation — its verdict, the in-text sentence it was cited in, and a link to the real record. Deterministic by default (no API key); the `--llm` fallback only structures messy bibliographies — every citation is still verified against the real record deterministically.

> **Note:** arXiv references are verified via their DataCite DOI (reliable, no rate-limit issues), so arXiv-heavy CS papers work too. The *claim-to-abstract support* check is PubMed-only — non-PubMed references get existence + metadata verification rather than claim-context. Author-year bibliographies (no `[n]` numbers) are handled by extracting and verifying every cited identifier; use `--llm` for full per-claim context on those.

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
  url    = {https://github.com/boheling/deltasci},
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
