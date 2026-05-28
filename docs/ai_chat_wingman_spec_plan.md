# AI 帮聊助手 v0.2 Spec & Plan

> 版本：v0.2 MVP 方案（架构定型版）
> 目标平台：Windows 电脑版优先
> 前端形态：桌面悬浮窗（PyWebView + React + Vite）
> 后端：FastAPI（与前端同进程，PyInstaller 打包分发）
> 核心定位：根据用户表达风格、聊天对象特征、当前上下文，生成更贴近用户本人习惯但更高情商的回复建议。
> 边界：AI 只生成候选回复，用户确认后手动发送；不做自动发送

---

## 0. v0.2 相对 v0.1 的关键变更

本版本针对“前期定框架尽量考虑充分”的目标，把以下几点提前到框架层定死，避免后期返工：

- **前端技术栈**：Electron + React 改为 **PyWebView + React + Vite**，前后端同进程，PyInstaller 一把梭打包。Tauri 作为 fallback。
- **LLM 层**：Phase 0 就引入 **Provider 抽象 + Mock Provider + 配置表**，支持多 provider、文本/多模态模型分离、可在设置页切换。
- **流式响应**：`/reply/generate` 与 `/style-test/.../message` 从一开始就走 **SSE**，避免后期改协议。
- **异步任务**：QQ JSON 导入、风格分析等耗时操作走**后台任务 + 轮询状态**，API 形态从一开始就定好。
- **数据模型**：新增 `app_settings` / `llm_calls` / `user_profile_versions` / `chat_sessions` 表，`conversations` 加 `thread_id` / `prompt_version` / `llm_call_id`。
- **数据路径**：明确所有用户数据落在 `%APPDATA%/AIChatWingman/`，包含 SQLite、截图缓存、导入文件。
- **隐私边界**：首次启动向导加 disclaimer 页；设置页提供“一键清空所有数据”。
- **Phase 排序**：Phase 0 加重（含 LLM 抽象、SSE 骨架、任务队列骨架、配置表）；核心闭环（粘贴文本→出回复）尽早跑通，Target 档案/记忆/截图后置。

---

## 1. 项目定位

### 1.1 一句话描述

一个运行在电脑端的 AI 帮聊助手。用户可以通过粘贴聊天内容、上传截图或导入聊天记录，让系统结合用户自身说话风格、聊天对象性格特征和当前上下文，生成多个可复制的回复建议。

### 1.2 核心价值

用户不是要一个“替自己说话的机器人”，而是要一个：

- 能理解对方话里意思的阅读理解助手
- 能保持自己原本说话风格的回复生成器
- 能在原风格基础上提高情绪承接和表达质量的辅助工具
- 能记住聊天对象偏好、禁忌和关系状态的长期记忆系统

### 1.3 产品边界

必须坚持：

- 不自动发送消息
- 不把用户包装成完全不同的人
- 所有回复都由用户确认、修改、复制、手动发送

---

## 2. MVP 范围

### 2.1 v0.1 必须支持

#### 2.1.1 桌面悬浮窗

前端不要网页形态，初版直接做桌面悬浮窗。

悬浮窗能力：

- 置顶显示
- 可拖拽移动
- 可调整大小
- 粘贴当前聊天内容
- 上传截图给多模态模型理解
- 切换聊天对象
- 选择回复目标
- 选择语气强度
- 流式展示候选回复
- 一键复制候选回复
- 默认保存本轮输入与生成结果

**技术选型：PyWebView + React + Vite**

选这套的原因：

- 与 FastAPI **同一个 Python 进程**：FastAPI 在后台线程启动，PyWebView 主线程打开窗口加载 `http://127.0.0.1:<随机端口>`。
- **打包简单**：PyInstaller 把 Python + FastAPI + 前端 dist 一起打成单个 exe，不必同时维护 Electron Builder 和 Python 打包链。
- **窗口能力够用**：PyWebView 支持 `frameless` / `on_top` / `resizable` / `transparent` / 自定义拖拽区，悬浮窗体感与 Electron 接近。
- **前端开发体验不变**：仍是 React + Vite + TS，dev 模式下 PyWebView 直接指向 Vite dev server（含 HMR）。
- **系统能力补齐**：全局快捷键用 `keyboard` 或 `pynput`，剪贴板用 `pyperclip`，托盘用 `pystray`。

Fallback：如果后期发现 PyWebView 在多窗口/全局快捷键/系统级悬浮窗体验上撞墙，再切 **Tauri + React + FastAPI sidecar** 方案（Tauri 拉起独立的 FastAPI exe，IPC 用 HTTP）。Phase 0 的 LLM 层、API 形态、数据模型都与前端无关，切换前端不会动到这些。

前端运行模式：

```text
开发模式：
  Vite dev server (http://localhost:5173, HMR)
        ↑
  PyWebView 主窗口加载
        ↓
  调用 http://127.0.0.1:<api_port>/api/*
        ↓
  FastAPI（同进程线程内）

生产模式：
  PyInstaller 打包后的单 exe
        ↓
  内置 FastAPI 启动并托管前端 dist 静态文件
        ↓
  PyWebView 加载 http://127.0.0.1:<api_port>/
```

---

#### 2.1.2 FastAPI 后端

后端使用 FastAPI，负责：

- 用户风格预设管理
- 风格测试聊天窗口
- 用户表达风格分析
- 聊天对象档案管理
- 聊天对象性格分析
- 当前聊天内容解析
- 多模态截图理解
- Prompt 组装
- LLM 调用
- 记忆保存与检索

---

#### 2.1.3 默认保存

用户每次生成回复后，系统默认保存：

- 当前输入内容
- 生成的候选回复
- 用户最终复制或选中的回复
- 使用的人设
- 使用的聊天对象档案
- 回复目标和语气参数
- 创建时间

默认保存不等于默认写入长期记忆。长期记忆可以自动提取，但建议先进入“待确认记忆”状态，避免模型乱记。

---

#### 2.1.4 多模态截图理解，不做 OCR

初版先不接 PaddleOCR / EasyOCR。截图输入直接走多模态模型。

流程：

```text
用户上传聊天截图
↓
多模态模型读取截图内容
↓
输出结构化聊天文本
↓
用户可手动修正
↓
进入回复生成流程
```

多模态解析输出格式：

```json
{
  "messages": [
    {
      "speaker": "me",
      "content": "你今天怎么样",
      "time": "unknown"
    },
    {
      "speaker": "target",
      "content": "累死了，不太想说话",
      "time": "unknown"
    }
  ],
  "summary": "对方今天很累，回复欲望较低。",
  "uncertain_parts": ["截图右下角有一段文字可能被遮挡"]
}
```

