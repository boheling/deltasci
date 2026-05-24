from __future__ import annotations

import json
import re
from collections import deque
from typing import Callable

from deltasci.llm.base import LLMAdapter, Message


class MockLLM(LLMAdapter):
    """Test/demo adapter that returns canned responses.

    Two scripting modes:

    * `MockLLM(responses=["a", "b", ...])` — pop one response per `complete()` call.
    * `MockLLM(responder=fn)` — `fn(system, messages)` returns a string per call.

    If neither is provided, returns a generic, well-grounded stub useful for
    smoke tests of the engine pipeline.
    """

    def __init__(
        self,
        responses: list[str] | None = None,
        responder: Callable[[str, list[Message]], str] | None = None,
        model: str = "mock-llm-v1",
    ) -> None:
        self._queue: deque[str] = deque(responses or [])
        self._responder = responder
        self._model = model
        self.calls: list[tuple[str, list[Message]]] = []

    def complete(self, system: str, messages: list[Message], max_tokens: int = 2048) -> str:
        self.calls.append((system, list(messages)))
        if self._responder is not None:
            return self._responder(system, messages)
        if self._queue:
            return self._queue.popleft()
        return _default_grounded_stub(system, messages)

    def model_id(self) -> str:
        return self._model


_AXES_LINE_RE = re.compile(r"Rubric axes for this domain pack:\s*(.+)")


def _default_grounded_stub(system: str, messages: list[Message]) -> str:
    """A boring but well-formed response with valid CLAIM tags, useful for smoke tests.

    For synthesis calls, the stub dynamically emits one score per rubric axis
    mentioned in the system prompt, so it works with any domain pack out of the box.
    """

    # Synthesis system prompts start with "You are the synthesis step ..." — match
    # on that exact phrase rather than the substring "synthesis", because the role
    # prompts now mention NOVEL_SYNTHESIS as one of the allowed tags.
    if "synthesis step" in system.lower():
        return _build_synthesis_stub(system)
    return _ROUND_STUB


def _build_synthesis_stub(system: str) -> str:
    match = _AXES_LINE_RE.search(system)
    axes_str = match.group(1).strip() if match else "data_availability, technical_feasibility, novelty"
    axes = [a.strip() for a in axes_str.split(",") if a.strip()]
    payload = {
        "title": "Mock grounded hypothesis",
        "statement": "Mock hypothesis statement that ties domain mechanism to a learnable representation and predicts a measurable improvement over baseline.",
        "domain_grounding": {
            "mechanism": "Mock mechanism summary.",
            "unmet_need": "Mock unmet need.",
            "expected_impact": "Mock expected impact.",
        },
        "technical_approach": {
            "core_method": "Mock method.",
            "key_innovation": "Mock innovation.",
            "implementation_path": "Mock implementation steps.",
        },
        "falsifiability": {
            "prediction": "Mock model achieves measurable improvement on the held-out test set.",
            "threshold": "Primary metric exceeds baseline by >= 0.05 absolute on the external cohort.",
            "null_outcome": "Primary metric within 0.01 of baseline falsifies the hypothesis.",
        },
        "feasibility_scores": {axis: 4 for axis in axes},
        "feasibility_justifications": {axis: f"Mock justification for {axis}." for axis in axes},
    }
    return json.dumps(payload, indent=2)


_ROUND_STUB = """
This is a mock co-reasoning round.

[CLAIM type=published-evidence coverage=well-covered source="Doe et al 2024, Nature 600:123"]The proposed mechanism has prior support in the literature.[/CLAIM]

[CLAIM type=engineering-precedent coverage=well-covered source="github.com/example/repo"]A reference implementation of a similar approach exists.[/CLAIM]

[CLAIM type=observation coverage=sparse source=""]Recent specific quantitative numbers for this exact setup are uncertain.[/CLAIM]

[KNOWLEDGE_GAP category=unpublished-or-pilot-data]Does the lab have pilot data on the specific subgroup being modeled, and what was the effect size?[/KNOWLEDGE_GAP]

[NOVEL_SYNTHESIS rationale="combines two well-covered facts in a way no single source explicitly states"]The proposed connection between the domain mechanism and the chosen learnable representation has not been written up explicitly.[/NOVEL_SYNTHESIS]
""".strip()
