from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import ChatSession, ChatTarget, Conversation, LLMCall, UserProfile
from app.llm.base import LLMMessage, LLMProvider
from app.llm.router import provider_for_task
from app.prompts._registry import prompt_version
from app.services.memory_service import approved_memories, approved_memories_prompt
from app.services.onboarding_service import default_profile
from app.services.target_service import get_target, target_prompt_profile
from app.settings_store import utc_now

REPLY_PROMPT_VERSION = prompt_version("generate_reply")


@dataclass(frozen=True)
class ReplyGenerationRequest:
    chat_text: str
    target_id: int | None
    target_name: str | None
    target_strategy: str | None
    reply_goal: str
    tone: str
    length: str
    proactivity: float
    risk_level: str
    candidate_count: int = 3
    session_id: int | None = None


@dataclass(frozen=True)
class ReplyCandidate:
    index: int
    text: str


def start_reply_generation(db: Session, request: ReplyGenerationRequest) -> tuple[Conversation, LLMProvider, UserProfile | None, ChatTarget | None, str]:
    if not request.chat_text.strip():
        raise ValueError("chat_text is required")

    profile = default_profile(db)
    target = get_target(db, request.target_id) if request.target_id else None
    provider = provider_for_task(db, "reply_generation")
    memories_prompt = approved_memories_prompt(approved_memories(db, target.id)) if target else ""
    now = utc_now()
    target_name = target.name if target else _clean_optional(request.target_name)
    target_strategy = target_prompt_profile(target) if target else _clean_optional(request.target_strategy)

    session = db.get(ChatSession, request.session_id) if request.session_id else None
    if session is None:
        session = ChatSession(
            target_id=target.id if target else None,
            title=_session_title(request.chat_text),
            target_name=target_name,
            target_strategy=target_strategy,
            created_at=now,
            updated_at=now,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    conversation = Conversation(
        chat_session_id=session.id,
        target_id=target.id if target else None,
        profile_id=profile.id if profile else None,
        profile_version=profile.current_version if profile else None,
        prompt_version=REPLY_PROMPT_VERSION,
        input_text=request.chat_text.strip(),
        target_name=target_name,
        target_strategy=target_strategy,
        reply_goal=request.reply_goal,
        tone=request.tone,
        length=request.length,
        proactivity=request.proactivity,
        risk_level=request.risk_level,
        generated_replies="[]",
        created_at=now,
        updated_at=now,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation, provider, profile, target, memories_prompt


async def stream_reply_candidates(
    provider: LLMProvider,
    request: ReplyGenerationRequest,
    profile: UserProfile | None,
    target: ChatTarget | None,
    memories_prompt: str = "",
) -> AsyncIterator[ReplyCandidate]:
    count = max(1, min(request.candidate_count, 5))
    for index in range(count):
        messages = build_reply_messages(request, profile, target, index, memories_prompt)
        parts: list[str] = []
        async for chunk in provider.stream(messages, temperature=_temperature_for(index)):
            parts.append(chunk.delta)
            yield ReplyCandidate(index=index, text="".join(parts))


def finish_reply_generation(
    db: Session,
    conversation: Conversation,
    provider: LLMProvider,
    request: ReplyGenerationRequest,
    replies: list[str],
) -> LLMCall:
    now = utc_now()
    response_summary = json.dumps(replies, ensure_ascii=False)
    prompt_tokens = _estimate_tokens(request.chat_text)
    completion_tokens = _estimate_tokens("\n".join(replies))
    llm_call = LLMCall(
        task="reply_generation",
        provider=provider.provider_id,
        model=provider.model,
        prompt_version=conversation.prompt_version,
        request_summary=_request_summary(request),
        response_summary=response_summary,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        cost_usd=0.0,
        status="ok",
        created_at=now,
    )
    db.add(llm_call)
    db.commit()
    db.refresh(llm_call)

    conversation.llm_call_id = llm_call.id
    conversation.generated_replies = response_summary
    conversation.updated_at = now
    db.commit()
    db.refresh(conversation)
    return llm_call


def fail_reply_generation(db: Session, conversation: Conversation, provider: LLMProvider, request: ReplyGenerationRequest, error_message: str) -> LLMCall:
    now = utc_now()
    llm_call = LLMCall(
        task="reply_generation",
        provider=provider.provider_id,
        model=provider.model,
        prompt_version=conversation.prompt_version,
        request_summary=_request_summary(request),
        status="error",
        error_message=error_message,
        created_at=now,
    )
    db.add(llm_call)
    db.commit()
    db.refresh(llm_call)

    conversation.llm_call_id = llm_call.id
    conversation.updated_at = now
    db.commit()
    return llm_call


def select_reply(db: Session, conversation_id: int, selected_reply: str | None, selected_index: int | None) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise ValueError("Conversation not found")

    replies = json.loads(conversation.generated_replies or "[]")
    if selected_reply is None:
        if selected_index is None:
            raise ValueError("selected_reply or selected_index is required")
        if selected_index < 0 or selected_index >= len(replies):
            raise ValueError("selected_index is out of range")
        selected_reply = str(replies[selected_index])

    if not selected_reply.strip():
        raise ValueError("selected_reply is required")

    conversation.selected_reply = selected_reply.strip()
    conversation.updated_at = utc_now()
    db.commit()
    db.refresh(conversation)
    return conversation


def build_reply_messages(request: ReplyGenerationRequest, profile: UserProfile | None, target: ChatTarget | None, candidate_index: int, memories_prompt: str = "") -> list[LLMMessage]:
    profile_summary = profile.style_summary if profile else "用户尚未完成人设建模，先保持自然、清楚、不过度表演。"
    profile_guideline = profile.generation_guideline if profile else "表达要像真实聊天消息，避免 AI 腔。"
    target_name = target.name if target else request.target_name or "当前聊天对象"
    target_strategy = target_prompt_profile(target) or request.target_strategy or "先接住上下文和情绪，再给出自然可复制的回复。"
    variant = ["稳妥自然", "更有情绪承接", "更主动推进", "更简短克制", "更轻松一点"][candidate_index]
    memory_block = f"\n7. 已确认的长期记忆（务必参考，不要复述）：\n{memories_prompt}" if memories_prompt.strip() else ""
    system = f"""
你是 AI 帮聊助手，只生成候选回复，不自动发送。
生成规则：
1. 只输出一条可直接复制发送的中文回复，不要编号、解释或 Markdown。
2. 贴近用户表达风格：{profile_summary}
3. 人设生成约束：{profile_guideline}
4. 聊天对象：{target_name}；对象策略：{target_strategy}
5. 回复目标：{request.reply_goal}；语气：{request.tone}；长度：{request.length}；推进感：{request.proactivity:.2f}；风险：{request.risk_level}
6. 本候选侧重点：{variant}{memory_block}
""".strip()
    user = f"当前聊天内容：\n{request.chat_text.strip()}"
    return [LLMMessage(role="system", content=system), LLMMessage(role="user", content=user)]


def _session_title(chat_text: str) -> str:
    compact = " ".join(chat_text.strip().split())
    return compact[:32] or "新的帮聊会话"


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _temperature_for(index: int) -> float:
    return min(0.9, 0.55 + index * 0.08)


def _estimate_tokens(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, len(stripped) // 2)


def _request_summary(request: ReplyGenerationRequest) -> str:
    return json.dumps(
        {
            "chat_text_preview": request.chat_text[:120],
            "target_id": request.target_id,
            "target_name": request.target_name,
            "reply_goal": request.reply_goal,
            "tone": request.tone,
            "length": request.length,
            "proactivity": request.proactivity,
            "risk_level": request.risk_level,
            "candidate_count": request.candidate_count,
        },
        ensure_ascii=False,
    )