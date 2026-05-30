# Frontend UI/UX Redesign Implementation Plan

> Status: planning
> Source design: Figma `v2 layout refinement`
> Scope: frontend-only implementation plan for the revised main workspace and first-run entry flow.

## Goal

把当前纵向堆叠的前端页面改成更接近 Figma v2 的桌面工作台：

- 主界面以“当前聊天”为中心，视觉和操作方式接近 QQ / 微信桌面聊天窗口。
- 输入区固定在主聊天窗口底部，回复目标和语气控制紧贴输入框上方。
- 候选回复作为右侧辅助栏，不抢主聊天区空间。
- 首次使用先进入“导入或校准”选择页：JSON 导入、模拟聊天并列，并提供 Skip 直接进入主界面。

## Product Boundaries

必须继续遵守 `docs/ai_chat_wingman_spec_plan.md` 和 `AGENTS.md`：

- 不实现自动读取聊天软件内容。
- 不实现自动发送消息。
- 生成回复只用于用户复制、编辑、手动发送。
- 所有截图、导入文件、SQLite、日志仍然走本地数据目录。
- LLM 调用和 SSE 协议不在本任务中改动。
- 本次主要是前端信息架构和交互重组，不新增后端业务能力。

## Current Frontend State

当前 `frontend/src/App.tsx` 按顺序渲染：

1. `OnboardingWizard`
2. `TargetManager`
3. `QQImportPanel`
4. `MemoryReviewPanel`
5. `ReplyGenerator`
6. `HistoryPanel`
7. `DataPanel`
8. `StyleTestPanel`
9. Provider 设置
10. SSE Demo

问题：

- 所有模块纵向堆叠，主流程被管理面板淹没。
- `ReplyGenerator` 把聊天输入、截图、对象、目标、语气、候选都放在一个卡片里，缺少聊天软件式工作流。
- 首次启动直接进入风格预设选择，和新的“先导入/校准/跳过”入口不一致。
- `styles.css` 以窄窗口卡片流为主，无法承载三栏工作台。

## Target Information Architecture

### App Shell

`App.tsx` 只负责全局数据加载和路由状态：

- provider 列表和状态
- onboarding 状态
- style presets
- targets
- active target
- active workspace tab
- global status

主界面拆成：

```text
FloatingWorkspace
├─ AppTopBar
├─ WorkspaceRail
├─ TargetSidebar
├─ ChatReplyWorkspace
│  ├─ ChatContextPanel
│  ├─ ChatComposer
│  └─ PendingMemoryStrip
└─ CandidateSidebar
```

二级管理界面拆成：

```text
WorkspaceDrawer / SettingsWorkspace
├─ TargetManager
├─ MemoryReviewPanel
├─ HistoryPanel
├─ DataPanel
├─ StyleTestPanel
└─ ProviderSettingsPanel
```

第一版可以先用 tab / drawer 方式切换，不必做复杂多窗口。

### First Run Flow

`OnboardingWizard` 改成分步状态机：

```text
import-choice
├─ JSON import
├─ simulated chat
└─ skip

preset-profile
├─ style presets
├─ avoid patterns
└─ save default profile
```

第一阶段目标：

- JSON import：展示导入说明，进入已有 `QQImportPanel` 或触发内嵌导入步骤。
- simulated chat：展示说明，进入已有 `StyleTestPanel` 或后续风格测试步骤。
- skip：创建一个最小默认 profile 后进入主界面。

如果后端当前只支持 `createDefaultProfile(selected_preset_ids)`，Skip 需要复用第一个 preset 或要求用户选择一个默认 preset。不要伪造后端状态。

## Implementation Slices

### Slice 1: Shell And Layout

目标：先把主界面骨架落地，不改生成逻辑。

Files:

- `frontend/src/App.tsx`
- `frontend/src/components/FloatingWorkspace.tsx` (new)
- `frontend/src/components/AppTopBar.tsx` (new, optional)
- `frontend/src/components/WorkspaceRail.tsx` (new, optional)
- `frontend/src/styles.css`

