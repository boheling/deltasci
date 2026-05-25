# Gap Analysis — Where DeltaScience Can Win

**Date:** 2026-05-24
**Input:** `discovery/reports/ecosystem_scan.md`
**Target audience:** AI4Science researchers (grad students → PIs) turning a vague idea into a defensible, fundable, falsifiable hypothesis — and engineers building AI-scientist pipelines who keep tripping over hallucinated citations.
**Method:** Deep-dived 8 repos' issue trackers (sorted by reactions), READMEs, and discussions via the GitHub API; scored gaps on Impact × (6−Competition) ÷ Effort.

---

## Repos deep-dived (with maintenance signal)

| Repo | Stars | Maintenance signal |
|------|-------|--------------------|
| `SakanaAI/AI-Scientist` (+ v2) | 13.7k / 6.4k | **Abandoned** — last commit 2025-12-19; *zero* maintainer comments in last 100 issue comments on each; 116+68 open issues resolved peer-to-peer only |
| `aiming-lab/AutoResearchClaw` | 12.6k | **Very active** — same-day collaborator replies; triages by closing fast (1/270 open), so pain lives in *closed* issues |
| `EvoScientist/EvoScientist` | 3.2k | **Active**, pre-1.0; web UI / benchmarks / demo still unshipped |
| `stanford-oval/storm` | 28k | **Core effectively abandoned** — last maintainer-merged PR #54 (Jul 2024); 10+ community fix-PRs open & ignored |
| `Future-House/paper-qa` | 8.5k | **Active core dev, DX-deprioritized** — maintainer: *"not so much the user experience and docs"* (#1044); triage bot hallucinates config advice |
| `snap-stanford/Biomni` | 3.1k | **Code-active, thin triage** — OSS release *"frozen as of April 15 2025, differs from the current web platform"* |
| `OpenLAIR/dr-claw` | 964 | **Too young to judge** — 5 open issues, thin tracker; gaps inherited from CLIs it wraps |
| `Just-Curieous/Curie` | 360 | **Going quiet** — last push Sep 2025; markets "rigor" but the one organic user question is *"how do I reproduce your benchmark?"* (#73) |

---

## Pain points by category (with evidence)

**Feature gaps**
- Can't pinpoint the raw evidence sentence behind an answer "to cross-check accuracy" — PaperQA [#464](https://github.com/Future-House/paper-qa/issues/464)
- Can't pin / supply / prioritize your own high-quality sources; auto-retrieved ones are "biased, low-density, fluffy" — STORM [#138](https://github.com/stanford-oval/storm/issues/138) (4👍), [#187](https://github.com/stanford-oval/storm/issues/187), [#96](https://github.com/stanford-oval/storm/issues/96) (4👍)
- Citation logic not exposed to callers — PaperQA [#820](https://github.com/Future-House/paper-qa/issues/820), [#919](https://github.com/Future-House/paper-qa/issues/919)
- Can't skip experiment phases to just write up external results — ARC [#236](https://github.com/aiming-lab/AutoResearchClaw/issues/236) (4👍, top issue)

**Performance / quality gaps (the scientific core)**
- Hallucinated/broken citations: `[1]/[2]` labels with no matching reference, invalid links — STORM [#168](https://github.com/stanford-oval/storm/issues/168)
- Literature search returns topically-irrelevant high-citation papers (pulled the famous "ChatGPT opinion" paper for a knowledge-graph-RL query) — ARC [#258](https://github.com/aiming-lab/AutoResearchClaw/issues/258)
- Experiment-design stage hallucinates an **off-domain plan** (WikiText-103/LSTM benchmark for a non-ML task) that fails *its own validator* — ARC [#253](https://github.com/aiming-lab/AutoResearchClaw/issues/253)
- "Make it focus on replication rather than inventing new ideas" — users distrust generated-hypothesis novelty/validity — Sakana [Disc #166](https://github.com/SakanaAI/AI-Scientist/discussions/166); "Calling it AI Scientist is an overstatement" — [#198](https://github.com/SakanaAI/AI-Scientist/issues/198)
- Independent eval: median ~5 citations (mostly pre-2020), inaccurate citations, hallucinated numbers, 42% of experiments fail on coding errors — [arXiv:2502.14297](https://arxiv.org/abs/2502.14297)

**DX gaps**
- Local / non-default-vendor LLM friction is the **#1 DX complaint everywhere**: silent fallback to OpenAI + needs 4 separate LLM configs (PaperQA [#1321](https://github.com/Future-House/paper-qa/issues/1321) 17 comments, [#1044](https://github.com/Future-House/paper-qa/issues/1044)); Anthropic-key-locked (Biomni [#264](https://github.com/snap-stanford/Biomni/issues/264)); OLLAMA fails to emit valid queries (STORM [#217](https://github.com/stanford-oval/storm/issues/217)); local-model requests in ARC v2 [#101](https://github.com/SakanaAI/AI-Scientist-v2/issues/101), dr-claw [#203](https://github.com/OpenLAIR/dr-claw/issues/203), Curie [#84](https://github.com/Just-Curieous/Curie/issues/84)
- No end-to-end example; bot gives hallucinated config advice — PaperQA [#387](https://github.com/Future-House/paper-qa/issues/387)
- Stale setup docs, unpinned deps, Windows/path/sandbox bugs — Biomni [#267](https://github.com/snap-stanford/Biomni/issues/267)/[#283](https://github.com/snap-stanford/Biomni/issues/283), Curie [#100](https://github.com/Just-Curieous/Curie/issues/100)/[#109](https://github.com/Just-Curieous/Curie/issues/109), Sakana [#43](https://github.com/SakanaAI/AI-Scientist/issues/43) (Apple Silicon)

**Integration gaps**
- Semantic Scholar is a single point of failure: key unobtainable (Sakana [#104](https://github.com/SakanaAI/AI-Scientist/issues/104)), 403 Forbidden (v2 [#105](https://github.com/SakanaAI/AI-Scientist-v2/issues/105)), config ignored, no PubMed/arXiv backends (ARC [#244](https://github.com/aiming-lab/AutoResearchClaw/issues/244))
- No paywalled/institutional journal access — ARC [#194](https://github.com/aiming-lab/AutoResearchClaw/issues/194)

**Maintenance gaps**
- The two most-starred ideation/writing incumbents (Sakana, STORM core) are maintainer-abandoned with large, active, frustrated user bases.
- **Reproducibility gap between demo/internal and OSS release**: PaperQA README admits internal version has paper-access/tools it "cannot share openly" (+ [#1211](https://github.com/Future-House/paper-qa/issues/1211)); Biomni frozen; Curie benchmark unreproducible due to undocumented "file masking" ([#73](https://github.com/Just-Curieous/Curie/issues/73)).
- Code-execution safety: unsandboxed `exec` with full privileges (Biomni [#254](https://github.com/snap-stanford/Biomni/issues/254)), `pickle.loads` RCE (PaperQA [#1227](https://github.com/Future-House/paper-qa/issues/1227)).

---

## Gap scoring matrix

`Opportunity = Impact × (6 − Competition) ÷ Effort` (Impact 1-5; Competition 1=unaddressed…5=saturated; Effort 1=easy…5=hard)

| Gap | Impact | Competition | Effort | **Score** | Rationale |
|-----|:------:|:-----------:|:------:|:---------:|-----------|
| **A. Embeddable evidence verifier (claim→evidence grounding + record audit) as lib/CLI/MCP** | 5 | 2 | 2 | **10.0** | Universal pain; DeltaScience already has the audit pillar built (`grounding.py`, citation audit vs PubMed/Crossref/OpenAlex/GitHub). ARC's 4-layer is in-pipeline only — no *standalone, embeddable* verifier exists. |
| **B. Epistemic-honesty layer (KNOWLEDGE_GAP + coverage tagging)** | 4 | 1 | 3 | **6.7** | Zero competitors do it. But value is *invisible* and effort to make it land (UX, persuading users to read tags) is real. |
| **C. Falsifiability / scientific-validity gate** | 4 | 2 | 3 | **5.3** | Catches the off-domain/false-novelty failures (ARC #253, Sakana #166/#198). Curie's "rigor" is the only weak analog. Hard part is *domain-specific* disconfirmation criteria. |
| **D. Vendor-neutral, fail-loud LLM config** | 5 | 4 | 2 | **5.0** | #1 DX complaint, but litellm/OpenRouter already crowd this; not differentiated for DeltaScience (which already supports anthropic/openai/mock). |
| **G. Independent grounding/hallucination benchmark ("the referee")** | 4 | 1 | 4 | **5.0** | *Surfaced by the second opinion.* No shared eval for hallucinated-citation / false-novelty rates exists; owning the leaderboard makes DeltaScience the referee. High effort, high strategic payoff. |
| **F. Reproducible-OSS practice (installable == benchmarked)** | 3 | 2 | 3 | **4.0** | A practice/trust differentiator more than a product; DeltaScience already runs fully local, no phone-home. |
| **E. Maintained ideation alternative to abandoned incumbents** | 4 | 3 | 4 | **3.0** | Real opening (Sakana/STORM abandoned) but "be a maintained competitor" is positioning, not a buildable feature, and is a long grind. |

---

## Top opportunity briefs

### A. Embeddable scientific-evidence verifier — *score 10.0* ⭐ Quick Win + Future-Proof
- **Gap (1 sentence):** There is no standalone, embeddable tool that takes any LLM-generated scientific text and verifies that each cited PMID/DOI/arXiv ID exists, matches its metadata, **and actually supports the sentence it's attached to** — flagging ungrounded claims for a human.
- **Evidence:** Hallucinated/broken citations are the field's signature failure (STORM #168, Sakana eval arXiv:2502.14297, ~100 fabricated citations into NeurIPS'25 papers); irrelevant high-citation retrieval (ARC #258); users explicitly want to pinpoint the raw evidence sentence to cross-check (PaperQA #464) and to expose citation logic (PaperQA #820/#919).
- **Persona:** (a) an engineer maintaining an AI-scientist pipeline who needs a drop-in grounding check; (b) a researcher who pastes an LLM-drafted related-work section and wants it audited before submission.
- **Why existing tools don't solve it:** ARC's 4-layer verification is locked inside its pipeline; PaperQA cites but exposes no standalone verifier; everyone else hallucinates. None check *claim-to-evidence support* (the hard part) — they check *existence*.
- **Solution shape:** Extract DeltaScience's audit pillar into `deltasci-verify` — a library + CLI + **MCP server** so it rides the distribution of the 13k-star incumbents rather than competing with them. Output: per-claim PASS / METADATA-MISMATCH / UNSUPPORTED / FABRICATED with the real record shown alongside.

### C. Falsifiability / scientific-validity gate — *score 5.3* — most groundbreaking
- **Gap:** No tool *refuses to emit* a hypothesis or experiment plan that lacks a measurable disconfirmation threshold or that is off-domain for the stated problem.
- **Evidence:** ARC #253 (hallucinated off-domain plan that fails its own validator), Sakana Disc #166 / #198 (users distrust novelty/validity), Curie's claimed-but-unreproducible rigor (#73).
- **Persona:** PI / grant reviewer who needs the output to survive scrutiny, not just sound plausible.
- **Why existing tools don't:** They optimize for *generating more*; DeltaScience would be the only one optimizing for *generating less but defensible* — "the tool that says no."
- **Solution shape:** Harden DeltaScience's existing falsifiability + epistemic-humility gates into a reusable validator that also runs on imported third-party plans.

### B. Epistemic-honesty layer — *score 6.7* — ⚠️ Model-Fragile
- **Gap:** Productize "tell me what the model does *not* reliably know" (KNOWLEDGE_GAP + coverage tags).
- **Evidence:** Ecosystem scan found zero tools do this; "co-scientist not scientist" overclaiming critique.
- **Why fragile:** see warning below.

---

## Strategic assessment

| Gap | Quick Win | Groundbreaking | Model-Fragile | Future-Proof |
|-----|-----------|----------------|---------------|--------------|
| **A. Evidence verifier** | **High** — audit pillar already built; lib/CLI/MCP in ~2-4 wks | Medium — verifier exists in pipelines, but *claim→evidence* + embeddable is fresh | **Low risk** — checking a PMID against the real PubMed record is about *the world*, not model skill | **High** — grounding-against-external-record never stops mattering |
| **C. Falsifiability gate** | Medium — gate logic exists; domain criteria take work | **High** — "the tool that says no" is a category-defining posture | Medium risk — better models propose better hypotheses, but *enforcing* disconfirmability is durable | **High** — scientific method doesn't change as models scale |
| **B. Epistemic-honesty layer** | Medium | Medium | **⚠️ High risk** | Low–Medium |
| **G. Grounding benchmark** | Low — needs dataset + harness | **High** — being the referee beats being a player | Low risk | **High** — evals outlive the tools they measure |

**⚠️ Model-Fragile warning — Gap B:** Self-assessed training-coverage is *the model grading its own homework*. Frontier labs (GPT-5/Claude-5) are investing heavily in native, better-calibrated uncertainty — a bolt-on coverage tag risks becoming a worse version of a built-in feature in 12–18 months. It's also *invisible* (a KNOWLEDGE_GAP tag doesn't change the output the way a blocked hypothesis or a flagged dead citation does), so users won't notice it working. **Recommendation: don't sell B standalone — fold its honesty into A's output.**

**⭐ Strong-candidate flag — Gap A** scores **High on both Quick Win AND Future-Proof**: it's the recommended lead.

---

## Second Opinion

*Independent strategist subagent, verbatim summary:*

> **Short answer: B is the weakest. Build A first. Bet the brand on C.**
>
> **Most immediate return → A.** Citation auditing is bounded and testable with public APIs as ground truth; ships in weeks; the only one with a clean adoption path (rides *on top* of incumbents instead of fighting them).
>
> **Most groundbreaking → C.** A gate that *refuses to emit* a non-disconfirmable hypothesis is a genuinely new posture — "the tool that says no" — when every competitor optimizes for generating more.
>
> **Most likely obsoleted → B.** Self-assessed coverage is the model grading its own homework; frontier models will ship better-calibrated uncertainty natively. It's also invisible — hard to demo, benchmark, or monetize.
>
> **Most future-proof → A, then C.** Checking a PMID against the actual PubMed entry is about *the world*, not the model's reasoning — no model improvement removes that need.
>
> **What you're missing:**
> - **The verifier is a commodity risk** — ARC already has 4-layer verification. Your edge isn't "verify citations exist," it's **claim-to-evidence grounding** (does this PMID actually *support this sentence?*). Lead with that.
> - **Distribution is the real gap, not capability.** Abandoned incumbents won't maintain your hooks — bet on the **MCP-server** form so adoption survives without their cooperation.
> - **The missing gap: an independent benchmark.** Nobody trusts these tools because there's no shared eval for hallucinated-citation / false-novelty rates. Owning *"the leaderboard that scores everyone's grounding"* makes you the referee — and a referee's verifier becomes the default.
> - **Do researchers read epistemic tags? Mostly no** — reinforces deprioritizing B.
>
> **Verdict:** Ship A (grounding-first, MCP-form), brand on C, fold B's honesty into A's output.

**Agreement / disagreement notes:**
- **Agrees** with my ranking on all three: A = best immediate + future-proof; C = most groundbreaking; B = weakest / model-fragile (matches my ⚠️ flag on B).
- **Adds (and I'm adopting):** (1) **lead with claim-to-evidence grounding, not citation existence** — plain existence-checking is a commodity now that ARC ships it; (2) **MCP-server form is the real distribution play**; (3) **a new gap not on my original list — Gap G, the independent grounding benchmark** ("be the referee"). I've added G to the scoring matrix (score 5.0, high strategic payoff but high effort).
- **Flag for the user:** the second opinion implies the *highest-ceiling* move (Gap G, the benchmark/referee) is **not** the highest-immediate-return move (Gap A). If you want a quick, shippable win → A. If you want the boldest strategic bet → G. They are complementary (A is the engine a benchmark would run).

---

## Recommendation

**Build Gap A — the embeddable evidence verifier — framed around *claim-to-evidence grounding*, shipped as a library + CLI + MCP server.** It's the highest opportunity score (10.0), reuses DeltaScience's already-built audit pillar (fast), is the one feature that *visibly* catches a competitor-style failure, and is future-proof. Pair it with Gap C's falsifiability gate as the brand ("the tool that says no"), fold Gap B's honesty into A's output rather than selling it standalone, and keep Gap G (the grounding benchmark) as the longer-horizon "become the referee" bet.

---

## Decision

**Selected gap:** A — Embeddable scientific-evidence verifier (opportunity score 10.0)

**What to build:** Extract DeltaScience's citation-audit / claim-grounding pillar into a standalone tool — shipped as a **library + CLI + MCP server** — that takes any LLM-generated scientific text and returns a per-claim verdict:
- `✓ PASS` — cited identifier (PMID/DOI/arXiv/GEO) exists, metadata matches, and the source actually supports the sentence
- `⚠ METADATA-MISMATCH` — the real record differs from what was claimed
- `✗ UNSUPPORTED` — the citation is real but does not back the attached claim
- `✗ FABRICATED` — no such record exists

Lead with **claim-to-evidence grounding** (does this PMID actually support *this sentence?*), not mere citation existence — that's the non-commodity edge over AutoResearchClaw's in-pipeline 4-layer check. The **MCP-server form is the primary distribution play**: it drops into the abandoned-but-high-traffic incumbents (Sakana, STORM) and the active ones (AutoResearchClaw, EvoScientist) without needing their maintainers' cooperation. Fold Gap B's epistemic-honesty (KNOWLEDGE_GAP / coverage) into this tool's output rather than selling it standalone. Keep Gap C (falsifiability gate) as the brand and Gap G (grounding benchmark) as the longer-horizon "referee" bet — both downstream of this engine.

**Confirmed by user:** yes
