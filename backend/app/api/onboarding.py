from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.onboarding_service import create_default_profile, default_profile, style_presets

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class CreateDefaultProfileRequest(BaseModel):
    name: str = Field(default="默认人设", min_length=1, max_length=64)
    selected_preset_ids: list[int] = Field(min_length=1)
    avoid_patterns: list[str] = Field(default_factory=list)


@router.get("/status")
def read_onboarding_status(db: Session = Depends(get_db)) -> dict[str, object]:
    profile = default_profile(db)
    return {
        "has_default_profile": profile is not None,
        "default_profile_id": profile.id if profile else None,
    }


@router.get("/style-presets")
def list_style_presets(db: Session = Depends(get_db)) -> dict[str, list[dict[str, object]]]:
    return {"presets": [preset.to_dict() for preset in style_presets(db)]}


@router.post("/default-profile")
def save_default_profile(payload: CreateDefaultProfileRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        profile = create_default_profile(db, payload.name, payload.selected_preset_ids, payload.avoid_patterns)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"profile": profile.to_dict()}