Tasks:

1. 在 `App.tsx` 中把已登录后的渲染入口替换为 `FloatingWorkspace`。
2. 提升 `activeTargetId` 到 `App.tsx`。
3. `FloatingWorkspace` 建立三栏布局：rail、target sidebar、main chat workspace、candidate sidebar。
4. Provider 设置、SSE Demo、历史、数据、风格测试先移入管理区入口，不再默认全部展开。

Acceptance:

- 默认主界面不再纵向堆叠。
- 窗口宽度足够时呈现 Figma v2 的三栏布局。
- 小宽度下布局可降级为单列或横向滚动，但不能出现文本重叠。

### Slice 2: Chat-First Reply Workspace

目标：复用现有 `ReplyGenerator` 的 API 逻辑，重排为聊天软件式操作。

Files:

- `frontend/src/components/ReplyGenerator.tsx`
- `frontend/src/components/ChatContextPanel.tsx` (new, optional)
- `frontend/src/components/ChatComposer.tsx` (new, optional)
- `frontend/src/components/CandidateSidebar.tsx` (new, optional)
- `frontend/src/components/ImageInputPanel.tsx`
- `frontend/src/styles.css`

Tasks:

1. 保留 `generateReply`、`selectReply`、`favoriteReply`、剪贴板读取和 SSE 事件处理。
2. 将 `chatText` 的编辑入口移到底部 composer。
3. 在主聊天区用简易解析展示聊天气泡：
   - `对方:` / `对方：` / `target:` 视为对方气泡。
   - `我:` / `我：` / `me:` 视为用户气泡。
   - 无法识别时作为普通上下文块展示。
4. 回复目标、语气、长度、风险、推进感改成紧贴 composer 的 chips / compact controls。
5. 候选回复移动到右侧，卡片展示文本、候选序号、复制、选中、收藏。
6. 截图入口保持存在，但折叠在输入区附近，不在主界面单独占大块。

Acceptance:

- 用户能粘贴聊天内容并生成候选回复。
- SSE 流式候选仍正常显示。
- 复制、选中、收藏仍可用。
- 输入区固定在主聊天工作区底部。

### Slice 3: Target And Memory Context

目标：让对象和待确认记忆成为主流程的轻量上下文，不把完整管理面板塞进主屏。

Files:

- `frontend/src/components/TargetSidebar.tsx` (new)
- `frontend/src/components/MemoryReviewPanel.tsx`
- `frontend/src/components/TargetManager.tsx`
- `frontend/src/App.tsx`

Tasks:

1. `TargetSidebar` 显示对象列表、当前对象摘要、对象策略提示。
2. 完整对象编辑继续由 `TargetManager` 管理，可通过二级入口打开。
3. 主聊天区只展示少量 pending memory，例如最近 1-2 条，避免挤压聊天。
4. pending memory 的确认/忽略操作优先复用现有 `MemoryReviewPanel` API。

Acceptance:

- 切换对象会影响 `ReplyGenerator` 的 target 参数。
- 主界面能看到对象策略提示。
- 待确认记忆不再占据大段主屏空间。

### Slice 4: First-Run Import Choice

目标：按 Figma v2 改造首次启动入口。

Files:

- `frontend/src/components/OnboardingWizard.tsx`
- `frontend/src/components/QQImportPanel.tsx`
- `frontend/src/components/StyleTestPanel.tsx`
- `frontend/src/styles.css`

Tasks:

1. `OnboardingWizard` 增加 `step` 状态：`choice`、`json-import`、`style-test`、`preset-profile`。
2. `choice` 页面展示：
   - 导入/校准作用说明
   - JSON 导入卡片
   - 模拟聊天校准卡片
   - Skip
3. JSON 导入路径：
   - 第一版可以跳转到内嵌 `QQImportPanel`。
   - 导入完成后继续让用户确认/创建默认 profile，不能静默污染 approved 记忆。
