from __future__ import annotations

import importlib
import json
import os
import time

from fastapi.testclient import TestClient


def test_paths_create_app_dirs() -> None:
    import app.paths as paths

    importlib.reload(paths)
    assert str(paths.APP_DATA_DIR) == os.environ["AI_CHAT_WINGMAN_DATA_DIR"]
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


def test_provider_settings_test_logs_llm_call() -> None:
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


def test_demo_job_reaches_success() -> None:
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


def test_onboarding_presets_and_default_profile() -> None:
    from app.main import create_app

    with TestClient(create_app()) as client:
        presets_response = client.get("/onboarding/style-presets")
        assert presets_response.status_code == 200
        presets = presets_response.json()["presets"]
        assert len(presets) >= 8

        status_response = client.get("/onboarding/status")
        assert status_response.json()["has_default_profile"] is False

        save_response = client.post(
            "/onboarding/default-profile",
            json={
                "name": "默认人设",
                "selected_preset_ids": [presets[0]["id"], presets[1]["id"]],
                "avoid_patterns": ["不要太油", "不要像 AI"],
            },
        )
        assert save_response.status_code == 200
        profile = save_response.json()["profile"]
        assert profile["source_type"] == "preset"
        assert profile["is_default"] is True

        next_status = client.get("/onboarding/status").json()
        assert next_status["has_default_profile"] is True
        assert next_status["default_profile_id"] == profile["id"]


def test_reply_generation_stream_saves_conversation_and_selection() -> None:
    from app.db.database import SessionLocal
    from app.db.models import Conversation, LLMCall
    from app.main import create_app

    with TestClient(create_app()) as client:
        presets = client.get("/onboarding/style-presets").json()["presets"]
        if not client.get("/onboarding/status").json()["has_default_profile"]:
            client.post(
                "/onboarding/default-profile",
                json={"name": "默认人设", "selected_preset_ids": [presets[0]["id"]], "avoid_patterns": ["不要像 AI"]},
            )

        response = client.post(
            "/reply/generate",
            json={
                "chat_text": "对方：今天真的累死了，不太想说话。",
                "target_name": "小夏",
                "target_strategy": "先接住情绪，不要追问太多。",
                "reply_goal": "安慰并保留继续聊天空间",
                "tone": "自然温柔",
                "length": "短",
                "proactivity": 0.35,
                "risk_level": "稳妥",
                "candidate_count": 3,
            },
        )
        assert response.status_code == 200
        assert "event: token" in response.text
        done = _sse_payload(response.text, "done")
        assert done["conversation_id"] >= 1
        assert done["llm_call_id"] >= 1
        assert len(done["replies"]) == 3

        with SessionLocal() as db:
            conversation = db.get(Conversation, done["conversation_id"])
            assert conversation is not None
            assert conversation.prompt_version == "generate_reply_v1"
            assert conversation.llm_call_id == done["llm_call_id"]
            assert json.loads(conversation.generated_replies or "[]") == done["replies"]
            llm_call = db.get(LLMCall, done["llm_call_id"])
            assert llm_call is not None
            assert llm_call.task == "reply_generation"

        select_response = client.post(f"/reply/{done['conversation_id']}/select", json={"selected_index": 0})
        assert select_response.status_code == 200
        selected = select_response.json()["conversation"]["selected_reply"]
        assert selected == done["replies"][0]


def test_style_test_session_message_and_analysis_updates_profile() -> None:
    from app.db.database import SessionLocal
    from app.db.models import StyleTestMessage, StyleTestSession, UserProfile, UserProfileVersion
    from app.main import create_app

    with TestClient(create_app()) as client:
        presets = client.get("/onboarding/style-presets").json()["presets"]
        if not client.get("/onboarding/status").json()["has_default_profile"]:
            client.post(
                "/onboarding/default-profile",
                json={"name": "默认人设", "selected_preset_ids": [presets[0]["id"]], "avoid_patterns": ["不要像 AI"]},
            )

        create_response = client.post(
            "/style-test/sessions",
            json={"target_type": "朋友", "scenario": "对方工作很累，回复欲望不高。"},
        )
        assert create_response.status_code == 200
        session_id = create_response.json()["session"]["id"]

        message_response = client.post(f"/style-test/sessions/{session_id}/message", json={"content": "那你先歇会儿，不急着回我。"})
        assert message_response.status_code == 200
        assert "event: token" in message_response.text
        done = _sse_payload(message_response.text, "done")
        assert done["message_id"] >= 1
        assert done["text"]

        analysis_response = client.post(f"/style-test/sessions/{session_id}/analysis")
        assert analysis_response.status_code == 200
        body = analysis_response.json()
        assert body["analysis"]["style_summary"]
        assert body["profile"]["source_type"] == "style_test"
        assert body["profile"]["current_version"] >= 2

        with SessionLocal() as db:
            session = db.get(StyleTestSession, session_id)
            assert session is not None
            assert session.status == "analyzed"
            messages = db.query(StyleTestMessage).filter(StyleTestMessage.session_id == session_id).all()
            assert {message.role for message in messages} == {"user", "simulated_target"}
            profile = db.get(UserProfile, body["profile"]["id"])
            assert profile is not None
            versions = db.query(UserProfileVersion).filter(UserProfileVersion.profile_id == profile.id).all()
            assert any(version.merge_reason == "style_test_merge" for version in versions)


