from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.sse import encode_sse, sse_response
from app.db.database import get_db
from app.services.memory_service import extract_memories_from_text
from app.services.reply_service import (
    ReplyGenerationRequest,
    fail_reply_generation,
    finish_reply_generation,
    select_reply,
    start_reply_generation,
    stream_reply_candidates,
)

router = APIRouter(prefix="/reply", tags=["reply"])


class GenerateReplyRequest(BaseModel):
    chat_text: str = Field(min_length=1, max_length=12000)
    target_id: int | None = None
    target_name: str | None = Field(default=None, max_length=80)
    target_strategy: str | None = Field(default=None, max_length=1000)
    reply_goal: str = Field(default="继续自然聊天", max_length=80)
    tone: str = Field(default="自然", max_length=40)
    length: str = Field(default="中等", max_length=40)
    proactivity: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_level: str = Field(default="稳妥", max_length=40)
    candidate_count: int = Field(default=3, ge=1, le=5)
    session_id: int | None = None


class SelectReplyRequest(BaseModel):
    selected_reply: str | None = Field(default=None, max_length=4000)
    selected_index: int | None = Field(default=None, ge=0)


@router.post("/generate")
async def generate_reply(payload: GenerateReplyRequest, db: Session = Depends(get_db)):
    request = ReplyGenerationRequest(**payload.model_dump())
    try:
        conversation, provider, profile, target, memories_prompt = start_reply_generation(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def events() -> AsyncIterator[str]:
        replies_by_index: dict[int, str] = {}
        yield encode_sse(
            "conversation",
            {
                "conversation_id": conversation.id,
                "prompt_version": conversation.prompt_version,
            },
        )
        try:
            async for candidate in stream_reply_candidates(provider, request, profile, target, memories_prompt):
                previous = replies_by_index.get(candidate.index, "")
                delta = candidate.text.removeprefix(previous)
                replies_by_index[candidate.index] = candidate.text
                if delta:
                    yield encode_sse("token", {"index": candidate.index, "delta": delta})
            replies = [replies_by_index[index].strip() for index in sorted(replies_by_index)]
            llm_call = finish_reply_generation(db, conversation, provider, request, replies)
            for index, text in enumerate(replies):
                yield encode_sse("candidate", {"index": index, "text": text})
            yield encode_sse(
                "done",
                {
                    "conversation_id": conversation.id,
                    "llm_call_id": llm_call.id,
                    "prompt_version": conversation.prompt_version,
                    "replies": replies,
                },
            )
            if target is not None:
                try:
                    await extract_memories_from_text(
                        db,
                        target_id=target.id,
                        conversation_text=request.chat_text,
                        source_conversation_id=conversation.id,
                    )
                except Exception:  # noqa: BLE001 - memory extraction must not break replies
                    pass
        except Exception as exc:
            llm_call = fail_reply_generation(db, conversation, provider, request, str(exc))
            yield encode_sse("error", {"message": str(exc), "llm_call_id": llm_call.id})

    return sse_response(events())


@router.post("/{conversation_id}/select")
def save_selected_reply(conversation_id: int, payload: SelectReplyRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        conversation = select_reply(db, conversation_id, payload.selected_reply, payload.selected_index)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"conversation": conversation.to_dict()}