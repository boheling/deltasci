from __future__ import annotations

from deltasci.llm.base import LLMAdapter, Message

DEFAULT_MODEL = "claude-sonnet-4-6"


class AnthropicAdapter(LLMAdapter):
    """Adapter for the Anthropic Python SDK. Requires `pip install deltasci[anthropic]`."""

    def __init__(self, model: str | None = None) -> None:
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "The anthropic package is not installed. Install it with: pip install deltasci[anthropic]"
            ) from exc
        from anthropic import Anthropic

        self._client = Anthropic()
        self._model = model or DEFAULT_MODEL

    def complete(self, system: str, messages: list[Message], max_tokens: int = 2048) -> str:
        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=api_messages,
        )
        chunks = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        return "".join(chunks)

    def model_id(self) -> str:
        return self._model
