from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.jobs.runner import create_job, run_privacy_export_job
from app.services.privacy_service import data_summary

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/data-summary")
def read_data_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    return data_summary(db)


@router.post("/export")
def export_privacy_data(background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> dict[str, int | str]:
    job = create_job(db, job_type="privacy_export", payload={})
    background_tasks.add_task(run_privacy_export_job, job.id)
    return {"job_id": job.id, "status": job.status}
