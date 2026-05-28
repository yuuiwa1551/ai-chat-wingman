from __future__ import annotations

PROMPT_VERSIONS: dict[str, str] = {
    "generate_reply": "generate_reply_v1",
}


def prompt_version(prompt_name: str) -> str:
    return PROMPT_VERSIONS[prompt_name]