from __future__ import annotations

import json

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import StylePreset, UserProfile, UserProfileVersion
from app.settings_store import utc_now

STYLE_PRESET_SEED: list[dict[str, object]] = [
    {
        "name": "自然随和型",
        "description": "表达自然、不端着，适合日常轻松聊天。",
        "example_reply": "还行，今天就是普通打工人续命的一天。",
        "config": {"humor_level": 0.35, "empathy_level": 0.55, "directness": 0.45, "formality": 0.2},
    },
    {
        "name": "轻松幽默型",
        "description": "用轻微玩笑缓和气氛，但不过度油腻。",
        "example_reply": "懂了，今天是被工作吸干电量了。",
        "config": {"humor_level": 0.7, "empathy_level": 0.5, "directness": 0.45, "formality": 0.15},
    },
    {
        "name": "温柔共情型",
        "description": "优先接住情绪，表达稳定、柔和。",
        "example_reply": "听起来今天真的挺耗人的，你先缓一会儿也没关系。",
        "config": {"humor_level": 0.2, "empathy_level": 0.8, "directness": 0.35, "formality": 0.25},
    },
    {
        "name": "冷静克制型",
        "description": "回复简洁、边界清楚，不强行热络。",
        "example_reply": "明白，那你先休息，想说的时候我在。",
        "config": {"humor_level": 0.15, "empathy_level": 0.55, "directness": 0.6, "formality": 0.35},
    },
    {
        "name": "直接坦率型",
        "description": "表达明确，不绕弯，适合高效率沟通。",
        "example_reply": "我懂，你现在应该就是想先安静一下。",
        "config": {"humor_level": 0.25, "empathy_level": 0.5, "directness": 0.8, "formality": 0.25},
    },
    {
        "name": "嘴硬吐槽型",
        "description": "带一点吐槽感，外壳轻松，内里有关心。",
        "example_reply": "行，今天先允许你当一会儿低电量人类。",
        "config": {"humor_level": 0.75, "empathy_level": 0.45, "directness": 0.55, "formality": 0.1},
    },
    {
        "name": "理性分析型",
        "description": "更偏分析和拆解问题，不急着煽情。",
        "example_reply": "感觉主要是工作把你的精力压满了，先别急着处理别的。",
        "config": {"humor_level": 0.2, "empathy_level": 0.45, "directness": 0.7, "formality": 0.45},
    },
    {
        "name": "高情商稳妥型",
        "description": "兼顾情绪承接、边界和继续聊天的空间。",
        "example_reply": "那你先缓缓，我不追问。等你想说了我再听。",
        "config": {"humor_level": 0.3, "empathy_level": 0.75, "directness": 0.55, "formality": 0.3},
    },
]


def seed_style_presets() -> None:
    with SessionLocal() as db:
        has_presets = db.scalar(select(StylePreset.id).limit(1)) is not None
        if has_presets:
            return
        now = utc_now()
        for item in STYLE_PRESET_SEED:
            db.add(
                StylePreset(
                    name=str(item["name"]),
                    description=str(item["description"]),
                    example_reply=str(item["example_reply"]),
                    config_json=json.dumps(item["config"], ensure_ascii=False),
                    created_at=now,
                )
            )
        db.commit()


def style_presets(db: Session) -> list[StylePreset]:
    return list(db.scalars(select(StylePreset).order_by(StylePreset.id)).all())


def default_profile(db: Session) -> UserProfile | None:
    return db.scalars(select(UserProfile).where(UserProfile.is_default.is_(True)).limit(1)).first()


def create_default_profile(db: Session, name: str, selected_preset_ids: list[int], avoid_patterns: list[str]) -> UserProfile:
    presets = list(db.scalars(select(StylePreset).where(StylePreset.id.in_(selected_preset_ids))).all())
    if len(presets) != len(set(selected_preset_ids)):
        raise ValueError("Selected style preset does not exist")

    db.execute(update(UserProfile).where(UserProfile.is_default.is_(True)).values(is_default=False))
    now = utc_now()
    profile = UserProfile(
        name=name,
        source_type="preset",
        style_summary=_style_summary(presets),
        tone_features=json.dumps(_merge_tone_features(presets), ensure_ascii=False),
        common_patterns=json.dumps([preset.name for preset in presets], ensure_ascii=False),
        avoid_patterns=json.dumps(_clean_patterns(avoid_patterns), ensure_ascii=False),
        generation_guideline=_generation_guideline(presets, avoid_patterns),
        confidence=0.55,
        is_default=True,
        current_version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    snapshot = profile.to_dict()
    db.add(
        UserProfileVersion(
            profile_id=profile.id,
            version=1,
            snapshot_json=json.dumps(snapshot, ensure_ascii=False),
            merge_reason="onboarding_preset",
            created_at=now,
        )
    )
    db.commit()
    db.refresh(profile)
    return profile


def _clean_patterns(patterns: list[str]) -> list[str]:
    return [pattern.strip() for pattern in patterns if pattern.strip()]


def _style_summary(presets: list[StylePreset]) -> str:
    names = "、".join(preset.name for preset in presets)
    return f"用户冷启动选择了 {names}，生成回复应先贴近这些表达倾向，再根据上下文调整。"


def _generation_guideline(presets: list[StylePreset], avoid_patterns: list[str]) -> str:
    names = "、".join(preset.name for preset in presets)
    style_text = names or "自然"
    avoids = "、".join(_clean_patterns(avoid_patterns)) or "不要像 AI、不要突然换人设"
    return f"保持{style_text}的表达基调；优先自然、可复制、不过度表演；避免：{avoids}。"


def _merge_tone_features(presets: list[StylePreset]) -> dict[str, float | str]:
    totals: dict[str, float] = {}
    for preset in presets:
        config = json.loads(preset.config_json or "{}")
        for key, value in config.items():
            if isinstance(value, int | float):
                totals[key] = totals.get(key, 0.0) + float(value)
    count = max(len(presets), 1)
    merged = {key: round(value / count, 2) for key, value in totals.items()}
    merged["sentence_length"] = "medium"
    return merged
