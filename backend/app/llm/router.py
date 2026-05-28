from __future__ import annotations

from sqlalchemy.orm import Session

from app.llm.base import LLMMessage, LLMProvider
from app.llm.call_logger import log_async_call
from app.llm.mock_provider import MockProvider
from app.llm.openai_compatible_provider import OpenAICompatibleProvider


def provider_from_config(config: dict[str, object]) -> LLMProvider:
    provider_type = str(config.get("type") or "mock")
    provider_id = str(config.get("id") or provider_type)
    model = str(config.get("default_model") or "mock-chat")

    if provider_type == "mock":
        return MockProvider(provider_id=provider_id, model=model)

    if provider_type == "openai_compatible":
        base_url = config.get("base_url")
        api_key = config.get("api_key")
        if not isinstance(base_url, str) or not base_url:
            raise ValueError("OpenAI compatible provider requires base_url")
        if not isinstance(api_key, str) or not api_key:
            raise ValueError("OpenAI compatible provider requires api_key")
        return OpenAICompatibleProvider(provider_id=provider_id, base_url=base_url, api_key=api_key, model=model)

    raise ValueError(f"Unsupported provider type: {provider_type}")


async def test_provider(db: Session, provider_config: dict[str, object]) -> dict[str, object]:
    provider = provider_from_config(provider_config)
    messages = [LLMMessage(role="user", content="ping")]

    async def run_call():
        return await provider.complete(messages)

    response, llm_call = await log_async_call(
        db=db,
        task="provider_test",
        provider=provider.provider_id,
        model=provider.model,
        request_summary="provider connectivity test",
        call=run_call,
    )
    return {"ok": True, "text": response.text, "llm_call_id": llm_call.id}
