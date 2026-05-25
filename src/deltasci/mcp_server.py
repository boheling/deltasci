"""MCP server exposing DeltaScience's evidence verifier as a tool.

This is the distribution play: any MCP client — Claude Code / Desktop, Cursor, or an
AI-scientist pipeline like Sakana AI-Scientist or AutoResearchClaw — can verify the
citations in generated text *without forking DeltaScience*. It rides on top of the
incumbents instead of competing with them.

Install:  pip install "deltasci[mcp]"
Run:      deltasci-mcp            # stdio transport

Register with Claude Code, e.g.:
    claude mcp add deltasci-verify -- deltasci-mcp
"""

from __future__ import annotations

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError as exc:  # pragma: no cover - exercised only without the extra
    raise SystemExit(
        "deltasci-mcp requires the MCP SDK, which is not installed.\n"
        'Install it with:  pip install "deltasci[mcp]"'
    ) from exc

from deltasci.verify import verify_payload, verify_text

mcp = FastMCP("deltasci-verify")


@mcp.tool()
def verify_scientific_claims(text: str, format: str = "auto", check_support: bool = True) -> dict:
    """Verify the citations/claims in scientific text against the real literature record.

    For each cited PMID / DOI / arXiv / GitHub identifier, checks: does it exist, does its
    metadata match what's claimed, and (when check_support) does the cited paper actually
    support the sentence it's attached to? Returns a per-claim verdict — PASS, FABRICATED,
    METADATA-MISMATCH, UNSUPPORTED, UNVERIFIABLE, or SKIPPED — plus verdict counts and a
    one-line summary. First-pass checks are deterministic (real API lookups + string
    comparison), so a verdict of FABRICATED means the identifier genuinely did not resolve.

    Use this before trusting an LLM-generated related-work section, hypothesis, or
    experiment plan — it catches hallucinated citations and "right-existence, wrong-paper"
    miscitations (the failure mode that has plagued autonomous AI-scientist pipelines).

    Args:
        text: Scientific text to verify — prose with inline citations, DeltaScience
            ``[CLAIM ... source="..."]`` tags, a JSON ``[{"claim","source"}]`` array, or BibTeX.
        format: Input format: "auto" (default, sniffs it), "tagged", "text", "records", or "bibtex".
        check_support: If true (default), also run the deterministic claim-to-abstract
            support check (PubMed). Set false for existence + metadata checks only.

    Returns:
        ``{"summary": str, "verdicts": {verdict: count}, "findings": [{...,"verdict": str}]}``.
    """

    return verify_payload(verify_text(text, fmt=format, check_support=check_support))


def main() -> None:
    """Console entry point: run the server over stdio."""

    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
