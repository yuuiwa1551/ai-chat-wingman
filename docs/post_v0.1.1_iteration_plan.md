# AI Chat Wingman Post v0.1.1 Iteration Plan

本文档基于 `docs/ai_chat_wingman_spec_plan.md`、`docs/business_optimization_completion_log.md` 和当前代码状态，整理 v0.1.1 之后最值得更新的方向。

目标不是继续堆功能，而是把已经存在的能力变成更容易发现、更可信、更安全、更接近真实使用的产品。

## Current Read

当前已经具备：

1. 核心回复生成、SSE 流式候选、复制、选中、收藏。
2. 首次启动、风格预设、风格测试、profile version 快照。
3. Provider 配置、模型检测、连通测试、Mock 与 OpenAI-compatible provider。
4. 对象档案 CRUD、对象策略整理、对象影响规则展示。
5. 截图解析、QQ JSON 导入、pending memory、历史搜索、收藏回复、本地备份导出。
6. Windows tag 自动构建和 release asset 上传。

当前主要缺口：

1. 主工作区已经实现的导入、历史、数据、风格测试等面板没有全部暴露在左侧导航里，用户不容易发现。
2. 首次使用流程顺序不够强：应该先配置真实 `api_url` / `api_key`，再进入导入与校准；导入应放在最前面，且不导入不能继续使用，不提供 skip。
3. 桌面窗口初始尺寸偏小，需要用户手动拉大；同时窗口不应默认置顶，应提供“钉在最前面 / 取消置顶”的显式按钮。
4. 页面内部仍有外层框感和页面级滚动条，应该去掉窗口内容里的外框/横向滚动，让应用壳直接贴合窗口。
5. `start_app.bat` 会弹出终端窗口，普通用户容易误关；需要静默启动或至少避免暴露多个可关闭的终端。
6. `frontend/package.json` 与 `backend/pyproject.toml` 仍是 `0.1.0`，release tag 已到 `v0.1.1`，版本元数据需要统一。
7. 数据页已有备份导出，但还缺备份导入、一键清空和二次确认闭环。
8. 真实 Provider 可用性还停留在能配置、能测试，缺少任务级模型路由 UI、失败诊断和调用成本可视化。
9. 记忆和对象档案已经能跑通，但缺少去重、合并、来源解释和导入前预览。
10. 桌面形态仍偏普通窗口，收起、托盘、快捷键、窗口位置记忆等能力还没形成产品手感。

## Recommended Next Version: v0.1.2

v0.1.2 建议定位为：

> 把 v0.1.1 已实现的能力整理成“首次使用顺序清晰、桌面启动不打扰、功能入口可发现”的桌面 preview。

不建议 v0.1.2 做大模型效果的大重构，也不建议直接上向量库。先让现有链路更像可交付产品。

## P0 - First-Run Gate, Desktop Shell, And Release Hygiene

目标：先修用户第一次打开就会遇到的问题：配置顺序、导入门槛、窗口形态、静默启动、功能入口和版本发布可信度。

范围：

1. 首次使用第一步改成 Provider 配置，必须填写 `api_url`、`api_key` 和模型名，并通过连通测试后才能继续。
2. Provider 配置后进入导入与校准步骤，其中导入放在最前面；不导入不能继续进入主工作台，不提供 skip。
3. 导入步骤先支持 QQ JSON 当前格式；如果后续允许“样例体验”，也必须明确标为 demo，不等同于真实可用流程。
4. 工作区左侧导航补齐：回复、对象、导入、记忆、历史、风格、数据。
5. 保留设置为顶部独立入口，但设置页内补清晰返回路径。
6. 让对象搜索框从 read-only 变成可用过滤。
7. 桌面窗口初始尺寸调大，建议不小于 `1100 x 760`，避免用户打开后还要手动拉伸。
8. PyWebView 窗口默认 `on_top=false`，顶部提供“钉在最前面 / 取消置顶”按钮并同步真实窗口状态。
9. 去掉页面内部的外框感和页面级横向滚动条：应用壳贴合窗口，`body` 与根节点禁止横向 overflow，仅内容区域按需滚动。
10. `收起窗口` 改成真实行为，至少在桌面壳不可控时隐藏按钮或改为明确的占位状态。
11. `start_app.bat` 改成用户友好的静默启动：不弹出多个终端窗口；开发调试日志写入本地日志文件，失败时再展示可读错误。
12. 同步版本元数据：`frontend/package.json`、`backend/pyproject.toml`、README、release notes 模板。
13. workflow 对 tag release 优先读取 `docs/release_notes_<tag>.md`，避免 release 正文靠手动补。
14. 处理 GitHub Actions 的 Node.js 20 runtime deprecation 提醒，提前兼容 Node 24 actions 运行时。

验收：

1. 新用户必须先完成真实 Provider 配置，再完成导入；没有 skip 可以绕过这两步进入主工作台。
2. 用户可以从主工作区进入导入、历史、数据、风格测试。
3. 应用首次打开窗口尺寸足够承载主工作区，不出现页面级横向滚动条。
4. 窗口默认不置顶；点击置顶按钮后窗口才保持在最前面，再次点击可取消。
5. 双击 `start_app.bat` 不弹出多个常驻终端窗口；错误日志可在本地 logs 中追踪。
6. v0.1.2 包内和文档中的版本号一致。
7. tag 构建后 release body 和 zip asset 都自动就位。
8. `npm run build`、后端 pytest、tag workflow dry path 或实际 tag 构建通过。

