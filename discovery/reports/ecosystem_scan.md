# Ecosystem Scan — DeltaScience vs. the AI-Scientist Landscape

**Date:** 2026-05-24
**Scope:** Open-source (and notable closed) LLM agents for scientific research — hypothesis generation, experiment design, autonomous execution, literature synthesis, and full paper pipelines.
**Subject under comparison:** DeltaScience (`deltasci`) — two-perspective co-reasoning for AI4Science *hypothesis ideation*, with hard gates for grounding, falsifiability, epistemic humility, and citation auditing.
**Method:** GitHub REST API pulls (`api.github.com/repos/...`) for star counts, push dates, issues, language, license — snapshot as of 2026-05-24; web/forum search for community sentiment.

---

## Executive summary

The AI-scientist space in May 2026 is crowded, hype-driven, and bifurcated: flashy *end-to-end* pipelines that promise "idea → paper" (Sakana AI-Scientist ~13.7k★, AutoResearchClaw ~12.6k★, EvoScientist ~3.2k★) on one side, and *grounded literature tools* (STORM, GPT-Researcher, PaperQA2) on the other. The field's dominant, repeatedly-documented failure mode is **fabricated citations and false-novelty claims** — yet almost no tool makes *honesty about the model's own training-distribution edges* its headline feature. DeltaScience deliberately occupies the smallest, least-contested wedge in the map — *get to one defensible, falsifiable hypothesis and explicitly hand off what only the researcher can know* — which is differentiated but also pre-traction (alpha, no public stars) in a field where attention concentrates on autonomy theater.

---

## Head-to-head: DeltaScience vs. the named tools

This is the core comparison you asked for. "Lifecycle stage" is where each tool spends its effort; the last three columns are exactly the axes DeltaScience competes on.

| Tool | Lifecycle stage | Open source | Stars | Honesty about model's *own* gaps | Falsifiability gate | Citation **audit** (verifies the real record) |
|------|-----------------|-------------|-------|----------------------------------|---------------------|-----------------------------------------------|
| **DeltaScience** | **Hypothesis ideation only** | ✅ MIT | alpha / ~0 | ✅ **core feature** (`KNOWLEDGE_GAP` + `coverage` tags) | ✅ **hard gate** (refuses without threshold) | ✅ verifies PMID/DOI/arXiv/GEO vs. real record |
| **Google "AI co-scientist"** | Ideation + proposal | ❌ closed (Gemini) | n/a (paper/product) | ⚠️ self-critique (Reflection agent), not gap-honesty | ❌ emphasizes "testable," no hard gate | ⚠️ grounds via search, no audit-vs-record |
| **CMU Coscientist** | **Experiment design → real execution** | ◑ partial (Apache + Commons Clause) | 202 | ❌ | ❌ (validates empirically by running it) | ❌ |
| **EvoScientist** | **Full end-to-end** (plan→code→write) | ✅ Apache-2.0 | ~3,212 | ❌ weak | ❌ (scores novelty/feasibility/clarity) | ❌ |
| **Dr. Claw** (`OpenLAIR/dr-claw`) | **Full-stack research IDE** | ✅ GPL/AGPL | ~964 | ❌ | ❌ | ⚠️ cross-refs peer-reviewed DBs, HITL checkpoints |
| **AutoResearchClaw** (`aiming-lab`) | **Full pipeline** (23-stage) | ✅ MIT | ~12,632 | ❌ | ❌ | ✅ **4-layer verification** + anti-fabrication registry |
| **AI Scientist v1/v2** (Sakana) | **Full pipeline + auto-review** | ◑ custom license | 13.7k / 6.4k | ❌ | ❌ | ❌ (documented to hallucinate citations) |
| **Curie** | Experiment design + execution | ✅ Apache-2.0 | ~360 | ❌ | ⚠️ rigor/reproducibility modules (closest analog) | ❌ |

