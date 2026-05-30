# AI Chat Wingman v0.1.0

Windows preview build for the local desktop chat-reply assistant.

AI Chat Wingman generates candidate replies from user-provided chat context. It does not read chat apps automatically, does not send messages automatically, and does not upload telemetry. User data stays in the local AI Chat Wingman data directory unless the user explicitly sends context to their configured LLM provider.

## Try It First

1. Download `ai-chat-wingman-windows-v0.1.0.zip`.
2. Run `ai-chat-wingman.exe`.
3. Click "试用示例聊天" on first launch.
4. Pick a reply scenario such as "对方累了" or "推进邀约".
5. Review the generated candidates and their strategy explanations.

Without a real provider, the app runs in Mock demo mode. Mock mode only proves the local flow and streaming UI; configure an OpenAI-compatible provider in Settings to evaluate real reply quality.

## Included In This Preview

- PyWebView desktop shell with FastAPI running in the same local process.
- React/Vite main workspace based on the current Figma direction.
- First-run import/calibration flow plus one-click sample chat.
- SSE reply generation with copy, select, favorite, and candidate explanations.
- Scenario shortcuts for common reply goals.
- Provider settings guide for Mock and OpenAI-compatible providers.
- Target profiles with visible reply-impact rules and prompt summaries.
- Style test flow for user expression calibration.
- Screenshot parsing through multimodal LLM providers.
- QQ JSON import through background jobs.
- Pending memory review grouped by recommendation strength.
- Local data summary and backup export.

## Boundaries

- No automatic reading from WeChat, QQ, or other chat apps.
- No automatic sending.
- No telemetry upload.
- API keys are stored only through local settings or environment variables.
- Long-term memories must be confirmed before they affect later generation.

## Known Limits

- Windows is the primary supported platform for this preview.
- Mock mode does not represent real model quality.
- QQ JSON compatibility may need more adapters for different exporters.
- Screenshot parsing depends on the configured multimodal model.
- Memory retrieval is currently local SQLite storage, not a full vector recall system.
