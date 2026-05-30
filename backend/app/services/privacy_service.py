from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AppSetting,
    ChatSession,
    ChatTarget,
    Conversation,
    Job,
    LLMCall,
    Memory,
    SavedReply,
    StylePreset,
    StyleTestMessage,
    StyleTestSession,
    UserProfile,
    UserProfileVersion,
)
from app.jobs.runner import update_job
from app.paths import APP_DATA_DIR, BACKUPS_DIR, DB_DIR, IMPORTS_DIR, LOGS_DIR, SCREENSHOTS_DIR, ensure_app_dirs

COUNTED_MODELS = {
    "app_settings": AppSetting,
    "llm_calls": LLMCall,
    "jobs": Job,
    "user_profiles": UserProfile,
    "user_profile_versions": UserProfileVersion,
    "style_presets": StylePreset,
    "style_test_sessions": StyleTestSession,
    "style_test_messages": StyleTestMessage,
    "chat_targets": ChatTarget,
    "chat_sessions": ChatSession,
    "conversations": Conversation,
    "memories": Memory,
    "saved_replies": SavedReply,
}


def data_summary(db: Session) -> dict[str, object]:
    ensure_app_dirs()
    return {
        "data_path": str(APP_DATA_DIR),
        "db_path": str(DB_DIR / "app.sqlite"),
        "screenshots_path": str(SCREENSHOTS_DIR),
        "imports_path": str(IMPORTS_DIR),
        "logs_path": str(LOGS_DIR),
        "backups_path": str(BACKUPS_DIR),
        "total_size_bytes": _directory_size(APP_DATA_DIR),
        "section_sizes": {
            "db": _directory_size(DB_DIR),
            "screenshots": _directory_size(SCREENSHOTS_DIR),
            "imports": _directory_size(IMPORTS_DIR),
            "logs": _directory_size(LOGS_DIR),
            "backups": _directory_size(BACKUPS_DIR),
        },
        "table_counts": _table_counts(db),
    }


def export_backup(db: Session, job_id: int) -> dict[str, object]:
    ensure_app_dirs()
    update_job(db, job_id, status="running", progress=0.1)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%SZ")
    backup_path = BACKUPS_DIR / f"ai-chat-wingman-backup-{timestamp}.zip"
    included_files = _write_backup_zip(backup_path)
    update_job(db, job_id, progress=0.9)
    return {
        "backup_path": _relative_data_path(backup_path),
        "backup_size_bytes": backup_path.stat().st_size,
        "included_file_count": included_files,
        "data_path": str(APP_DATA_DIR),
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def _table_counts(db: Session) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name, model in COUNTED_MODELS.items():
        counts[name] = int(db.scalar(select(func.count()).select_from(model)) or 0)
    return counts


def _directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def _write_backup_zip(backup_path: Path) -> int:
    included = 0
    with ZipFile(backup_path, mode="w", compression=ZIP_DEFLATED) as archive:
        for root in (DB_DIR, SCREENSHOTS_DIR, IMPORTS_DIR, LOGS_DIR):
            included += _add_directory(archive, root)
    return included


def _add_directory(archive: ZipFile, directory: Path) -> int:
    if not directory.exists():
        return 0
    count = 0
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        archive.write(path, _relative_data_path(path))
        count += 1
    return count


def _relative_data_path(path: Path) -> str:
    try:
        return path.relative_to(APP_DATA_DIR).as_posix()
    except ValueError:
        return path.name