---

#### 2.1.5 QQ JSON 聊天记录导入

支持导入 QQ 导出的 JSON 聊天记录。

用途：

- 抽取用户原本说话风格
- 抽取聊天对象性格特征
- 生成聊天对象长期记忆
- 建立历史上下文检索库

导入后需要解析：

- 消息发送者
- 消息内容
- 时间戳
- 图片/表情占位
- 群聊/私聊信息，如果有

注意：不同导出工具的 JSON 格式可能不同，所以需要做适配层。

建议设计成：

```text
importers/
├── base_importer.py
├── qq_json_importer.py
└── generic_json_importer.py
```

---

#### 2.1.6 用户人格 / 表达风格抽取

这里不要写成“伪装成用户”，而是写成“用户表达风格建模”。

目标：

- 生成的回复尽量贴近用户原本的表达习惯
- 不让对方一眼看出像换了个人
- 在原本风格上增强情绪承接、边界感、推进能力
- 不突然变成过度完美、过度深情、过度客服化的 AI 腔

抽取来源有三种：

```text
A. 性格/风格预设选择
B. 聊天测试窗口采样
C. 历史聊天记录导入
```

三者融合成最终用户风格档案。

后续还需考虑加入用户最终发送的消息来动态更新用户风格档案。
---

#### 2.1.7 聊天测试窗口

因为让用户导入大量聊天记录门槛太高，所以新增“风格校准”模块。

流程：

```text
首次启动
↓
选择基础风格预设
↓
选择不想要的表达风格
↓
选择模拟聊天对象类型
↓
进入聊天测试窗口
↓
用户和 LLM 模拟对象聊 10-20 轮
↓
系统分析用户回复
↓
生成用户表达风格档案
↓
用户确认后保存
```
聊到一定轮数后可以提醒用户采集样本够了，但也可以继续聊来获得更精准的风格档案。
这个模块不做心理诊断，不判断 MBTI，只分析聊天表达习惯。

---

#### 2.1.8 聊天对象性格分析

对每个聊天对象建立档案。档案描述对象特征，用于协助生成回复。档案需可以手动添加、修改、删除。且可以随着聊天自动更新。

档案包括：

- 基础关系
- 对方聊天风格
- 对方可能的偏好
- 对方禁忌点
- 最近关系状态
- 历史重要事件
- 适合的回复策略

示例：

```json
{
  "target_name": "A",
  "relationship": "暧昧对象",
  "style_summary": "对方回复偏短，情绪不好时不喜欢被追问，但会接受轻微玩笑式安慰。",
  "preferences": [
    "喜欢自然、轻松的回复",
    "不喜欢被连续追问"
  ],
  "taboos": [
    "不要在她说累的时候继续问很多细节",
    "不要突然长篇深情"
  ],
  "strategy_guideline": "回复时先接住情绪，给空间，再用轻微幽默降低压力。"
}
```

---

#### 2.1.9 LLM Provider 抽象与配置管理（Phase 0 必需）

为了避免后期在 provider 、模型、多模态上反复返工，**LLM 层在 Phase 0 就定型**。

设计要点：

- 统一接口 `LLMProvider`，包含：
  - `complete(messages, **opts) -> LLMResponse`
  - `stream(messages, **opts) -> AsyncIterator[LLMChunk]`
  - `complete_multimodal(messages_with_images, **opts) -> LLMResponse`
- 内置实现：
  - `MockProvider`（默认，无 key 也能跑通所有流程）
  - `OpenAICompatibleProvider`（覆盖 OpenAI / DeepSeek / 智谱 / Moonshot / 本地 vLLM 等所有 OpenAI 兼容 endpoint）
  - `AnthropicProvider`（可选）
- **文本模型与多模态模型分离配置**：回复生成、风格分析可以用便宜模型；仅截图解析走多模态模型。
- **任务到模型的映射**放在配置里，不硬编码：

```json
{
  "task_model_routing": {
    "reply_generation": "text_main",
    "style_analysis": "text_main",
    "style_test_simulation": "text_main",
    "memory_extraction": "text_cheap",
    "profile_merge": "text_main",
    "screenshot_parse": "multimodal"
  }
}
```

- **所有调用写入 `llm_calls` 表**（见 §6.8），记录 provider / model / tokens / latency / cost / prompt_version，以便后期查错与成本统计。
- **API key 不进版本控制**：存在 `app_settings` 表（SQLite），由设置页管理；允许环境变量覆盖。

---

#### 2.1.10 流式响应（SSE）

以下接口从 Phase 0 就定为 SSE，避免后期改协议：

- `POST /reply/generate`：流式返回多个候选的 token（按候选序号分隔），结束时发送包含 conversation_id 的 `done` 事件。
- `POST /style-test/session/{id}/message`：流式返回模拟对象的下一句。
- `POST /multimodal/parse-chat-screenshot`：可选 SSE（多模态输出 JSON 较慢，流式体验更好）。

事件格式统一：

```text
event: token
data: {"candidate_index": 0, "delta": "懂了"}

event: candidate_done
data: {"candidate_index": 0, "text": "...", "reason": "...", "risk_level": "low"}

event: done
data: {"conversation_id": 101, "llm_call_id": 555}

event: error
data: {"code": "provider_error", "message": "..."}
```

其他 CRUD 仍用普通 REST JSON。

---

#### 2.1.11 异步任务与进度查询

以下操作不能同步等返回，从一开始就走后台任务：

- QQ JSON 导入与解析
- 导入后的风格/对象抽取
- 带起 user_profile 版本合并（profile_merge）
- 未来可能的向量库重建

实现：

- v0.1 使用 FastAPI `BackgroundTasks` + 一张 `jobs` 表（见 §6.9）足够，不引入 Celery/Redis。
- 统一 API 形态：

```http
POST /jobs/{action}            → 返回 { job_id }
GET  /jobs/{job_id}            → 返回 { status, progress, result, error }
DELETE /jobs/{job_id}          → 取消（可选）
```

前端轮询或走 SSE `/jobs/{id}/stream`。

---

#### 2.1.12 本地数据路径与隐私

- 所有用户数据一律落在 `%APPDATA%/AIChatWingman/`（Windows）、`~/Library/Application Support/AIChatWingman/`（macOS）、`~/.local/share/AIChatWingman/`（Linux）。结构：

