from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

Role = Literal["user", "assistant"]


@dataclass
class Message:
    role: Role
    content: str


class LLMAdapter(ABC):
    """Minimal LLM interface DeltaScience depends on.

    Adapters must implement `complete()` and `model_id()`. Everything else
    (retries, streaming, tool use) is out of scope for v0.
    """

    @abstractmethod
    def complete(self, system: str, messages: list[Message], max_tokens: int = 2048) -> str:
        ...

    @abstractmethod
    def model_id(self) -> str:
        ...

    @property
    def provider_name(self) -> str:
        return self.__class__.__name__.replace("Adapter", "").lower()
