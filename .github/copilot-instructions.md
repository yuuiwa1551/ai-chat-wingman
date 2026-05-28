# Copilot Instructions

请始终用简体中文和用户沟通。

本项目是 AI Chat Wingman，架构与阶段计划以 `docs/ai_chat_wingman_spec_plan.md` 为准。开始编码前先阅读 `AGENTS.md`。

核心约束：

- 每次只实现一个明确 phase 或一个小任务。
- 桌面端默认 PyWebView + React + Vite；后端 FastAPI；生产用 PyInstaller 打包。
- 不要自动读取微信/QQ消息，不要自动发送消息。
- 所有 LLM 调用必须走 `backend/app/llm/router.py`。
- API Key 不得写死或提交，必须走 `app_settings` / 环境变量。
- 流式接口统一使用 SSE。
- 超过 2 秒的任务走 `jobs` 表。
- profile 更新必须生成 `user_profile_versions` 快照。
- 长期记忆默认 pending，用户确认后才能 approved。
- 默认数据路径使用 `backend/app/paths.py`，不要使用仓库相对路径保存用户数据。

完成任务前必须运行最窄可用验证，并在最终说明中写清验证结果。
