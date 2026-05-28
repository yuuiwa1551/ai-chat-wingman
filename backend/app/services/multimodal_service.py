from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db.models import LLMCall
from app.llm.base import LLMProvider
from app.llm.router import provider_for_task
from app.paths import SCREENSHOTS_DIR
from app.prompts._registry import prompt_version
from app.settings_store import utc_now

PARSE_SCREENSHOT_PROMPT_VERSION = prompt_version("parse_chat_screenshot")
MAX_IMAGE_BYTES = 5 * 1024 * 1024
SUPPORTED_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


@dataclass(frozen=True)
class ParsedChatMessage:
    speaker: str
    content: str
    time: str

    def to_dict(self) -> dict[str, str]:
        return {"speaker": self.speaker, "content": self.content, "time": self.time}


@dataclass(frozen=True)
class ScreenshotParseResult:
    messages: list[ParsedChatMessage]
    summary: str
    uncertain_parts: list[str]
    stored_image_path: str

    def to_dict(self) -> dict[str, object]:
        return {
            "messages": [message.to_dict() for message in self.messages],
            "summary": self.summary,
            "uncertain_parts": self.uncertain_parts,
            "stored_image_path": self.stored_image_path,
        }


async def parse_chat_screenshot(
    db: Session,
    image_base64: str,
    mime_type: str,
    filename: str | None = None,
) -> tuple[ScreenshotParseResult, LLMCall]:
    clean_mime_type = _normalize_mime_type(mime_type)
    image_bytes = _decode_image_base64(image_base64)
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 5 MB or smaller")

    stored_image_path = _store_screenshot(image_bytes, clean_mime_type)
    data_url = f"data:{clean_mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"

    provider = provider_for_task(db, "screenshot_parse")
    messages = build_screenshot_parse_messages(data_url)
    request_summary = json.dumps(
        {
            "filename": filename,
            "mime_type": clean_mime_type,
            "image_bytes": len(image_bytes),
            "stored_image_path": stored_image_path,
        },
        ensure_ascii=False,
    )
    started = perf_counter()
    try:
        response = await provider.complete_multimodal(messages, temperature=0.1)
        result = _parse_response_text(response.text, stored_image_path)
        llm_call = _log_llm_call(db, provider, request_summary, result.summary, started, "ok", response)
    except Exception as exc:
        _log_llm_call(db, provider, request_summary, "", started, "error", error_message=str(exc))
        raise
    return result, llm_call


def build_screenshot_parse_messages(data_url: str) -> list[dict[str, object]]:
    system_prompt = """
你是一个聊天截图解析器。
请阅读用户上传的聊天截图，提取其中可见的聊天内容。
只输出严格 JSON，不要输出 Markdown。
""".strip()
    user_prompt = """
请输出 JSON：
{
  "messages": [
    {"speaker": "me/target/unknown", "content": "...", "time": "...或 unknown"}
  ],
  "summary": "...",
  "uncertain_parts": []
}

要求：
- 尽量按截图中的上下顺序输出
- 不确定说话人时标记为 unknown
- 不要编造截图中没有的内容
- 表情包或图片可以描述其大致含义
- 如果有被遮挡或看不清的文字，放入 uncertain_parts
""".strip()
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]


def _parse_response_text(text: str, stored_image_path: str) -> ScreenshotParseResult:
    parsed = json.loads(_extract_json(text))
    if not isinstance(parsed, dict):
        raise ValueError("Screenshot parser returned non-object JSON")
    messages = [_parse_message(item) for item in parsed.get("messages") or []]
    if not messages:
        raise ValueError("Screenshot parser returned no messages")
    uncertain_parts = parsed.get("uncertain_parts") or []
    if not isinstance(uncertain_parts, list):
        uncertain_parts = [str(uncertain_parts)]
    return ScreenshotParseResult(
        messages=messages,
        summary=str(parsed.get("summary") or "未能生成截图摘要。"),
        uncertain_parts=[str(item) for item in uncertain_parts if str(item).strip()],
        stored_image_path=stored_image_path,
    )


def _parse_message(raw: Any) -> ParsedChatMessage:
    if not isinstance(raw, dict):
        raise ValueError("Screenshot parser returned an invalid message")
    speaker = str(raw.get("speaker") or "unknown").strip().lower()
    if speaker not in {"me", "target", "unknown"}:
        speaker = "unknown"
    content = str(raw.get("content") or "").strip()
    if not content:
        raise ValueError("Screenshot parser returned an empty message")
    return ParsedChatMessage(speaker=speaker, content=content, time=str(raw.get("time") or "unknown").strip() or "unknown")


def _decode_image_base64(image_base64: str) -> bytes:
    payload = image_base64.strip()
    if "," in payload and payload.startswith("data:"):
        payload = payload.split(",", 1)[1]
    try:
        return base64.b64decode(payload, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64 image payload") from exc


def _normalize_mime_type(mime_type: str) -> str:
    clean_mime_type = mime_type.split(";", 1)[0].strip().lower()
    if clean_mime_type not in SUPPORTED_MIME_TYPES:
        raise ValueError("Only PNG, JPEG, and WebP screenshots are supported")
    return clean_mime_type


def _store_screenshot(image_bytes: bytes, mime_type: str) -> str:
    month = datetime.now(UTC).strftime("%Y-%m")
    directory = SCREENSHOTS_DIR / month
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{uuid4().hex}{SUPPORTED_MIME_TYPES[mime_type]}"
    path.write_bytes(image_bytes)
    return str(Path("screenshots") / month / path.name).replace("\\", "/")


def _log_llm_call(
    db: Session,
    provider: LLMProvider,
    request_summary: str,
    response_summary: str,
    started: float,
    status: str,
    response: object | None = None,
    error_message: str | None = None,
) -> LLMCall:
    llm_call = LLMCall(
        task="screenshot_parse",
        provider=provider.provider_id,
        model=provider.model,
        prompt_version=PARSE_SCREENSHOT_PROMPT_VERSION,
        request_summary=request_summary,
        response_summary=response_summary,
        prompt_tokens=getattr(response, "prompt_tokens", None),
        completion_tokens=getattr(response, "completion_tokens", None),
        total_tokens=getattr(response, "total_tokens", None),
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


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object found")
    return stripped[start : end + 1]