# Code Review Follow-up: Jobs 合规与数据清空 Plan

本文档承接最近一轮全量代码审查。审查中已修复的正确性 / 安全问题（记忆提取静默吞异常、删除对象级联清理、JSON 解析失败无日志、SSE reader 泄漏、启动 `Promise.all` 无降级、QQ 导入轮询不可取消、前端错误类型守卫）已直接落地并通过后端 `pytest` 与前端 `npm run build`。

本 plan 只覆盖审查里**剩余、且需要改契约或新增功能**的三项，逐阶段闭环，每阶段单独可验收，不一次性铺开。

依据：`AGENTS.md`（>2 秒耗时操作必须走 `jobs` 表；一键清空数据必须二次确认）、`docs/ai_chat_wingman_spec_plan.md`。

## Current Read

当前 jobs 表已有可复用范式：

- 后端 `app/jobs/runner.py` 提供 `create_job` / `get_job` / `update_job` 与各 `run_*_job`。
- `app/api/privacy.py`、`app/api/jobs.py` 使用 `BackgroundTasks.add_task(run_*_job, job.id, ...)` 提交，立即返回 `{job_id, status}`。
- 前端 `api.ts` 有 `getJob`，`QQImportPanel` 有「提交任务 + 轮询 `getJob` + 解析 `job.result`」的完整模式可参照。

当前不合规 / 缺口：

1. `POST /multimodal/parse-chat-screenshot` 是 async 端点，直接 `await parse_chat_screenshot`（含多模态 LLM 调用），在 HTTP 请求内同步阻塞返回，违反「>2 秒走 jobs 表」。
2. `POST /targets/{id}/organize` 同样直接 `await organize_target`（含 LLM 调用）阻塞返回，违反同一约束。
3. `app/api/privacy.py` 只有 `data-summary` 与 `export`，缺少 spec 要求的「一键清空全部本地数据 + 二次确认」闭环。

## P0 - Screenshot Parse 走 Jobs 表

目标：把截图解析改成异步任务，HTTP 立即返回 `job_id`，前端轮询取结果。

范围：

1. `app/jobs/runner.py` 新增 `run_screenshot_parse_job(job_id, payload)`（async def，BackgroundTasks 可 await）：
   - 内部 `with SessionLocal() as db`，`update_job` 推进 `running` → 进度 → `success/failed`。
   - 复用现有 `app/services/multimodal_service.parse_chat_screenshot`，把 `ScreenshotParseResult.to_dict()` + `llm_call_id` + `prompt_version` 序列化进 `job.result`。
   - 失败时 `status="failed"`，`error_message=str(exc)`，与 `run_privacy_export_job` 一致。
2. `app/api/multimodal.py` 的 `parse_chat_screenshot_endpoint` 改为：`create_job(job_type="screenshot_parse")` + `background_tasks.add_task(...)`，返回 `{job_id, status}`；保留请求体校验（mime/base64 大小）在入口同步完成，提交前先快速失败。
3. 前端 `api.ts`：`parseChatScreenshot` 改为提交任务并复用统一的轮询（抽出 `pollJobResult<T>(jobId)` 辅助，QQ 导入与截图共用）。
4. 前端 `ImageInputPanel.tsx`：解析按钮触发后显示任务进度，组件卸载时停止轮询（参照 QQImportPanel 的 `cancelledRef`）。

验收：

1. 上传截图后 `POST /multimodal/parse-chat-screenshot` 立即返回 `job_id`，不再长时间阻塞。
2. 轮询 `GET /jobs/{id}` 最终拿到 `messages/summary/uncertain_parts/stored_image_path/llm_call_id/prompt_version`。
3. 解析失败时前端显示可读错误，任务 `status=failed`。
4. 后端 `pytest`、前端 `tsc --noEmit && vite build` 通过。

## P1 - Organize Target 走 Jobs 表

目标：对象档案 AI 整理改成异步任务。

范围：

1. `app/jobs/runner.py` 新增 `run_organize_target_job(job_id, payload)`（async def），复用 `target_service.organize_target`，把 `target.to_dict()` + `llm_call_id` 写进 `job.result`。
2. `app/api/targets.py` 的 `organize_chat_target` 改为提交任务返回 `{job_id, status}`；目标不存在等校验仍在入口同步完成。
3. 前端 `api.ts`：`organizeTarget` 改为提交 + `pollJobResult`。
4. 前端 `TargetManager.tsx`：`handleOrganize` 显示任务进度，卸载时停止轮询。

验收：

1. 触发整理后立即返回 `job_id`，不阻塞 HTTP。
2. 轮询拿到整理后的 target 与 `llm_call_id`，UI 正确替换档案。
3. 后端 `pytest`、前端构建通过。

## P2 - 一键清空数据 + 二次确认

目标：补齐隐私闭环，允许用户清空全部本地数据，且必须二次确认。

范围：

1. `app/services/privacy_service.py` 新增 `purge_all_data(db, confirm_token)`：清空业务表（targets、conversations、saved_replies、memories、chat_sessions、style_test_*、user_profiles/versions、llm_calls、jobs 等），并清理本地数据目录（screenshots / imports / exports，均经 `app/paths.py`）。保留 `app_settings`（Provider 配置）由参数决定是否一并清除，默认保留。
2. `app/api/privacy.py` 新增 `POST /privacy/purge`，请求体要求显式 `confirm: true` 且 `confirm_text` 匹配固定串（如 `DELETE`），否则 400；二次确认在后端再校验一次。
3. 前端数据面板（`DataPanel.tsx`）新增「清空全部数据」按钮 + 二次确认对话（输入确认词后才可执行），成功后刷新 `data-summary` 并提示。

验收：

1. 未带正确二次确认参数调用 `POST /privacy/purge` 返回 400，不删除任何数据。
2. 带正确确认后，业务数据与本地用户数据目录被清空，`data-summary` 归零。
3. 默认不清除 Provider 配置（除非显式要求）。
4. 后端 `pytest`（含针对 purge 的最小用例）、前端构建通过。

## Out of Scope

- token 数 `len//2` 粗估优化（已记为已知近似）。
- API Key 本地明文存储加密（设计取舍，spec 只要求不硬编码 / 不提交，优先级低）。
- 风格测试分析端点是否同样改走 jobs（待确认其平均耗时后再决定，本轮先不动）。

## Execution Order

P0 → P1 → P2，每阶段完成即验证并提交。每次推送提交信息遵循 `AGENTS.md` 的英文类型前缀 + 编号正文格式。
