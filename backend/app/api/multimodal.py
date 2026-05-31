from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.jobs.runner import create_job, run_screenshot_parse_job
from app.services.multimodal_service import validate_screenshot_payload

router = APIRouter(prefix="/multimodal", tags=["multimodal"])


class ChatScreenshotParseRequest(BaseModel):
    filename: str | None = Field(default=None, max_length=240)
    mime_type: str = Field(min_length=1, max_length=80)
    image_base64: str = Field(min_length=1, max_length=8_000_000)


@router.post("/parse-chat-screenshot")
def parse_chat_screenshot_endpoint(
    payload: ChatScreenshotParseRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    try:
        validate_screenshot_payload(payload.image_base64, payload.mime_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # Keep the large base64 out of the persisted job payload; pass it only to the worker.
    job = create_job(
        db,
        job_type="screenshot_parse",
        payload={"filename": payload.filename, "mime_type": payload.mime_type},
    )
    background_tasks.add_task(run_screenshot_parse_job, job.id, payload.model_dump())
    return {"job_id": job.id, "status": job.status}