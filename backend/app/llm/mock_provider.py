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
        system_text = next((message.content for message in messages if message.role == "system"), "")
        if "长期记忆提取器" in system_text:
            text = self._mock_memory_extraction(user_text)
        else:
            text = f"mock reply: {user_text}" if user_text else "mock reply"
        return LLMResponse(text=text, prompt_tokens=len(messages), completion_tokens=len(text.split()), total_tokens=len(messages) + len(text.split()))

    async def stream(self, messages: list[LLMMessage], **opts: object) -> AsyncIterator[LLMChunk]:
        response = await self.complete(messages, **opts)
        for token in response.text.split(" "):
            yield LLMChunk(delta=f"{token} ")
            await asyncio.sleep(0)

    @staticmethod
    def _mock_memory_extraction(user_text: str) -> str:
        if not user_text.strip():
            return "[]"
        return json.dumps(
            [
                {
                    "memory_type": "preference",
                    "content": "Mock extracted: target prefers low-pressure replies when feeling tired.",
                    "confidence": 0.6,
                }
            ],
            ensure_ascii=False,
        )

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
