# 渣男模拟器

被零感情经验的亲友问情感问题问烦了后让人去问ai，结果亲友和我说ai不知道前后文每次都要重新说好麻烦不如问我，于是就有了这玩意。vibe前看了看网上现有的这类app好像在长期记忆和用户人格继承这方面都没怎么做，于是自己整了一个看看。目前只有win端，后续后端业务部分稳定后再考虑整个安卓端。

以下是ai写的废话： 

AI Chat Wingman 是一个 Windows 优先的本地桌面帮聊助手。它不会自动读取聊天软件，也不会自动发送消息；用户手动粘贴聊天内容、上传截图或导入聊天记录后，应用结合用户表达风格、聊天对象档案和长期记忆，生成可复制的候选回复。

当前仓库已经进入预览版发布准备阶段：核心闭环、桌面壳、Provider 配置、对象档案、风格校准、截图解析、记忆确认、QQ JSON 导入、历史收藏和本地数据导出都已经接入，UI 已按最新 Figma 方向重做。

## 当前能力

- 桌面形态：PyWebView + FastAPI 同进程运行，React/Vite 前端由本地 API 托管。
- 首次使用：可选择导入 QQ JSON、通过模拟聊天校准，或跳过校准直接进入。
- 回复生成：粘贴聊天内容后通过 SSE 流式生成多条候选回复，支持复制、选中、收藏。
- 聊天对象：支持对象档案 CRUD、关系/偏好/禁忌/策略记录，并参与回复生成。
- 风格校准：模拟聊天采样用户表达习惯，保存默认 profile 并生成版本快照。
- 多模态截图：上传聊天截图后走 LLM 多模态任务解析成可编辑聊天文本。
- 记忆系统：生成后抽取 pending 记忆，用户确认后才进入 approved 记忆。
- QQ JSON 导入：通过 jobs 后台任务解析导出记录，生成用户风格和对象档案。
- Provider 设置：支持 Mock Provider、OpenAI 兼容 Provider、模型列表探测和连通性测试。
- 本地数据：查看数据目录、表计数和占用空间，支持导出本地备份 zip。
- 自动构建：GitHub Actions 可在 Windows runner 上测试、构建前端、打包 exe 并上传 zip。

## 明确边界

- 不自动读取微信、QQ 或其他聊天软件内容。
- 不自动发送任何消息。
- 不上传遥测。
- API Key 不进仓库，必须通过设置页、`app_settings` 或环境变量配置。
- 用户数据默认保存在本机数据目录，路径由 `backend/app/paths.py` 统一生成。
- 长期记忆默认进入 pending，必须由用户确认后才会用于后续生成。

## 技术栈

```text
frontend/  React + TypeScript + Vite
backend/   FastAPI + SQLite + SQLAlchemy + Alembic
desktop/   PyWebView + Uvicorn 同进程本地服务
build/     PyInstaller one-file Windows exe
ci/        GitHub Actions Windows desktop build
```

生产模式下，PyInstaller 打出的 `ai-chat-wingman.exe` 会启动本地 FastAPI，并托管 `frontend/dist` 静态资源。PyWebView 窗口通过 `?apiBase=http://127.0.0.1:<port>` 指向当前进程内 API。

## 环境要求

- Windows 10/11
- Python 3.11+
- Node.js 22+
- PowerShell
- `uv`
- WebView2 Runtime

首次开发前安装依赖：

```powershell
Set-Location frontend
npm install

Set-Location ..\backend
uv sync --group dev --extra desktop --extra build
```

## 本地开发

从仓库根目录启动：

```powershell
.\start_app.bat
```

常用开发命令：

```powershell
.\dev.ps1 web       # 分别启动 FastAPI 和 Vite
.\dev.ps1 desktop   # 启动 Vite + PyWebView 桌面壳
.\dev.ps1 backend   # 只启动 FastAPI
.\dev.ps1 frontend  # 只启动 Vite
.\dev.ps1 test      # 后端 pytest
.\dev.ps1 build     # 前端 build
.\dev.ps1 verify    # 本地完整桌面包验证
```

如果只跑前端，它默认请求 `http://127.0.0.1:8000`。桌面壳会自动传入真实 API 端口：

