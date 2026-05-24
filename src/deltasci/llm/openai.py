from __future__ import annotations

from deltasci.llm.base import LLMAdapter, Message

DEFAULT_MODEL = "gpt-4o"


class OpenAIAdapter(LLMAdapter):
    """Adapter for the OpenAI Python SDK. Requires `pip install deltasci[openai]`."""

    def __init__(self, model: str | None = None) -> None:
        try:
            import openai  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "The openai package is not installed. Install it with: pip install deltasci[openai]"
            ) from exc
        from openai import OpenAI

        self._client = OpenAI()
        self._model = model or DEFAULT_MODEL

    def complete(self, system: str, messages: list[Message], max_tokens: int = 2048) -> str:
        api_messages = [{"role": "system", "content": system}]
        api_messages.extend({"role": m.role, "content": m.content} for m in messages)
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=api_messages,
        )
        return response.choices[0].message.content or ""

    def model_id(self) -> str:
        return self._model
