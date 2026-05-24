# Contributing to DeltaScience

Thanks for your interest in DeltaScience. We optimize for **small contributions that make the AI4Science community happier**: new domain packs, better grounding rules, better adapter coverage. We try to keep the engine itself stable.

## What we want most

1. **New domain packs** — neuroscience, particle physics, chemistry, ecology, genomics, fluid dynamics, social science, you name it. See [`docs/AUTHORING_DOMAIN_PACKS.md`](docs/AUTHORING_DOMAIN_PACKS.md).
2. **Real-world transcripts** — anonymized examples of running DeltaScience on a real lab idea. We add good ones to `docs/examples/`.
3. **Adapter improvements** — additional LLM backends (Ollama, vLLM, llama.cpp, Bedrock).
4. **Bug reports + fixes**.

## What we are cautious about

- Expanding the engine surface area. The core engine is intentionally small; new features need a strong reason.
- Scope creep into paper writing, experiment running, or literature search. DeltaScience handles ideation; we hand off to other tools downstream.
- Adding mandatory dependencies. New LLM providers go behind an `extras_require`.

## Development setup

```bash
git clone https://github.com/deltasci/deltasci
cd deltasci
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

`pytest` should pass without any LLM API keys (we use a mock adapter in tests).

## Style

- Python 3.10+ syntax (`X | Y` unions, `match` allowed).
- Type hints everywhere on public APIs.
- Pydantic v2 for all schemas.
- One short comment line max per surprising decision; nothing else.
- Tests use `MockLLM` — no live LLM calls in CI.

## Pull request checklist

- [ ] `pytest` passes.
- [ ] `ruff check src/ tests/` is clean.
- [ ] If adding a domain pack: `deltasci validate-pack ./src/deltasci/packs/<your-pack>` is OK.
- [ ] If adding a CLI flag or output file: README updated.
- [ ] Commit messages are descriptive (no AI co-author trailers).

## Adding a domain pack — short version

```bash
deltasci init-pack mydomain --path src/deltasci/packs/mydomain
# edit pack.toml + lens.md
deltasci validate-pack src/deltasci/packs/mydomain
deltasci demo --pack mydomain --llm mock --out /tmp/mydomain-demo
```

Then add `"mydomain"` to `BUILTIN_PACK_NAMES` in `src/deltasci/packs/__init__.py` and add a row to the README's pack table.

## Code of conduct

We follow a standard code of conduct: be kind, attack ideas not people, prioritize the experience of newcomers and underrepresented researchers. See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## License

By contributing, you agree your contributions are licensed under the MIT License.