```text
%APPDATA%/AIChatWingman/
├─ db/app.sqlite
├─ screenshots/<yyyy-mm>/<uuid>.png
├─ imports/<job_id>/raw.json
├─ logs/app.log
└─ backups/<yyyymmdd>.zip
```

- 首次启动向导展示隐私声明：所有数据仅存本地；只有发往 LLM provider 的请求会出本机；不上传任何遥测。
- 设置页提供：查看数据路径、导出备份、导入备份、**一键清空所有数据**。
- 装载截图默认保本地 30 天后自动清理，可在设置页调整。

---

## 3. 用户风格冷启动设计

### 3.1 三种入口

#### 入口 A：风格预设

适合快速开始。

预设示例：

- 自然随和型
- 轻松幽默型
- 温柔共情型
- 冷静克制型
- 直接坦率型
- 嘴硬吐槽型
- 理性分析型
- 高情商稳妥型

用户还可以选择聊天倾向：

- 偏主动
- 偏被动
- 偏暧昧
- 偏朋友感
- 偏安全距离
- 偏短句
- 偏话多
- 偏吐槽

以及禁区：

- 不要太油
- 不要太舔
- 不要太正式
- 不要长篇大论
- 不要强行暧昧
- 不要过度说教
- 不要像客服
- 不要像 AI

---

#### 入口 B：聊天测试窗口

适合没有历史聊天记录，但愿意聊几分钟的用户。

开始前选择模拟对象：

- 普通朋友
- 暧昧对象
- 恋人
- 刚认识的人
- 同事
- 高冷话少的人
- 爱开玩笑的人
- 情绪低落的人
- 有点敏感的人

选择场景：

- 日常闲聊
- 对方心情不好
- 对方分享生活
- 对方冷淡回复
- 对方抱怨工作
- 对方发来暧昧试探
- 对方生气了
- 聊天快断了

系统模拟对方与用户聊天，采样用户真实回复。

---

#### 入口 C：聊天记录导入

适合高级用户。

导入 QQ JSON 或其他格式聊天记录，从历史语料中提炼用户真实表达风格。

---

### 3.2 三路融合权重

冷启动阶段：

```json
{
  "preset": 0.4,
  "style_test": 0.6,
  "chat_import": 0.0,
  "user_selected_replies": 0.0
}
```

导入聊天记录后：

```json
{
  "preset": 0.15,
  "style_test": 0.25,
  "chat_import": 0.6,
  "user_selected_replies": 0.0
}
```

长期使用后：

```json
{
  "preset": 0.1,
  "style_test": 0.2,
  "chat_import": 0.4,
  "user_selected_replies": 0.3
}
```

用户最终选择了哪条回复很重要，因为这代表用户“认可什么风格”。

---

### 3.3 融合时机与实现方式

**什么时候触发融合：**

- 首次启动完成风格测试 → preset + style_test 融合为 v1 默认 profile
- 导入 QQ JSON 并分析完成 → 融合 chat_import 到现有 profile，升为 v2
- 用户选择回复达到阈值（默认 50 条） → 增量融合一次，升 vN
- 用户手动点击“重新校准” → 全量融合

**怎么融合：**

- 数值型字段（`tone_features` 里的 humor_level / empathy_level / ... ）→ **程序加权平均**
- 文本型字段（`style_summary` / `common_patterns` / `avoid_patterns` / `generation_guideline`）→ **LLM 融合**，使用 `merge_profile.md` prompt，入参是各路的文本字段 + 当前权重
- 每次融合前先快照现有 profile 到 `user_profile_versions`（§6.10），支持回滚
- 用户选择回复不直接改 profile，而是记在 `conversations.selected_reply`，达阈值后批量融合，避免单次选择污染

---

## 4. 核心用户流程

### 4.1 首次启动流程

```text
打开应用
↓
进入首次启动向导
↓
选择基础风格预设
↓
选择禁区
↓
选择模拟聊天对象和场景
↓
进入风格测试聊天窗口
↓
完成 10-20 轮对话
↓
系统分析用户表达习惯
↓
用户确认/修改人设
↓
保存为默认人设
↓
进入悬浮窗主界面
```

---

### 4.2 日常使用流程

```text
打开悬浮窗
↓
选择聊天对象
↓
粘贴聊天内容或上传截图
↓
系统解析当前上下文
↓
系统检索用户风格和对象记忆
↓
选择回复目标和语气参数
↓
生成 3-5 个候选回复
↓
用户复制/编辑其中一条
↓
系统默认保存本轮记录
↓
系统提取待确认记忆
```

---

### 4.3 QQ JSON 导入流程

```text
用户导入 QQ JSON
↓
选择哪一方是“我”
↓
选择聊天对象
↓
系统解析消息
↓
系统区分用户消息和对方消息
↓
抽取用户表达风格
↓
抽取对方性格特征
↓
生成或更新用户风格档案
↓
生成或更新聊天对象档案
```

---

## 5. 功能模块

### 5.1 前端模块

```text
frontend/                       # React + Vite + TS，产物由 FastAPI 静态托管
├─ FloatingWindow              # 悬浮窗主界面
├─ OnboardingWizard            # 首次启动向导（含隐私声明页）
├─ StylePresetSelector         # 风格预设选择
├─ StyleTestChat               # 风格测试聊天窗口（SSE）
├─ TargetSelector              # 聊天对象选择
├─ ChatInputPanel              # 当前聊天输入区
├─ ImageInputPanel             # 截图上传区
├─ ReplyCandidatePanel         # 候选回复区（SSE 流式渲染）
├─ MemoryReviewPanel           # 待确认记忆区
├─ JobProgressToast            # 异步任务进度提示
└─ SettingsPanel               # 设置页（provider/模型/快捷键/数据路径/清空数据）
```

### 5.2 后端模块

