from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LLMCall, StyleTestMessage, StyleTestSession, UserProfile
from app.llm.base import LLMMessage, LLMProvider
from app.llm.router import provider_for_task
from app.prompts._registry import prompt_version
from app.services.profile_merge_service import merge_style_test_profile
from app.settings_store import utc_now

SIMULATE_PROMPT_VERSION = prompt_version("simulate_style_test")
ANALYZE_PROMPT_VERSION = prompt_version("analyze_style_test")


@dataclass(frozen=True)
class StyleTestSimulationChunk:
    message_id: int | None
    delta: str
    text: str


def create_style_test_session(db: Session, target_type: str, scenario: str, simulated_target_profile: str | None) -> StyleTestSession:
    now = utc_now()
    session = StyleTestSession(
        target_type=target_type.strip(),
        scenario=scenario.strip(),
        simulated_target_profile=simulated_target_profile.strip() if simulated_target_profile else _default_target_profile(target_type, scenario),
        status="active",
        created_at=now,
        updated_at=now,
    )
    if not session.target_type or not session.scenario:
        raise ValueError("target_type and scenario are required")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_style_test_session(db: Session, session_id: int) -> StyleTestSession:
    session = db.get(StyleTestSession, session_id)
    if session is None:
        raise ValueError("Style test session not found")
    return session


def list_style_test_messages(db: Session, session_id: int) -> list[StyleTestMessage]:
    return list(db.scalars(select(StyleTestMessage).where(StyleTestMessage.session_id == session_id).order_by(StyleTestMessage.id)).all())


def save_user_message(db: Session, session: StyleTestSession, content: str) -> StyleTestMessage:
    cleaned = content.strip()
    if not cleaned:
        raise ValueError("content is required")
    now = utc_now()
    message = StyleTestMessage(session_id=session.id, role="user", content=cleaned, created_at=now)
    session.updated_at = now
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


async def stream_simulated_target_reply(db: Session, session: StyleTestSession) -> AsyncIterator[StyleTestSimulationChunk]:
    provider = provider_for_task(db, "style_test_simulation")
    messages = build_simulation_messages(session, list_style_test_messages(db, session.id))
    started = perf_counter()
    parts: list[str] = []
    try:
        async for chunk in provider.stream(messages, temperature=0.72):
            parts.append(chunk.delta)
            yield StyleTestSimulationChunk(message_id=None, delta=chunk.delta, text="".join(parts))
    except Exception as exc:
        _log_llm_call(db, provider, "style_test_simulation", SIMULATE_PROMPT_VERSION, _session_summary(session), "", started, "error", str(exc))
        raise

    text = "".join(parts).strip()
    llm_call = _log_llm_call(db, provider, "style_test_simulation", SIMULATE_PROMPT_VERSION, _session_summary(session), text, started, "ok")
    now = utc_now()
    message = StyleTestMessage(session_id=session.id, role="simulated_target", content=text, created_at=now)
    session.updated_at = now
    db.add(message)
    db.commit()
    db.refresh(message)
    yield StyleTestSimulationChunk(message_id=message.id, delta="", text=text)
    _ = llm_call.id


async def analyze_style_test_session(db: Session, session_id: int) -> tuple[dict[str, Any], UserProfile, LLMCall]:
    session = get_style_test_session(db, session_id)
    user_messages = [message.content for message in list_style_test_messages(db, session.id) if message.role == "user"]
    if not user_messages:
        raise ValueError("At least one user message is required before analysis")

    provider = provider_for_task(db, "style_analysis")
    messages = build_analysis_messages(user_messages)
    started = perf_counter()
    try:
        response = await provider.complete(messages, temperature=0.2)
        analysis = _parse_analysis(response.text, user_messages)
        llm_call = _log_llm_call(db, provider, "style_analysis", ANALYZE_PROMPT_VERSION, _analysis_summary(user_messages), json.dumps(analysis, ensure_ascii=False), started, "ok")
    except Exception as exc:
        analysis = _fallback_analysis(user_messages)
        llm_call = _log_llm_call(db, provider, "style_analysis", ANALYZE_PROMPT_VERSION, _analysis_summary(user_messages), json.dumps(analysis, ensure_ascii=False), started, "error", str(exc))

    profile = merge_style_test_profile(db, analysis, session.id)
    session.status = "analyzed"
    session.updated_at = utc_now()
    db.commit()
    return analysis, profile, llm_call