```text
http://127.0.0.1:<api_port>/?apiBase=http://127.0.0.1:<api_port>
```

## 本地验证

后端测试：

```powershell
Set-Location backend
uv run --group dev python -m pytest -v
```

前端构建：

```powershell
Set-Location frontend
npm run build
```

完整桌面包验证：

```powershell
Set-Location ..
.\scripts\verify_desktop_package.ps1
```

`verify_desktop_package.ps1` 会构建前端、用 PyInstaller 打包 exe、启动打包产物，并验证 `/healthz`、首次启动状态、Provider、回复生成、截图解析、记忆、风格测试和数据导出等关键路径。

## 打包

手动打包 Windows exe：

```powershell
Set-Location frontend
npm run build

Set-Location ..\backend
uv run --extra desktop --extra build python -m PyInstaller ..\build\wingman.spec --noconfirm
```

默认产物：

```text
backend/dist/ai-chat-wingman.exe
```

发布前建议跑完整验证脚本，而不是只检查 exe 是否存在。

## GitHub 自动构建

Workflow 文件：

```text
.github/workflows/windows-desktop-build.yml
```

触发条件：

- push 到 `main`
- pull request 到 `main`
- 手动 `workflow_dispatch`
- 推送 `v*` tag

CI 步骤：

1. 安装 Python、Node 和 `uv`
2. `npm ci`
3. `uv run --group dev python -m pytest -v`
4. `npm run build`
5. PyInstaller 打包 `ai-chat-wingman.exe`
6. 压缩为 `ai-chat-wingman-windows-<tag-or-sha>.zip`
7. 上传 GitHub Actions artifact
8. 如果是 `v*` tag，创建或更新 GitHub Release 并上传 zip

创建一个版本包：

```powershell
git tag v0.1.0
git push origin v0.1.0
```

GitHub runner 不启动 PyWebView 窗口，避免 CI 图形环境导致误报。桌面启动验证仍以本地 `.\scripts\verify_desktop_package.ps1` 为准。

## 数据目录

默认数据目录由 `backend/app/paths.py` 管理：

```text
%APPDATA%/AIChatWingman/
├─ db/app.sqlite
├─ screenshots/
├─ imports/
├─ logs/
└─ backups/
```

测试或打包验证可临时覆盖：

```powershell
$env:AI_CHAT_WINGMAN_DATA_DIR = "C:\Temp\AIChatWingmanData"
```

## 主要 API

- `GET /healthz`
- `GET /onboarding/status`
- `GET /onboarding/style-presets`
- `POST /onboarding/default-profile`
- `GET/PUT /settings/llm/providers/{provider_id}`
- `POST /settings/llm/providers/{provider_id}/test`
- `GET /settings/llm/providers/{provider_id}/models`
- `POST /reply/generate`
- `POST /reply/{conversation_id}/select`
- `POST /style-test/sessions`
- `POST /style-test/sessions/{session_id}/message`
- `POST /style-test/sessions/{session_id}/analysis`
- `GET/POST/PUT/DELETE /targets`
- `POST /targets/{target_id}/organize`
- `GET/POST /targets/{target_id}/memories`
- `POST /memories/{memory_id}/approve`
- `POST /memories/{memory_id}/reject`
- `POST /multimodal/parse-chat-screenshot`
- `POST /import/qq-json`
- `GET /jobs/{job_id}`
- `GET /history/conversations`
- `GET /history/favorites`
- `GET /privacy/data-summary`
- `POST /privacy/export`

## 文档

- [AGENTS.md](AGENTS.md): Agent / Codex / Copilot 工作规则。
- [docs/ai_chat_wingman_spec_plan.md](docs/ai_chat_wingman_spec_plan.md): 产品 spec 和 phase plan。
- [docs/frontend_uiux_redesign_plan.md](docs/frontend_uiux_redesign_plan.md): 当前 UI/UX 重做计划。

后续任务仍按 `AGENTS.md` 约束执行：每次只做一个 phase、issue 或可验收小任务；遇到 spec 与实现冲突时先按 spec 保守执行，必要时先修 spec。
