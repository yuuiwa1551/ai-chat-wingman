from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.jobs.runner import create_job, run_privacy_export_job
from app.services.privacy_service import PURGE_CONFIRM_TEXT, data_summary, purge_all_data

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/data-summary")
def read_data_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    return data_summary(db)


@router.post("/export")
def export_privacy_data(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict[str, int | str]:
    job = create_job(db, job_type="privacy_export", payload={})
    background_tasks.add_task(run_privacy_export_job, job.id)
    return {"job_id": job.id, "status": job.status}


class PurgeRequest(BaseModel):
    confirm: bool = False
    confirm_text: str | None = None
    include_settings: bool = False


@router.post("/purge")
def purge_data(payload: PurgeRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    if not payload.confirm or payload.confirm_text != PURGE_CONFIRM_TEXT:
        raise HTTPException(
            status_code=400,
            detail=f"Purge requires confirm=true and confirm_text={PURGE_CONFIRM_TEXT}",
        )
    return purge_all_data(db, include_settings=payload.include_settings)
