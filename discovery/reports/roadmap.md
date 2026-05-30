# DeltaScience Roadmap — from verifier to *AI science runtime*

## North star
Not "an AI scientist" — foundation models win that. DeltaScience is the **AI science runtime**:
the independent layer any model or agent's scientific output must pass through to become *trustworthy*.
Like **Git / CI / debuggers / observability / type systems** for code — the stronger the generator
gets, the more the runtime matters. We grow *with* the model ecosystem, not against it.

## Five invariants (the constitution — every feature must pass all five)
1. **Independence.** No model in the trust path. The runtime *audits*; it never *generates* the verdict. A model cannot be its own auditor.
2. **Every edge is anchored.** A claim-graph edge is trustworthy only if independently verified against a real record. Unverified edges are visibly marked (INCONCLUSIVE / grey), never silently asserted.
3. **The 10× test.** Ship only what gets *more* valuable when the model gets 10× better. If a stronger model makes it redundant, don't build it.
4. **Ideation is a wedge, not the moat.** Use it for distribution; never compete with foundation models on generation. It has a shelf life.
5. **Governance needs a forced gate.** A moat forms only where verification is *required*. Earn it by embedding in pipelines; don't declare an "OS".

## The architecture — grounding × lifecycle

DeltaScience is not "a verifier." It is the **grounding + governance fabric for the whole
research lifecycle**. Two orthogonal axes define it:

- **Axis A — grounding operations** (deterministic, no LLM, against the real record):
  **`scan`** (what exists?) · **`gap`** (what's missing / novel?) · **`verify`** (is it real & supported?).
- **Axis B — research lifecycle** (the stages where science happens):
  **假说 Hypothesis** · **执行 Execution** · **审查 Review**.

The grounding ops apply at *every* lifecycle stage — a 3×3 of capabilities:

|  | **Hypothesis 假说** | **Execution 执行** | **Review 审查** |
|---|---|---|---|
| **Scan** | closest real prior art near the idea | tools / datasets / methods that already exist | work this paper should have cited |
| **Gap** | genuine white space, or already done? | is this approach already published? | does it overclaim novelty? |
| **Verify** | are the hypothesis's citations real & supportive? | **data/code provenance real; results reproducible?** | citations real; claims supported? |

The empty corner — **Execution × Verify (computational grounding: provenance + reproducibility)** — is
the biggest gap, and the one the Biomni execution trace exposed (agents mostly *compute*, and a claim
there is grounded in data+code+results, not literature).

### Four-layer stack

```
① Generation surface (PLUGGABLE — done by others / models)
   Hypothesis (co-reasoning · ideate) · Execution (Biomni / any agent framework) · Review drafts (LLM)
                              │  produces claims
                              ▼
② Grounding substrate (THE MOAT — deterministic, no LLM, real record)
   scan · gap · verify     — literature edges + computational edges
                              │  certifies every edge
                              ▼
③ Claim Graph (THE SPINE)
   claim → {evidence | data | code | result} · provenance · confidence · coverage
                              │  policy over the graph
                              ▼
④ Governance gate (THE LONG-TERM MOAT)
   no unverified claim ships · provenance required · coverage honesty · institutional memory
   — journals / funders / CI / agents plug in here
```

### Positioning
> The generation surface is pluggable — *who* forms the hypothesis, runs the experiment, or drafts the
> review can be Biomni, any agent framework, or any model. DeltaScience is the layer **every stage must
> pass through to be trusted**: it grounds and audits, it does not generate. (A generator can't be its
> own auditor.) Model/agent gets stronger → layer ① gets stronger → layers ②③④ get *more* needed.

### Discipline (so "imagination" doesn't drift into the red ocean)
Scale toward **grounding/governance across the lifecycle**, never toward "a bigger AI scientist." Every
cell's verb is `scan`/`gap`/`verify` (grounding) — **never `generate`**. Generation stays in the
pluggable ① layer. This is what keeps DeltaScience orthogonal to (and symbiotic with) the foundation
models and Biomni-class agents, instead of competing with them.

## Surface vs substrate (landing ≠ roadmap)
Two **separate** decisions, kept separate: *what we show* (distribution) vs *what we build* (the moat).
The landing should be maximally **wow**; engineering hours should go maximally **deep**. These can — and
should — point in opposite directions. (Don't let a *build/moat* judgment like "this gets eaten" leak
into a *marketing* judgment like "don't show it." Stripe shows beautiful payment flows; its moat is the
infra. Datadog shows pretty dashboards; its moat is the pipeline.)

- **Surface (landing / adoption):** ride the full agentic-research workflow — domain packs, multi-role
  brainstorming, experiment design, hypothesis generation — and **integrate with the orchestration
  frameworks people already use (AutoGen, LangGraph, CrewAI)** instead of competing with them. This is
  the *wow* and the distribution; it makes DeltaScience look native to where the field is heading.
- **Substrate (what we actually develop):** the **runtime observability** (claim graph · replay ·
  dropped evidence) and **governance** (gates · audit · institutional memory) *beneath* that workflow.
  This is the moat — the layer any of those frameworks, agents, or models plugs into and structurally
  cannot be for itself.

Three guardrails so the wow doesn't capsize the boat:
1. **Wow is the hook; the moat is the punchline — both on the landing, in that order.** Lead with the
   workflow to win attention, then immediately land on "…and every claim is grounded, every reasoning
   step observable and audited." Without the second beat we read as "yet another agentic framework" and bounce.
2. **Wow must be real or labelled preview — never vapor.** If the engine doesn't robustly do a step yet
   (e.g. running experiments), show it as "supported workflow / research preview," not a solved capability.
   Honesty is itself the brand (see invariants).
3. **Show thick, build thin.** The workflow and the AutoGen/LangGraph integrations are *surface features* —
   keep them as light as possible (lean on the frameworks we integrate with); pour real engineering into
   the substrate. Showing it ≠ owning it ≠ maintaining it.

## Competitive map — generators vs the verification layer
Everyone else in the space is a **generator, runtime, or behavior-governor**. *None* is an independent
verifier of whether scientific **content** is grounded — the same gap whether the producer is a
foundation-model runtime or a domain science agent.

| Player | What it is | Verifies scientific *content* / truth? | To us |
|---|---|---|---|
| **OpenAI Agents SDK** | model execution runtime (handoffs, tools, sandbox) | ❌ execution only | integrate via MCP (reach) |
| **Anthropic Claude Agent SDK / Managed Agents** | agent loop (self-host) + hosted runtime; safety = Constitutional AI (model-level *harmlessness*) | ❌ safety ≠ factuality | integrate via MCP — **deepest; self-host SDK matches our CI/gate angle** |
| **Microsoft Agent Framework + Agent Governance Toolkit** | runtime (AutoGen+SK merged) + governance: policy engine, trust score, kill switch, SLO, OWASP, SOC2/HIPAA | ❌ governs *agent behavior / security*, not claim truth | be a **domain "scientific-evidence" policy** in its policy engine |
| **Biomni / Biomni Lab (Phylo)** | domain *scientific agent* — autonomous biomedical co-scientist (gene prioritization, drug repurposing, protocols). Stanford SNAP; commercialized; $1M Biomni-AD prize | ❌ **its own paper falls back to *manual human verification* of traces** | best design-partner / consumer (below) |

**The split that matters:** *general* governance (behavior, security, compliance) is being taken by the
platforms — don't compete there. *Domain-specific scientific epistemic* governance (is this claim grounded
in real literature? provenance? freshness / retraction? fact vs conjecture?) is what none of them does
per-domain. That — plus **independence** (the auditor is not the generator) and **ground-truth coupling**
(PubMed / Crossref / OpenAlex) — is the moat.