def test_chat_targets_crud_organize_and_reply_uses_target_profile() -> None:
    from app.db.database import SessionLocal
    from app.db.models import ChatTarget, Conversation, LLMCall
    from app.main import create_app

    with TestClient(create_app()) as client:
        create_response = client.post(
            "/targets",
            json={
                "name": "小夏",
                "relationship": "朋友",
                "preferences": "喜欢低压力聊天",
                "taboos": "不要连续追问",
                "strategy_guideline": "先接住情绪，给对方空间。",
            },
        )
        assert create_response.status_code == 200
        target = create_response.json()["target"]
        target_id = target["id"]

        update_response = client.put(f"/targets/{target_id}", json={"style_summary": "压力大时回复会变慢。"})
        assert update_response.status_code == 200
        assert update_response.json()["target"]["style_summary"] == "压力大时回复会变慢。"

        organize_response = client.post(f"/targets/{target_id}/organize", json={"notes": "她不喜欢被催回复。"})
        assert organize_response.status_code == 200
        assert organize_response.json()["llm_call_id"] >= 1

        list_response = client.get("/targets")
        assert list_response.status_code == 200
        assert any(item["id"] == target_id for item in list_response.json()["targets"])

        reply_response = client.post(
            "/reply/generate",
            json={
                "chat_text": "对方：今天太累了。",
                "target_id": target_id,
                "reply_goal": "安慰并保留空间",
                "tone": "自然",
                "length": "短",
                "proactivity": 0.3,
                "risk_level": "稳妥",
                "candidate_count": 2,
            },
        )
        assert reply_response.status_code == 200
        done = _sse_payload(reply_response.text, "done")

        with SessionLocal() as db:
            saved_target = db.get(ChatTarget, target_id)
            assert saved_target is not None
            conversation = db.get(Conversation, done["conversation_id"])
            assert conversation is not None
            assert conversation.target_id == target_id
            assert conversation.target_name == "小夏"
            assert conversation.target_strategy is not None
            assert "不要连续追问" in conversation.target_strategy
            llm_call = db.get(LLMCall, organize_response.json()["llm_call_id"])
            assert llm_call is not None
            assert llm_call.task == "target_profile_organize"


def test_multimodal_screenshot_parse_can_feed_reply_generation() -> None:
    from app.db.database import SessionLocal
    from app.db.models import LLMCall
    from app.main import create_app

    one_pixel_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="

    with TestClient(create_app()) as client:
        parse_response = client.post(
            "/multimodal/parse-chat-screenshot",
            json={
                "filename": "chat.png",
                "mime_type": "image/png",
                "image_base64": one_pixel_png,
            },
        )
        assert parse_response.status_code == 200
        parsed = parse_response.json()
        assert parsed["prompt_version"] == "parse_chat_screenshot_v1"
        assert parsed["messages"][0]["speaker"] == "target"
        assert parsed["stored_image_path"].startswith("screenshots/")

        chat_text = "\n".join(f"{message['speaker']}: {message['content']}" for message in parsed["messages"])
        reply_response = client.post(
            "/reply/generate",
            json={
                "chat_text": chat_text,
                "reply_goal": "安慰并保留空间",
                "tone": "自然",
                "length": "短",
                "proactivity": 0.3,
                "risk_level": "稳妥",
                "candidate_count": 1,
            },
        )
        assert reply_response.status_code == 200
        assert _sse_payload(reply_response.text, "done")["conversation_id"] >= 1

        with SessionLocal() as db:
            llm_call = db.get(LLMCall, parsed["llm_call_id"])
            assert llm_call is not None
            assert llm_call.task == "screenshot_parse"
            assert llm_call.prompt_version == "parse_chat_screenshot_v1"


