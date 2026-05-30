---
name: deltasci-ground
description: >
  The grounding layer for AI-assisted research: scan the real prior art around an idea,
  gauge how crowded or open the gap is, and verify every citation against the source of
  truth. You (the agent) supply the discovery intelligence — writing search queries,
  judging relevance, reasoning about the gap — while the deterministic deltasci engine
  fetches real records and runs the citation checks. No LLM ever sits in the trust path:
  a citation is "verified" only when the engine says so, never from your memory. Use when
  a researcher wants to ground an idea, a related-work section, or a whole paper against
  the real literature — find the closest existing work, see where the genuine opening is,
  and catch fabricated / wrong-paper / unsupported citations.
---

# DeltaScience: The Grounding Layer (scan → gap → verify)

## Purpose

Ground an AI-assisted research idea or draft against the **real record**, in three moves:

1. **Scan** — find the closest existing work (prior art) across OpenAlex, arXiv, PubMed, GitHub.
2. **Gap** — judge whether that space is crowded, contested, or open, and name the distinguishing angle.
3. **Verify** — check every citation against the source of truth: does the identifier resolve, does the metadata match, does the cited paper actually support the claim?

## The one rule that governs everything: no LLM in the trust path

There are two kinds of work here, and they are *not* symmetric:

- **Discovery (scan, gap) is yours.** You are the LLM. Write the queries, judge which results are genuinely relevant, reason about where the gap is. A weak discovery pass can only make you *miss* a paper — it cannot make a false statement about what exists — so your judgement is welcome here.
- **Trust (verify) is the engine's.** A citation is real, and supports its claim, **only when `deltasci verify` says so.** Never assert from memory that a PMID/DOI is valid or that a paper supports a claim. The engine fetches the live record and decides deterministically. This is the entire point of the tool: the verdict must not depend on a model that can hallucinate agreement.

If you ever catch yourself about to write "this citation looks correct" without having run `deltasci verify`, stop and run it.

## Prerequisites

```bash
pip install deltasci          # core engine (keyless)
pip install 'deltasci[pdf]'   # add PDF support for whole-paper input
```

The engine is deterministic and needs **no API key**. All three commands emit `--json`.

## Inputs

| Input | How |
|-------|-----|
| A research idea / abstract | pass the text |
| A paper or draft PDF | pass the path with `--pdf` |
| A related-work snippet with citations | pass the text to `verify` |

## Procedure

### Step 1 — Frame the idea

Read the idea or the paper's title + abstract. Identify, in the field's *standard* vocabulary:
- the **problem** (e.g. "long-horizon sparse-reward credit assignment"),
- the **technique** (e.g. "group-based reinforcement learning for LLM agents"),
- the **application / domain**.

**Critical:** find the paper's own **coined names** — its method, system, or benchmark names (e.g. a made-up acronym like `SkillEvo`, `WebArena-Lite`) — and **set them aside. Never search for them.** No other work uses those terms, so they return nothing and poison a query. This is the single most common reason a scan finds "no prior art" for a hot area.

### Step 2 — SCAN: you write the queries, the engine fetches real records

Write 3–5 search queries, most-specific first, collectively covering problem + technique + application, using canonical terms and synonyms. Then issue them with the explicit-query primitive:

```bash
deltasci scan \
  --query "llm agent reinforcement learning skill" \
  --query "long-horizon sparse reward credit assignment" \
  --query "group relative policy optimization GRPO" \
  --json
```

- For a non-biomedical idea, drop PubMed: `--sources openalex,arxiv,github`.
- `--limit 20` for a wider net.

Every hit in the JSON is a **real, retrieved record** (title, authors, year, venue, url). Read them and **rerank by genuine relevance** — judge by *meaning*, not shared words. A paper that merely shares vocabulary but solves a different problem is not close. Do **not** invent or embellish any record; only use what the engine returned.

If `failed_sources` is non-empty, a corpus was slow/rate-limited — note it as a coverage gap (the run is incomplete, not empty).

### Step 3 — GAP: reason, grounded only in the retrieved works

From the real hits, classify the space:

- **CROWDED** — strong, direct prior art exists; the researcher should read it before building.
- **CONTESTED** — adjacent work exists; a distinguishing angle is needed.
- **OPEN** — little direct prior art.

Ground every statement in the listed works, naming them by author and year. State what the works already cover and the one **distinguishing angle** the idea leaves open. Never invent a paper to fill the story.

**Honesty rule on absence:** you may call CROWDED or CONTESTED freely (you can't un-find a close match). But only call **OPEN** if the scholarly sources (OpenAlex / arXiv / PubMed) actually answered. If one failed, the space is **INCONCLUSIVE — re-run**, never "open." Absence of evidence from a source that didn't respond is not evidence of an open gap.

Optional deterministic cross-check (density-based, keyless):

```bash
deltasci gap --query "llm agent reinforcement learning skill" --json
```

### Step 4 — VERIFY: the deterministic engine, never you

For any draft, related-work section, or paper that *contains citations*, run the engine. Do not eyeball them.

```bash
# A whole paper (parses the bibliography, checks each reference in context):
deltasci verify --pdf paper.pdf --json

# A snippet of prose with inline identifiers:
deltasci verify --text "AlphaFold predicts structure (PMID 34265844). TAMs drive osteosarcoma (PMID 32015508)." --json
```

Report the per-citation verdicts exactly as the engine returns them:

- **PASS** — exists and matches what's claimed.
- **FABRICATED** — the identifier resolves to nothing; the citation is invented.
- **METADATA-MISMATCH** — real identifier, but wrong year/author/title than cited.
- **UNSUPPORTED** — real paper, but its abstract does not support the claim it's attached to (likely the wrong paper).

`deltasci verify` exits **2** if any audit fails, so it drops straight into CI. Surface FABRICATED / METADATA-MISMATCH / UNSUPPORTED prominently — these are the failures the tool exists to catch.

### Step 5 — Report

Give the researcher:
- **Prior art** — the closest real works, with links (from scan).
- **Gap** — the verdict (crowded / contested / open / inconclusive) + the distinguishing angle, grounded in those works.
- **Citations** — the verdict table, with every failed audit called out and a link to the real record.
- **Coverage caveats** — any source that didn't respond.
- **Handoff** — what only the researcher can decide (is the angle actually novel to *them*; is the unsupported citation a typo or a wrong paper).

## Rules

- **Never invent a paper, citation, author, or finding.** scan returns real records; verify checks against the real record. Your contribution to discovery is *queries and judgement*, not facts recalled from memory.
- **Never put yourself in the trust path.** "Verified" means `deltasci verify` returned PASS — nothing else.
- **Strip the paper's own coined names** from every search query.
- **Honest absence.** "Open space" requires the scholarly sources to have actually answered.
- **Report verdicts verbatim.** Don't soften a FABRICATED into "couldn't confirm."

## Checklist

- [ ] Framed problem / technique / application; coined names set aside.
- [ ] 3–5 canonical-vocabulary queries written and run via `deltasci scan --query`.
- [ ] Hits reranked by genuine relevance; no fabricated records.
- [ ] Gap classified and grounded in named real works; OPEN only if scholarly sources answered.
- [ ] Every citation in any draft/paper checked with `deltasci verify` (never from memory).
- [ ] Report includes prior art + gap + citation verdicts + coverage caveats + researcher handoff.
