from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ImportedChatMessage:
    role: str
    speaker: str
    content: str
    timestamp: str | None
    raw: dict[str, Any]

    def to_dict(self) -> dict[str, object]:
        return {
            "role": self.role,
            "speaker": self.speaker,
            "content": self.content,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class ChatImportResult:
    messages: list[ImportedChatMessage]
    speaker_counts: dict[str, int]
    target_name: str | None

    def role_messages(self, role: str) -> list[ImportedChatMessage]:
        return [message for message in self.messages if message.role == role]

    def preview(self, limit: int = 8) -> list[dict[str, object]]:
        return [message.to_dict() for message in self.messages[:limit]]
