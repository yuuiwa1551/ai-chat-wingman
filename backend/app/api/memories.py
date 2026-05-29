from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.memory_service import (
    approve_memory,
    create_memory,
    delete_memory,
    extract_memories_from_text,
    list_memories,
    reject_memory,
    update_memory,
)
from app.services.target_service import get_target

router = APIRouter(tags=["memories"])


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    memory_type: str | None = Field(default=None, max_length=40)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    status: str = Field(default="pending", max_length=20)
    source_conversation_id: int | None = None


class MemoryPatch(BaseModel):
    content: str | None = Field(default=None, max_length=2000)
    memory_type: str | None = Field(default=None, max_length=40)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: str | None = Field(default=None, max_length=20)


class MemoryExtractRequest(BaseModel):
    chat_text: str = Field(min_length=1, max_length=12000)
    source_conversation_id: int | None = None


@router.get("/targets/{target_id}/memories")
def read_target_memories(
    target_id: int,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    try:
        get_target(db, target_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    memories = list_memories(db, target_id=target_id, status=status)
    return {"memories": [memory.to_dict() for memory in memories]}


@router.post("/targets/{target_id}/memories")
def create_target_memory(target_id: int, payload: MemoryCreate, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        get_target(db, target_id)
        memory = create_memory(db, target_id=target_id, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"memory": memory.to_dict()}


@router.post("/targets/{target_id}/memories/extract")
async def extract_target_memories(target_id: int, payload: MemoryExtractRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        get_target(db, target_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    memories = await extract_memories_from_text(
        db,
        target_id=target_id,
        conversation_text=payload.chat_text,
        source_conversation_id=payload.source_conversation_id,
    )
    return {"memories": [memory.to_dict() for memory in memories]}


@router.put("/memories/{memory_id}")
def edit_memory(memory_id: int, payload: MemoryPatch, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        memory = update_memory(db, memory_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"memory": memory.to_dict()}


@router.delete("/memories/{memory_id}")
def remove_memory(memory_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    try:
        delete_memory(db, memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/memories/{memory_id}/approve")
def approve_memory_endpoint(memory_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        memory = approve_memory(db, memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"memory": memory.to_dict()}


@router.post("/memories/{memory_id}/reject")
def reject_memory_endpoint(memory_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        memory = reject_memory(db, memory_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"memory": memory.to_dict()}