def test_memory_lifecycle_extract_approve_and_feed_reply() -> None:
    from app.db.database import SessionLocal
    from app.db.models import LLMCall, Memory
    from app.main import create_app

    with TestClient(create_app()) as client:
        presets = client.get("/onboarding/style-presets").json()["presets"]
        if not client.get("/onboarding/status").json()["has_default_profile"]:
            client.post(
                "/onboarding/default-profile",
                json={"name": "默认人设", "selected_preset_ids": [presets[0]["id"]], "avoid_patterns": ["不要像 AI"]},
            )

        target = client.post("/targets", json={"name": "小记", "relationship": "朋友"}).json()["target"]
        target_id = target["id"]

        reply_response = client.post(
            "/reply/generate",
            json={"chat_text": "对方：我最近压力很大，不太想被追问。", "target_id": target_id, "candidate_count": 1},
        )
        assert reply_response.status_code == 200
        assert _sse_payload(reply_response.text, "done")["conversation_id"] >= 1

        pending = client.get(f"/targets/{target_id}/memories", params={"status": "pending"}).json()["memories"]
        assert len(pending) >= 1
        auto_memory = pending[0]
        assert auto_memory["status"] == "pending"
        assert auto_memory["source_conversation_id"] is not None

        with SessionLocal() as db:
            extraction_call = db.query(LLMCall).filter(LLMCall.task == "memory_extraction").first()
            assert extraction_call is not None
            assert extraction_call.prompt_version == "extract_memory_v1"

        created = client.post(
            f"/targets/{target_id}/memories",
            json={"content": "对方不喜欢一上来就被追问近况。", "memory_type": "warning", "confidence": 0.8},
        ).json()["memory"]
        assert created["status"] == "pending"

        approved = client.post(f"/memories/{created['id']}/approve").json()["memory"]
        assert approved["status"] == "approved"

        approved_list = client.get(f"/targets/{target_id}/memories", params={"status": "approved"}).json()["memories"]
        assert any(memory["id"] == created["id"] for memory in approved_list)

        second_reply = client.post(
            "/reply/generate",
            json={"chat_text": "对方：在干嘛呢？", "target_id": target_id, "candidate_count": 1},
        )
        assert second_reply.status_code == 200
        done = _sse_payload(second_reply.text, "done")
        assert done["conversation_id"] >= 1

        with SessionLocal() as db:
            memory = db.get(Memory, created["id"])
            assert memory is not None
            assert memory.status == "approved"
            assert memory.target_id == target_id

        rejected = client.post(f"/memories/{auto_memory['id']}/reject").json()["memory"]
        assert rejected["status"] == "rejected"


def test_qq_json_import_job_creates_profile_and_target() -> None:
    from app.db.database import SessionLocal
    from app.db.models import ChatTarget, UserProfile, UserProfileVersion
    from app.main import create_app

    raw_chat = {
        "messages": [
            {"sender": "我", "content": "哈哈那你先躺会儿，不急着回我。", "time": "2026-05-01 20:00:00"},
            {"sender": "小夏", "content": "今天真的累死了，不太想说话。", "time": "2026-05-01 20:01:00"},
            {"sender": "我", "content": "懂，今天是被工作吸干电量了。", "time": "2026-05-01 20:02:00"},
            {"sender": "小夏", "content": "嗯嗯，我先缓一下。", "time": "2026-05-01 20:03:00"},
        ]
    }

    with TestClient(create_app()) as client:
        start_response = client.post(
            "/import/qq-json",
            json={"filename": "qq.json", "raw_json": raw_chat, "me_speakers": ["我"], "target_name": "小夏"},
        )
        assert start_response.status_code == 200
        job_id = start_response.json()["job_id"]

        final_body = None
        for _ in range(10):
            job_response = client.get(f"/jobs/{job_id}")
            assert job_response.status_code == 200
            final_body = job_response.json()
            if final_body["status"] in {"success", "failed"}:
                break
            time.sleep(0.05)

        assert final_body is not None
        assert final_body["status"] == "success", final_body.get("error_message")
        result = json.loads(final_body["result"])
        assert result["message_count"] == 4
        assert result["user_message_count"] == 2
        assert result["target_message_count"] == 2
        assert result["raw_path"].startswith("imports/")
        assert result["profile"]["source_type"] == "chat_import"
        assert result["target"]["name"] == "小夏"
        assert "不要连续追问" in result["target"]["taboos"]

        with SessionLocal() as db:
            profile = db.get(UserProfile, result["profile"]["id"])
            target = db.get(ChatTarget, result["target"]["id"])
            assert profile is not None
            assert profile.is_default is True
            assert target is not None
            assert target.strategy_guideline is not None
            versions = db.query(UserProfileVersion).filter(UserProfileVersion.profile_id == profile.id).all()
            assert any(version.merge_reason == "chat_import_create" and version.source_job_id == job_id for version in versions)


