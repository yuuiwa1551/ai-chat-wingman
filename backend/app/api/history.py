from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.history_service import delete_saved_reply, favorite_reply, list_saved_replies, search_conversations

router = APIRouter(prefix="/history", tags=["history"])


class FavoriteReplyRequest(BaseModel):
    selected_reply: str | None = Field(default=None, max_length=4000)
    candidate_index: int | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=800)


@router.get("/conversations")
def read_conversations(
    query: str | None = Query(default=None, max_length=200),
    target_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    return {"conversations": [conversation.to_dict() for conversation in search_conversations(db, query, target_id, limit)]}


@router.post("/conversations/{conversation_id}/favorite")
def save_favorite_reply(conversation_id: int, payload: FavoriteReplyRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        saved = favorite_reply(db, conversation_id, payload.selected_reply, payload.candidate_index, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"saved_reply": saved.to_dict()}


@router.get("/favorites")
def read_saved_replies(
    query: str | None = Query(default=None, max_length=200),
    target_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    return {"saved_replies": [saved.to_dict() for saved in list_saved_replies(db, query, target_id, limit)]}


@router.delete("/favorites/{saved_reply_id}")
def delete_favorite_reply(saved_reply_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    try:
        delete_saved_reply(db, saved_reply_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}
