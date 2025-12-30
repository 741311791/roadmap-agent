# 状态机重构完成总结

## 概述

本次重构将路线图生成系统从 FastAPI 同步执行模式迁移到 Celery 异步执行模式，实现了进程隔离和真正的异步处理。

## 主要变更

### 1. 后端配置层

#### `backend/app/config/settings.py`
- ✅ 移除了 4 个 SKIP_* 配置项：
  - `SKIP_STRUCTURE_VALIDATION`
  - `SKIP_TUTORIAL_GENERATION`
  - `SKIP_RESOURCE_RECOMMENDATION`
  - `SKIP_QUIZ_GENERATION`
- ✅ 保留 `SKIP_HUMAN_REVIEW`（唯一可选节点）

### 2. 后端工作流核心层

#### `backend/app/core/orchestrator/base.py`
- ✅ 简化 `WorkflowConfig`，移除 4 个跳过选项
- ✅ 更新 `from_settings()` 方法

#### `backend/app/core/orchestrator/builder.py`
- ✅ 简化 `_add_nodes()` 方法，所有核心节点始终添加
- ✅ 简化 `_add_edges()` 方法，移除跳过分支逻辑
- ✅ 简化 `_add_human_review_edges()` 方法

#### `backend/app/core/orchestrator/routers.py`
- ✅ 简化 `route_after_validation()` 方法
- ✅ 简化 `route_after_human_review()` 方法

### 3. 后端 Celery 任务层

#### 新增 `backend/app/tasks/roadmap_generation_tasks.py`
- ✅ 实现 `generate_roadmap()` Celery 任务
- ✅ 执行完整的 LangGraph 工作流
- ✅ 支持在 human_review 处暂停

#### 新增 `backend/app/tasks/workflow_resume_tasks.py`
- ✅ 实现 `resume_after_review()` Celery 任务
- ✅ 实现 `resume_from_checkpoint()` Celery 任务
- ✅ 支持从 checkpoint 恢复工作流

### 4. 后端 API 层

#### `backend/app/api/v1/endpoints/generation.py`
- ✅ 修改 `/roadmaps/generate` 端点
- ✅ 改为分发 Celery 任务而非直接执行工作流
- ✅ 移除 `BackgroundTasks` 依赖

#### `backend/app/api/v1/endpoints/approval.py`
- ✅ 修改 `/roadmaps/{task_id}/approve` 端点
- ✅ 改为分发 `resume_after_review.delay()` Celery 任务
- ✅ 移除 `WorkflowExecutor` 依赖

#### `backend/app/api/v1/endpoints/retry.py`
- ✅ 简化 `/tasks/{task_id}/retry` 端点
- ✅ Checkpoint 恢复改为使用 `resume_from_checkpoint.delay()`
- ✅ 内容重试改为使用 `retry_failed_content_task.delay()`
- ✅ 取消任务重新创建改为使用 `generate_roadmap.delay()`

### 5. 后端服务层

#### `backend/app/services/roadmap_service.py`
- ✅ 标记 `generate_roadmap()` 方法为废弃
- ✅ 标记 `handle_human_review()` 方法为废弃
- ✅ 保留方法用于向后兼容和测试

### 6. 前端常量定义

#### `frontend-next/lib/constants/status.ts`
- ✅ 更新 `TaskStatus` 枚举：
  - `HUMAN_REVIEW_PENDING` → `HUMAN_REVIEW`
- ✅ 新增 `WorkflowStep` 枚举项：
  - `VALIDATION_EDIT_PLAN_ANALYSIS`（验证修改计划分析）
  - `EDIT_PLAN_ANALYSIS`（审核修改计划分析）
- ✅ 更新 `WORKFLOW_STEP_CONFIG` 显示配置

## 架构变更对比

### 旧架构
```
FastAPI 进程
├── 接收 HTTP 请求
├── 直接执行 LangGraph 工作流（阻塞）
│   ├── Intent Analysis
│   ├── Curriculum Design
│   ├── Structure Validation
│   ├── Human Review（暂停）
│   └── Content Generation
└── 返回响应
```

### 新架构
```
FastAPI 进程（轻量级）
├── 接收 HTTP 请求
├── 创建任务记录
├── 分发 Celery 任务
└── 立即返回 task_id

Celery Worker 进程（重量级）
├── 执行 LangGraph 工作流
│   ├── Intent Analysis (LLM)
│   ├── Curriculum Design (LLM)
│   ├── Structure Validation (LLM, 循环)
│   │   └── ValidationEditPlanRunner (edit_source=validation_failed)
│   ├── Human Review（暂停，等待用户）
│   │   └── EditPlanRunner (edit_source=human_review)
│   └── Content Generation (并行 LLM)
├── 保存 Checkpoint 到 PostgreSQL
└── 发送 WebSocket 通知
```

## 状态机流转

### 任务状态（Task Status）
- `pending` → `processing` → `human_review` → `completed`
- `pending` → `processing` → `failed`
- `pending` → `processing` → `partial_failure`