**Read of the table:** DeltaScience is the *only* entry that treats the AI's epistemic boundary as the product. AutoResearchClaw is the strongest on citation *verification* (and dwarfs everything on stars), and Curie is the closest on *rigor*, but neither does (a) the "what only you, the researcher, know" handoff, (b) a hard falsifiability gate, or (c) the deliberately narrow ideation-only scope. The "co-scientist" name is badly overloaded — Google's closed Gemini system and CMU's open chemistry-execution system share a name but target opposite ends of the lifecycle.

### Disambiguation flags (honesty notes)
- **"Dr-CLAW"** resolves to **`OpenLAIR/dr-claw`** (Lehigh, Lichao Sun, ~964★) per the press coverage — *but* there's a confusingly-named, much larger **`aiming-lab/AutoResearchClaw`** (~12.6k★, lobster mascot). If your source meant the popular one, it's AutoResearchClaw. Both are in the table.
- **EvoScientist** is confirmed (repo + paper, same authors), but its arXiv ID (2603.08127) uses an unusual month encoding; treat the exact submission date as approximate.
- **DeltaScience** itself is pre-release alpha (v0.1.0); it has no public star traction to report, so it is excluded from the momentum table below.

---

## Technology cluster map

| Cluster | What it does | Representative repos | Maturity |
|---------|--------------|----------------------|----------|
| **End-to-end "AI scientist"** | idea → experiment → paper, chase autonomy & benchmarks | AI-Scientist v1/v2, AutoResearchClaw, EvoScientist, Agent Laboratory, HKUDS AI-Researcher, Dr. Claw | High hype, high stars, most criticized |
| **Lit-review / grounded QA / report writing** | research a topic, synthesize, cite | STORM, GPT-Researcher, PaperQA2 | Most mature, highest stars |
| **Hypothesis generation / ideation** | propose & rank research ideas | DeltaScience, ResearchAgent, SciAgentsDiscovery, MOOSE-Chem, Google co-scientist + OSS clones | Fragmented, early, low-star |
| **Domain-specific autonomous labs** | design+run real experiments in one field | CMU Coscientist & ChemCrow (chem); Biomni, Robin, Virtual Lab (biomed); finch (data) | Mixed; bio cluster rising |
| **Eval / infra (enabling layer)** | gyms & benchmarks for science agents | Aviary, BixBench, LAB-Bench | Quiet but active |

**Where DeltaScience sits:** the *hypothesis-generation* cluster — the most fragmented and least-trafficked one. It is the only member that foregrounds an *epistemic-honesty* contract rather than raw idea throughput.

---

## Top repos by momentum

Sorted by stars; all metrics from the GitHub API on 2026-05-24.