```text
backend/app/
├─ main.py                     # FastAPI + PyWebView 启动入口
├─ desktop/
│   ├─ window.py               # PyWebView 窗口创建、置顶、拖拽
│   ├─ hotkey.py               # 全局快捷键
│   └─ clipboard.py            # 剪贴板读取
├─ api/
│   ├─ profiles.py
│   ├─ targets.py
│   ├─ replies.py              # SSE
│   ├─ memories.py
│   ├─ style_test.py           # SSE
│   ├─ importers.py            # 提交任务后返回 job_id
│   ├─ multimodal.py
│   ├─ jobs.py                 # 任务状态查询
│   └─ settings.py             # provider/模型配置 CRUD
├─ llm/
│   ├─ base.py                 # LLMProvider 抽象
│   ├─ mock_provider.py
│   ├─ openai_compatible_provider.py
│   ├─ anthropic_provider.py
│   ├─ router.py               # 任务→模型路由
│   └─ call_logger.py          # 写 llm_calls
├─ services/
│   ├─ reply_service.py
│   ├─ profile_service.py
│   ├─ profile_merge_service.py
│   ├─ profile_version_service.py
│   ├─ target_service.py
│   ├─ memory_service.py
│   ├─ style_test_service.py
│   ├─ style_analyzer.py
│   ├─ chat_import_service.py
│   ├─ multimodal_service.py
│   └─ settings_service.py
├─ jobs/
│   ├─ runner.py               # BackgroundTasks 调度器
│   ├─ import_qq_job.py
│   └─ profile_merge_job.py
├─ importers/
│   ├─ base_importer.py
│   ├─ qq_json_importer.py
│   └─ generic_json_importer.py
├─ prompts/
│   ├─ _registry.py            # prompt 加载 + 版本号（文件 hash）
│   ├─ generate_reply.md
│   ├─ analyze_user_style.md
│   ├─ analyze_target_style.md
│   ├─ simulate_style_test.md
│   ├─ parse_chat_screenshot.md
│   ├─ extract_memory.md
│   └─ merge_profile.md
├─ db/
│   ├─ database.py             # SQLite + WAL + JSON1
│   ├─ models.py
│   └─ migrations/             # 使用 Alembic
├─ paths.py                    # %APPDATA% 等平台路径
└─ config.py                   # 读取 app_settings + 环境变量覆盖
```

---

## 6. 数据库设计

### 6.1 user_profiles

```sql
CREATE TABLE user_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source_type TEXT,
    style_summary TEXT,
    tone_features TEXT,
    common_patterns TEXT,
    avoid_patterns TEXT,
    generation_guideline TEXT,
    confidence REAL DEFAULT 0.7,
    is_default INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);
```

source_type：

- preset
- style_test
- chat_import
- merged
- manual

---

### 6.2 style_presets

```sql
CREATE TABLE style_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    example_reply TEXT,
    config_json TEXT,
    created_at TEXT
);
```

---

### 6.3 style_test_sessions

```sql
CREATE TABLE style_test_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type TEXT,
    scenario TEXT,
    simulated_target_profile TEXT,
    status TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

---

### 6.4 style_test_messages

```sql
CREATE TABLE style_test_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    role TEXT,
    content TEXT,
    created_at TEXT,
    FOREIGN KEY(session_id) REFERENCES style_test_sessions(id)
);
```

role：

- user
- simulated_target

---

### 6.5 chat_targets

```sql
CREATE TABLE chat_targets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    relationship TEXT,
    style_summary TEXT,
    preferences TEXT,
    taboos TEXT,
    strategy_guideline TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

---

### 6.6 conversations

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER,                     -- 关联 chat_sessions
    profile_id INTEGER,
    profile_version INTEGER,               -- 生成时使用的 profile 版本
    target_id INTEGER,
    input_type TEXT,
    raw_input TEXT,
    parsed_context TEXT,
    reply_goal TEXT,
    tone TEXT,
    length TEXT,
    initiative TEXT,
    risk_level TEXT,
    generated_replies TEXT,
    selected_reply TEXT,
    user_final_sent TEXT,                  -- 可选：用户人工回填实际发送内容
    prompt_version TEXT,                   -- generate_reply.md 的 hash
    llm_call_id INTEGER,
    created_at TEXT,                       -- ISO8601 UTC
    FOREIGN KEY(thread_id) REFERENCES chat_sessions(id),
    FOREIGN KEY(profile_id) REFERENCES user_profiles(id),
    FOREIGN KEY(target_id) REFERENCES chat_targets(id),
    FOREIGN KEY(llm_call_id) REFERENCES llm_calls(id)
);
```

input_type：

- text
- image
- json_import

---

### 6.7 memories

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER,
    memory_type TEXT,
    content TEXT NOT NULL,
    confidence REAL DEFAULT 0.7,
    status TEXT DEFAULT 'pending',
    source_conversation_id INTEGER,
    created_at TEXT,
    updated_at TEXT,
    FOREIGN KEY(target_id) REFERENCES chat_targets(id),
    FOREIGN KEY(source_conversation_id) REFERENCES conversations(id)
);
```

status：

- pending
- approved
- rejected

memory_type：

- preference
- event
- relationship
- warning
- fact
- style

---

### 6.8 llm_calls

记录所有 LLM 调用，用于调试、成本统计、prompt A/B。

```sql
CREATE TABLE llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT,                             -- reply_generation / style_analysis / ...
    provider TEXT,
    model TEXT,
    prompt_version TEXT,
    request_summary TEXT,                  -- 脱敏的请求摘要
    response_summary TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd REAL,
    latency_ms INTEGER,
    status TEXT,                           -- ok / error / cancelled
    error_message TEXT,
    created_at TEXT
);
```

---

### 6.9 jobs

后台任务状态。

```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_type TEXT,                         -- import_qq_json / profile_merge / ...
    status TEXT,                           -- pending / running / success / failed / cancelled
    progress REAL DEFAULT 0,               -- 0.0 ~ 1.0
    payload TEXT,                          -- 任务入参 JSON
    result TEXT,                           -- 任务输出 JSON
    error_message TEXT,
    created_at TEXT,
    updated_at TEXT
);
```

---

### 6.10 user_profile_versions

用户风格档案的历史快照。每次融合不是原地覆盖，而是新增一个版本，`user_profiles.current_version` 指向它。

```sql
CREATE TABLE user_profile_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id INTEGER,
    version INTEGER,
    snapshot_json TEXT,                    -- 完整 profile 快照
    merge_reason TEXT,                     -- onboarding / chat_import / incremental / manual
    source_job_id INTEGER,                 -- 可选，指向触发的 job
    created_at TEXT,
    FOREIGN KEY(profile_id) REFERENCES user_profiles(id)
);
```

`user_profiles` 表需加一列：

```sql
ALTER TABLE user_profiles ADD COLUMN current_version INTEGER DEFAULT 1;
```

---

### 6.11 chat_sessions

代表一个连续的帮聊会话线程（同一对象 + 一段时间连续的多轮生成）。

```sql
CREATE TABLE chat_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id INTEGER,
    profile_id INTEGER,
    title TEXT,                            -- 可选手动标题
    last_active_at TEXT,
    created_at TEXT,
    FOREIGN KEY(target_id) REFERENCES chat_targets(id),
    FOREIGN KEY(profile_id) REFERENCES user_profiles(id)
);
```