def test_history_search_and_favorite_reply() -> None:
    from app.main import create_app

    with TestClient(create_app()) as client:
        target = client.post("/targets", json={"name": "置顶对象", "relationship": "朋友"}).json()["target"]
        target_id = target["id"]

        reply_response = client.post(
            "/reply/generate",
            json={"chat_text": "对方：今天被工作折腾麻了。", "target_id": target_id, "candidate_count": 2},
        )
        assert reply_response.status_code == 200
        done = _sse_payload(reply_response.text, "done")
        conversation_id = done["conversation_id"]

        favorite_response = client.post(f"/history/conversations/{conversation_id}/favorite", json={"candidate_index": 1, "note": "适合低压力安慰"})
        assert favorite_response.status_code == 200
        saved_reply = favorite_response.json()["saved_reply"]
        assert saved_reply["conversation_id"] == conversation_id
        assert saved_reply["target_id"] == target_id
        assert saved_reply["text"] == done["replies"][1]

        history_response = client.get("/history/conversations", params={"query": "折腾麻", "limit": 5})
        assert history_response.status_code == 200
        conversations = history_response.json()["conversations"]
        assert any(item["id"] == conversation_id for item in conversations)

        favorites_response = client.get("/history/favorites", params={"query": "安慰"})
        assert favorites_response.status_code == 200
        assert any(item["id"] == saved_reply["id"] for item in favorites_response.json()["saved_replies"])

        targets_response = client.get("/targets")
        assert targets_response.status_code == 200
        assert targets_response.json()["targets"][0]["id"] == target_id

        delete_response = client.delete(f"/history/favorites/{saved_reply['id']}")
        assert delete_response.status_code == 200
        assert client.get("/history/favorites", params={"query": "安慰"}).json()["saved_replies"] == []


def test_privacy_data_summary_and_export_backup_job() -> None:
    from pathlib import Path
    from zipfile import ZipFile

    from app.main import create_app
    from app.paths import APP_DATA_DIR

    with TestClient(create_app()) as client:
        client.post("/targets", json={"name": "备份对象", "relationship": "朋友"})

        summary_response = client.get("/privacy/data-summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["data_path"] == str(APP_DATA_DIR)
        assert summary["table_counts"]["style_presets"] >= 8
        assert summary["table_counts"]["chat_targets"] >= 1
        assert summary["total_size_bytes"] >= 0

        export_response = client.post("/privacy/export")
        assert export_response.status_code == 200
        job_id = export_response.json()["job_id"]

        final_body = None
        for _ in range(10):
            job_response = client.get(f"/jobs/{job_id}")
            assert job_response.status_code == 200
            final_body = job_response.json()
            if final_body["status"] in {"success", "failed"}:
                break
            time.sleep(0.05)

        assert final_body is not None
        assert final_body["status"] == "success", final_body.get("error_message")
        result = json.loads(final_body["result"])
        assert result["backup_path"].startswith("backups/")
        assert result["backup_size_bytes"] > 0
        archive_path = Path(APP_DATA_DIR) / result["backup_path"]
        assert archive_path.exists()
        with ZipFile(archive_path) as archive:
            names = archive.namelist()
        assert any(name.startswith("db/") for name in names)


def _sse_payload(response_text: str, event_name: str) -> dict[str, object]:
    for block in response_text.split("\n\n"):
        if f"event: {event_name}" not in block:
            continue
        data_line = next(line for line in block.splitlines() if line.startswith("data: "))
        return json.loads(data_line.removeprefix("data: "))
    raise AssertionError(f"Missing SSE event: {event_name}")
