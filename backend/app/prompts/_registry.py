from __future__ import annotations

PROMPT_VERSIONS: dict[str, str] = {
    "generate_reply": "generate_reply_v1",
    "simulate_style_test": "simulate_style_test_v1",
    "analyze_style_test": "analyze_style_test_v1",
    "merge_profile": "merge_profile_v1",
    "organize_chat_target": "organize_chat_target_v1",
}


def prompt_version(prompt_name: str) -> str:
    return PROMPT_VERSIONS[prompt_name]