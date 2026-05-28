from __future__ import annotations

import importlib
import time

from fastapi.testclient import TestClient


def test_paths_create_app_dirs(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AI_CHAT_WINGMAN_DATA_DIR", str(tmp_path / "data"))
    import app.paths as paths

    importlib.reload(paths)
    assert paths.database_path().parent.exists()
    assert paths.SCREENSHOTS_DIR.exists()


def test_health_and_demo_sse() -> None:
    from app.main import create_app

    with TestClient(create_app()) as client:
        assert client.get("/healthz").json() == {"status": "ok"}
        response = client.get("/demo/sse")
        assert response.status_code == 200
        assert "event: token" in response.text
        assert "event: done" in response.text


def test_mock_provider() -> None:
    import asyncio

    from app.llm.base import LLMMessage
    from app.llm.mock_provider import MockProvider

    async def run() -> str:
        response = await MockProvider().complete([LLMMessage(role="user", content="hello")])
        return response.text

    assert asyncio.run(run()) == "mock reply: hello"


def test_provider_settings_test_logs_llm_call(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AI_CHAT_WINGMAN_DATA_DIR", str(tmp_path / "provider-data"))

    from app.main import create_app

    with TestClient(create_app()) as client:
        payload = {"id": "local-mock", "type": "mock", "default_model": "mock-chat", "enabled": True}
        upsert_response = client.put("/settings/llm/providers/local-mock", json=payload)
        assert upsert_response.status_code == 200

        test_response = client.post("/settings/llm/providers/local-mock/test")
        assert test_response.status_code == 200
        body = test_response.json()
        assert body["ok"] is True
        assert body["llm_call_id"] >= 1


def test_demo_job_reaches_success(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AI_CHAT_WINGMAN_DATA_DIR", str(tmp_path / "job-data"))

    from app.main import create_app

    with TestClient(create_app()) as client:
        start_response = client.post("/jobs/demo", json={"duration_seconds": 0})
        assert start_response.status_code == 200
        job_id = start_response.json()["job_id"]

        final_body = None
        for _ in range(10):
            job_response = client.get(f"/jobs/{job_id}")
            assert job_response.status_code == 200
            final_body = job_response.json()
            if final_body["status"] == "success":
                break
            time.sleep(0.05)

        assert final_body is not None
        assert final_body["status"] == "success"
        assert final_body["progress"] == 1.0
