from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.db.models import AppSetting
from app.security import secret_box

PROVIDERS_KEY = "llm.providers"


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


def get_providers(db: Session) -> list[dict[str, Any]]:
    """Return provider configs with ``api_key`` decrypted for runtime use."""
    providers = get_json_setting(db, PROVIDERS_KEY, [])
    decrypted: list[dict[str, Any]] = []
    for provider in providers:
        item = dict(provider)
        api_key = item.get("api_key")
        if isinstance(api_key, str) and secret_box.is_encrypted(api_key):
            try:
                item["api_key"] = secret_box.decrypt(api_key)
                item["api_key_status"] = "valid"
            except ValueError:
                item["api_key"] = ""
                item["api_key_status"] = "invalid"
        elif isinstance(api_key, str) and api_key:
            item["api_key_status"] = "valid"
        else:
            item["api_key_status"] = "missing"
        decrypted.append(item)
    return decrypted


def set_providers(db: Session, providers: list[dict[str, Any]]) -> None:
    """Persist provider configs, encrypting any plain ``api_key`` at rest."""
    stored: list[dict[str, Any]] = []
    for provider in providers:
        item = dict(provider)
        item.pop("api_key_status", None)
        api_key = item.get("api_key")
        if isinstance(api_key, str) and api_key:
            item["api_key"] = secret_box.encrypt(api_key)
        stored.append(item)
    set_json_setting(db, PROVIDERS_KEY, stored, is_secret=True)
