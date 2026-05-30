from __future__ import annotations

import json
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Conversation, SavedReply
from app.settings_store import utc_now


def search_conversations(db: Session, query: str | None = None, target_id: int | None = None, limit: int = 30) -> list[Conversation]:
    stmt = select(Conversation)
    if target_id is not None:
        stmt = stmt.where(Conversation.target_id == target_id)
    cleaned_query = (query or "").strip()
    if cleaned_query:
        pattern = f"%{cleaned_query}%"
        stmt = stmt.where(
            or_(
                Conversation.input_text.like(pattern),
                Conversation.target_name.like(pattern),
                Conversation.selected_reply.like(pattern),
                Conversation.generated_replies.like(pattern),
            )
        )
    stmt = stmt.order_by(Conversation.updated_at.desc(), Conversation.id.desc()).limit(max(1, min(limit, 100)))
    return list(db.scalars(stmt).all())


def favorite_reply(
    db: Session,
    conversation_id: int,
    selected_reply: str | None = None,
    candidate_index: int | None = None,
    note: str | None = None,
) -> SavedReply:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise ValueError("Conversation not found")
    text = _resolve_reply_text(conversation, selected_reply, candidate_index)
    saved = SavedReply(
        conversation_id=conversation.id,
        target_id=conversation.target_id,
        candidate_index=candidate_index,
        text=text,
        note=_clean_optional(note),
        created_at=utc_now(),
    )
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return saved


def list_saved_replies(db: Session, query: str | None = None, target_id: int | None = None, limit: int = 30) -> list[SavedReply]:
    stmt = select(SavedReply)
    if target_id is not None:
        stmt = stmt.where(SavedReply.target_id == target_id)
    cleaned_query = (query or "").strip()
    if cleaned_query:
        pattern = f"%{cleaned_query}%"
        stmt = stmt.where(or_(SavedReply.text.like(pattern), SavedReply.note.like(pattern)))
    stmt = stmt.order_by(SavedReply.created_at.desc(), SavedReply.id.desc()).limit(max(1, min(limit, 100)))
    return list(db.scalars(stmt).all())


def delete_saved_reply(db: Session, saved_reply_id: int) -> None:
    saved = db.get(SavedReply, saved_reply_id)
    if saved is None:
        raise ValueError("Saved reply not found")
    db.delete(saved)
    db.commit()


def _resolve_reply_text(conversation: Conversation, selected_reply: str | None, candidate_index: int | None) -> str:
    if selected_reply is not None and selected_reply.strip():
        return selected_reply.strip()
    replies = _load_replies(conversation.generated_replies)
    if candidate_index is not None:
        if candidate_index < 0 or candidate_index >= len(replies):
            raise ValueError("candidate_index is out of range")
        return str(replies[candidate_index]).strip()
    if conversation.selected_reply and conversation.selected_reply.strip():
        return conversation.selected_reply.strip()
    if replies:
        return str(replies[0]).strip()
    raise ValueError("No reply text available to favorite")


def _load_replies(value: str | None) -> list[Any]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