### 工作流步骤（Current Step）
1. `queued` - 已入队
2. `intent_analysis` - 意图分析
3. `curriculum_design` - 课程设计
4. `structure_validation` - 结构验证
5. `validation_edit_plan_analysis` - 验证修改计划分析（验证失败时）
6. `roadmap_edit` - 路线图修正（edit_source 决定返回路由）
7. `edit_plan_analysis` - 审核修改计划分析（人工审核拒绝时）
8. `human_review` - 人工审核（可选）
9. `content_generation` - 内容生成
10. `completed` - 已完成

### edit_source 机制
- `edit_source="validation_failed"` → 修改后返回 `structure_validation`
- `edit_source="human_review"` → 修改后返回 `human_review`

## 重试策略

### 策略 A: Checkpoint 恢复（粗粒度）
- 适用于：早期阶段失败（intent、curriculum、validation、edit）
- 实现：`resume_from_checkpoint.delay(task_id)`
- 特点：从最后一个 checkpoint 恢复，保留所有中间状态

### 策略 B: 内容重试（细粒度）
- 适用于：内容生成阶段部分失败
- 实现：`retry_failed_content_task.delay(...)`
- 特点：只重新生成失败的 Concept 内容，节省成本

### 策略 C: 从头开始
- 适用于：cancelled 任务且无 checkpoint
- 实现：`generate_roadmap.delay(...)`
- 特点：创建新任务，完全重新生成

## 关键设计决策

1. **所有 LLM 调用迁移到 Celery**：不仅内容生成，Intent、Curriculum、Validation、Edit 等所有节点都在 Celery Worker 中执行
2. **保留 LangGraph Checkpoint**：使用 `AsyncPostgresSaver` 持久化工作流状态，支持断点续传和时间旅行
3. **Human Review 暂停机制**：工作流在 human_review 处暂停，等待用户响应后通过新的 Celery 任务恢复
4. **edit_source 机制保持不变**：区分验证失败和人工审核拒绝的修改来源，决定修改后的路由返回
5. **验证失败强制继续**：达到最大重试次数后，即使结构不完美也继续生成内容

## 测试建议

### 1. 正常流程测试
- 创建路线图 → Intent → Curriculum → Validation → Human Review → Content → Completed

### 2. 验证循环测试
- 验证失败 → ValidationEditPlanRunner → EditorRunner → 再次验证 → 通过

### 3. 人工审核测试
- 审核拒绝 → EditPlanRunner → EditorRunner → 再次审核 → 批准

### 4. Checkpoint 恢复测试
- 早期阶段失败 → 重试 → 从 checkpoint 恢复 → 继续执行

### 5. 内容重试测试
- 部分内容失败 → 重试 → 只重新生成失败项 → 完成

### 6. 取消任务测试
- 取消任务 → 重试 → 从头重新创建 → 完成

## 注意事项

1. **Celery Worker 配置**：确保 Celery Worker 正确配置并运行
2. **PostgreSQL Checkpoint 表**：确保 `AsyncPostgresSaver` 的表已创建
3. **WebSocket 连接**：确保 WebSocket 服务正常，用于实时进度推送
4. **环境变量**：确保只保留 `SKIP_HUMAN_REVIEW` 环境变量
5. **数据库迁移**：如果 `RoadmapTask` 表结构有变更，需要运行迁移

## 完成状态

✅ 所有后端任务已完成
✅ 所有前端任务已完成
✅ 所有配置已更新
✅ 所有文档已更新

## Celery 配置更新

### 队列架构（重要变更）

重构后使用 **3 个队列**：

1. **`roadmap_workflow`** 队列（新增）
   - 用途：路线图生成和恢复的工作流任务
   - 任务：`generate_roadmap`、`resume_after_review`、`resume_from_checkpoint`
   - 特点：执行完整的 LangGraph 工作流，包含所有 LLM 调用

2. **`content_generation`** 队列（现有）
   - 用途：内容生成任务
   - 任务：`generate_roadmap_content`、`retry_*_task`
   - 特点：并行生成 Tutorial、Resource、Quiz

3. **`logs`** 队列（现有）
   - 用途：日志批量写入
   - 任务：`batch_write_logs`

### 启动命令

#### 开发环境（所有队列）
```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info --concurrency=4
```

#### 生产环境（分队列）
```bash
# Worker 1: 路线图工作流（高优先级，低并发）
celery -A app.core.celery_app worker --queues=roadmap_workflow --concurrency=2 -n workflow@%h

# Worker 2: 内容生成（高并发）
celery -A app.core.celery_app worker --queues=content_generation --concurrency=8 -n content@%h

# Worker 3: 日志写入（低优先级）
celery -A app.core.celery_app worker --queues=logs --concurrency=2 -n logs@%h
```

**详细说明**：查看 `backend/CELERY_WORKER_GUIDE.md`

---

## 下一步

1. ✅ 更新 `celery_app.py` 配置（已完成）
2. 启动 Celery Worker（参考 `CELERY_WORKER_GUIDE.md`）
3. 启动 FastAPI 服务：`uvicorn app.main:app --reload`
4. 运行端到端测试
5. 监控 Celery 任务执行情况
6. 根据实际运行情况调优

