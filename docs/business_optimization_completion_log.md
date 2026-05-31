# AI Chat Wingman Business Optimization Completion Log

本文档记录 v0.1.0 之后围绕“首次成功体验”和“业务可用性”完成的 P0-P4 改动，作为后续继续规划、复盘和发布说明的整理入口。

## Version Scope

- 基线版本：`v0.1.0`
- 本次整理目标：`v0.1.1`
- 覆盖提交：`0c5b077` 到 `349146b`，以及 v0.1.1 发布整理提交
- 计划来源：`docs/business_optimization_phase_plan.md`

`v0.1.0` 的 tag 与 Windows zip 早于 P0-P4 落地。`v0.1.1` 用来把这些业务优化正式纳入可下载版本，并补齐 release 说明和记录文档。

## P0 - First Successful Reply Loop

提交：`0c5b077 feat: improve first reply activation`

完成内容：

1. 初次导入页新增“试用示例聊天”，未配置真实 Provider 时也能直接进入主工作台。
2. 主工作台增加常见场景快捷项，例如“对方累了”“对方冷淡”“推进邀约”“缓和误会”“体面结束”。
3. 候选回复卡片展示策略解释，让用户知道每条候选为什么这样写。
4. Mock 演示状态更明确，避免把流程演示误解成真实模型质量。

验收结果：

1. 前端构建通过。
2. 浏览器检查覆盖首次页和主工作台核心路径。

## P1 - Provider Setup Confidence

提交：`13a3401 feat: guide provider setup flow`

完成内容：

1. Provider 设置页增加 OpenAI-compatible 配置步骤说明。
2. 对 Mock、真实 Provider 未完成、模型检测失败、连通失败分别给出更具体的状态反馈。
3. 主界面 Provider 状态能够说明当前仍在演示模式，还是已经启用真实模型。

验收结果：

1. 前端构建通过。
2. 浏览器检查覆盖设置页配置提示和状态文案。

## P2 - Target Value Front Loading

提交：`fba84bd feat: surface target reply impact`

完成内容：

1. 新增对象策略推导逻辑，按关系、沟通偏好、禁忌和最近上下文生成可读规则。
2. 对象侧栏展示“这个对象会如何影响回复”的规则摘要。
3. 回复区在选择对象后展示当前对象策略对候选回复的影响。

验收结果：

1. 前端构建通过。
2. 浏览器检查覆盖对象策略在主工作台中的展示。

## P3 - Memory Confirmation Simplification

提交：`cad0cd0 feat: simplify memory confirmation`

完成内容：

1. 待确认记忆按“建议保存”“不确定”“不建议保存”分组。
2. 支持按分组批量确认、忽略和拒绝。
3. 每条记忆建议展示来源、影响范围和建议动作。
4. 继续保持长期记忆进入 approved 前必须用户确认的边界。

验收结果：

1. 前端构建通过。
2. 浏览器检查覆盖记忆分组与批量操作入口。

## P4 - Public Positioning And Release Readiness

提交：`349146b docs: clarify public preview positioning`

完成内容：

1. README 从功能堆叠改为“本地、可控、不自动发送”的 Windows preview 表达。
2. README 增加适合人群、一分钟试用、明确边界、当前限制、自动构建和数据目录说明。
3. 新增 v0.1.0 release notes，并把 GitHub v0.1.0 release body 更新为同一套边界表达。

验收结果：

1. README 与当前 UI 流程保持一致。
2. `git diff --check` 通过。

## v0.1.1 Release Checklist

1. 新增本完成记录，方便后续追踪 P0-P4 的业务价值和验收情况。
2. 新增 `docs/release_notes_v0.1.1.md`，作为 GitHub Release 正文来源。
3. README 试用入口切换到 v0.1.1。
4. 从最新 `main` 创建并推送 `v0.1.1` tag。
5. GitHub Actions Windows desktop build 应在 tag 推送后生成 `ai-chat-wingman-windows-v0.1.1.zip`。

## Residual Risks

1. Mock 演示仍然只能证明流程，不代表真实模型质量。
2. QQ JSON 导入已经接入，但不同导出工具的字段兼容仍需要继续补适配器。
3. 截图解析依赖用户配置的多模态模型，解析质量不由本地代码完全决定。
4. 当前长期记忆仍是 SQLite 本地存储，尚未接入完整向量召回。
5. v0.1.1 的 Windows zip 需要等待 tag 触发的 GitHub Actions 完成后才会出现在 release asset 中。
