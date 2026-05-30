# AI Chat Wingman

AI 帮聊助手：Windows 桌面悬浮窗优先，使用 PyWebView + React + Vite + FastAPI，同进程运行并通过 PyInstaller 打包。

## Repository

- GitHub: https://github.com/yuuiwa1551/ai-chat-wingman
- Default branch: `main`
- Canonical spec: [docs/ai_chat_wingman_spec_plan.md](docs/ai_chat_wingman_spec_plan.md)
- Agent rules: [AGENTS.md](AGENTS.md)

## Product Boundary

- 不自动读取微信/QQ消息。
- 不自动发送任何聊天内容。
- 只生成候选回复，由用户确认、修改、复制、手动发送。
- 默认本地存储，长期记忆必须可查看、可编辑、可删除。

## Phase Order

1. Phase 0: 架构地基
2. Phase 1: 预设 + 首次启动向导 + 隐私声明
3. Phase 4: 文本输入生成回复核心闭环
4. Phase 2: 风格测试聊天窗口
5. Phase 3: 聊天对象档案完整化
6. Phase 5: 多模态截图输入
7. Phase 7: 记忆系统 v1
8. Phase 6: QQ JSON 导入
9. Phase 8: 体验优化

## Agent Handoff

任何后续 Agent 开始前必须先阅读：

1. [AGENTS.md](AGENTS.md)
2. [docs/ai_chat_wingman_spec_plan.md](docs/ai_chat_wingman_spec_plan.md)

每次只实现一个明确阶段或一个小任务，不允许一次性铺完整产品。

## Phase 0 Development

Quick local debug from the repo root:

```powershell
.\start_app.bat
.\dev.ps1
.\dev.ps1 desktop
.\dev.ps1 test
```

### Backend

```powershell
Set-Location backend
uv run python -m pytest -v
uv run uvicorn app.main:app --reload --port 8000
```

Useful endpoints:

- `GET /healthz`
- `GET /demo/sse`
- `POST /jobs/demo`
- `GET /jobs/{id}`
- `GET /settings/llm/providers`
- `PUT /settings/llm/providers/{id}`
- `POST /settings/llm/providers/{id}/test`
- `GET /settings/llm/providers/{id}/models`
- `POST /reply/generate`
- `POST /reply/{conversation_id}/select`
- `POST /style-test/sessions`
- `POST /style-test/sessions/{session_id}/message`
- `POST /style-test/sessions/{session_id}/analysis`
- `GET/POST /targets`
- `GET/PUT/DELETE /targets/{target_id}`
- `POST /targets/{target_id}/organize`
- `GET/POST /targets/{target_id}/memories`
- `POST /targets/{target_id}/memories/extract`
- `PUT/DELETE /memories/{memory_id}`
- `POST /memories/{memory_id}/approve`
- `POST /memories/{memory_id}/reject`
- `POST /multimodal/parse-chat-screenshot`
- `POST /import/qq-json`
- `GET /history/conversations`
- `POST /history/conversations/{conversation_id}/favorite`
- `GET /history/favorites`
- `DELETE /history/favorites/{saved_reply_id}`
- `GET /privacy/data-summary`
- `POST /privacy/export`

Phase 4 reply generation is a streaming POST endpoint. It creates a `chat_sessions` row when needed, saves the generation in `conversations`, writes the aggregated LLM metadata to `llm_calls`, and accepts the final user choice with `/reply/{conversation_id}/select`.

Phase 2 style testing creates a simulated chat session, streams the simulated target reply over SSE, analyzes user replies, and saves the merged default profile with a `user_profile_versions` snapshot.

Phase 3 target profiles store relationship, preferences, taboos, and reply strategy. `POST /reply/generate` can take `target_id` so generation reads the saved target profile instead of only ad hoc target text.

Phase 5 screenshot parsing accepts a local screenshot payload, stores the image under the app data screenshot directory, calls the `screenshot_parse` multimodal route, and returns editable structured chat text for reply generation.

Phase 7 memory system v1 extracts reusable long-term memories after reply generation through the `memory_extraction` route and stores them as `pending`. Memories never auto-pollute long-term context: only after a user approves them do they feed into later reply generation. Memories are scoped to a chat target and are listable, editable, approvable, rejectable, and deletable.

Phase 6 QQ JSON import is a background job. The frontend reads a user-selected local JSON file, posts it to `/import/qq-json` with the sender aliases that count as “me”, then polls `/jobs/{id}`. The job stores the raw file under the app data imports directory, parses messages through the QQ importer, creates a `chat_import` default user profile, and creates or updates the selected chat target profile.

Phase 8 starts with daily-use polish: the reply panel can read text from the clipboard, successful generation moves the used target to the top, users can favorite generated replies, and the history panel searches saved conversations plus favorite replies.

Phase 8 also includes local data management. `/privacy/data-summary` reports the app data path, table counts, and storage usage. `/privacy/export` creates a local zip backup through the `jobs` table and writes it under the app data backups directory.

Provider settings can detect available remote models through `/settings/llm/providers/{id}/models`. The frontend stores the provider first, then shows the returned model list as a dropdown so users do not need to type model names manually.

### Frontend

```powershell
Set-Location frontend
npm install
npm run dev
npm run build
```

When running the frontend alone, it defaults to `http://127.0.0.1:8000` for the API. PyWebView passes the active FastAPI port with `?apiBase=...`.

### Desktop Shell

Dev mode loads the Vite server and starts FastAPI on a local port:

```powershell
Set-Location backend
uv run --extra desktop python -m app.desktop.launcher --dev-server http://127.0.0.1:5173
```

Production packaging expects `frontend/dist` to exist:

```powershell
Set-Location frontend
npm run build

Set-Location ..\backend
uv run --extra desktop --extra build python -m PyInstaller ..\build\wingman.spec --noconfirm
```

Run the full packaged-app verification before calling the desktop build good. This builds the frontend, packages the exe, starts it on a fixed local port, and checks `/healthz` plus onboarding status from outside the process:

```powershell
.\scripts\verify_desktop_package.ps1
```

Core validation before pushing a phase branch:

```powershell
Set-Location backend
uv run python -m pytest -v

Set-Location ..\frontend
npm run build

Set-Location ..
.\scripts\verify_desktop_package.ps1
```