def build_simulation_messages(session: StyleTestSession, messages: list[StyleTestMessage]) -> list[LLMMessage]:
    history = "\n".join(f"{message.role}: {message.content}" for message in messages[-12:])
    system = f"""
你在风格测试窗口里扮演一个模拟聊天对象，帮助用户暴露真实表达习惯。
对象类型：{session.target_type}
场景：{session.scenario}
对象设定：{session.simulated_target_profile}
要求：只输出模拟对象下一句话；自然、简短、有来有回；不要评价用户，不要解释规则。
""".strip()
    return [LLMMessage(role="system", content=system), LLMMessage(role="user", content=f"聊天历史：\n{history}")]


def build_analysis_messages(user_messages: list[str]) -> list[LLMMessage]:
    samples = "\n".join(f"- {message}" for message in user_messages)
    system = """
你是一个聊天表达风格分析器。只分析表达习惯，不做心理诊断，不贴人格标签。
请输出严格 JSON，字段包含 style_summary、tone_features、common_patterns、avoid_patterns、generation_guideline。
""".strip()
    user = f"用户回复样本：\n{samples}"
    return [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]


def _parse_analysis(text: str, user_messages: list[str]) -> dict[str, Any]:
    try:
        parsed = json.loads(_extract_json(text))
    except (json.JSONDecodeError, ValueError):
        return _fallback_analysis(user_messages)
    if not isinstance(parsed, dict):
        return _fallback_analysis(user_messages)
    fallback = _fallback_analysis(user_messages)
    return {**fallback, **parsed, "tone_features": {**fallback["tone_features"], **(parsed.get("tone_features") if isinstance(parsed.get("tone_features"), dict) else {})}}


def _fallback_analysis(user_messages: list[str]) -> dict[str, Any]:
    average_length = sum(len(message) for message in user_messages) / max(len(user_messages), 1)
    sentence_length = "short" if average_length < 18 else "long" if average_length > 60 else "medium"
    joined = "\n".join(user_messages)
    return {
        "style_summary": f"用户在风格测试中提供了 {len(user_messages)} 条回复，整体表达偏{sentence_length}，需要继续用更多样本校准。",
        "tone_features": {
            "sentence_length": sentence_length,
            "humor_level": 0.45 if any(marker in joined for marker in ["哈哈", "笑", "hhh"]) else 0.25,
            "empathy_level": 0.7 if any(marker in joined for marker in ["辛苦", "抱抱", "理解", "没事"]) else 0.5,
            "initiative_level": 0.55 if any(marker in joined for marker in ["要不要", "我来", "下次"]) else 0.4,
            "directness": 0.55,
            "formality": 0.2,
        },
        "common_patterns": _common_patterns(user_messages),
        "avoid_patterns": ["不要突然变成过度正式或客服式表达", "不要过度推断对方心理"],
        "generation_guideline": "生成回复时优先保持用户在测试中呈现的句长、语气和常用表达；在此基础上增强情绪承接和边界感。",
    }


def _common_patterns(user_messages: list[str]) -> list[str]:
    patterns: list[str] = []
    joined = "\n".join(user_messages)
    if any(marker in joined for marker in ["哈哈", "hhh", "笑"]):
        patterns.append("会用轻微笑意缓和语气")
    if any(marker in joined for marker in ["没事", "先", "不急"]):
        patterns.append("倾向先降低对方压力")
    if not patterns:
        patterns.append("表达自然直接，样本仍需继续积累")
    return patterns


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found")
    return stripped[start : end + 1]


def _log_llm_call(
    db: Session,
    provider: LLMProvider,
    task: str,
    prompt_version: str,
    request_summary: str,
    response_summary: str,
    started: float,
    status: str,
    error_message: str | None = None,
) -> LLMCall:
    llm_call = LLMCall(
        task=task,
        provider=provider.provider_id,
        model=provider.model,
        prompt_version=prompt_version,
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


def _default_target_profile(target_type: str, scenario: str) -> str:
    return f"模拟对象是{target_type.strip()}，当前场景是{scenario.strip()}；回复应自然、有情绪反应，但不要过度戏剧化。"


def _session_summary(session: StyleTestSession) -> str:
    return json.dumps({"session_id": session.id, "target_type": session.target_type, "scenario": session.scenario}, ensure_ascii=False)


def _analysis_summary(user_messages: list[str]) -> str:
    return json.dumps({"message_count": len(user_messages), "samples": user_messages[-8:]}, ensure_ascii=False)