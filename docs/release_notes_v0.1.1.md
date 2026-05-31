# AI Chat Wingman v0.1.1

Windows preview patch release for the local desktop chat-reply assistant.

This release brings the P0-P4 business optimization work into an official downloadable version. The focus is not new automation; it is making the first successful reply loop, provider setup, target-profile value, memory confirmation, and public documentation easier to understand.

## What's Updated

1. First-run sample chat: new users can click "试用示例聊天" and reach the main workspace without importing data or configuring a real provider first.
2. Scenario shortcuts: the reply workspace now exposes concrete goals such as "对方累了", "对方冷淡", "推进邀约", "缓和误会", and "体面结束".
3. Candidate explanations: reply cards show why a candidate is written that way, so users can judge whether it fits before copying.
4. Provider setup guide: the settings page now explains Mock mode, OpenAI-compatible configuration, model detection, and connection testing more clearly.
5. Target-profile impact: the workspace surfaces how the selected target's relationship, preferences, taboos, and recent context affect the current reply.
6. Memory confirmation grouping: pending memories are grouped into "建议保存", "不确定", and "不建议保存", with batch confirm, ignore, and reject actions.
7. Public preview docs: README and release documentation now emphasize the product boundary: local, user-controlled, no automatic reading, no automatic sending, and no telemetry.

## Still The Same Boundaries

1. The app does not automatically read WeChat, QQ, or other chat apps.
2. The app does not automatically send messages.
3. The app does not upload telemetry.
4. API keys must be configured locally through settings, `app_settings`, or environment variables.
5. Long-term memories stay pending until the user confirms them.

## Validation

1. Frontend build was run for the P0-P3 implementation commits.
2. Browser checks covered the first-run flow, main workspace, provider settings, target-impact display, and memory grouping.
3. Documentation updates were checked with `git diff --check`.
4. The `v0.1.1` tag triggers the Windows desktop build workflow, which runs backend tests, builds the frontend, packages the PyInstaller executable, and uploads the Windows zip to the GitHub Release.

## Known Limits

1. Mock mode proves the local flow only; real reply quality depends on the configured provider and model.
2. QQ JSON import may still need adapters for more exporter formats.
3. Screenshot parsing depends on the configured multimodal model.
4. Memory storage is local SQLite and has not yet become a full vector recall system.
