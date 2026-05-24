from __future__ import annotations

from deltasci.llm.base import LLMAdapter, Message
from deltasci.llm.mock import MockLLM


def get_adapter(provider: str = "auto", model: str | None = None) -> LLMAdapter:
    """Resolve a provider name to an adapter instance.

    Provider precedence when `provider="auto"`:
    1. ANTHROPIC_API_KEY -> anthropic
    2. OPENAI_API_KEY    -> openai
    3. raise informative error
    """

    import os

    if provider == "auto":
        if os.environ.get("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.environ.get("OPENAI_API_KEY"):
            provider = "openai"
        else:
            raise RuntimeError(
                "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
                "or pass --llm anthropic|openai|mock explicitly."
            )

    if provider == "mock":
        return MockLLM()
    if provider == "anthropic":
        from deltasci.llm.anthropic import AnthropicAdapter

        return AnthropicAdapter(model=model)
    if provider == "openai":
        from deltasci.llm.openai import OpenAIAdapter

        return OpenAIAdapter(model=model)
    raise ValueError(f"Unknown LLM provider: {provider!r}. Expected: anthropic, openai, mock, auto.")


__all__ = ["LLMAdapter", "Message", "MockLLM", "get_adapter"]
