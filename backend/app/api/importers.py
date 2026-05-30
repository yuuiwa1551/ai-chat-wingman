from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.jobs.runner import create_job, run_qq_json_import_job

router = APIRouter(prefix="/import", tags=["import"])


class QQJsonImportRequest(BaseModel):
    filename: str | None = Field(default=None, max_length=240)
    raw_json: Any | None = None
    raw_text: str | None = Field(default=None, max_length=10_000_000)
    me_speakers: list[str] = Field(min_length=1, max_length=16)
    target_id: int | None = Field(default=None, ge=1)
    target_name: str | None = Field(default=None, max_length=120)
    max_messages: int = Field(default=5000, ge=1, le=50000)

    @model_validator(mode="after")
    def validate_raw_payload(self) -> "QQJsonImportRequest":
        if self.raw_json is None and not (self.raw_text and self.raw_text.strip()):
            raise ValueError("raw_json or raw_text is required")
        return self


@router.post("/qq-json")
def import_qq_json(
    payload: QQJsonImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    serialized_payload = payload.model_dump(mode="json")
    job_payload = {
        "filename": payload.filename,
        "me_speakers": payload.me_speakers,
        "target_id": payload.target_id,
        "target_name": payload.target_name,
        "max_messages": payload.max_messages,
        "raw_size": len(payload.raw_text or str(payload.raw_json)),
    }
    try:
        job = create_job(db, job_type="import_qq_json", payload=job_payload)
        background_tasks.add_task(run_qq_json_import_job, job.id, serialized_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job_id": job.id, "status": job.status}
