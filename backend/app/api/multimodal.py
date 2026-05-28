from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.multimodal_service import PARSE_SCREENSHOT_PROMPT_VERSION, parse_chat_screenshot

router = APIRouter(prefix="/multimodal", tags=["multimodal"])


class ChatScreenshotParseRequest(BaseModel):
    filename: str | None = Field(default=None, max_length=240)
    mime_type: str = Field(min_length=1, max_length=80)
    image_base64: str = Field(min_length=1, max_length=8_000_000)


@router.post("/parse-chat-screenshot")
async def parse_chat_screenshot_endpoint(payload: ChatScreenshotParseRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        result, llm_call = await parse_chat_screenshot(db, payload.image_base64, payload.mime_type, payload.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Screenshot parse failed: {exc}") from exc
    return {**result.to_dict(), "llm_call_id": llm_call.id, "prompt_version": PARSE_SCREENSHOT_PROMPT_VERSION}