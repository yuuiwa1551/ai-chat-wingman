from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import DEFAULT_TASK_ROUTING
from app.db.database import get_db
from app.llm.router import list_provider_models, test_provider
from app.settings_store import get_json_setting, set_json_setting

router = APIRouter(prefix="/settings", tags=["settings"])


class LLMProviderConfig(BaseModel):
    id: str = Field(min_length=1)
    type: str = Field(default="mock")
    base_url: str | None = None
    api_key: str | None = None
    default_model: str = "mock-chat"
    enabled: bool = True


def _mask_provider(provider: dict[str, object]) -> dict[str, object]:
    masked = dict(provider)
    api_key = masked.get("api_key")
    if isinstance(api_key, str) and api_key:
        masked["api_key"] = "***"
    return masked


@router.get("")
def read_settings(db: Session = Depends(get_db)) -> dict[str, object]:
    return {
        "llm.providers": [_mask_provider(item) for item in get_json_setting(db, "llm.providers", [])],
        "llm.task_routing": get_json_setting(db, "llm.task_routing", DEFAULT_TASK_ROUTING),
    }


@router.get("/llm/providers")
def list_providers(db: Session = Depends(get_db)) -> dict[str, list[dict[str, object]]]:
    providers = get_json_setting(db, "llm.providers", [])
    return {"providers": [_mask_provider(provider) for provider in providers]}


@router.put("/llm/providers/{provider_id}")
def upsert_provider(provider_id: str, payload: LLMProviderConfig, db: Session = Depends(get_db)) -> dict[str, object]:
    if provider_id != payload.id:
        raise HTTPException(status_code=400, detail="Provider id mismatch")

    providers = get_json_setting(db, "llm.providers", [])
    existing = next((provider for provider in providers if provider.get("id") == provider_id), None)
    provider_data = payload.model_dump()
    if existing is not None and provider_data.get("api_key") in (None, "", "***") and existing.get("api_key"):
        provider_data["api_key"] = existing.get("api_key")
    next_providers = [provider for provider in providers if provider.get("id") != provider_id]
    next_providers.append(provider_data)
    set_json_setting(db, "llm.providers", next_providers, is_secret=True)
    return {"provider": _mask_provider(provider_data)}


@router.post("/llm/providers/{provider_id}/test")
async def test_llm_provider(provider_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    providers = get_json_setting(db, "llm.providers", [])
    provider = next((item for item in providers if item.get("id") == provider_id), None)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    try:
        return await test_provider(db, provider)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Provider test failed: {_provider_error_detail(exc)}") from exc


@router.get("/llm/providers/{provider_id}/models")
async def read_provider_models(provider_id: str, db: Session = Depends(get_db)) -> dict[str, object]:
    providers = get_json_setting(db, "llm.providers", [])
    provider = next((item for item in providers if item.get("id") == provider_id), None)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    try:
        models = await list_provider_models(provider)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to list provider models: {_provider_error_detail(exc)}") from exc
    return {"provider_id": provider_id, "models": models, "default_model": provider.get("default_model")}


@router.get("/llm/task-routing")
def get_task_routing(db: Session = Depends(get_db)) -> dict[str, object]:
    return {"task_routing": get_json_setting(db, "llm.task_routing", DEFAULT_TASK_ROUTING)}


@router.put("/llm/task-routing")
def put_task_routing(payload: dict[str, str], db: Session = Depends(get_db)) -> dict[str, object]:
    set_json_setting(db, "llm.task_routing", payload)
    return {"task_routing": payload}


def _provider_error_detail(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        response_text = exc.response.text.strip()
        if response_text:
            return f"{exc.response.status_code} {exc.response.reason_phrase}: {response_text[:1000]}"
        return f"{exc.response.status_code} {exc.response.reason_phrase}"
    return str(exc)