**Biomni — two roles for us:**
1. **The "AI-scientist line — don't imitate" benchmark.** Well-funded, Stanford-backed, commercialized via
   Phylo. If we tried to be a science *generator*, we'd lose to Biomni-class projects + foundation models.
   Its existence confirms the roadmap's core "don't build an AI scientist" call.
2. **Best forcing-function design-partner / consumer.** Its own paper admits findings are checked for
   hallucination by *manual human verification of the agent's traces* — exactly the toil we automate
   (claim graph + dropped evidence + verdict). Biomni Lab is a *shipping* product running autonomous
   agents at scale → the agent-pipeline forcing function, already real, not hypothetical. Caveat: a
   generator verifying itself isn't independent (that's *why* they use humans) and it's biomedical-only —
   so our lane stays the **independent, cross-domain** verifier it plugs into via MCP.

(The OSS / SaaS *verifier* competition — refchecker, Citely, etc. — is mapped separately in
`verifier_competition_scan.md`.)

## Where we already are (shipped foundation)
- **`verify`** — deterministic, keyless, multi-source citation audit (existence / metadata / claim-support). The trust anchor.
- **`scan`** — real prior-art retrieval (OpenAlex / arXiv / PubMed / GitHub), source-health tracked.
- **`gap`** — crowding read with **INCONCLUSIVE** humility (refuses to assert absence on incomplete retrieval).
- **`workflow`** — goal orchestration (grant / paper / review / ideate).
- **MCP server + CLI + exit code 2 + JSON audit payload** — the pipeline / CI hooks.
- **co-reasoning engine + `CLAIM` / `KNOWLEDGE_GAP` / `NOVEL_SYNTHESIS` tags** — the claim-graph schema seed.

