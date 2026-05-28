from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.sse import encode_sse, sse_response

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/sse")
def demo_sse() -> StreamingResponse:
    async def events() -> AsyncIterator[str]:
        for token in ("AI", " Chat", " Wingman"):
            yield encode_sse("token", {"delta": token})
            await asyncio.sleep(0.01)
        yield encode_sse("done", {"text": "AI Chat Wingman"})

    return sse_response(events())
