from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[str | None] = mapped_column(String, nullable=True)


class LLMCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
    request_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="ok", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "payload": self.payload,
            "result": self.result,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str | None] = mapped_column(String, nullable=True)
    style_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone_features: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_patterns: Mapped[str | None] = mapped_column(Text, nullable=True)
    avoid_patterns: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_guideline: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "source_type": self.source_type,
            "style_summary": self.style_summary,
            "tone_features": self.tone_features,
            "common_patterns": self.common_patterns,
            "avoid_patterns": self.avoid_patterns,
            "generation_guideline": self.generation_guideline,
            "confidence": self.confidence,
            "is_default": self.is_default,
            "current_version": self.current_version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class StylePreset(Base):
    __tablename__ = "style_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    example_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "example_reply": self.example_reply,
            "config_json": self.config_json,
            "created_at": self.created_at,
        }


class UserProfileVersion(Base):
    __tablename__ = "user_profile_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    merge_reason: Mapped[str] = mapped_column(String, nullable=False)
    source_job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    target_name: Mapped[str | None] = mapped_column(String, nullable=True)
    target_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "target_id": self.target_id,
            "title": self.title,
            "target_name": self.target_name,
            "target_strategy": self.target_strategy,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    profile_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prompt_version: Mapped[str] = mapped_column(String, nullable=False)
    llm_call_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    target_name: Mapped[str | None] = mapped_column(String, nullable=True)
    target_strategy: Mapped[str | None] = mapped_column(Text, nullable=True)
    reply_goal: Mapped[str] = mapped_column(String, nullable=False)
    tone: Mapped[str] = mapped_column(String, nullable=False)
    length: Mapped[str] = mapped_column(String, nullable=False)
    proactivity: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    generated_replies: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "chat_session_id": self.chat_session_id,
            "target_id": self.target_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "prompt_version": self.prompt_version,
            "llm_call_id": self.llm_call_id,
            "input_text": self.input_text,
            "target_name": self.target_name,
            "target_strategy": self.target_strategy,
            "reply_goal": self.reply_goal,
            "tone": self.tone,
            "length": self.length,
            "proactivity": self.proactivity,
            "risk_level": self.risk_level,
            "generated_replies": self.generated_replies,
            "selected_reply": self.selected_reply,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ChatTarget(Base):
    __tablename__ = "chat_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    relationship: Mapped[str | None] = mapped_column(String, nullable=True)
    style_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferences: Mapped[str | None] = mapped_column(Text, nullable=True)
    taboos: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategy_guideline: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "relationship": self.relationship,
            "style_summary": self.style_summary,
            "preferences": self.preferences,
            "taboos": self.taboos,
            "strategy_guideline": self.strategy_guideline,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class StyleTestSession(Base):
    __tablename__ = "style_test_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    target_type: Mapped[str] = mapped_column(String, nullable=False)
    scenario: Mapped[str] = mapped_column(Text, nullable=False)
    simulated_target_profile: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "target_type": self.target_type,
            "scenario": self.scenario,
            "simulated_target_profile": self.simulated_target_profile,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class StyleTestMessage(Base):
    __tablename__ = "style_test_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }
