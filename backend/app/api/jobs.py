from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.jobs.runner import create_job, get_job, run_demo_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


class DemoJobRequest(BaseModel):
    duration_seconds: float = Field(default=1.0, ge=0.0, le=10.0)


@router.post("/demo")
def start_demo_job(
    payload: DemoJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    job = create_job(db, job_type="demo", payload=payload.model_dump())
    background_tasks.add_task(run_demo_job, job.id, payload.duration_seconds)
    return {"job_id": job.id, "status": job.status}


@router.get("/{job_id}")
def read_job(job_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    job = get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()
