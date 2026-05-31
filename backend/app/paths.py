from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "AIChatWingman"


def _default_data_root() -> Path:
    override = os.getenv("AI_CHAT_WINGMAN_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if sys.platform == "win32":
        base = os.getenv("APPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
        return Path.home() / "AppData" / "Roaming" / APP_DIR_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME

    return Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME


APP_DATA_DIR = _default_data_root()
DB_DIR = APP_DATA_DIR / "db"
SCREENSHOTS_DIR = APP_DATA_DIR / "screenshots"
IMPORTS_DIR = APP_DATA_DIR / "imports"
LOGS_DIR = APP_DATA_DIR / "logs"
BACKUPS_DIR = APP_DATA_DIR / "backups"
SECRET_KEY_PATH = APP_DATA_DIR / "secret.key"


def ensure_app_dirs() -> None:
    for directory in (APP_DATA_DIR, DB_DIR, SCREENSHOTS_DIR, IMPORTS_DIR, LOGS_DIR, BACKUPS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def database_path() -> Path:
    ensure_app_dirs()
    return DB_DIR / "app.sqlite"


ensure_app_dirs()