## P1 - Real Provider Confidence

目标：让用户配置真实模型后，能知道每个任务到底用哪个模型、失败在哪里、花了多少。

范围：

1. 设置页新增任务路由 UI：回复生成、风格分析、记忆提取、截图解析分别选择 provider/model。
2. 将 `llm.task_routing` 从后端 API 贯通到前端设置页。
3. Provider 测试拆成文本测试和多模态测试。
4. OpenAI-compatible 错误归类：鉴权失败、模型不存在、base URL 错、网络超时、响应格式不兼容。
5. `llm_calls` 在数据页展示最近调用、耗时、token、错误状态。
6. 为 OpenAI-compatible provider 增加 httpx mock 测试，覆盖 models、complete、stream、multimodal 的成功和失败路径。

验收：

1. 用户能明确看到“回复生成用 A 模型，截图解析用 B 模型”。
2. Provider 失败反馈能指向下一步，而不是只显示原始异常。
3. 后端有 provider mock 测试覆盖，不依赖真实 API Key。

## P2 - Data Safety And Recovery

目标：把“本地可控”从文案变成完整操作闭环。

范围：

1. 增加备份导入 API 和 UI，导入前展示备份内容摘要。
2. 增加一键清空所有数据 API，必须使用二次确认 token。
3. 数据页显示截图、导入文件、日志、备份四类占用，并支持打开路径。
4. 增加截图/导入文件清理策略，默认只清理文件，不误删数据库记录。
5. 导出备份时写入 manifest，包括应用版本、创建时间、表计数和包含文件数。

验收：

1. 用户可以导出备份、导入备份，并看到导入前风险提示。
2. 清空数据必须二次确认，且有后端测试证明不会被普通误触触发。
3. 所有路径仍通过 `backend/app/paths.py` 生成。

## P3 - Import Preview And Memory Quality

目标：降低导入和长期记忆污染风险。

范围：

1. QQ JSON 导入增加预览步骤：识别 speakers、消息数量、时间范围、可能的“我”。
2. 导入前允许用户确认或修改“哪一方是我”和目标对象。
3. 导入分析结果先展示，不直接覆盖默认 profile；用户确认后再 merge。
4. 记忆增加相似项检测，提示合并、替换或保留。
5. 记忆卡片展示来源 conversation、提取原因、会怎样影响回复。
6. 批量操作增加 undo 窗口或最近操作记录。

验收：

1. 导入错误的 speaker 不会直接污染 profile。
2. approved memory 仍必须来自用户确认。
3. 记忆重复率下降，用户能看懂每条记忆为什么值得保存。

## P4 - Style Learning From User Selection

目标：让用户选中的回复逐渐反哺用户风格，但仍保持可控。

范围：

1. `/reply/{conversation_id}/select` 支持记录用户最终修改后的发送文本。
2. 增加 selected reply 样本统计，达到阈值后生成待确认 profile merge 建议。
3. `profile_merge_service` 支持 selection-based merge，并写入 `user_profile_versions`。
4. 前端提供 profile 版本历史、差异摘要和回滚入口。
5. 用户可以关闭“从选中回复学习”的开关。

验收：

1. 单次选中不会立即污染默认 profile。
2. 达到阈值后产生可审阅的风格更新建议。
3. 每次 profile 变化都有版本快照和回滚路径。

## P5 - Desktop Usability

目标：让它更像桌面帮聊工具，而不是包在桌面壳里的网页。

范围：

1. 托盘图标、最小化到托盘、恢复窗口。
2. 全局快捷键唤起窗口。
3. 窗口大小和位置记忆。
4. 用户主动点击后读取剪贴板文本，不做后台自动读取。
5. 打包后启动烟雾验证：exe 启动、healthz 可用、窗口可打开。

验收：

1. 用户能用快捷键调出窗口。
2. 关闭/收起行为符合桌面软件预期。
3. 不违反“不自动读取聊天软件内容”的边界。

## Suggested Execution Order

1. v0.1.2 P0：首次启动门槛 + 桌面启动体验 + 导航/发布卫生。
2. v0.1.2 P1：真实 Provider 信心增强。
3. v0.1.3 P2：数据安全和恢复闭环。
4. v0.1.3 P3：导入预览和记忆质量。
5. v0.2.0 P4：基于用户选择的风格学习。
6. v0.2.0 P5：桌面可用性完善。

## First Work Unit Recommendation

下一步最建议先做 `v0.1.2 P0 - First-Run Gate, Desktop Shell, And Release Hygiene`。

理由：

1. 首次使用顺序会决定用户能不能真正跑出有质量的回复；先配置真实 Provider，再导入历史记录，比先看 demo 更符合真实使用。
2. 已有功能很多，但入口不完整会让用户误以为没有这些能力。
3. 窗口尺寸、置顶、内部滚动条和终端弹窗都属于第一印象问题，应该在继续做深层能力前先修。
4. 版本号和 release 自动化属于发布可信度问题，越早修越省后续成本。
5. 验收清晰，可以在一个小阶段内完成并发布 v0.1.2。

不建议下一步直接做：

1. 向量记忆：当前 memory 质量、确认流和去重还没稳。
2. 自动读取聊天软件：明确不做，违反产品边界。
3. 手机端：Windows preview 还没有足够稳定。
4. 多 Agent 编排：当前价值不依赖复杂编排。
