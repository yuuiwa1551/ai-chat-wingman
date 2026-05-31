from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import ChatTarget, Conversation, LLMCall, Memory, SavedReply
from app.llm.base import LLMMessage, LLMProvider
from app.llm.router import provider_for_task
from app.prompts._registry import prompt_version
from app.settings_store import utc_now

ORGANIZE_TARGET_PROMPT_VERSION = prompt_version("organize_chat_target")


def list_targets(db: Session) -> list[ChatTarget]:
    return list(db.scalars(select(ChatTarget).order_by(ChatTarget.updated_at.desc(), ChatTarget.id.desc())).all())


def get_target(db: Session, target_id: int) -> ChatTarget:
    target = db.get(ChatTarget, target_id)
    if target is None:
        raise ValueError("Chat target not found")
    return target


def create_target(
    db: Session,
    name: str,
    relationship: str | None = None,
    style_summary: str | None = None,
    preferences: str | None = None,
    taboos: str | None = None,
    strategy_guideline: str | None = None,
) -> ChatTarget:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("name is required")
    now = utc_now()
    target = ChatTarget(
        name=cleaned_name,
        relationship=_clean_optional(relationship),
        style_summary=_clean_optional(style_summary),
        preferences=_clean_optional(preferences),
        taboos=_clean_optional(taboos),
        strategy_guideline=_clean_optional(strategy_guideline),
        created_at=now,
        updated_at=now,
    )
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


def update_target(db: Session, target_id: int, payload: dict[str, str | None]) -> ChatTarget:
    target = get_target(db, target_id)
    if "name" in payload:
        cleaned_name = (payload.get("name") or "").strip()
        if not cleaned_name:
            raise ValueError("name is required")
        target.name = cleaned_name
    for field in ["relationship", "style_summary", "preferences", "taboos", "strategy_guideline"]:
        if field in payload:
            setattr(target, field, _clean_optional(payload.get(field)))
    target.updated_at = utc_now()
    db.commit()
    db.refresh(target)
    return target


def delete_target(db: Session, target_id: int) -> None:
    target = get_target(db, target_id)
    # The schema uses plain integer foreign keys without DB-level cascades, so
    # clean up the rows that reference this target to avoid orphan records.
    db.execute(delete(Memory).where(Memory.target_id == target_id))
    db.execute(delete(SavedReply).where(SavedReply.target_id == target_id))
    db.execute(delete(Conversation).where(Conversation.target_id == target_id))
    db.delete(target)
    db.commit()


async def organize_target(db: Session, target_id: int, notes: str | None) -> tuple[ChatTarget, LLMCall]:
    target = get_target(db, target_id)
    provider = provider_for_task(db, "profile_merge")
    request_summary = _target_request_summary(target, notes)
    messages = build_organize_messages(target, notes)
    started = perf_counter()
    try:
        response = await provider.complete(messages, temperature=0.2)
        organized = _parse_target_fields(response.text, target, notes)
        llm_call = _log_llm_call(db, provider, request_summary, json.dumps(organized, ensure_ascii=False), started, "ok")
    except Exception as exc:
        organized = _fallback_target_fields(target, notes)
        llm_call = _log_llm_call(db, provider, request_summary, json.dumps(organized, ensure_ascii=False), started, "error", str(exc))
    return update_target(db, target.id, organized), llm_call


def target_prompt_profile(target: ChatTarget | None) -> str | None:
    if target is None:
        return None
    parts = [f"对象名称：{target.name}"]
    if target.relationship:
        parts.append(f"关系：{target.relationship}")
    if target.style_summary:
        parts.append(f"对象表达/性格摘要：{target.style_summary}")
    if target.preferences:
        parts.append(f"偏好：{target.preferences}")
    if target.taboos:
        parts.append(f"禁忌：{target.taboos}")
    if target.strategy_guideline:
        parts.append(f"回复策略：{target.strategy_guideline}")
    return "\n".join(parts)


def build_organize_messages(target: ChatTarget, notes: str | None) -> list[LLMMessage]:
    system = """
你是聊天对象档案整理助手。只整理可用于生成回复的对象档案，不做心理诊断。
请输出严格 JSON，字段包含 relationship、style_summary、preferences、taboos、strategy_guideline。
""".strip()
    user = f"""
当前档案：
{target_prompt_profile(target)}

补充笔记：
{notes or "无"}
""".strip()
    return [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]


def _parse_target_fields(text: str, target: ChatTarget, notes: str | None) -> dict[str, str | None]:
    try:
        parsed = json.loads(_extract_json(text))
    except (json.JSONDecodeError, ValueError):
        return _fallback_target_fields(target, notes)
    if not isinstance(parsed, dict):
        return _fallback_target_fields(target, notes)
    fallback = _fallback_target_fields(target, notes)
    return {key: _clean_optional(parsed.get(key)) or fallback.get(key) for key in fallback}


def _fallback_target_fields(target: ChatTarget, notes: str | None) -> dict[str, str | None]:
    compact_notes = _clean_optional(notes)
    preferences = target.preferences or ""
    taboos = target.taboos or ""
    if compact_notes:
        preferences = _append_sentence(preferences, compact_notes)
    return {
        "relationship": target.relationship or "待补充关系",
        "style_summary": target.style_summary or "对象档案仍在积累中，回复时先保持自然、尊重边界。",
        "preferences": preferences or "偏好仍需继续观察。",
        "taboos": taboos or "避免连续追问、过度替对方下判断。",
        "strategy_guideline": target.strategy_guideline or "先结合对象偏好和禁忌，给出自然、低压力、可复制的回复。",
    }


def _log_llm_call(
    db: Session,
    provider: LLMProvider,
    request_summary: str,
    response_summary: str,
    started: float,
    status: str,
    error_message: str | None = None,
) -> LLMCall:
    llm_call = LLMCall(
        task="target_profile_organize",
        provider=provider.provider_id,
        model=provider.model,
        prompt_version=ORGANIZE_TARGET_PROMPT_VERSION,
        request_summary=request_summary,
        response_summary=response_summary,
        prompt_tokens=max(1, len(request_summary) // 2),
        completion_tokens=max(1, len(response_summary) // 2) if response_summary else None,
        total_tokens=max(1, (len(request_summary) + len(response_summary)) // 2),
        cost_usd=0.0,
        latency_ms=int((perf_counter() - started) * 1000),
        status=status,
        error_message=error_message,
        created_at=utc_now(),
    )
    db.add(llm_call)
    db.commit()
    db.refresh(llm_call)
    return llm_call


def _target_request_summary(target: ChatTarget, notes: str | None) -> str:
    return json.dumps({"target_id": target.id, "name": target.name, "notes_preview": (notes or "")[:160]}, ensure_ascii=False)


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found")
    return stripped[start : end + 1]


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _append_sentence(existing: str, sentence: str) -> str:
    if sentence in existing:
        return existing
    return f"{existing}\n{sentence}".strip()