4. 模拟聊天路径：
   - 第一版可以跳转到内嵌 `StyleTestPanel`。
   - 风格测试完成后进入默认 profile 保存。
5. Skip 路径：
   - 若有 presets，默认选第一个 preset + 默认 avoid pattern 创建 profile。
   - 若无 presets，显示错误并要求用户等待数据加载或手动选择。

Acceptance:

- 首次打开不再直接进入 preset grid。
- 用户能从选择页进入 JSON 导入、模拟聊天或 Skip。
- Skip 后能进入主工作台。
- 页面明确说明本地保存和不自动读取/发送。

### Slice 5: Settings And Secondary Panels

目标：把非主流程功能收纳起来，保持可访问但不干扰回复工作台。

Files:

- `frontend/src/components/ProviderSettingsPanel.tsx` (new or extracted)
- `frontend/src/components/WorkspaceDrawer.tsx` (new, optional)
- `frontend/src/components/DataPanel.tsx`
- `frontend/src/components/HistoryPanel.tsx`
- `frontend/src/components/StyleTestPanel.tsx`
- `frontend/src/App.tsx`

Tasks:

1. 从 `App.tsx` 抽出 Provider 设置逻辑，避免主组件过大。
2. 将 `SSE Demo` 移到开发/诊断区，生产主界面默认隐藏。
3. `DataPanel` 和 `HistoryPanel` 放到二级面板。
4. 保持现有功能可用，不在本任务中删除业务能力。

Acceptance:

- 主界面只聚焦对象、聊天、输入、候选。
- 设置、历史、数据、风格测试仍可通过入口打开。

## CSS Direction

需要重写为 token 化的桌面工作台样式：

```css
--color-bg: #f6f8f6;
--color-surface: #ffffff;
--color-surface-soft: #fafcfb;
--color-border: #dde6e0;
--color-primary: #2d7a68;
--color-primary-soft: #e8f4f0;
--color-text: #16201d;
--color-muted: #6b7a73;
--radius: 8px;
```

布局原则：

- `.window-shell` 从 `720px` 窄容器改为桌面 shell，宽度允许 `min(100vw, 1220px)` 或更接近 PyWebView 实际窗口。
- 三栏使用 CSS grid：
  - rail: 64px
  - target sidebar: 214px
  - main chat: minmax(420px, 1fr)
  - candidate sidebar: 266px
- 主聊天区内部使用 grid/flex，把 composer 固定到底部。
- 所有按钮、chips、卡片半径不超过 8px。
- 禁止文本挤压溢出；长文本用 `overflow-wrap: anywhere` 或限制行数。

## Validation Plan

每个 slice 完成后至少跑：

```powershell
cd frontend
npm run build
```

最终 UI 验证：

1. 启动前端 dev server。
2. 用浏览器检查默认主界面。
3. 检查首次启动选择页。
4. 检查生成回复流式渲染。
5. 检查窄宽度下无明显重叠。

如果后端未启动导致部分接口不可用，需在最终说明中明确哪些验证只完成了 build/typecheck，哪些交互未实测。

## Risk And Open Questions

- 当前 Figma v2 是 SVG 粘贴稿，不是精确 auto-layout 规范；实现时以信息结构和比例为准，不追逐像素级 1:1。
- Skip 创建默认 profile 依赖已有 style preset；如果后端可能返回空 presets，需要前端错误态。
- JSON 导入属于 Phase 6，但产品入口在首次启动中提前出现。实现时只能复用现有导入能力，不新增 importer 后端范围。
- `ReplyGenerator` 当前职责较重。实现时可以先保持状态在一个组件内，等 UI 稳定后再拆更细。
- 主界面要避免把所有二级面板一次性挂载，防止首屏复杂度继续膨胀。

## Suggested Execution Order

1. Slice 1: Shell and layout.
2. Slice 2: Chat-first reply workspace.
3. Slice 4: First-run import choice.
4. Slice 3: Target and memory context.
5. Slice 5: Settings and secondary panels.

每个 slice 都应当独立可构建、可回退、可截图检查。
