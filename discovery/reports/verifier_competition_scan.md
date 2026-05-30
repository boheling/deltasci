# Ecosystem Scan — Citation/Reference Verification (mid-2026)

**Scope:** Tools that verify the citations/references in AI-generated or human-drafted scientific
writing — OSS libraries/CLIs/MCP servers, consumer SaaS, research-assistant platforms, and native
foundation-model features. **Question:** does DeltaScience's verifier have a lot of competition now?

## Executive summary

**Yes — this went from a near-empty niche to a crowded category in the last ~12–18 months.** The
"is this citation real?" capability (existence + metadata match against OpenAlex/Crossref/PubMed/
Semantic Scholar) is now **commoditized**: a dozen free, no-signup SaaS checkers, a high-profile OSS
rival (Mark Russinovich's `refchecker`, 369★), an MCP clone of DeltaScience's exact play, *and*
native model improvements all exist. Even the "two-layer audit" (real **and** supports the claim)
that DeltaScience treats as its edge is now a published protocol (arXiv 2511.04683). The durable
differentiation is no longer the check itself — it's **independence (no model in the trust path),
auditability, dev-surface/CI embedding, and epistemic humility (INCONCLUSIVE)**.

## Technology cluster map

| Cluster | What it is | Examples | Crowding |
|---|---|---|---|
| **Consumer SaaS citation checkers** | Free/freemium web tools: paste refs → Verified / Partial / Not-Found vs 150–250M records | Citely, Citea, SwanRef, CiteMe, CiteTrue, GPTZero Hallucination Detector, Clarity | 🔴 saturated |
| **OSS reference verifiers (dev tools)** | Libraries / CLIs / MCP servers for programmatic verification | **markrussinovich/refchecker** (369★), JonasBaath/mcp-refchecker, academic-refchecker, **DeltaScience** | 🟠 contested |
| **Research-assistant platforms** | Search + evidence + citation-stance features | scite.ai (supporting/contrasting), Consensus, Elicit, Semantic Scholar | 🟠 adjacent |
| **Native foundation-model features** | Grounding/citation built into the model product | Anthropic Citations API, Claude-with-search, OpenAI Deep Research | 🟡 rising |
| **Academic protocols / benchmarks** | Papers formalizing the method + measuring the problem | arXiv 2511.04683 (zero-assumption auditing), 2602.05930 (NeurIPS fabrication taxonomy), 2604.03173 (Deep-Research reference hallucination), FACT framework | 🟡 formalizing |

## Top players by momentum

| Tool | Type | Signal | Notes |
|---|---|---|---|
| **markrussinovich/refchecker** | OSS (MIT, Python) | **369★, pushed 2026-05-20**, 3 issues | Direct rival. Azure CTO. Multi-source + **LLM web-search to flag fabrications** + whole-OpenReview-venue scanning. Featured in press as "the open tool fixing peer-review hallucinations." |
| **Citely** | SaaS | 200M+ records, "95%+ accuracy", journal-editor angle | Most marketed; explicit two-layer "real + supports claim" pitch |
| **CiteMe** | SaaS | 250M sources, free no-signup, per-AI (ChatGPT/Gemini/Claude) | Batch bibliography checker |
| **SwanRef** | SaaS | 150M papers, free hallucination detector | Consumer-grade |
| **scite.ai** | SaaS | 1.2B citation statements classified supporting/contrasting/mentioning | Owns the "does it support the claim?" framing at scale |
| **JonasBaath/mcp-refchecker** | OSS MCP | 0★, 2026-04-23, no license | **Occupies DeltaScience's exact MCP niche** — new, no traction yet |
| **Anthropic Citations API** | Native | grounds answers in supplied docs, cites exact sentences | Grounding-in-your-docs, not literature verification (different) — but the wedge of platform absorption |

## Community sentiment / external signals

- **The problem is now mainstream + measured.** Reported LLM citation-fabrication rates of **25–40%**; **50+ hallucinated references in ICLR 2026 submissions**; a NeurIPS 2025 "100 fabricated citations" failure-mode taxonomy (arXiv 2602.05930). Source: arXiv, citely.ai.
- **The "two-layer audit" is now textbook.** arXiv 2511.04683 ("AI-Powered Citation Auditing: A Zero-Assumption Protocol") describes *exactly* DeltaScience's design — confirm real, then check it supports the claim — at 91.7% verification rate. The method is no longer novel/proprietary.
- **Native models are closing the gap.** FACT framework: Claude-with-search **94%** citation accuracy vs OpenAI Deep Research **78%**; Anthropic shipped a Citations API. The "AI makes up citations" pain erodes as models improve — directly the platform-absorption risk flagged in the strategy discussion.
- **Press validates the OSS dev-tool angle but a rival already owns it.** the-decoder.com framed Russinovich's `refchecker` as "a new open tool" fixing conference-grade hallucinations.

Sources: [citely.ai](https://citely.ai/posts/fake-citations-how-to-spot-them) · [CiteMe](https://citeme.app/ai-bibliography-checker) · [SwanRef](https://www.swanref.org/) · [refchecker](https://github.com/markrussinovich/refchecker) · [mcp-refchecker](https://github.com/JonasBaath/mcp-refchecker) · [arXiv 2511.04683](https://arxiv.org/pdf/2511.04683) · [arXiv 2602.05930](https://arxiv.org/pdf/2602.05930) · [arXiv 2604.03173](https://arxiv.org/html/2604.03173v1) · [Anthropic Citations](https://claude.com/blog/introducing-citations-api) · [the-decoder](https://the-decoder.com/hallucinated-references-are-passing-peer-review-at-top-ai-conferences-and-a-new-open-tool-wants-to-fix-that/)

## Gap signals — where DeltaScience is still differentiated (vs commoditized)

1. **Deterministic / no-LLM-in-trust-path / no-key.** Most SaaS and even `refchecker` put an LLM in the loop (web-search fabrication detection). DeltaScience's verdict is reproducible string-math — the **independence + auditability** angle, which is the one thing a foundation model structurally can't be (it can't be its own auditor). *Strongest remaining moat.*
2. **Dev-surface / CI-native.** Exit-code-2, library, MCP — built to be a *gate in a pipeline*, not a consumer web form. Only `refchecker` competes here; the SaaS cluster does not. This is "CI for citations," and it's far less crowded than the consumer wedge.
3. **Epistemic humility (INCONCLUSIVE).** Competitors return a flat "Not Found" — the exact confidently-wrong failure. DeltaScience refuses to assert absence when retrieval was incomplete. No competitor surfaces coverage-honesty.
4. **Whole-paper PDF + author-year resolution (DataCite/Crossref).** Broader input handling than the paste-a-list checkers.

**Strategic read:** the scan empirically confirms the prior strategy discussion — the *verify-a-citation capability is commoditizing fast*. The defensible position is the **independent, auditable verification layer embedded where verification is forced** (CI, agent/MCP pipelines, journal/preprint checks), not the verification feature itself.
