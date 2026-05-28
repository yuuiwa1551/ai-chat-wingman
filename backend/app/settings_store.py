from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AppSetting


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def get_json_setting(db: Session, key: str, default: Any) -> Any:
    setting = db.get(AppSetting, key)
    if setting is None or setting.value in (None, ""):
        return default
    return json.loads(setting.value)


def set_json_setting(db: Session, key: str, value: Any, is_secret: bool = False) -> AppSetting:
    setting = db.get(AppSetting, key)
    serialized = json.dumps(value, ensure_ascii=False)
    if setting is None:
        setting = AppSetting(key=key, value=serialized, is_secret=is_secret, updated_at=utc_now())
        db.add(setting)
    else:
        setting.value = serialized
        setting.is_secret = is_secret
        setting.updated_at = utc_now()
    db.commit()
    db.refresh(setting)
    return setting
