from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.db.models import ChatTarget, UserProfile, UserProfileVersion
from app.importers.base_importer import ImportedChatMessage
from app.importers.qq_json_importer import parse_qq_json
from app.jobs.runner import update_job
from app.paths import IMPORTS_DIR
from app.services.target_service import create_target, get_target, update_target
from app.settings_store import utc_now


def process_qq_json_import_payload(db: Session, job_id: int, payload: dict[str, Any]) -> dict[str, object]:
    update_job(db, job_id, status="running", progress=0.08)
    raw_json = _raw_json_from_payload(payload)
    stored_raw_path = _store_raw_json(job_id, payload.get("filename"), raw_json)

    update_job(db, job_id, progress=0.25)
    import_result = parse_qq_json(
        raw_json,
        me_speakers=payload.get("me_speakers") or [],
        target_name=_clean_optional(payload.get("target_name")),
        max_messages=int(payload.get("max_messages") or 5000),
    )
    user_messages = import_result.role_messages("me")
    target_messages = import_result.role_messages("target")
    if not user_messages:
        raise ValueError("Import did not identify any user messages; check me_speakers")
    if not target_messages:
        raise ValueError("Import did not identify any target messages")

    update_job(db, job_id, progress=0.55)
    user_analysis = analyze_user_style(user_messages)
    target_analysis = analyze_target_style(target_messages, import_result.target_name)

    update_job(db, job_id, progress=0.78)
    profile = _create_chat_import_profile(db, user_analysis, job_id)
    target = _create_or_update_target(db, payload.get("target_id"), import_result.target_name, target_analysis)

    return {
        "import_id": job_id,
        "raw_path": stored_raw_path,
        "message_count": len(import_result.messages),
        "user_message_count": len(user_messages),
        "target_message_count": len(target_messages),
        "speaker_counts": import_result.speaker_counts,
        "messages_preview": import_result.preview(),
        "profile": profile.to_dict(),
        "target": target.to_dict(),
        "analysis": {"user": user_analysis, "target": target_analysis},
    }


def analyze_user_style(messages: list[ImportedChatMessage]) -> dict[str, object]:
    stats = _message_stats(messages)
    common_patterns = _common_patterns(stats, subject="用户")
    avoid_patterns = ["避免突然变得过度正式或客服化", "避免生成明显 AI 腔的完整套话"]
    if stats["avg_length"] <= 24:
        avoid_patterns.append("避免长篇大论，优先保留短句和自然停顿")
    else:
        avoid_patterns.append("避免把用户本来较完整的表达压缩得太生硬")

    return {
        "style_summary": _style_summary(stats, subject="用户"),
        "tone_features": {
            "sentence_length": _length_label(stats["avg_length"]),
            "humor_level": stats["humor_rate"],
            "empathy_level": stats["empathy_rate"],
            "initiative_level": stats["question_rate"],
            "directness": stats["directness"],
            "formality": stats["formality"],
        },
        "common_patterns": common_patterns,
        "avoid_patterns": avoid_patterns,
        "generation_guideline": "生成回复时贴近导入记录里的用户表达：保持自然、可复制，不突然拔高成过度完美的表达；在原风格上补足情绪承接和边界感。",
    }


def analyze_target_style(messages: list[ImportedChatMessage], target_name: str | None) -> dict[str, str]:
    stats = _message_stats(messages)
    name = target_name or "聊天对象"
    preferences = _target_preferences(stats)
    taboos = _target_taboos(stats)
    return {
        "relationship": "由 QQ 导入记录生成，关系待用户确认",
        "style_summary": _style_summary(stats, subject=name),
        "preferences": "\n".join(preferences),
        "taboos": "\n".join(taboos),
        "strategy_guideline": "回复时先参考对象历史表达节奏：接住情绪，少替对方下判断；如果对方偏短句或低主动，就给空间，不连续追问。",
    }


def _raw_json_from_payload(payload: dict[str, Any]) -> Any:
    if payload.get("raw_json") is not None:
        return payload["raw_json"]
    raw_text = payload.get("raw_text")
    if isinstance(raw_text, str) and raw_text.strip():
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError("raw_text must be valid JSON") from exc
    raise ValueError("raw_json or raw_text is required")


