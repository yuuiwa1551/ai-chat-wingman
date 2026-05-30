from __future__ import annotations

import json
from collections import Counter
from typing import Any, Iterable

from app.importers.base_importer import ChatImportResult, ImportedChatMessage

CONTENT_KEYS = ("content", "text", "message", "msg", "raw_message", "body")
SENDER_KEYS = ("sender", "sender_name", "nickname", "nick", "from", "from_name", "user", "username", "uin", "qq")
TIME_KEYS = ("time", "timestamp", "datetime", "date", "send_time", "created_at")
MESSAGE_LIST_KEYS = ("messages", "message_list", "msgList", "msgs", "records", "items", "list", "data")


def parse_qq_json(raw: Any, me_speakers: Iterable[str], target_name: str | None = None, max_messages: int = 5000) -> ChatImportResult:
    aliases = {_normalize_speaker(alias) for alias in me_speakers if str(alias).strip()}
    if not aliases:
        raise ValueError("At least one me_speaker is required")

    records = _find_message_records(raw)
    if not records:
        raise ValueError("No message list found in QQ JSON")

    messages: list[ImportedChatMessage] = []
    for record in records[-max_messages:]:
        if not isinstance(record, dict):
            continue
        content = _message_content(record)
        if not content:
            continue
        speaker = _message_speaker(record)
        normalized_speaker = _normalize_speaker(speaker)
        role = "me" if normalized_speaker in aliases else "target" if speaker != "unknown" else "unknown"
        messages.append(
            ImportedChatMessage(
                role=role,
                speaker=speaker,
                content=content,
                timestamp=_message_time(record),
                raw=record,
            )
        )

    if not messages:
        raise ValueError("QQ JSON contains no usable text messages")

    speaker_counts = Counter(message.speaker for message in messages)
    inferred_target_name = target_name or _infer_target_name(messages)
    return ChatImportResult(messages=messages, speaker_counts=dict(speaker_counts), target_name=inferred_target_name)


def _find_message_records(raw: Any, depth: int = 0) -> list[dict[str, Any]]:
    if depth > 5:
        return []
    if isinstance(raw, list):
        dict_items = [item for item in raw if isinstance(item, dict)]
        if dict_items and sum(1 for item in dict_items[:20] if _looks_like_message(item)) >= max(1, min(len(dict_items), 20) // 2):
            return dict_items
        for item in dict_items:
            nested = _find_message_records(item, depth + 1)
            if nested:
                return nested
        return []
    if not isinstance(raw, dict):
        return []
    if _looks_like_message(raw):
        return [raw]
    for key in MESSAGE_LIST_KEYS:
        if key in raw:
            nested = _find_message_records(raw[key], depth + 1)
            if nested:
                return nested
    for value in raw.values():
        nested = _find_message_records(value, depth + 1)
        if nested:
            return nested
    return []


def _looks_like_message(record: dict[str, Any]) -> bool:
    has_content = any(key in record for key in CONTENT_KEYS)
    has_sender_or_time = any(key in record for key in SENDER_KEYS + TIME_KEYS)
    return has_content and has_sender_or_time


def _message_speaker(record: dict[str, Any]) -> str:
    for key in SENDER_KEYS:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    sender = record.get("sender") if isinstance(record.get("sender"), dict) else None
    if isinstance(sender, dict):
        for key in SENDER_KEYS:
            value = sender.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
    return "unknown"


def _message_content(record: dict[str, Any]) -> str:
    for key in CONTENT_KEYS:
        value = record.get(key)
        content = _content_to_text(value)
        if content:
            return content
    return ""


def _content_to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, int | float | bool):
        return str(value)
    if isinstance(value, list):
        parts = [_content_to_text(item) for item in value]
        return " ".join(part for part in parts if part).strip()
    if isinstance(value, dict):
        message_type = str(value.get("type") or value.get("msg_type") or "").lower()
        if "image" in message_type or "pic" in message_type:
            return "[图片]"
        if "face" in message_type or "emoji" in message_type or "emoticon" in message_type:
            return "[表情]"
        for key in ("text", "content", "name", "summary", "desc"):
            content = _content_to_text(value.get(key))
            if content:
                return content
        scalar_values = [str(item).strip() for item in value.values() if isinstance(item, str | int | float) and str(item).strip()]
        if scalar_values:
            return " ".join(scalar_values[:3])
        return json.dumps(value, ensure_ascii=False)[:200]
    return str(value).strip()


def _message_time(record: dict[str, Any]) -> str | None:
    for key in TIME_KEYS:
        value = record.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _normalize_speaker(value: object) -> str:
    return str(value).strip().lower()


def _infer_target_name(messages: list[ImportedChatMessage]) -> str | None:
    for message in messages:
        if message.role == "target" and message.speaker != "unknown":
            return message.speaker
    return None
