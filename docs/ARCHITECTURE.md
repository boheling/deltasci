# Architecture

DeltaScience is small on purpose. The whole engine is a few hundred lines of Python; everything else is configuration (domain packs) or delivery (CLI / skill bundle).

## Module map

```
src/deltasci/
├── __init__.py          public exports
├── __main__.py          python -m deltasci entry point
├── cli.py               argparse CLI
├── config.py            Config dataclass with env-var resolution
├── engine.py            CoReasoner orchestrator
├── roles.py             DomainScientist + MLEngineer role classes
├── transcript.py        Transcript + RoundEntry dataclasses
├── grounding.py         CLAIM tag extraction + violation detection
├── synthesis.py         transcript -> GroundedHypothesis
├── hypothesis.py        Pydantic schemas
├── llm/
│   ├── base.py          LLMAdapter abstract base
│   ├── anthropic.py     Anthropic SDK adapter
│   ├── openai.py        OpenAI SDK adapter
│   └── mock.py          deterministic test adapter
└── packs/
    ├── __init__.py      DomainPack loader (TOML + MD)
    ├── biomed/
    ├── materials/
    └── climate/
```

## Engine flow

```
CoReasoner.run(idea)
    │
    ├─ for each round in [domain_r1, engineer_r1, domain_r2, engineer_r2]:
    │       role = role_for_round(kind, llm, pack)
    │       output = role.run(kind, idea, transcript)
    │       report = grounding.extract_claims(output.text)
    │       grounding.check_against_rules(report, pack.evidence_rules)
    │       if violations and strictness=high:
    │           output = role.repair(output.text, violations_msg)
    │           ... re-extract & re-check ...
    │       transcript.append(round_entry, report)
    │
    ├─ hypothesis = synthesis.assemble(transcript, pack, llm)
    │       └─ if no falsifiability clause and require_falsifiability:
    │              raise SynthesisError
    │
    └─ return Result(transcript, hypothesis, grounding_summary)
```

## Key types

### `GroundedHypothesis` (Pydantic)

```
title: str
statement: str
domain_grounding: dict[str, str]       # mechanism, unmet_need, expected_impact
technical_approach: dict[str, str]     # core_method, key_innovation, implementation_path
evidence_trail: list[EvidenceItem]
falsifiability: FalsifiabilityClause   # required, not optional
feasibility_scores: FeasibilityScores
metadata: HypothesisMetadata
```

### `FalsifiabilityClause`

```
prediction: str
threshold: str       # MUST be measurable
null_outcome: str    # what observation would falsify the hypothesis
```

This is a hard schema requirement — a hypothesis without a falsifiability clause is not emitted.

### `EvidenceItem`

```
claim: str
type: "published-evidence" | "established-guideline" | "engineering-precedent" | "observation"
source: str          # required for the first three types
```

### `DomainPack`

```
name: str
display_name: str
version: str
description: str
lens: str                      # the markdown lens, raw
evidence_rules: list[dict]     # per-type source patterns
scoring_rubric: ScoringRubric  # axes + weights
example_idea: str
```

## Grounding tag format

Every factual claim in a role output must be wrapped:

```
[CLAIM type=<TYPE> source="<CITATION>"]<the claim>[/CLAIM]
```

Parsed by a single regex in `grounding.py`. Untagged factual claims are ignored by the evidence trail (so the model is incentivized to tag everything).

## LLM adapter interface

```python
class LLMAdapter(ABC):
    def complete(self, system: str, messages: list[Message], max_tokens: int = 2048) -> str: ...
    def model_id(self) -> str: ...
```

Three concrete implementations. The mock adapter is the default in tests; the user picks `anthropic` or `openai` (or `auto`) for real runs.

## What the architecture deliberately leaves out

- **No agent framework.** No tools, no multi-step planning. The 4 rounds are a fixed program.
- **No retrieval.** If you want literature retrieval, run it yourself and pass results in via the idea text or context dir.
- **No streaming.** Each round is a single completion call.
- **No multi-LLM dialogues.** Both roles use the same adapter (a single LLM playing two roles, separated by system prompts). Multi-LLM ensembles are an obvious extension; not in v0.
- **No telemetry.** Local-first.

## Extension points

If you want to extend DeltaScience without touching the engine:

| To add | Where |
|--------|-------|
| A new domain | a `DomainPack` directory |
| A new LLM provider | a new module in `src/deltasci/llm/`, register in `llm/__init__.py` |
| A new evidence type | extend `EvidenceType` in `hypothesis.py` and update `grounding.VALID_TYPES` |
| A custom output format | wrap `Result` in your own renderer; the JSON is stable |
