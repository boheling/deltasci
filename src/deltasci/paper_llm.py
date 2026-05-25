"""LLM fallback for whole-paper citation extraction.

The deterministic parser handles numbered bibliographies. When a paper uses author-year
citations (``(Smith et al., 2020)``) or a bibliography the regex can't segment, this asks
an LLM to do the *structuring* only: for each in-text citation, return the claim sentence
and the cited work's best identifier or reference string.

The actual **verification stays deterministic** — the LLM never decides whether a citation
is valid; deltasci still checks every returned identifier against the real record. The LLM
is also told never to invent identifiers (the one thing it must not hallucinate here).

Used only when a provider adapter is supplied AND deterministic parsing came up short.
"""

from __future__ import annotations

import json
import re

from deltasci.audit.intake import Claim
from deltasci.llm.base import LLMAdapter, Message

_SYSTEM = (
    "You extract citations from scientific papers for a verification tool. You connect each "
    "in-text citation to its entry in the reference list and report the claim it supports. "
    "You NEVER invent identifiers: only copy a DOI/PMID/arXiv id if it literally appears in "
    "the reference list; otherwise give the reference's authors, year and title verbatim."
)

_PROMPT = """\
Below is the text of a scientific paper (possibly truncated). For every in-text citation,
output one JSON object with:
  - "claim": the sentence (or clause) in the body that the citation supports, verbatim.
  - "source": the cited work's identifier taken from the reference list — prefer a DOI,
    PMID, or arXiv id if one is present in that reference; otherwise the reference's
    "Author(s) Year Title Venue" text. Copy it; never fabricate an identifier.

Resolve author-year and numbered markers to the actual reference entry at the bottom.
Return ONLY a JSON array, no prose. Example:
[{{"claim": "Transformers rely on self-attention.", "source": "Vaswani et al. 2017. Attention Is All You Need. arXiv:1706.03762"}}]

PAPER:
{text}
"""


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    head = (max_chars * 2) // 3
    tail = max_chars - head
    # Keep the intro AND the reference list (which lives at the end).
    return text[:head] + "\n…\n" + text[-tail:]


def _parse_json_array(raw: str) -> list:
    raw = raw.strip()
    # Strip ```json fences if present, then grab the first [...] block.
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
    match = re.search(r"\[.*\]", raw, flags=re.DOTALL)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def llm_extract_citations(text: str, llm: LLMAdapter, max_chars: int = 24000) -> list[Claim]:
    """Ask `llm` to extract (claim, source) pairs for every in-text citation."""

    prompt = _PROMPT.format(text=_truncate(text, max_chars))
    raw = llm.complete(system=_SYSTEM, messages=[Message(role="user", content=prompt)], max_tokens=4000)
    claims: list[Claim] = []
    for item in _parse_json_array(raw):
        if not isinstance(item, dict):
            continue
        claim = str(item.get("claim", "")).strip()
        source = str(item.get("source", "")).strip()
        if claim and source:
            claims.append(Claim(claim=claim, source=source))
    return claims


__all__ = ["llm_extract_citations"]