v0.1 可以简化为每次打开悬浮窗 + 选定 target 就创建一个 session，30 分钟无活动自动结束。

---

### 6.12 app_settings

键值存储。包含所有 provider 配置、模型路由、快捷键、UI 偏好。

```sql
CREATE TABLE app_settings (
    key TEXT PRIMARY KEY,
    value TEXT,                            -- JSON 字符串
    is_secret INTEGER DEFAULT 0,           -- 读取时决定是否脱敏
    updated_at TEXT
);
```

预定义 key：

- `llm.providers`：`[{id, type, base_url, api_key, default_model, ...}]`
- `llm.task_routing`：见 §2.1.9
- `app.data_path`：只读，展示用
- `ui.hotkey.summon`：默认 `Ctrl+Shift+Space`
- `privacy.screenshot_ttl_days`：默认 30

---

### 6.13 字段规范

- 所有时间字段一律 `TEXT`，存 **ISO8601 UTC**（`2026-05-28T03:14:15.123Z`），前端根据本地时区展示。
- 所有 JSON 字段设计时明确给出 JSON Schema，代码侧用 Pydantic 模型包装。
- SQLite 开启 `journal_mode=WAL` 与 `synchronous=NORMAL`，并启用 JSON1 扩展。
- 迁移全部走 **Alembic**，避免手写 SQL 随意加列。

---

## 7. API Spec

### 7.1 风格预设

```http
GET /onboarding/style-presets
```

返回：

```json
{
  "presets": [
    {
      "id": 1,
      "name": "轻松幽默型",
      "description": "自然、轻松，偶尔用玩笑缓和气氛。",
      "example_reply": "懂了，今天是被工作吸干电量了。"
    }
  ]
}
```

---

### 7.2 创建风格测试会话

```http
POST /style-test/session
```

请求：

```json
{
  "selected_preset_ids": [1, 3],
  "avoid_patterns": ["不要太油", "不要长篇大论"],
  "target_type": "暧昧对象",
  "scenario": "对方工作很累"
}
```

返回：

```json
{
  "session_id": 1,
  "first_message": "唉，今天上班真的有点累。"
}
```

---

### 7.3 发送风格测试回复（SSE）

```http
POST /style-test/session/{session_id}/message
Accept: text/event-stream
```

请求：

```json
{
  "user_message": "那你今天是被工作榨干了吧，先躺会？"
}
```

SSE 流：

```text
event: token
data: {"delta": "嗯"}

event: token
data: {"delta": "，有点不想说话。"}

event: done
data: {"message_id": 42, "text": "嗯，有点不想说话。", "llm_call_id": 88}
```

---

### 7.4 分析风格测试结果

```http
POST /style-test/session/{session_id}/analyze
```

返回：

```json
{
  "style_summary": "用户表达偏短句、自然、轻微吐槽，不喜欢过度煽情。",
  "tone_features": {
    "sentence_length": "short",
    "humor_level": 0.65,
    "empathy_level": 0.58,
    "initiative_level": 0.42,
    "directness": 0.55,
    "formality": 0.2
  },
  "common_patterns": [
    "倾向用轻微玩笑缓和气氛",
    "回复不会过长",
    "面对情绪低落对象时会给空间"
  ],
  "avoid_patterns": [
    "避免长篇安慰",
    "避免突然深情",
    "避免过度追问"
  ],
  "generation_guideline": "生成回复时保持短句、自然、轻微幽默，在不改变用户风格的基础上增强情绪承接。"
}
```

---

### 7.5 聊天对象管理

```http
POST /targets
GET /targets
GET /targets/{id}
PUT /targets/{id}
DELETE /targets/{id}
```

---

### 7.6 粘贴文本生成回复（SSE）

```http
POST /reply/generate
Accept: text/event-stream
```

请求：

```json
{
  "thread_id": 12,
  "profile_id": 1,
  "target_id": 2,
  "conversation_text": "她：今天真的累死了\n我：怎么了\n她：也没啥，就是工作烦",
  "reply_goal": "接住情绪并继续聊天",
  "tone": "自然",
  "length": "短",
  "initiative": "中",
  "risk_level": "保守",
  "candidate_count": 4
}
```

SSE 流（多个候选以 candidate_index 区分）：

```text
event: candidate_start
data: {"candidate_index": 0, "label": "自然版"}

event: token
data: {"candidate_index": 0, "delta": "那你先"}

event: token
data: {"candidate_index": 0, "delta": "别急着说也行"}

event: candidate_done
data: {
  "candidate_index": 0,
  "text": "那你先别急着说也行，感觉今天是真的被工作耗干了。",
  "reason": "接住情绪，但没有继续追问。",
  "risk_level": "low"
}

event: done
data: {"conversation_id": 101, "llm_call_id": 555, "prompt_version": "v3-7f2a"}

event: error
data: {"code": "provider_error", "message": "upstream timeout"}
```

后续上报用户选择：

```http
POST /reply/{conversation_id}/select
{ "selected_text": "...", "user_final_sent": "..." }
```

---

### 7.7 多模态截图解析

```http
POST /multimodal/parse-chat-screenshot
```

请求：上传图片。

返回：

```json
{
  "messages": [
    {
      "speaker": "target",
      "content": "今天真的累死了",
      "time": "unknown"
    }
  ],
  "summary": "对方表达疲惫，回复欲望偏低。",
  "uncertain_parts": []
}
```

---

### 7.8 QQ JSON 导入（异步）

```http
POST /import/qq-json
```

请求：上传 JSON 文件，并指定当前用户标识。

返回：

```json
{
  "job_id": 42,
  "status": "pending"
}
```

轮询进度：

```http
GET /jobs/42
```

```json
{
  "status": "running",
  "progress": 0.42,
  "result": null
}
```

完成后 `result` 会包含 `import_id` 与检测到的 speakers。

---

### 7.9 分析导入记录

```http
POST /import/{import_id}/analyze
```

返回：

```json
{
  "user_style_profile_id": 3,
  "target_profile_id": 2,
  "summary": "已从聊天记录中提取用户表达风格和对象特征。"
}
```

---

### 7.10 记忆管理

```http
GET /targets/{id}/memories
POST /targets/{id}/memories
PUT /memories/{id}
DELETE /memories/{id}
POST /memories/{id}/approve
POST /memories/{id}/reject
```

---

### 7.11 会话线程（threads）

```http
POST /threads                    # 创建会话
{ "target_id": 2, "profile_id": 1 }
→ { "thread_id": 12 }

GET  /threads?target_id=2        # 列出某对象的最近会话
GET  /threads/{id}/conversations # 某会话下的所有生成记录
```

