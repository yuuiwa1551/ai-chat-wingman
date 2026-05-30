from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMChunk:
    delta: str


@dataclass(frozen=True)
class LLMResponse:
    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMProvider(ABC):
    provider_id: str
    model: str

    async def list_models(self) -> list[str]:
        return [self.model]

    @abstractmethod
    async def complete(self, messages: list[LLMMessage], **opts: object) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    async def stream(self, messages: list[LLMMessage], **opts: object) -> AsyncIterator[LLMChunk]:
        raise NotImplementedError

    async def complete_multimodal(self, messages_with_images: list[dict[str, object]], **opts: object) -> LLMResponse:
        raise NotImplementedError("Multimodal completion is not implemented for this provider")
