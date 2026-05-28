# Agent Operating Rules

本文件定义本项目后续 Agent / Codex / Copilot 的默认工作范式。开始任何任务前，先读本文件与 `docs/ai_chat_wingman_spec_plan.md`。

## Current Canon

- 产品 spec 与 phase plan 以 `docs/ai_chat_wingman_spec_plan.md` 为准。
- 默认远端为 `origin`，仓库为 `yuuiwa1551/ai-chat-wingman`。
- 默认分支为 `main`。
- 默认本地数据路径必须通过 `backend/app/paths.py` 统一生成，不能写死相对路径。

## Work Unit

- 每次只做一个 phase、一个 issue、或一个可验收的小任务。
- 如果任务横跨多个 phase，先拆分并只实现最小可验收部分。
- 不允许一次性实现悬浮窗、LLM、多模态、导入、记忆等所有功能。
- 代码变更必须保持最小范围，避免顺手重构无关模块。

## Branching

- 长任务使用功能分支：`phase-0-foundation`、`phase-1-onboarding`、`feature/<short-name>`。
- 小文档或治理类更新可直接在 `main` 做，但提交前必须确认没有无关改动。
- 提交信息使用中文或英文均可，但必须说明阶段和可验证结果，例如：`phase 0: scaffold FastAPI and PyWebView shell`。

## Architecture Guardrails

- 桌面端默认使用 PyWebView + React + Vite；Tauri 仅作为 fallback。
- FastAPI 与 PyWebView 默认同进程运行，生产版通过 PyInstaller 打包。
- LLM 调用必须走 `backend/app/llm/router.py`，禁止业务代码直接 import provider SDK。
- Provider 配置必须走 `app_settings` 或环境变量，禁止把 API Key 写进仓库。
- 流式接口必须使用 spec 中定义的 SSE 事件格式。
- 超过 2 秒的耗时操作必须走 `jobs` 表，不要同步阻塞 HTTP 请求。
- profile 修改必须走 `profile_merge_service`，并写入 `user_profile_versions` 快照。
- 长期记忆默认进入 pending，不得自动污染 approved 记忆。

## Validation

每个任务完成前至少做一种可执行验证：

- 后端：`pytest` 或更窄的测试命令。
- 前端：`npm test` / `npm run lint` / `npm run build` 中与任务最相关的一项。
- 打包相关：必须验证 PyInstaller 输出可以启动。
- 如果暂时没有测试框架，至少跑最窄的启动/构建/类型检查，并在最终说明中写明缺口。

## Agent Communication

- 开始继续实现时，先显示当前阶段 title 与 todo。
- 中途发现 spec 与实现冲突，先按 spec 保守执行；如果 spec 明显错误，先修 spec 再实现。
- 完成后说明：改了什么、怎么验证、还有哪些风险或下一步。

## Safety And Privacy

- 不实现自动读取聊天软件内容。
- 不实现自动发送消息。
- 不上传遥测。
- 截图、导入记录、SQLite、日志都必须在本地用户数据目录下。
- 一键清空数据必须有二次确认。
