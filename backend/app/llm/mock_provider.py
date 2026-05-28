from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.llm.base import LLMChunk, LLMMessage, LLMProvider, LLMResponse


class MockProvider(LLMProvider):
    def __init__(self, provider_id: str = "mock", model: str = "mock-chat") -> None:
        self.provider_id = provider_id
        self.model = model

    async def complete(self, messages: list[LLMMessage], **opts: object) -> LLMResponse:
        user_text = next((message.content for message in reversed(messages) if message.role == "user"), "")
        text = f"mock reply: {user_text}" if user_text else "mock reply"
        return LLMResponse(text=text, prompt_tokens=len(messages), completion_tokens=len(text.split()), total_tokens=len(messages) + len(text.split()))

    async def stream(self, messages: list[LLMMessage], **opts: object) -> AsyncIterator[LLMChunk]:
        response = await self.complete(messages, **opts)
        for token in response.text.split(" "):
            yield LLMChunk(delta=f"{token} ")
            await asyncio.sleep(0)
