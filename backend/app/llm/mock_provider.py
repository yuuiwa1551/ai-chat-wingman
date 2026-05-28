from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json

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

    async def complete_multimodal(self, messages_with_images: list[dict[str, object]], **opts: object) -> LLMResponse:
        text = json.dumps(
            {
                "messages": [
                    {
                        "speaker": "target",
                        "content": "I am exhausted today and do not really want to talk.",
                        "time": "unknown",
                    }
                ],
                "summary": "The target sounds tired and may prefer a low-pressure reply.",
                "uncertain_parts": ["Mock provider did not inspect the actual image."],
            },
            ensure_ascii=False,
        )
        return LLMResponse(text=text, prompt_tokens=len(messages_with_images), completion_tokens=len(text.split()), total_tokens=len(messages_with_images) + len(text.split()))
