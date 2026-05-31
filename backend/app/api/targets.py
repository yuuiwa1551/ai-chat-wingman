from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.jobs.runner import create_job, run_organize_target_job
from app.services.target_service import create_target, delete_target, get_target, list_targets, update_target

router = APIRouter(prefix="/targets", tags=["targets"])


class ChatTargetPayload(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    relationship: str | None = Field(default=None, max_length=120)
    style_summary: str | None = Field(default=None, max_length=1200)
    preferences: str | None = Field(default=None, max_length=1600)
    taboos: str | None = Field(default=None, max_length=1600)
    strategy_guideline: str | None = Field(default=None, max_length=1600)


class ChatTargetPatch(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    relationship: str | None = Field(default=None, max_length=120)
    style_summary: str | None = Field(default=None, max_length=1200)
    preferences: str | None = Field(default=None, max_length=1600)
    taboos: str | None = Field(default=None, max_length=1600)
    strategy_guideline: str | None = Field(default=None, max_length=1600)


class OrganizeTargetRequest(BaseModel):
    notes: str | None = Field(default=None, max_length=4000)


@router.get("")
def read_targets(db: Session = Depends(get_db)) -> dict[str, list[dict[str, object]]]:
    return {"targets": [target.to_dict() for target in list_targets(db)]}


@router.post("")
def create_chat_target(payload: ChatTargetPayload, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        target = create_target(db, **payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"target": target.to_dict()}


@router.get("/{target_id}")
def read_target(target_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        target = get_target(db, target_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"target": target.to_dict()}


@router.put("/{target_id}")
def update_chat_target(target_id: int, payload: ChatTargetPatch, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        target = update_target(db, target_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"target": target.to_dict()}


@router.delete("/{target_id}")
def delete_chat_target(target_id: int, db: Session = Depends(get_db)) -> dict[str, bool]:
    try:
        delete_target(db, target_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.post("/{target_id}/organize")
def organize_chat_target(
    target_id: int,
    payload: OrganizeTargetRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    try:
        get_target(db, target_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    job = create_job(
        db,
        job_type="organize_target",
        payload={"target_id": target_id, "notes": payload.notes},
    )
    background_tasks.add_task(run_organize_target_job, job.id, {"target_id": target_id, "notes": payload.notes})
    return {"job_id": job.id, "status": job.status}