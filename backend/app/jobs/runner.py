from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Job
from app.settings_store import utc_now


def create_job(db: Session, job_type: str, payload: dict[str, Any] | None = None) -> Job:
    now = utc_now()
    job = Job(
        job_type=job_type,
        status="pending",
        progress=0.0,
        payload=json.dumps(payload or {}, ensure_ascii=False),
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def _update_job(db: Session, job_id: int, **fields: object) -> None:
    job = db.get(Job, job_id)
    if job is None:
        return
    for key, value in fields.items():
        setattr(job, key, value)
    job.updated_at = utc_now()
    db.commit()


def run_demo_job(job_id: int, duration_seconds: float) -> None:
    with SessionLocal() as db:
        _update_job(db, job_id, status="running", progress=0.1)

    steps = 4
    sleep_time = duration_seconds / steps if duration_seconds else 0
    for step in range(1, steps + 1):
        if sleep_time:
            time.sleep(sleep_time)
        with SessionLocal() as db:
            _update_job(db, job_id, progress=min(step / steps, 0.95))

    with SessionLocal() as db:
        _update_job(db, job_id, status="success", progress=1.0, result=json.dumps({"message": "demo complete"}))
