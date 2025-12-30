# Intent Analysis 显示问题修复

## 问题描述

用户反馈：在任务详情页，当任务进行到 `curriculum_design` 阶段时，Learning Path Overview 中的 Intent Analysis 卡片没有展示出来。

## 根本原因分析

经过深入分析，发现了以下潜在问题：

### 1. 后端事务管理问题

**问题位置**：`backend/app/core/orchestrator/workflow_brain.py`

在 `save_intent_analysis()` 和 `save_roadmap_framework()` 方法中存在事务管理混乱：

```python
# 原代码（有问题）
async with AsyncSessionLocal() as session:
    repo = RoadmapRepository(session)
    
    # save_intent_analysis_metadata 内部已经 commit
    await repo.save_intent_analysis_metadata(task_id, intent_analysis)
    
    # update_task_status 内部也已经 commit
    await repo.update_task_status(...)
    
    # 这里再次 commit，可能导致问题
    await session.commit()
```

**问题说明**：
- `save_intent_analysis_metadata()` 内部执行了 `commit`（第987行）
- `update_task_status()` 内部也执行了 `commit`（第345行）
- 外层又执行了一次 `commit`
- 这导致三次commit操作，且两个业务操作不在同一个事务中，违反了注释中声明的"在同一事务中执行"

**修复方案**：
改用两个独立的 session 和事务，明确每个操作的事务边界：

```python
# 第一步：保存 Intent Analysis 元数据（内部会 commit）
async with AsyncSessionLocal() as session:
    repo = RoadmapRepository(session)
    await repo.save_intent_analysis_metadata(task_id, intent_analysis)
    # 此方法内部已经 commit，metadata 已经持久化

# 第二步：更新任务状态（内部会 commit）
async with AsyncSessionLocal() as session:
    repo = RoadmapRepository(session)
    await repo.update_task_status(
        task_id=task_id,
        status="processing",
        current_step="intent_analysis",
        roadmap_id=unique_roadmap_id,
    )
    # 此方法内部已经 commit，task 状态已经更新
```

### 2. 前端错误日志不足

**问题位置**：`frontend-next/app/(app)/tasks/[taskId]/page.tsx`

前端在 `loadIntentAnalysis()` 函数中，如果 API 调用失败（例如返回 404），错误被 catch 但只有简单的 console.error，没有详细的错误信息。

**修复方案**：
增强错误日志，显示详细信息：

```typescript
console.error('[TaskDetail] Failed to load intent analysis:', {
  task_id: taskId,
  error: err,
  status: err.response?.status,
  message: err.response?.data?.detail || err.message,
});
```

同时添加成功日志：

```typescript
console.log('[TaskDetail] Intent analysis loaded successfully:', {
  task_id: taskId,
  has_data: !!intentData,
  parsed_goal_length: intentData?.parsed_goal?.length,
  key_technologies_count: intentData?.key_technologies?.length,
});
```

## 修复内容

### 文件修改

1. **backend/app/core/orchestrator/workflow_brain.py**
   - 修复 `save_intent_analysis()` 方法的事务管理
   - 修复 `save_roadmap_framework()` 方法的事务管理
   - 更新日志，添加 commit 状态标记

2. **frontend-next/app/(app)/tasks/[taskId]/page.tsx**
   - 增强 `loadIntentAnalysis()` 的错误日志
   - 添加成功加载的日志

3. **backend/scripts/test_intent_analysis.py**（新增）
   - 创建测试脚本，用于验证 Intent Analysis 数据是否正确保存到数据库
   - 支持列出最近的任务
   - 支持查询特定任务的 Intent Analysis 数据

## 排查步骤

如果用户仍然遇到 Intent Analysis 不显示的问题，请按以下步骤排查：

### 1. 检查浏览器控制台

打开浏览器的开发者工具（F12），查看 Console 标签页：

**成功的情况**：
```
[TaskDetail] Intent analysis loaded successfully: {
  task_id: "xxx",
  has_data: true,
  parsed_goal_length: 150,
  key_technologies_count: 5
}
```

**失败的情况**：
```
[TaskDetail] Failed to load intent analysis: {
  task_id: "xxx",
  status: 404,
  message: "Intent analysis metadata not found"
}
```

### 2. 使用测试脚本检查后端数据