---

### 7.12 任务状态

```http
GET    /jobs/{id}
GET    /jobs/{id}/stream         # SSE 推送 progress
DELETE /jobs/{id}
```

---

### 7.13 应用设置与 Provider

```http
GET  /settings                   # 返回所有非敏感 key
PUT  /settings/{key}             # 更新单个 key
GET  /settings/llm/providers     # 列出 provider，api_key 脱敏
PUT  /settings/llm/providers/{id}
POST /settings/llm/providers/{id}/test   # 发一句测试消息验证
GET  /settings/llm/task-routing
PUT  /settings/llm/task-routing
```

---

### 7.14 隐私与数据

```http
GET  /privacy/data-summary       # 总记录数、所占空间、数据路径
POST /privacy/export             # 生成备份 zip（返回 job_id）
POST /privacy/import             # 导入备份 zip
POST /privacy/wipe               # 一键清空，需二次确认 token
```

---

## 8. Prompt 设计

### 8.1 测试聊天模拟 Prompt

```text
你正在扮演一个用于“聊天风格测试”的模拟聊天对象。

你的目标不是恋爱角色扮演，而是通过自然对话，让用户产生足够多的真实回复样本，以便系统分析用户的表达习惯。

【对象类型】
{target_type}

【当前场景】
{scenario}

【模拟对象性格】
{simulated_target_profile}

【对话历史】
{history}

请生成下一句模拟对象会说的话。

要求：
- 每次只说 1 句或 2 句
- 保持自然聊天，不要像测试题
- 不要暴露你在测试用户
- 重点制造日常、情绪、选择、玩笑、误会等常见聊天场景
```

---

### 8.2 用户风格分析 Prompt

```text
你是一个聊天表达风格分析器。

请根据用户在测试聊天中的回复，分析用户的表达习惯。
注意：这不是医学、心理诊断，也不是 MBTI 测试，只分析聊天表达风格。

【用户回复样本】
{user_messages}

请输出 JSON：

{
  "style_summary": "...",
  "tone_features": {
    "sentence_length": "short/medium/long",
    "humor_level": 0.0-1.0,
    "empathy_level": 0.0-1.0,
    "initiative_level": 0.0-1.0,
    "directness": 0.0-1.0,
    "formality": 0.0-1.0
  },
  "common_patterns": [],
  "avoid_patterns": [],
  "generation_guideline": "..."
}

分析要求：
- 只基于用户实际说过的话
- 不要过度推断人格
- 不要给用户贴病理化标签
- 不要把一次回复当成稳定特征
- 重点提炼“如何生成更像用户的回复”
```

---

### 8.3 聊天截图解析 Prompt

```text
你是一个聊天截图解析器。

请阅读用户上传的聊天截图，提取其中可见的聊天内容。

请输出 JSON：

{
  "messages": [
    {
      "speaker": "me/target/unknown",
      "content": "...",
      "time": "...或 unknown"
    }
  ],
  "summary": "...",
  "uncertain_parts": []
}

要求：
- 尽量按截图中的上下顺序输出
- 不确定说话人时标记为 unknown
- 不要编造截图中没有的内容
- 表情包或图片可以描述其大致含义
- 如果有被遮挡或看不清的文字，放入 uncertain_parts
```

---

### 8.4 回复生成 Prompt

```text
你是一个聊天回复建议助手。

你的任务不是替用户自动发送消息，而是根据当前聊天内容、用户表达风格、聊天对象档案和相关记忆，给出几个适合用户手动选择的回复建议。

【用户表达风格】
{user_profile}

【聊天对象档案】
{target_profile}

【相关长期记忆】
{memories}

【最近聊天内容】
{conversation_context}

【用户希望达成的目标】
{reply_goal}

【回复参数】
语气：{tone}
长度：{length}
推进感：{initiative}
风险程度：{risk_level}

请输出 3-5 个候选回复。

每个候选包含：
- label
- text
- reason
- risk_level

要求：
- 回复要贴近用户原有说话风格
- 在原风格基础上提高情绪承接能力
- 不要显得突然换了个人
- 不要过度油腻
- 不要过度舔
- 不要像客服
- 不要像 AI 作文
- 不要输出操控、威胁、攻击、PUA 式内容
- 不要替用户承诺现实中做不到的事情
- 每条回复尽量可以直接复制使用
```

---

### 8.5 记忆提取 Prompt

```text
你是一个聊天长期记忆提取器。

请从下面这段聊天中提取对未来回复有帮助的记忆。

只提取稳定、可复用的信息，不要记录无意义闲聊。

【聊天内容】
{conversation}

请按 JSON 输出：

[
  {
    "memory_type": "preference/event/relationship/warning/fact/style",
    "content": "...",
    "confidence": 0.0-1.0
  }
]

要求：
- 不要凭空猜测
- 不要把一次性情绪当成永久性格
- 不要记录过于敏感或无关的信息
- 如果没有值得保存的内容，返回 []
```

---

## 9. 开发 Plan

### Phase 0：项目骨架与架构地基

目标：把后期最容易扣不出来的架构点一次定完，走通主链路：FastAPI + PyWebView + LLM Mock + SSE + 任务队列 + 设置页。

任务：

```text
[ ] 初始化 backend FastAPI（Python 3.11+ 、uv/poetry 任选一个包管理）
[ ] 初始化 frontend（React + Vite + TS + Tailwind 可选）
[ ] 接入 PyWebView，dev 模式加载 Vite dev server，prod 模式加载 FastAPI 静态托管的 dist
[ ] 配置 SQLite + WAL + JSON1，Alembic 初始迁移
[ ] 建表：app_settings、llm_calls、jobs（其他业务表后面 phase 加）
[ ] 实现 paths.py：平台相关的 %APPDATA% 路径与创建逻辑
[ ] 实现 LLMProvider 抽象、MockProvider、OpenAICompatibleProvider 骨架
[ ] 实现 llm.router（task → model 路由）与 call_logger（写 llm_calls）
[ ] 实现 SSE 骨架接口 GET /demo/sse，验证前后端连通
[ ] 实现 BackgroundTasks Job 调度器 + GET /jobs/{id}
[ ] 实现 GET/PUT /settings/llm/providers + POST /settings/llm/providers/{id}/test
[ ] 前端实现悬浮窗基础外观（置顶、可拖拽、可调整大小）
[ ] 前端实现设置页骨架（provider 配置 + “发一条测试消息”按钮）
[ ] pytest 跑起来，加 1-2 个烟雾用例
[ ] PyInstaller 试打包一次，验证能运行
[ ] README 写启动与打包说明
```

