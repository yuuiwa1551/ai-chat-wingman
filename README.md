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

### Backend

```powershell
Set-Location backend
uv run pytest -v
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
uv run --extra desktop --extra build pyinstaller ..\build\wingman.spec --noconfirm
```

Run the full packaged-app verification before calling the desktop build good. This builds the frontend, packages the exe, starts it on a fixed local port, and checks `/healthz` plus onboarding status from outside the process:

```powershell
.\scripts\verify_desktop_package.ps1
```