| # | Repo | Stars | Last push | Open issues | Lang | License | Momentum |
|---|------|-------|-----------|-------------|------|---------|----------|
| 1 | `stanford-oval/storm` | 28,261 | 2025-09-30 | 119 | Python | MIT | Flagship, **cooling** (~8mo push gap) |
| 2 | `assafelovic/gpt-researcher` | 27,272 | 2026-04-16 | 232 | Python | Apache-2.0 | Large + active |
| 3 | `SakanaAI/AI-Scientist` | 13,748 | 2025-12-19 | 116 | Jupyter | custom | Category-definer; maintained |
| 4 | `aiming-lab/AutoResearchClaw` | 12,632 | 2026-05-22 | 5 | Python | MIT | **Rising fast** (~12.6k in ~2mo) |
| 5 | `Future-House/paper-qa` | 8,547 | 2026-03-20 | 138 | Python | Apache-2.0 | Mature, well-cited |
| 6 | `SakanaAI/AI-Scientist-v2` | 6,360 | 2025-12-19 | 68 | Python | custom | Strong; first peer-reviewed AI paper |
| 7 | `SamuelSchmidgall/AgentLaboratory` | 5,620 | 2025-08-20 | 58 | Python | MIT | **Stagnant** (no push since Aug '25) |
| 8 | `HKUDS/AI-Researcher` | 5,376 | 2025-10-16 | 62 | Python | none | NeurIPS'25 spotlight; cooling |
| 9 | `EvoScientist/EvoScientist` | 3,212 | 2026-05-23 | 19 | Python | Apache-2.0 | **Rising** (~3.2k in ~4mo) |
| 10 | `snap-stanford/Biomni` | 3,120 | 2026-05-18 | 67 | Python | Apache-2.0 | **Rising, very active** (biomed) |
| 11 | `paperswithcode/galai` (Galactica) | 2,737 | 2023-03-05 | 30 | Jupyter | Apache-2.0 | **Abandoned** (cautionary tale) |
| 12 | `ur-whitelab/chemcrow-public` | 913 | 2024-12-19 | 12 | Python | MIT | **Stagnant** (~17mo idle) |
| 13 | `OpenLAIR/dr-claw` | 964 | 2026-05-06 | 19 | JS/TS/Py | GPL/AGPL | **Emerging** (~964 in ~3mo) |
| 14 | `zou-group/virtual-lab` | 683 | 2025-12-31 | 6 | Jupyter | MIT | Steady; Nature-published |
| 15 | `lamm-mit/SciAgentsDiscovery` | 610 | 2025-05-10 | 11 | Python | Apache-2.0 | Niche; ~1yr idle |
| 16 | `Future-House/robin` | 399 | 2026-04-21 | 4 | Python | Apache-2.0 | **Emerging**, active (biomed) |
| 17 | `Just-Curieous/Curie` | 360 | 2025-09-28 | 23 | Python | Apache-2.0 | Emerging; rigor-focused |
| 18 | `Future-House/aviary` | 264 | 2026-05-21 | 10 | Python | Apache-2.0 | Active infra/eval |
| 19 | `gomesgroup/coscientist` (CMU) | 202 | 2025-08-11 | 3 | Python | NOASSERTION | Notable (Nature'23), low-star |
| 20 | `Future-House/finch` (ex data-analysis-crow) | 63 | 2026-04-22 | 1 | HTML | Apache-2.0 | Emerging, active |

*(Hypothesis-gen long tail: `conradry/open-coscientist-agents` 57★, `ZonglinY/MOOSE-Chem` 55★, `JinheonBaek/ResearchAgent` 38★, `llnl/open-ai-co-scientist` 29★.)*

**License caution for anyone forking:** Sakana v1/v2 and CMU `coscientist` are NOASSERTION/custom; HKUDS AI-Researcher and ResearchAgent ship **no license** (all-rights-reserved). DeltaScience's clean MIT is a real differentiator against these.

---

## Community sentiment highlights

The recurring complaints below are *exactly* the failure modes DeltaScience's gates target — strong tailwind for the positioning, if it can get seen.

- **Hallucinated / outdated citations.** Independent eval of Sakana's AI Scientist: generated papers had a median of ~5 citations (mostly pre-2020), inaccurate citations, duplicated figures, and hallucinated numerical results. → [arXiv:2502.14297](https://arxiv.org/abs/2502.14297)
- **False-novelty.** Same eval: keyword-based lit review flagged well-established ideas (e.g., micro-batching for SGD) as "novel"; 5/12 (42%) proposed experiments failed on coding errors. → [arXiv:2502.14297v1](https://arxiv.org/html/2502.14297v1)
- **"First peer-reviewed AI paper" caveats.** Sakana v2's workshop paper still misattributed LSTM history and was withdrawn by prior agreement (no real meta-review). → [sakana.ai](https://sakana.ai/ai-scientist-first-publication/)
- **Reproducibility / black-box distrust.** Survey: underlying LLMs are opaque, eval write-ups omit reproduction details, lit-review performance "drops significantly." → [arXiv:2503.08979v1](https://arxiv.org/html/2503.08979v1)
- **The "AI slop" flood.** ~100 fabricated/hallucinated citations slipped past reviewers into ~53 accepted NeurIPS 2025 papers; arXiv stopped hosting un-reviewed CS review/position papers (Oct 2025) over the surge. → [Science](https://www.science.org/content/article/new-preprint-server-welcomes-papers-written-and-reviewed-ai)
- **Galactica, the cautionary tale.** Meta's science LLM pulled after 3 days — "statistical nonsense," invented fake papers, 85% of facts about a named researcher wrong. → [MIT Tech Review](https://www.technologyreview.com/2022/11/18/1063487/meta-large-language-model-ai-only-survived-three-days-gpt-3-science/)
- **"Co-scientist, not scientist."** Commentary argues the "autonomous scientist" framing overclaims; these tools are assistive at best. → [k-dense.ai](https://www.k-dense.ai/blog/ai-co-scientist-not-ai-scientist)
- **Even the best lit agents aren't clean.** PaperQA2's own authors note it can cite a secondary source quoted inside a primary one; LitQA2 accuracy ~36.7%. → [arXiv:2409.13740](https://arxiv.org/pdf/2409.13740)

---

## Preliminary gap signals (DeltaScience's wedge)

1. **Nobody productizes "honesty about the model's own edges."** Across 20+ repos, *zero* make the AI's training-distribution boundary a first-class output. DeltaScience's `KNOWLEDGE_GAP` + `coverage={well-covered,sparse}` tagging is genuinely unique. *Evidence:* the entire community-sentiment section is a list of trust failures that this directly addresses; the only tools touching grounding (AutoResearchClaw, Dr. Claw, PaperQA2) verify *external* citations but never flag *"this is outside what I reliably know — ask your domain expert."*

2. **The falsifiability gate is unoccupied.** The hyped end-to-end tools score ideas on novelty/feasibility/clarity; none *refuse to emit* a hypothesis that lacks a measurable disconfirmation threshold. Curie (rigor/reproducibility) is the nearest neighbor and still doesn't gate on falsifiability. *Evidence:* head-to-head table column 6 — only DeltaScience has ✅ as a hard gate.

3. **Citation *auditing* (vs. citation *adding*) is rare.** Only AutoResearchClaw matches DeltaScience on verifying a cited identifier against the real PubMed/Crossref/OpenAlex record (DeltaScience's "FAILED AUDIT" surfacing of metadata mismatches). Most tools "cite" without ever fetching the record. *Evidence:* documented hallucinated-citation failures across Sakana, Galactica, and even the NeurIPS'25 slop figures.

4. **The ideation-only niche is under-contested.** The hypothesis-generation cluster is the most fragmented and lowest-star; gravity (and stars) flows to "idea → paper" autonomy. DeltaScience's "do one thing, hand off downstream" scope is defensible *product* design — but it is also why it will struggle for attention against 12k-star pipelines. *Evidence:* momentum table — every >5k-star repo is full-pipeline; the entire ideation cluster sits under ~700 stars.

5. **Two-perspective structure is differentiated but unproven as a moat.** Multi-agent debate (Google co-scientist's tournament, Virtual Lab's PI+specialists) is well-trodden; DeltaScience's specific *domain-scientist ⊥ ML-engineer* split with pluggable packs is a cleaner, narrower take, but the structural novelty is incremental, not categorical. *Evidence:* Google co-scientist and Virtual Lab already ship multi-agent reasoning at far greater scale.

### Strategic implication
DeltaScience's differentiation is **real and points at the field's most-documented weakness (trust/hallucination)** — but it is differentiation on *epistemic discipline*, which is invisible in a README screenshot and easy for users to undervalue next to "watch it write a whole paper." The wedge to press, loudly: *"Every other tool tries to do more; DeltaScience is the only one engineered to tell you what it doesn't know."* Pair that with the citation-audit "FAILED AUDIT" demo (the one feature that visibly catches a competitor-style failure) as the hero artifact.

---

*Sources are linked inline. All GitHub metrics are point-in-time snapshots (2026-05-24) and will drift. DeltaScience is pre-release alpha and carries no public star data.*