验收标准：

```text
[ ] dev 模式一键启动，悬浮窗可置顶显示
[ ] 设置页能添加 OpenAI 兼容 provider 并“测试连通”
[ ] /demo/sse 能从后端流式推送 token 到前端
[ ] 创建一个 Mock LLM 任务后能在 llm_calls 表看到记录
[ ] 提交一个耗时 5 秒的假任务，能轮询进度 0→1
[ ] PyInstaller 打出的 exe 能独立运行并打开悬浮窗
```

---

### Phase 1：首次启动与风格预设

目标：用户能选择基础风格并生成初始人设。

任务：

```text
[ ] 内置风格预设 seed 数据
[ ] 实现风格预设 API
[ ] 实现首次启动向导 UI
[ ] 实现禁区选择
[ ] 生成 preset 类型 user_profile
[ ] 保存默认人设
```

验收标准：

```text
[ ] 用户第一次打开能看到向导
[ ] 用户能选择风格和禁区
[ ] 系统能保存默认人设
```

---

### Phase 2：风格测试聊天窗口

目标：用户能和模拟对象聊天，并生成表达风格档案。

任务：

```text
[ ] 实现 style_test_sessions 表
[ ] 实现 style_test_messages 表
[ ] 实现创建测试会话 API
[ ] 实现发送测试消息 API
[ ] 接入 LLM 生成模拟对象下一句话
[ ] 实现测试聊天 UI
[ ] 实现分析测试结果 API
[ ] 保存 style_test 类型 user_profile
```

验收标准：

```text
[ ] 用户能选择模拟对象和场景
[ ] 用户能完成 10-20 轮测试聊天
[ ] 系统能输出用户表达风格分析
[ ] 用户能确认并保存人设
```

---

### Phase 3：聊天对象档案

目标：用户能创建聊天对象，并保存对象特征。

任务：

```text
[ ] 实现 chat_targets 表
[ ] 实现目标对象 CRUD API
[ ] 实现聊天对象管理 UI
[ ] 支持手动填写关系、偏好、禁忌
[ ] 支持 AI 辅助整理对象档案
```

验收标准：

```text
[ ] 用户能创建聊天对象
[ ] 用户能编辑对象偏好和禁忌
[ ] 回复生成时能读取对象档案
```

---

### Phase 4：文本输入生成回复（核心闭环，优先级最高）

> 注：本阶段与 Phase 3 可交换。建议先跑通本阶段的“最小 target”（只要 name 与手写 strategy），拿到核心价值验证，再回过头完善 target 档案。

目标：跑通核心帮聊闭环。

任务：

```text
[ ] 实现 conversations、chat_sessions 表
[ ] 实现 reply/generate 的 SSE 接口
[ ] 实现回复生成 Prompt，并在 prompts/_registry.py 中记录 prompt_version
[ ] 前端支持粘贴聊天内容
[ ] 前端 SSE 流式渲染多候选
[ ] 支持选择回复目标
[ ] 支持语气、长度、推进感、风险参数
[ ] 返回 3-5 个候选回复
[ ] 支持一键复制
[ ] 默认保存本轮记录，存入 conversations.profile_version / prompt_version / llm_call_id
[ ] POST /reply/{id}/select 上报用户选择
```

验收标准：

```text
[ ] 用户粘贴聊天内容后能流式看到多候选回复
[ ] 回复受到用户人设影响
[ ] 回复受到对象档案影响（如该 target 存在）
[ ] llm_calls 表能查到本次调用的 tokens 与 cost
[ ] 用户选择后能在 conversations 表看到 selected_reply
```

---

### Phase 5：多模态截图输入

目标：用户可以上传聊天截图，系统直接用多模态模型解析。

任务：

```text
[ ] 实现图片上传 API
[ ] 实现 multimodal_service
[ ] 实现聊天截图解析 Prompt
[ ] 前端支持上传截图
[ ] 展示结构化解析结果
[ ] 用户可手动修正解析结果
[ ] 修正后进入回复生成流程
```

验收标准：

```text
[ ] 用户上传截图后能得到聊天文本
[ ] 用户能修改解析结果
[ ] 修改后的内容可用于生成回复
```

---

### Phase 6：QQ JSON 导入

目标：支持从 QQ JSON 历史聊天中抽取用户和对象特征。

任务：

```text
[ ] 设计导入数据结构
[ ] 实现 qq_json_importer
[ ] 支持选择“哪一方是我”
[ ] 解析消息列表
[ ] 对用户消息做表达风格分析
[ ] 对对方消息做对象风格分析
[ ] 生成 chat_import 类型 user_profile
[ ] 更新 chat_target 档案
```

验收标准：

```text
[ ] 能导入一份 QQ JSON
[ ] 能识别用户和对方消息
[ ] 能输出用户风格档案
[ ] 能输出对象风格档案
```

---

### Phase 7：记忆系统 v1

目标：系统开始沉淀对象记忆。

任务：

```text
[ ] 实现 memories 表
[ ] 生成回复后自动提取待确认记忆
[ ] 前端展示待确认记忆
[ ] 用户可通过/拒绝/编辑记忆
[ ] 回复生成时读取 approved 记忆
```

验收标准：

```text
[ ] 系统能从聊天中提取记忆
[ ] 默认不直接污染长期记忆
[ ] 用户确认后记忆能进入后续生成上下文
```

---

### Phase 8：体验优化

目标：让悬浮窗更像真实可用产品。

任务：

```text
[ ] 全局快捷键唤起
[ ] 快捷读取剪贴板
[ ] 最近对象置顶
[ ] 回复收藏
[ ] 历史记录搜索
[ ] Prompt 模板可编辑
[ ] 数据导入/导出
[ ] 本地数据备份
```

---

## 10. v0.1 Must / Should / Could

### Must Have

```text
[ ] 悬浮窗前端
[ ] FastAPI 后端
[ ] SQLite 本地存储
[ ] 默认保存对话和生成记录
[ ] 性格/风格预设选择
[ ] 聊天测试窗口
[ ] 从测试聊天中提炼用户表达风格
[ ] 创建聊天对象档案
[ ] 粘贴当前聊天内容
[ ] 生成 3-5 个候选回复
[ ] 候选回复一键复制
[ ] 保存用户最终选择的回复
```

### Should Have

```text
[ ] 多模态截图输入
[ ] QQ JSON 导入
[ ] 分析聊天对象性格特征
[ ] 待确认记忆系统
[ ] 根据用户选择持续修正用户风格
```