```bash
cd backend

# 列出最近的任务
python scripts/test_intent_analysis.py

# 测试特定任务
python scripts/test_intent_analysis.py <task_id>
```

**预期输出**：
- ✅ 如果数据存在，会显示 Intent Analysis 的详细信息
- ❌ 如果数据不存在，会显示错误信息和可能的原因

### 3. 检查任务当前步骤

确认任务的 `current_step` 是否在以下列表中：
- `curriculum_design`
- `framework_generation`
- `structure_validation`
- `edit_plan_analysis`
- `edit_plan`
- `validation_edit_plan`
- `roadmap_edit`
- `human_review`
- `human_review_pending`
- `content_generation`
- `tutorial_generation`
- `resource_recommendation`
- `quiz_generation`
- `finalizing`
- `completed`

如果 `current_step` 还是 `intent_analysis`，说明任务还未进入后续阶段，此时不应该显示 Intent Analysis 卡片（按设计）。

### 4. 检查 API 响应

在浏览器开发者工具的 Network 标签页中，查找 `/intent-analysis/<task_id>` 的请求：

**成功的情况**（200）：
```json
{
  "id": "...",
  "task_id": "...",
  "roadmap_id": "...",
  "parsed_goal": "...",
  "key_technologies": [...],
  "difficulty_profile": "intermediate",
  "time_constraint": "...",
  ...
}
```

**失败的情况**（404）：
```json
{
  "detail": "Intent analysis metadata not found"
}
```

## 可能的其他原因

如果以上检查都正常，但 Intent Analysis 仍然不显示，可能的原因：

1. **前端代码未更新**：清除浏览器缓存，强制刷新（Ctrl+Shift+R 或 Cmd+Shift+R）

2. **后端数据迁移问题**：检查数据库中 `intent_analysis_metadata` 表是否存在且结构正确

3. **数据库连接问题**：检查后端是否连接到正确的数据库实例

4. **时区问题**：检查 `time_constraint` 字段格式，确保 `parseTimeConstraint()` 能正确解析

## 测试验证

### 后端测试

```bash
cd backend
python scripts/test_intent_analysis.py <task_id>
```

### 前端测试

1. 打开任务详情页
2. 打开浏览器控制台（F12）
3. 查看日志输出：
   - 应该看到 `[TaskDetail] Intent analysis loaded successfully` 或错误信息
4. 检查 Network 标签页的 API 请求状态

### 端到端测试

1. 创建一个新的路线图生成任务
2. 等待任务进入 `curriculum_design` 阶段
3. 检查任务详情页是否显示 Intent Analysis 卡片
4. 如果不显示，按照上述排查步骤检查

## 预防措施

为避免类似问题再次发生，建议：

1. **统一事务管理模式**：
   - Repository 方法应该是纯数据操作，不自动 commit
   - 在 Service 层或 Workflow 层统一管理事务

2. **增强错误处理**：
   - 所有 API 调用都应该有详细的错误日志
   - 前端应该显示用户友好的错误提示

3. **添加监控和告警**：
   - 监控 Intent Analysis API 的 404 错误率
   - 如果错误率异常，发送告警

4. **自动化测试**：
   - 添加端到端测试，覆盖完整的路线图生成流程
   - 确保 Intent Analysis 数据的保存和展示正常工作

## 相关文件

- `backend/app/core/orchestrator/workflow_brain.py` - WorkflowBrain 类
- `backend/app/core/orchestrator/node_runners/intent_runner.py` - Intent Analysis 执行器
- `backend/app/db/repositories/roadmap_repo.py` - Repository 方法
- `backend/app/api/v1/endpoints/intent.py` - Intent Analysis API 端点
- `frontend-next/app/(app)/tasks/[taskId]/page.tsx` - 任务详情页
- `frontend-next/components/task/core-display-area.tsx` - 核心展示区域组件
- `backend/scripts/test_intent_analysis.py` - 测试脚本（新增）

## 总结

本次修复主要解决了：

1. ✅ 后端事务管理混乱的问题，确保数据正确持久化
2. ✅ 前端错误日志不足的问题，便于排查
3. ✅ 提供了测试工具，方便验证数据是否正确保存

**下一步行动**：

1. 重启后端服务，使修改生效
2. 清除浏览器缓存，刷新前端页面
3. 创建测试任务，验证修复是否成功
4. 如果问题仍然存在，使用测试脚本和浏览器控制台进行详细排查

