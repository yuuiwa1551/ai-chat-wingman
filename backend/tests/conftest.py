from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def isolated_app_data_dir(tmp_path_factory: pytest.TempPathFactory) -> None:
    data_dir = tmp_path_factory.mktemp("ai-chat-wingman-data")
    os.environ["AI_CHAT_WINGMAN_DATA_DIR"] = str(data_dir)
