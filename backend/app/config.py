from __future__ import annotations

import os

DEFAULT_TASK_ROUTING: dict[str, str] = {
    "reply_generation": "text_main",
    "style_analysis": "text_main",
    "style_test_simulation": "text_main",
    "memory_extraction": "text_cheap",
    "profile_merge": "text_main",
    "screenshot_parse": "multimodal",
}


def is_dev_mode() -> bool:
    return os.getenv("AI_CHAT_WINGMAN_DEV", "0") == "1"
