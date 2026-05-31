from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.sse import encode_sse, sse_response
from app.db.database import get_db
from app.jobs.runner import create_job, run_style_analysis_job
from app.services.style_test_service import (
    create_style_test_session,
    get_style_test_session,
    list_style_test_messages,
    save_user_message,
    stream_simulated_target_reply,
)

router = APIRouter(prefix="/style-test", tags=["style-test"])


class CreateStyleTestSessionRequest(BaseModel):
    target_type: str = Field(min_length=1, max_length=80)
    scenario: str = Field(min_length=1, max_length=500)
    simulated_target_profile: str | None = Field(default=None, max_length=1200)


class SendStyleTestMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


@router.post("/sessions")
def create_session(payload: CreateStyleTestSessionRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        session = create_style_test_session(db, payload.target_type, payload.scenario, payload.simulated_target_profile)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"session": session.to_dict()}


@router.get("/sessions/{session_id}")
def read_session(session_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        session = get_style_test_session(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"session": session.to_dict(), "messages": [message.to_dict() for message in list_style_test_messages(db, session.id)]}


@router.post("/sessions/{session_id}/message")
async def send_message(session_id: int, payload: SendStyleTestMessageRequest, db: Session = Depends(get_db)):
    try:
        session = get_style_test_session(db, session_id)
        user_message = save_user_message(db, session, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def events() -> AsyncIterator[str]:
        yield encode_sse("user_message", {"message": user_message.to_dict()})
        last_text = ""
        try:
            async for chunk in stream_simulated_target_reply(db, session):
                last_text = chunk.text
                if chunk.delta:
                    yield encode_sse("token", {"delta": chunk.delta})
                if chunk.message_id is not None:
                    yield encode_sse("done", {"message_id": chunk.message_id, "text": last_text})
        except Exception as exc:
            yield encode_sse("error", {"message": str(exc)})

    return sse_response(events())


@router.post("/sessions/{session_id}/analysis")
def analyze_session(
    session_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict[str, int | str]:
    try:
        get_style_test_session(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    job = create_job(db, job_type="style_analysis", payload={"session_id": session_id})
    background_tasks.add_task(run_style_analysis_job, job.id, {"session_id": session_id})
    return {"job_id": job.id, "status": job.status}