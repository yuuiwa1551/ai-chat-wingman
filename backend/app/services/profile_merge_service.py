from __future__ import annotations

import json
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import UserProfile, UserProfileVersion
from app.prompts._registry import prompt_version
from app.services.onboarding_service import default_profile
from app.settings_store import utc_now

MERGE_PROFILE_PROMPT_VERSION = prompt_version("merge_profile")


def merge_style_test_profile(db: Session, analysis: dict[str, Any], source_session_id: int) -> UserProfile:
    base_profile = default_profile(db)
    now = utc_now()

    if base_profile is None:
        profile = UserProfile(
            name="风格测试人设",
            source_type="style_test",
            style_summary=str(analysis.get("style_summary") or "已根据风格测试生成表达风格档案。"),
            tone_features=json.dumps(_tone_features(analysis), ensure_ascii=False),
            common_patterns=json.dumps(_string_list(analysis.get("common_patterns")), ensure_ascii=False),
            avoid_patterns=json.dumps(_string_list(analysis.get("avoid_patterns")), ensure_ascii=False),
            generation_guideline=str(analysis.get("generation_guideline") or "保持用户在风格测试中呈现的表达习惯。"),
            confidence=0.62,
            is_default=True,
            current_version=1,
            created_at=now,
            updated_at=now,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        _snapshot_profile(db, profile, "style_test_create", source_session_id)
        return profile

    _snapshot_profile(db, base_profile, "before_style_test_merge", source_session_id)

    next_version = base_profile.current_version + 1
    base_profile.source_type = "style_test"
    base_profile.style_summary = _merge_summary(base_profile.style_summary, analysis)
    base_profile.tone_features = json.dumps(_merge_tone_features(base_profile.tone_features, analysis), ensure_ascii=False)
    base_profile.common_patterns = json.dumps(_merge_lists(base_profile.common_patterns, analysis.get("common_patterns")), ensure_ascii=False)
    base_profile.avoid_patterns = json.dumps(_merge_lists(base_profile.avoid_patterns, analysis.get("avoid_patterns")), ensure_ascii=False)
    base_profile.generation_guideline = str(analysis.get("generation_guideline") or base_profile.generation_guideline or "保持自然、可复制、不过度表演。")
    base_profile.confidence = min(0.9, max(base_profile.confidence, 0.68))
    base_profile.current_version = next_version
    base_profile.updated_at = now
    db.execute(update(UserProfile).where(UserProfile.id != base_profile.id).values(is_default=False))
    base_profile.is_default = True
    db.commit()
    db.refresh(base_profile)
    _snapshot_profile(db, base_profile, "style_test_merge", source_session_id)
    return base_profile


def _snapshot_profile(db: Session, profile: UserProfile, merge_reason: str, source_session_id: int) -> None:
    snapshot = profile.to_dict()
    snapshot["source_style_test_session_id"] = source_session_id
    snapshot["merge_prompt_version"] = MERGE_PROFILE_PROMPT_VERSION
    db.add(
        UserProfileVersion(
            profile_id=profile.id,
            version=profile.current_version,
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            merge_reason=merge_reason,
            created_at=utc_now(),
        )
    )
    db.commit()


def _merge_summary(current_summary: str | None, analysis: dict[str, Any]) -> str:
    next_summary = str(analysis.get("style_summary") or "").strip()
    if not current_summary:
        return next_summary or "已根据风格测试生成表达风格档案。"
    if not next_summary:
        return current_summary
    return f"{current_summary}\n风格测试补充：{next_summary}"


def _merge_tone_features(current_json: str | None, analysis: dict[str, Any]) -> dict[str, float | str]:
    current = _json_dict(current_json)
    incoming = _tone_features(analysis)
    merged: dict[str, float | str] = {}
    for key in set(current) | set(incoming):
        left = current.get(key)
        right = incoming.get(key)
        if isinstance(left, int | float) and isinstance(right, int | float):
            merged[key] = round((float(left) * 0.45) + (float(right) * 0.55), 2)
        else:
            merged[key] = right if right is not None else left if left is not None else "medium"
    return merged


def _tone_features(analysis: dict[str, Any]) -> dict[str, float | str]:
    raw = analysis.get("tone_features")
    if not isinstance(raw, dict):
        raw = {}
    return {
        "sentence_length": str(raw.get("sentence_length") or "medium"),
        "humor_level": _number(raw.get("humor_level"), 0.35),
        "empathy_level": _number(raw.get("empathy_level"), 0.55),
        "initiative_level": _number(raw.get("initiative_level"), 0.45),
        "directness": _number(raw.get("directness"), 0.5),
        "formality": _number(raw.get("formality"), 0.25),
    }


def _merge_lists(current_json: str | None, incoming: Any) -> list[str]:
    merged: list[str] = []
    for item in _string_list(_load_json(current_json)) + _string_list(incoming):
        if item not in merged:
            merged.append(item)
    return merged


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _json_dict(value: str | None) -> dict[str, Any]:
    loaded = _load_json(value)
    return loaded if isinstance(loaded, dict) else {}


def _load_json(value: str | None) -> Any:
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def _number(value: Any, default: float) -> float:
    if isinstance(value, int | float):
        return max(0.0, min(1.0, float(value)))
    return default