### Could Have

```text
[ ] 向量库召回
[ ] 快捷键唤起
[ ] 剪贴板辅助
[ ] 回复风险标签
[ ] 回复收藏
[ ] Prompt 模板编辑器
[ ] 历史记录搜索
```

### Won't Have in v0.1

```text
[ ] 自动读取微信/QQ消息
[ ] 自动发送消息
[ ] 手机端 App
[ ] 浏览器插件
[ ] 复杂多 Agent 编排
[ ] 完整向量记忆系统
[ ] 情感操控/PUA式策略生成
```

---

## 11. Codex 执行建议

### 11.1 可以直接把本文档交给 Codex 吗？

可以，但不建议让 Codex 一次性全做。

更合理的方式是：

1. 把本文档放进仓库根目录，例如：

```text
/docs/ai_chat_wingman_spec_plan.md
```

2. 再给 Codex 一个很小的阶段任务。

例如先让它做 Phase 0：

```text
请阅读 docs/ai_chat_wingman_spec_plan.md。
先只实现 Phase 0：架构地基。
要求：
- backend 使用 FastAPI + SQLite + Alembic
- frontend 使用 React + Vite + TS，由 PyWebView 加载
- 完成 LLM Provider 抽象、MockProvider、OpenAICompatibleProvider 骨架
- 完成 SSE 骨架接口与 BackgroundTasks 任务调度
- 完成 app_settings / llm_calls / jobs 三张表
- 完成设置页 provider 配置与"一键测试连通"
- PyInstaller 能打出可运行的 exe
- 不要实现任何业务功能（不动预设/测试/生成）
- 完成后更新 README，写清启动与打包方式
```

3. 每次只让 Codex 做一个 Phase。

不要一条消息让它从悬浮窗、FastAPI、LLM、多模态、QQ JSON、记忆系统全部做完。那样容易架构漂移，也容易写出一堆半成品。

---

### 11.2 推荐 Codex 任务拆分

#### Task 1：架构地基

```text
请阅读 docs/ai_chat_wingman_spec_plan.md。
只实现 Phase 0：架构地基。
严格按 §2.1.9 / 2.1.10 / 2.1.11 / 2.1.12 / 6.8 / 6.9 / 6.12 / 7.12 / 7.13 的定义实现。
不要实现业务功能。完成后更新 README、验证 PyInstaller 可打包。
```

#### Task 2：预设 + 首次启动向导 + 隐私声明

```text
基于现有骨架，实现 Phase 1。
包括 style_presets 表、seed 数据、API、首次启动向导（含隐私声明页）、保存默认 user_profile。
不要实现聊天测试。
```

#### Task 3：文本输入生成回复（核心闭环）

```text
实现 Phase 4。
包括 conversations / chat_sessions 表、/reply/generate 的 SSE 接口、generate_reply prompt 与 prompt_version 记录、
前端流式渲染、一键复制、/reply/{id}/select。
llm 层一律走 Phase 0 的 LLMProvider 抽象。
target 可以只有 name + 手写 strategy，完整 target 档案放到 Task 5。
```

#### Task 4：风格测试聊天窗口

```text
实现 Phase 2。
包括 style_test_sessions / style_test_messages、创建测试会话、SSE 流式发送测试消息、分析测试结果。
完成后出一份 profile_merge_service 骨架（§3.3），并生成 user_profile_versions 快照。
```

#### Task 5：聊天对象档案完整化

```text
实现 Phase 3。
包括 chat_targets CRUD、手动填写 / AI 辅助整理、生成回复时读取档案。
```

#### Task 6：多模态截图解析

```text
实现 Phase 5。
走多模态模型（通过 llm.router 的 multimodal task），不做 OCR。
解析结果允许用户手动修正后进入回复生成。
```

#### Task 7：记忆系统 v1

```text
实现 Phase 7。
生成回复后提取 pending memories，用户确认后转为 approved。
回复生成时只读取 approved memories。
```

#### Task 8：QQ JSON 导入（走 jobs）

```text
实现 Phase 6。
设计 importer 抽象层，先支持一种 QQ JSON 示例格式。
全过程走 jobs 表，不能同步阻塞 HTTP。
解析完毕后触发 profile_merge 作为一个后续 job。
```

---

## 12. Codex / Agent 执行约束

让 Codex 或任何代码代理执行时明确以下约束：

```text
- 不要一次性实现全部功能
- 不要引入过重框架（不加 Celery/Redis/Kafka 之类，BackgroundTasks 足够）
- 不要把 LLM API Key 写死或写进仓库，必须走 app_settings + 环境变量
- 不要自动发送聊天消息
- 不要后台偷偷读取聊天软件内容
- 默认本地存储，所有路径走 paths.py，不要硬写相对路径
- 任何长期记忆写入都要可查看、可删除
- 所有生成回复都必须由用户确认后手动使用
- 所有 LLM 调用走 llm.router，不要直接 import provider SDK
- 所有耗时操作（>2s）走 jobs 表，不要同步阻塞 HTTP 连接
- 所有流式接口走§2.1.10 定义的 SSE 事件格式
- profile 变更一律走 profile_merge_service，进入后必须生成 user_profile_versions 快照
```

---

## 13. 当前最推荐的第一步

先把 **Phase 0（架构地基）** 独立完成并验收。这一步不交付业务价值，但是后面所有 phase 的能不能顺利跑都取决于它：

- 同进程 PyWebView + FastAPI 启动与打包路径跑通
- LLM Provider 抽象 + Mock 同时可用
- SSE 骨架与 jobs 骨架能走通
- app_settings / llm_calls / jobs / Alembic 存在
- 设置页能加 provider 并“一键测试连通”

验收后再进入 Phase 1（预设 + 首次启动向导，含隐私声明页）与 Phase 2（风格测试聊天窗口）。

推荐的 phase 顺序：

```text
Phase 0  架构地基【必要】
Phase 1  预设 + 首次启动向导 + 隐私声明
Phase 4  文本输入生成回复（提前跑通价值闭环，允许 target 只有 name）
Phase 2  风格测试聊天窗口（在有了流式与帮聊体验后才做，能复用 SSE）
Phase 3  聊天对象档案完整化
Phase 5  多模态截图输入
Phase 7  记忆系统 v1
Phase 6  QQ JSON 导入（走 jobs）
Phase 8  体验优化
```

不要在 Phase 0/1 完成前动多模态、QQ JSON、记忆系统。先把主架构定稳。
