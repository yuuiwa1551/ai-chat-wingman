from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import delete, func, select
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
from app.paths import APP_DATA_DIR, BACKUPS_DIR, DB_DIR, IMPORTS_DIR, LOGS_DIR, SCREENSHOTS_DIR, SECRET_KEY_PATH, ensure_app_dirs

PURGE_CONFIRM_TEXT = "DELETE"

# User-generated data tables, cleared on a full purge. Provider config
# (app_settings) and seeded style presets are preserved unless explicitly asked.
PURGEABLE_MODELS = (
    Conversation,
    SavedReply,
    Memory,
    ChatSession,
    ChatTarget,
    StyleTestMessage,
    StyleTestSession,
    UserProfileVersion,
    UserProfile,
    LLMCall,
    Job,
)

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


def purge_all_data(db: Session, include_settings: bool = False) -> dict[str, object]:
    """Delete all user-generated data and clear local data directories.

    Provider configuration and seeded style presets are preserved unless
    ``include_settings`` is True. Callers must enforce the confirmation gate.
    """
    ensure_app_dirs()
    deleted_rows: dict[str, int] = {}
    for model in PURGEABLE_MODELS:
        result = db.execute(delete(model))
        deleted_rows[model.__tablename__] = int(result.rowcount or 0)
    if include_settings:
        deleted_rows["app_settings"] = int(db.execute(delete(AppSetting)).rowcount or 0)
        deleted_rows["style_presets"] = int(db.execute(delete(StylePreset)).rowcount or 0)
    db.commit()

    removed_files = 0
    for directory in (SCREENSHOTS_DIR, IMPORTS_DIR, BACKUPS_DIR, LOGS_DIR):
        removed_files += _clear_directory(directory)
    if include_settings and SECRET_KEY_PATH.exists():
        try:
            SECRET_KEY_PATH.unlink()
            removed_files += 1
        except OSError:
            pass
    ensure_app_dirs()
    return {
        "deleted_rows": deleted_rows,
        "removed_files": removed_files,
        "include_settings": include_settings,
    }


def _clear_directory(directory: Path) -> int:
    if not directory.exists():
        return 0
    removed = 0
    for path in sorted(directory.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        try:
            if path.is_file():
                path.unlink()
                removed += 1
            elif path.is_dir():
                path.rmdir()
        except OSError:
            continue
    return removed


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