→ Most of the substrate exists. The work is **re-centering on the Claim Graph** and building observability + governance on top — not greenfield.

## Phases

### Phase 0 — Sharpen the wedge *(now, ~done)*
Keep the verifier the most independent, CI-native, honest checker in the space. Position as "a verification layer for scientific work," not "an AI scientist." Exportable audit report.
**10×:** ✅ independence compounds. **Risk:** the bare check is commoditizing (refchecker 369★, SaaS cluster) — this is the credibility anchor, not the moat.

### Phase 1 — The Claim Graph ★ *keystone (Layer 2 core)*
Define the model: `claim → {supporting | contradictory | dropped} evidence`, each edge carrying status, **confidence lineage** (grounded in overlap / #sources / freshness — never model vibe), **source freshness**, **provenance**. `verify` + `scan` populate and *certify* every edge. New `deltasci graph <text|pdf>` → a verified claim graph (JSON + viewer).
**Killer feature — dropped evidence:** "scan retrieved 6 real works; the synthesis used 2; here are the 4 it ignored." Deterministic, novel, only possible because we own retrieval.
**10×:** ✅✅ the audit graph gets *more* valuable as autonomy rises. Reuses verify/scan wholesale.

### Phase 2 — Reasoning replay + ideation surface *(Layer 1 ↔ 2)*
Wire the co-reasoning engine to *emit claim-graph nodes*, not just prose. `deltasci run` produces an auditable graph. **Replay:** step the inference path; each edge shows its verified status, the evidence dropped at that step, and where it's speculative. Ideation becomes the adoption surface whose *output is a graph worth auditing*.
**Guardrail:** keep ideation minimal — its only job is to emit a structured, taggable graph. Do **not** rebuild a multi-agent orchestration framework (CrewAI is red ocean).
**10×:** ⚠️ replay is durable only as *independent reconstruction*, never a pretty render of the model's self-reported (unfaithful) trace.

### Phase 3 — Governance substrate *(Layer 3 — long-term moat)*
Policy over the graph: publish / merge gates (extend exit-code-2 into rules — "no unverified CLAIM", "every NOVEL_SYNTHESIS flagged", "no dropped contradictory evidence"), org policies, auditability (graph + replay = the audit record), **institutional memory** (store of past graphs: "have we claimed this before? did it hold? was it retracted?").
**Gated on a forcing function** (below) — a moat only where verification is *required*.
**10×:** ✅✅✅ more autonomous science → more need for gates. **Risk:** slow; needs a buyer or standard.

## Forcing-function directions (all four open — undecided)
Layer 3 becomes a moat only where someone is *required* to pass the gate. Four directions are on the
table; **none is chosen yet.** Each would shape the Claim Graph schema (Phase 1) differently, so the
choice is deferred until a real pull signal or design partner appears — recorded here so it isn't lost.

| Direction | The forced gate | Who adopts | Who pays / pull | How it shapes the Claim Graph |
|---|---|---|---|---|
| **A. Agent-pipeline gate** | An autonomous research agent passes its own output through the runtime (via MCP) before acting/publishing | Devs building agents; rides model autonomy | Agent platforms, AI-research toolchains | Optimized for machine self-check: fast, structured verdicts an agent can branch on |
| **B. CI for papers / lab git** | Preprint/paper repos run the check on commit; build fails on unverified claims (exit code 2 already exists) | Labs/authors who keep papers in git | Labs, institutions | A diff-able artifact: per-commit graph, gate rules in config |
| **C. Journal / preprint editorial check** | Integrity screening before peer review at a venue | Editors, submission systems | Journals, preprint servers | Aligned to editorial integrity fields (provenance, retraction, conflicts) |
| **D. Regulated science QMS** | Evidence provenance required by compliance (pharma / clinical) | Regulated R&D teams | Pharma, CROs, regulated labs | An auditable compliance record: signoffs, immutable history, freshness SLAs |

**Axis (for later):** A/B are OSS-native, solo-pushable, lighter pull; C/D have real budgets and hard
mandates but need a partner/team and a longer, more political path. **Decision deferred** — revisit
when there's a pull signal; do not pre-commit the Phase 1 schema to any one of them.

## Anti-roadmap (do NOT build)
- A multi-agent orchestration framework *of our own* (red ocean; capability layer). **Integrate** with AutoGen / LangGraph / CrewAI as the surface instead — be the runtime they plug into, not a competitor in the orchestration race.
- An "AI scientist" that replaces the researcher (foundation models win).
- Anything with a model in the trust path (kills independence).
- A closed SaaS competing on the commoditized "is this citation real?" check.
- A static benchmark / leaderboard (commoditizes; gameable).
