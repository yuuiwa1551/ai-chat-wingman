# AI Chat Wingman（渣男模拟器）

一个 Windows 优先的本地桌面帮聊助手。它不会自动读取聊天软件，也不会自动发送消息；用户手动粘贴聊天内容、上传截图或导入聊天记录后，应用结合用户表达风格、聊天对象档案和长期记忆，生成可复制、可修改、可手动发送的候选回复。

项目起因很简单：亲友问情感问题时，经常卡在“AI 不知道前后文，也不像我本人说话”。所以这个项目重点放在长期记忆、对象档案和用户表达风格继承上，而不是做自动代聊。

## 适合谁

- 想快速组织回复，但仍然自己判断、复制、发送的人。
- 想保留自己说话习惯，只让回复更会接情绪、更有边界的人。
- 经常要根据不同聊天对象调整语气、主动程度和禁忌点的人。
- 想把聊天记录、截图、对象档案和长期记忆都留在本机的人。

## 一分钟试用

最短路径：

1. 下载 Windows preview 包：[v0.1.1](https://github.com/yuuiwa1551/ai-chat-wingman/releases/tag/v0.1.1)。
2. 运行 `ai-chat-wingman.exe`。
3. 首次页点击“试用示例聊天”。
4. 在主工作台选择场景，例如“对方累了”“推进邀约”。
5. 查看候选回复和“为什么这样写”的策略解释。

未配置真实 Provider 时，应用会使用 Mock 演示模式。Mock 只用于跑通流程，不代表真实模型质量。要看真实效果，请在设置页配置 OpenAI-compatible provider，再检测模型并测试连通。

## 当前能力

- 首次体验：导入 QQ JSON、模拟聊天校准，或一键试用示例聊天。
- 回复生成：粘贴聊天内容后通过 SSE 流式生成多条候选回复，支持复制、选中、收藏。
- 场景目标：提供“对方累了”“对方冷淡”“推进邀约”“缓和误会”“体面结束”等快捷场景。
- 候选解释：每条候选回复展示策略理由，方便用户判断是否可用。
- Provider 设置：支持 Mock Provider、OpenAI-compatible provider、模型列表检测、连通测试和配置向导。
- 聊天对象：支持对象档案 CRUD、关系/偏好/禁忌/策略记录，并在回复区直接展示它们会如何影响本轮回复。
- 风格校准：模拟聊天采样用户表达习惯，保存默认 profile 并生成版本快照。
- 多模态截图：上传聊天截图后走 LLM 多模态任务解析成可编辑聊天文本。
- 长期记忆：生成后抽取 pending 记忆，按“建议保存 / 不确定 / 不建议保存”分组，用户确认后才进入 approved 记忆。
- QQ JSON 导入：通过 jobs 后台任务解析导出记录，生成用户风格和对象档案。
- 本地数据：查看数据目录、表计数和占用空间，支持导出本地备份 zip。
- 自动构建：GitHub Actions 在 Windows runner 上测试、构建前端、打包 exe 并上传 zip。

## 明确边界

- 不自动读取微信、QQ 或其他聊天软件内容。
- 不自动发送任何消息。
- 不上传遥测。
- 不把用户包装成完全不同的人。
- API Key 不进仓库，必须通过设置页、`app_settings` 或环境变量配置。
- 用户数据默认保存在本机数据目录，路径由 `backend/app/paths.py` 统一生成。
- 长期记忆默认进入 pending，必须由用户确认后才会用于后续生成。

## 当前限制

- 目前优先支持 Windows；后端业务稳定后再考虑安卓端。
- Mock 演示模式只能验证流程，真实回复质量取决于用户配置的 provider 和模型。
- QQ JSON 导入已经接入，但不同导出工具格式可能仍需要继续适配。
- 截图解析走多模态模型，不做本地 OCR；解析准确度取决于模型能力。
- 记忆系统目前是 SQLite 本地存储，尚未接入完整向量召回。

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

## 验证与打包

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

CI 会安装 Python、Node 和 `uv`，运行后端测试、前端构建、PyInstaller 打包，并把 `ai-chat-wingman-windows-<tag-or-sha>.zip` 上传为 artifact。推送 `v*` tag 时会创建或更新 GitHub Release 并上传 zip。

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

## 文档

- [AGENTS.md](AGENTS.md): Agent / Codex / Copilot 工作规则。
- [docs/ai_chat_wingman_spec_plan.md](docs/ai_chat_wingman_spec_plan.md): 产品 spec 和 phase plan。
- [docs/business_optimization_phase_plan.md](docs/business_optimization_phase_plan.md): 业务优化 P0-P4 计划。
- [docs/business_optimization_completion_log.md](docs/business_optimization_completion_log.md): 业务优化 P0-P4 完成记录和 v0.1.1 发布整理。
- [docs/release_notes_v0.1.1.md](docs/release_notes_v0.1.1.md): v0.1.1 发布说明。
- [docs/release_notes_v0.1.2.md](docs/release_notes_v0.1.2.md): v0.1.2 发布说明草稿。
- [docs/post_v0.1.1_iteration_plan.md](docs/post_v0.1.1_iteration_plan.md): v0.1.1 之后的迭代计划。
- [docs/frontend_uiux_redesign_plan.md](docs/frontend_uiux_redesign_plan.md): 当前 UI/UX 重做计划。
