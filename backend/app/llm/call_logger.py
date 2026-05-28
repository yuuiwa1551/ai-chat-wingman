from __future__ import annotations

from time import perf_counter
from typing import Callable, TypeVar

from sqlalchemy.orm import Session

from app.db.models import LLMCall
from app.settings_store import utc_now

T = TypeVar("T")


async def log_async_call(
    db: Session,
    task: str,
    provider: str,
    model: str,
    request_summary: str,
    call: Callable[[], T],
) -> tuple[T, LLMCall]:
    started = perf_counter()
    try:
        result = await call()
    except Exception as exc:
        llm_call = LLMCall(
            task=task,
            provider=provider,
            model=model,
            request_summary=request_summary,
            status="error",
            error_message=str(exc),
            latency_ms=int((perf_counter() - started) * 1000),
            created_at=utc_now(),
        )
        db.add(llm_call)
        db.commit()
        raise

    llm_call = LLMCall(
        task=task,
        provider=provider,
        model=model,
        request_summary=request_summary,
        response_summary=getattr(result, "text", None),
        prompt_tokens=getattr(result, "prompt_tokens", None),
        completion_tokens=getattr(result, "completion_tokens", None),
        total_tokens=getattr(result, "total_tokens", None),
        cost_usd=0.0,
        latency_ms=int((perf_counter() - started) * 1000),
        status="ok",
        created_at=utc_now(),
    )
    db.add(llm_call)
    db.commit()
    db.refresh(llm_call)
    return result, llm_call
