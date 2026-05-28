# Agent Operating Rules

本文件定义本项目后续 Agent / Codex / Copilot 的默认工作范式。开始任何任务前，先读本文件与 `docs/ai_chat_wingman_spec_plan.md`。

## Current Canon

- 产品 spec 与 phase plan 以 `docs/ai_chat_wingman_spec_plan.md` 为准。
- 默认远端为 `origin`，仓库为 `yuuiwa1551/ai-chat-wingman`。
- 默认分支为 `main`。
- 默认本地数据路径必须通过 `backend/app/paths.py` 统一生成，不能写死相对路径。

## Work Unit

- 每次只做一个 phase、一个 issue、或一个可验收的小任务。
- 如果任务横跨多个 phase，先拆分边界，再实现当前阶段里能真正闭环的部分。
- 不允许一次性实现悬浮窗、LLM、多模态、导入、记忆等所有功能。
- 不要为了“最小改动”牺牲根因修复。遇到 bug 或设计缺口时，要优先修到拥有该行为的抽象层，而不是在调用点表面绕过。
- 改动范围应当“刚好足够”：覆盖根因、必要测试和相邻契约，但不顺手重构无关模块。
- 复用已有模块、服务、组件、工具函数和本地约定；只有在现有能力确实不适合时才新增抽象。
- 不写炫技或绕远的代码。优先清晰、直白、可读的实现，让后来维护者能快速理解控制流和数据结构。

## Branching

- 长任务使用功能分支：`phase-0-foundation`、`phase-1-onboarding`、`feature/<short-name>`。
- 小文档或治理类更新可直接在 `main` 做，但提交前必须确认没有无关改动。
- 每次推送到远端前，提交信息使用以下固定格式：

```text
<type>: <一句话简洁说明干了什么>

1. <详细说明 1>
2. <详细说明 2>
3. <详细说明 3>
```

- `<type>` 统一使用英文类型，例如：`feat`、`fix`、`docs`、`refactor`、`test`、`build`、`chore`。
- 标题行只写一件事，正文用 `1. 2. 3.` 说明具体改动、验证或影响范围。
- 示例：

```text
docs: clarify agent commit format and code quality rules

1. 规定远端提交信息使用英文类型前缀和编号正文
2. 补充根因修复优先于表面绕过的原则
3. 强调复用已有能力并保持代码可读
```

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
