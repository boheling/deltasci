"""Tests for v0.2.1 interactive round-end gates."""

from __future__ import annotations

from io import StringIO

import pytest

from deltasci.config import Config
from deltasci.engine import CoReasoner
from deltasci.interactive import (
    InteractionDecision,
    MockInteractionHandler,
    NullInteractionHandler,
    TTYInteractionHandler,
    gate_eligible,
)
from deltasci.llm.mock import MockLLM


def test_gate_eligible_only_domain_rounds():
    assert gate_eligible("domain_r1")
    assert gate_eligible("domain_r2")
    assert not gate_eligible("engineer_r1")
    assert not gate_eligible("engineer_r2")
    assert not gate_eligible("synthesis")


def test_null_handler_always_approves():
    h = NullInteractionHandler()
    decision = h.gate(kind="domain_r1", entry=None, transcript=None)  # type: ignore[arg-type]
    assert decision.action == "approve"


def test_mock_handler_pops_actions():
    h = MockInteractionHandler(["approve", "redirect", "re_do"])
    assert h.gate("domain_r1", None, None).action == "approve"  # type: ignore[arg-type]
    redirect = h.gate("domain_r2", None, None)  # type: ignore[arg-type]
    assert redirect.action == "redirect"
    redo = h.gate("domain_r1", None, None)  # type: ignore[arg-type]
    assert redo.action == "re_do"


def test_mock_handler_with_explicit_decisions():
    h = MockInteractionHandler([
        InteractionDecision(action="redirect", feedback="please be more specific about cohort"),
    ])
    decision = h.gate("domain_r1", None, None)  # type: ignore[arg-type]
    assert decision.action == "redirect"
    assert "cohort" in decision.feedback


def test_engine_interactive_approve_runs_through(biomed_pack, scripted_round_responses, scripted_synthesis_response):
    """Interactive=True with all-approve handler is equivalent to non-interactive."""

    handler = MockInteractionHandler(["approve", "approve"])
    llm = MockLLM(responses=list(scripted_round_responses) + [scripted_synthesis_response])
    config = Config(
        num_rounds=4,
        interactive=True,
        audit_enabled=False,
        generate_protocol=False,
        generate_risks=False,
        run_challenge=False,
        auto_view=False,
    )
    reasoner = CoReasoner(pack=biomed_pack, llm=llm, config=config, interaction_handler=handler)
    result = reasoner.run(idea="Test idea")
    assert len(result.transcript.rounds) == 4
    # Two gates fired (after domain_r1 and domain_r2).
    assert len(handler.calls) == 2
    assert handler.calls[0][0] == "domain_r1"
    assert handler.calls[1][0] == "domain_r2"


def test_engine_interactive_redirect_persists_in_transcript(biomed_pack, scripted_round_responses, scripted_synthesis_response):
    """Redirect feedback is stored on the transcript and visible in render_markdown."""

    handler = MockInteractionHandler([
        InteractionDecision(action="redirect", feedback="Please address sample-size power explicitly."),
        InteractionDecision(action="approve"),
    ])
    llm = MockLLM(responses=list(scripted_round_responses) + [scripted_synthesis_response])
    config = Config(
        num_rounds=4,
        interactive=True,
        audit_enabled=False,
        generate_protocol=False,
        generate_risks=False,
        run_challenge=False,
        auto_view=False,
    )
    reasoner = CoReasoner(pack=biomed_pack, llm=llm, config=config, interaction_handler=handler)
    result = reasoner.run(idea="Test idea")

    assert len(result.transcript.redirects) == 1
    assert result.transcript.redirects[0].after_round_kind == "domain_r1"
    assert "sample-size power" in result.transcript.redirects[0].feedback
    rendered = result.transcript.render_markdown()
    assert "Researcher redirect" in rendered
    assert "sample-size power" in rendered


def test_engine_interactive_redo_consumes_extra_llm_response(biomed_pack, scripted_round_responses, scripted_synthesis_response):
    """re_do regenerates the round; engine consumes one more LLM response."""

    handler = MockInteractionHandler([
        InteractionDecision(action="re_do"),
        InteractionDecision(action="approve"),
        InteractionDecision(action="approve"),
    ])
    # Provide one extra round response for the re-do
    extra = '[CLAIM type=observation coverage=well-covered source=""]re-do response[/CLAIM] [KNOWLEDGE_GAP category=other]?[/KNOWLEDGE_GAP] [NOVEL_SYNTHESIS]x[/NOVEL_SYNTHESIS]'
    responses = (
        [scripted_round_responses[0], extra]  # original domain_r1, then re-do replacement
        + list(scripted_round_responses[1:])
        + [scripted_synthesis_response]
    )
    llm = MockLLM(responses=responses)
    config = Config(
        num_rounds=4,
        interactive=True,
        audit_enabled=False,
        generate_protocol=False,
        generate_risks=False,
        run_challenge=False,
        auto_view=False,
    )
    reasoner = CoReasoner(pack=biomed_pack, llm=llm, config=config, interaction_handler=handler)
    result = reasoner.run(idea="Test idea")
    # The first round in the transcript is the re-do replacement
    assert "re-do response" in result.transcript.rounds[0].text


def test_tty_handler_redirect_path():
    """TTY handler reads stdin for action + feedback."""

    out = StringIO()

    inputs = iter(["r", "Please cite a 2024+ paper for this claim"])

    def fake_input(prompt: str) -> str:
        return next(inputs)

    h = TTYInteractionHandler(input_fn=fake_input, output_stream=out)
    from deltasci.transcript import RoundEntry
    entry = RoundEntry(role="domain_scientist", kind="domain_r1", text="round text", evidence=[], knowledge_gaps=[], novel_syntheses=[])
    decision = h.gate(kind="domain_r1", entry=entry, transcript=None)  # type: ignore[arg-type]
    assert decision.action == "redirect"
    assert "2024+" in decision.feedback


def test_tty_handler_quit_raises():
    out = StringIO()
    inputs = iter(["q"])

    def fake_input(prompt: str) -> str:
        return next(inputs)

    h = TTYInteractionHandler(input_fn=fake_input, output_stream=out)
    from deltasci.transcript import RoundEntry
    entry = RoundEntry(role="domain_scientist", kind="domain_r1", text="round text", evidence=[], knowledge_gaps=[], novel_syntheses=[])
    with pytest.raises(KeyboardInterrupt):
        h.gate(kind="domain_r1", entry=entry, transcript=None)  # type: ignore[arg-type]
