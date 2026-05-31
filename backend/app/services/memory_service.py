from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LLMCall, Memory
from app.llm.base import LLMMessage, LLMProvider
from app.llm.router import provider_for_task
from app.prompts._registry import prompt_version
from app.settings_store import utc_now

logger = logging.getLogger(__name__)

EXTRACT_MEMORY_PROMPT_VERSION = prompt_version("extract_memory")

MEMORY_TYPES = {"preference", "event", "relationship", "warning", "fact", "style"}
MEMORY_STATUSES = {"pending", "approved", "rejected"}


def list_memories(db: Session, target_id: int | None = None, status: str | None = None) -> list[Memory]:
    stmt = select(Memory)
    if target_id is not None:
        stmt = stmt.where(Memory.target_id == target_id)
    if status is not None:
        stmt = stmt.where(Memory.status == status)
    stmt = stmt.order_by(Memory.updated_at.desc(), Memory.id.desc())
    return list(db.scalars(stmt).all())


def get_memory(db: Session, memory_id: int) -> Memory:
    memory = db.get(Memory, memory_id)
    if memory is None:
        raise ValueError("Memory not found")
    return memory


def create_memory(
    db: Session,
    target_id: int | None,
    content: str,
    memory_type: str | None = None,
    confidence: float = 0.7,
    status: str = "pending",
    source_conversation_id: int | None = None,
) -> Memory:
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("content is required")
    now = utc_now()
    memory = Memory(
        target_id=target_id,
        memory_type=_clean_type(memory_type),
        content=cleaned,
        confidence=_clamp_confidence(confidence),
        status=_clean_status(status),
        source_conversation_id=source_conversation_id,
        created_at=now,
        updated_at=now,
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def update_memory(db: Session, memory_id: int, payload: dict[str, Any]) -> Memory:
    memory = get_memory(db, memory_id)
    if "content" in payload and payload["content"] is not None:
        cleaned = str(payload["content"]).strip()
        if not cleaned:
            raise ValueError("content is required")
        memory.content = cleaned
    if "memory_type" in payload:
        memory.memory_type = _clean_type(payload["memory_type"])
    if "confidence" in payload and payload["confidence"] is not None:
        memory.confidence = _clamp_confidence(float(payload["confidence"]))
    if "status" in payload and payload["status"] is not None:
        memory.status = _clean_status(str(payload["status"]))
    memory.updated_at = utc_now()
    db.commit()
    db.refresh(memory)
    return memory


def set_memory_status(db: Session, memory_id: int, status: str) -> Memory:
    memory = get_memory(db, memory_id)
    memory.status = _clean_status(status)
    memory.updated_at = utc_now()
    db.commit()
    db.refresh(memory)
    return memory


def approve_memory(db: Session, memory_id: int) -> Memory:
    return set_memory_status(db, memory_id, "approved")


def reject_memory(db: Session, memory_id: int) -> Memory:
    return set_memory_status(db, memory_id, "rejected")


def delete_memory(db: Session, memory_id: int) -> None:
    memory = get_memory(db, memory_id)
    db.delete(memory)
    db.commit()


def approved_memories(db: Session, target_id: int | None) -> list[Memory]:
    if target_id is None:
        return []
    stmt = (
        select(Memory)
        .where(Memory.target_id == target_id, Memory.status == "approved")
        .order_by(Memory.confidence.desc(), Memory.id.desc())
    )
    return list(db.scalars(stmt).all())


def approved_memories_prompt(memories: list[Memory], limit: int = 12) -> str:
    if not memories:
        return ""
    lines: list[str] = []
    for memory in memories[:limit]:
        label = memory.memory_type or "fact"
        lines.append(f"- [{label}] {memory.content}")
    return "\n".join(lines)


async def extract_memories_from_text(
    db: Session,
    target_id: int | None,
    conversation_text: str,
    source_conversation_id: int | None = None,
) -> list[Memory]:
    """Extract reusable long-term memories from chat text and store them as pending."""
    cleaned = conversation_text.strip()
    if not cleaned:
        return []
    provider = provider_for_task(db, "memory_extraction")
    messages = build_extract_memory_messages(cleaned)
    started = perf_counter()
    try:
        response = await provider.complete(messages, temperature=0.2)
    except Exception as exc:  # noqa: BLE001 - log failure, do not break the caller
        _log_call(db, provider, _request_summary(cleaned, target_id), "", started, "error", str(exc))
        return []

    candidates = _parse_memories(response.text)
    _log_call(
        db,
        provider,
        _request_summary(cleaned, target_id),
        json.dumps(candidates, ensure_ascii=False),
        started,
        "ok",
    )
    created: list[Memory] = []
    for candidate in candidates:
        content = str(candidate.get("content", "")).strip()
        if not content:
            continue
        created.append(
            create_memory(
                db,
                target_id=target_id,
                content=content,
                memory_type=candidate.get("memory_type"),
                confidence=_safe_confidence(candidate.get("confidence")),
                status="pending",
                source_conversation_id=source_conversation_id,
            )
        )
    return created


def build_extract_memory_messages(conversation_text: str) -> list[LLMMessage]:
    system = """
你是一个聊天长期记忆提取器。从对话里提取稳定、可复用的信息，用于以后帮用户更自然地聊天。
规则：
1. 只提取长期有用的信息：偏好、关系、重要事件、需要规避的雷点、稳定事实、表达风格。
2. 输出严格 JSON 数组，每项形如 {"memory_type": "preference|event|relationship|warning|fact|style", "content": "...", "confidence": 0.0-1.0}。
3. 没有值得长期保存的信息时输出 []。
4. 不要臆测，不要把一次性情绪当成永久特质，不要记录敏感或无关信息。
""".strip()
    user = f"以下是聊天内容：\n{conversation_text}"
    return [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]


def _parse_memories(text: str) -> list[dict[str, Any]]:
    payload = _extract_json_array(text)
    if payload is None:
        logger.warning("memory extraction returned no JSON array; raw text discarded")
        return []
    try:
        parsed = json.loads(payload)
    except (json.JSONDecodeError, ValueError):
        logger.warning("memory extraction JSON decode failed; raw payload discarded")
        return []
    if not isinstance(parsed, list):
        return []
    result: list[dict[str, Any]] = []
    for item in parsed:
        if isinstance(item, dict) and str(item.get("content", "")).strip():
            result.append(item)
    return result


def _extract_json_array(text: str) -> str | None:
    stripped = text.strip()
    start = stripped.find("[")
    end = stripped.rfind("]")
    if start < 0 or end <= start:
        return None
    return stripped[start : end + 1]


def _log_call(
    db: Session,
    provider: LLMProvider,
    request_summary: str,
    response_summary: str,
    started: float,
    status: str,
    error_message: str | None = None,
) -> LLMCall:
    llm_call = LLMCall(
        task="memory_extraction",
        provider=provider.provider_id,
        model=provider.model,
        prompt_version=EXTRACT_MEMORY_PROMPT_VERSION,
        request_summary=request_summary,
        response_summary=response_summary or None,
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


def _request_summary(conversation_text: str, target_id: int | None) -> str:
    return json.dumps(
        {"target_id": target_id, "chat_text_preview": conversation_text[:160]},
        ensure_ascii=False,
    )


def _clean_type(memory_type: str | None) -> str | None:
    if memory_type is None:
        return None
    cleaned = str(memory_type).strip().lower()
    if not cleaned:
        return None
    return cleaned if cleaned in MEMORY_TYPES else "fact"


def _clean_status(status: str) -> str:
    cleaned = status.strip().lower()
    if cleaned not in MEMORY_STATUSES:
        raise ValueError("status must be pending, approved or rejected")
    return cleaned


def _clamp_confidence(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _safe_confidence(value: Any) -> float:
    try:
        return _clamp_confidence(float(value))
    except (TypeError, ValueError):
        return 0.6