def _store_raw_json(job_id: int, filename: object, raw_json: Any) -> str:
    directory = IMPORTS_DIR / str(job_id)
    directory.mkdir(parents=True, exist_ok=True)
    safe_filename = _safe_filename(str(filename or "raw.json"))
    if not safe_filename.endswith(".json"):
        safe_filename = f"{safe_filename}.json"
    path = directory / safe_filename
    path.write_text(json.dumps(raw_json, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(Path("imports") / str(job_id) / safe_filename).replace("\\", "/")


def _safe_filename(filename: str) -> str:
    name = Path(filename).name.strip() or "raw.json"
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)[:120] or "raw.json"


def _create_chat_import_profile(db: Session, analysis: dict[str, object], job_id: int) -> UserProfile:
    now = utc_now()
    db.execute(update(UserProfile).values(is_default=False))
    profile = UserProfile(
        name="QQ 导入人设",
        source_type="chat_import",
        style_summary=str(analysis["style_summary"]),
        tone_features=json.dumps(analysis["tone_features"], ensure_ascii=False),
        common_patterns=json.dumps(analysis["common_patterns"], ensure_ascii=False),
        avoid_patterns=json.dumps(analysis["avoid_patterns"], ensure_ascii=False),
        generation_guideline=str(analysis["generation_guideline"]),
        confidence=0.72,
        is_default=True,
        current_version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    db.add(
        UserProfileVersion(
            profile_id=profile.id,
            version=profile.current_version,
            snapshot_json=json.dumps({**profile.to_dict(), "source_job_id": job_id}, ensure_ascii=False),
            merge_reason="chat_import_create",
            source_job_id=job_id,
            created_at=utc_now(),
        )
    )
    db.commit()
    return profile


def _create_or_update_target(db: Session, target_id: object, target_name: str | None, analysis: dict[str, str]) -> ChatTarget:
    payload = {
        "relationship": analysis["relationship"],
        "style_summary": analysis["style_summary"],
        "preferences": analysis["preferences"],
        "taboos": analysis["taboos"],
        "strategy_guideline": analysis["strategy_guideline"],
    }
    if target_id is not None:
        target = get_target(db, int(target_id))
        return update_target(db, target.id, payload)
    return create_target(db, name=target_name or "QQ 导入对象", **payload)


def _message_stats(messages: list[ImportedChatMessage]) -> dict[str, float]:
    count = max(1, len(messages))
    lengths = [len(message.content.strip()) for message in messages]
    avg_length = sum(lengths) / count
    question_count = sum(1 for message in messages if "?" in message.content or "？" in message.content)
    humor_count = sum(1 for message in messages if _contains_any(message.content, ("哈哈", "hhh", "笑死", "草", "绷", "乐")))
    empathy_count = sum(1 for message in messages if _contains_any(message.content, ("辛苦", "抱抱", "没事", "别急", "理解", "慢慢", "休息")))
    formal_count = sum(1 for message in messages if _contains_any(message.content, ("您好", "请问", "感谢", "麻烦", "建议")))
    direct_count = sum(1 for message in messages if _contains_any(message.content, ("我觉得", "直接", "不用", "别", "可以", "不想")))
    return {
        "count": float(count),
        "avg_length": round(avg_length, 2),
        "question_rate": round(question_count / count, 2),
        "humor_rate": round(humor_count / count, 2),
        "empathy_rate": round(empathy_count / count, 2),
        "formality": round(formal_count / count, 2),
        "directness": round(max(0.25, direct_count / count), 2),
    }


def _style_summary(stats: dict[str, float], subject: str) -> str:
    length_desc = {"short": "偏短句", "medium": "长度适中", "long": "表达较完整"}[_length_label(stats["avg_length"])]
    traits = [f"{subject}在导入记录中平均每条约 {stats['avg_length']} 个字，整体{length_desc}"]
    if stats["humor_rate"] >= 0.15:
        traits.append("经常用轻微玩笑或吐槽缓和语气")
    if stats["empathy_rate"] >= 0.12:
        traits.append("会主动承接情绪")
    if stats["question_rate"] >= 0.25:
        traits.append("会用问句推进话题")
    if stats["formality"] <= 0.08:
        traits.append("表达不太正式，更接近日常聊天")
    return "；".join(traits) + "。"


def _common_patterns(stats: dict[str, float], subject: str) -> list[str]:
    patterns = [f"{subject}表达{_length_pattern(stats['avg_length'])}"]
    if stats["question_rate"] >= 0.25:
        patterns.append("会通过问句维持对话")
    if stats["humor_rate"] >= 0.15:
        patterns.append("会使用轻微玩笑、吐槽或笑声")
    if stats["empathy_rate"] >= 0.12:
        patterns.append("面对负面情绪时会先安抚")
    if len(patterns) == 1:
        patterns.append("整体偏自然口语，不宜生成过度修饰的回复")
    return patterns


def _target_preferences(stats: dict[str, float]) -> list[str]:
    preferences = [f"更适合{_length_pattern(stats['avg_length'])}的回复"]
    if stats["question_rate"] < 0.18:
        preferences.append("对方历史消息里主动提问不多，适合低压力承接")
    if stats["empathy_rate"] >= 0.12:
        preferences.append("对方能接受情绪承接，但不宜过度拔高")
    return preferences


def _target_taboos(stats: dict[str, float]) -> list[str]:
    taboos = ["不要连续追问或替对方下判断"]
    if stats["avg_length"] <= 20:
        taboos.append("不要突然长篇输出，避免和对方节奏不匹配")
    if stats["formality"] <= 0.08:
        taboos.append("不要写得像客服或正式公文")
    return taboos


def _length_label(avg_length: float) -> str:
    if avg_length <= 18:
        return "short"
    if avg_length >= 48:
        return "long"
    return "medium"


def _length_pattern(avg_length: float) -> str:
    return {"short": "短句、轻量", "medium": "自然、长度适中", "long": "信息较完整"}[_length_label(avg_length)]


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None
