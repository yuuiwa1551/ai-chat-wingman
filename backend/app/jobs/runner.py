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


def update_job(db: Session, job_id: int, **fields: object) -> None:
    job = db.get(Job, job_id)
    if job is None:
        return
    for key, value in fields.items():
        setattr(job, key, value)
    job.updated_at = utc_now()
    db.commit()


def run_demo_job(job_id: int, duration_seconds: float) -> None:
    with SessionLocal() as db:
        update_job(db, job_id, status="running", progress=0.1)

    steps = 4
    sleep_time = duration_seconds / steps if duration_seconds else 0
    for step in range(1, steps + 1):
        if sleep_time:
            time.sleep(sleep_time)
        with SessionLocal() as db:
            update_job(db, job_id, progress=min(step / steps, 0.95))

    with SessionLocal() as db:
        update_job(db, job_id, status="success", progress=1.0, result=json.dumps({"message": "demo complete"}))


def run_qq_json_import_job(job_id: int, payload: dict[str, Any]) -> None:
    try:
        from app.services.chat_import_service import process_qq_json_import_payload

        with SessionLocal() as db:
            result = process_qq_json_import_payload(db, job_id, payload)
            update_job(db, job_id, status="success", progress=1.0, result=json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        with SessionLocal() as db:
            update_job(db, job_id, status="failed", progress=1.0, error_message=str(exc))


def run_privacy_export_job(job_id: int) -> None:
    try:
        from app.services.privacy_service import export_backup

        with SessionLocal() as db:
            result = export_backup(db, job_id)
            update_job(db, job_id, status="success", progress=1.0, result=json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        with SessionLocal() as db:
            update_job(db, job_id, status="failed", progress=1.0, error_message=str(exc))


async def run_screenshot_parse_job(job_id: int, payload: dict[str, Any]) -> None:
    try:
        from app.services.multimodal_service import PARSE_SCREENSHOT_PROMPT_VERSION, parse_chat_screenshot

        with SessionLocal() as db:
            update_job(db, job_id, status="running", progress=0.2)
            result, llm_call = await parse_chat_screenshot(
                db,
                payload["image_base64"],
                payload["mime_type"],
                payload.get("filename"),
            )
            job_result = {
                **result.to_dict(),
                "llm_call_id": llm_call.id,
                "prompt_version": PARSE_SCREENSHOT_PROMPT_VERSION,
            }
            update_job(db, job_id, status="success", progress=1.0, result=json.dumps(job_result, ensure_ascii=False))
    except Exception as exc:
        with SessionLocal() as db:
            update_job(db, job_id, status="failed", progress=1.0, error_message=str(exc))


async def run_organize_target_job(job_id: int, payload: dict[str, Any]) -> None:
    try:
        from app.services.target_service import organize_target

        with SessionLocal() as db:
            update_job(db, job_id, status="running", progress=0.2)
            target, llm_call = await organize_target(db, int(payload["target_id"]), payload.get("notes"))
            job_result = {"target": target.to_dict(), "llm_call_id": llm_call.id}
            update_job(db, job_id, status="success", progress=1.0, result=json.dumps(job_result, ensure_ascii=False))
    except Exception as exc:
        with SessionLocal() as db:
            update_job(db, job_id, status="failed", progress=1.0, error_message=str(exc))
