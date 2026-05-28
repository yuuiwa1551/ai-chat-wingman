from __future__ import annotations

from collections.abc import AsyncIterator

import json

import httpx

from app.llm.base import LLMChunk, LLMMessage, LLMProvider, LLMResponse


class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, provider_id: str, base_url: str, api_key: str, model: str) -> None:
        self.provider_id = provider_id
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    async def complete(self, messages: list[LLMMessage], **opts: object) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "stream": False,
            **opts,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        usage = body.get("usage") or {}
        text = body["choices"][0]["message"]["content"]
        return LLMResponse(
            text=text,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )

    async def stream(self, messages: list[LLMMessage], **opts: object) -> AsyncIterator[LLMChunk]:
        payload = {
            "model": self.model,
            "messages": [message.__dict__ for message in messages],
            "stream": True,
            **opts,
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ").strip()
                    if data == "[DONE]":
                        break
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                    if delta:
                        yield LLMChunk(delta=delta)

    async def complete_multimodal(self, messages_with_images: list[dict[str, object]], **opts: object) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages_with_images,
            "stream": False,
            **opts,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            response.raise_for_status()
        body = response.json()
        usage = body.get("usage") or {}
        text = body["choices"][0]["message"]["content"]
        return LLMResponse(
            text=text,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
        )
