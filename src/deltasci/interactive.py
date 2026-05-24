"""Interactive round-end gates.

After domain_r1 (framing) and domain_r2 (refinement), an `InteractionHandler`
is asked what to do with the round's output. Four actions are supported:

- approve     : continue to the next round
- redirect    : inject researcher feedback into the next round's context
- re_do       : regenerate this round (same prompt; may produce different content)
- audit_now   : run the citation auditor over the partial transcript so far
                and surface the result, then re-prompt the user

The default `TTYInteractionHandler` reads from stdin/stdout and is friendly
to a terminal user. Tests use `MockInteractionHandler` with a scripted action
sequence so no actual stdin/stdout is required.
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Literal

from deltasci.audit import AuditReport
from deltasci.transcript import RoundEntry, Transcript

InteractiveAction = Literal["approve", "redirect", "re_do", "audit_now"]
GATE_KINDS: frozenset[str] = frozenset({"domain_r1", "domain_r2"})


@dataclass
class ResearcherRedirect:
    after_round_kind: str
    feedback: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class InteractionDecision:
    action: InteractiveAction
    feedback: str = ""  # populated when action == "redirect"


class InteractionHandler(ABC):
    """Pluggable interactive gate. Engine calls `gate()` after gated rounds."""

    @abstractmethod
    def gate(self, kind: str, entry: RoundEntry, transcript: Transcript) -> InteractionDecision:
        ...

    def display_audit(self, audit: AuditReport) -> None:
        """Optional: implementations may override to render audit results."""


class NullInteractionHandler(InteractionHandler):
    """Always approves. Used when --interactive is not set."""

    def gate(self, kind: str, entry: RoundEntry, transcript: Transcript) -> InteractionDecision:
        return InteractionDecision(action="approve")


class MockInteractionHandler(InteractionHandler):
    """Test-friendly handler. Pops actions off a scripted queue."""

    def __init__(self, actions: list[InteractionDecision] | list[InteractiveAction]) -> None:
        self._queue: deque[InteractionDecision] = deque()
        for a in actions:
            if isinstance(a, str):
                self._queue.append(InteractionDecision(action=a))  # type: ignore[arg-type]
            else:
                self._queue.append(a)
        self.calls: list[tuple[str, RoundEntry]] = []
        self.audit_displays: list[AuditReport] = []

    def gate(self, kind: str, entry: RoundEntry, transcript: Transcript) -> InteractionDecision:
        self.calls.append((kind, entry))
        if not self._queue:
            return InteractionDecision(action="approve")
        return self._queue.popleft()

    def display_audit(self, audit: AuditReport) -> None:
        self.audit_displays.append(audit)


class TTYInteractionHandler(InteractionHandler):
    """Default interactive handler — prompts on stdin/stdout."""

    def __init__(
        self,
        input_fn: Callable[[str], str] = input,
        output_stream=sys.stdout,
    ) -> None:
        self._input = input_fn
        self._out = output_stream

    def _say(self, msg: str) -> None:
        self._out.write(msg + "\n")
        self._out.flush()

    def gate(self, kind: str, entry: RoundEntry, transcript: Transcript) -> InteractionDecision:
        # Show a digest of the round so the user can decide.
        self._say("")
        self._say(f"────────────  ROUND GATE: {kind}  ────────────")
        self._say(
            f"  {len(entry.evidence)} CLAIM(s) · "
            f"{len(entry.knowledge_gaps)} KNOWLEDGE_GAP(s) · "
            f"{len(entry.novel_syntheses)} NOVEL_SYNTHESIS(es)"
        )
        snippet = entry.text.strip()
        if len(snippet) > 600:
            snippet = snippet[:600] + " …(truncated; full round saved to transcript)"
        self._say("")
        self._say(snippet)
        self._say("")

        while True:
            self._say("Choose: [a]pprove   [r]edirect   [d]o-over   [u]dit-now   [q]uit")
            raw = self._input("> ").strip().lower()
            if raw in ("a", "approve", ""):
                return InteractionDecision(action="approve")
            if raw in ("d", "do-over", "redo", "re-do", "re_do"):
                return InteractionDecision(action="re_do")
            if raw in ("u", "audit", "audit-now", "audit_now"):
                return InteractionDecision(action="audit_now")
            if raw in ("r", "redirect"):
                self._say("Type your redirect feedback (single line):")
                feedback = self._input("> ").strip()
                if not feedback:
                    self._say("(empty feedback — treating as approve)")
                    return InteractionDecision(action="approve")
                return InteractionDecision(action="redirect", feedback=feedback)
            if raw in ("q", "quit"):
                raise KeyboardInterrupt("user quit during interactive gate")
            self._say(f"unknown option {raw!r}; try a / r / d / u / q")

    def display_audit(self, audit: AuditReport) -> None:
        self._say("")
        self._say(f"  audit-now: {audit.banner()}")
        if audit.mismatch_count:
            self._say("  Failed audits:")
            for f in audit.findings:
                if f.status != "mismatch":
                    continue
                self._say(f"    ✗ [{f.auditor_name}] {f.target_summary[:120]}")
                for r in f.mismatch_reasons[:2]:
                    self._say(f"        → {r}")
        self._say("")


def gate_eligible(round_kind: str) -> bool:
    return round_kind in GATE_KINDS
