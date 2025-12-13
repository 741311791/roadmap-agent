# Checkpoint 恢复数据持久化修复

## 问题描述

用户发现从 checkpoint 恢复的路线图任务执行过程中，虽然有日志记录和任务状态更新，但生成的内容数据没有保存到数据库中。

### 症状

对于从 checkpoint 恢复的任务（例如 `roadmap_id: python-design-patterns-a4b5c6d7`）：

- ✅ `execution_logs` 表有内容生成过程的记录
- ✅ `roadmap_tasks` 表有任务执行状态记录
- ❌ `roadmap_metadata` 表没有更新重新生成的任务状态
- ❌ `resource_recommendation_metadata` 表没有重新生成的内容记录
- ❌ `quiz_metadata` 表没有重新生成的内容记录

## 根本原因

### 正常流程（无恢复）

```
RoadmapService.generate_roadmap()
    ↓
WorkflowExecutor.execute(user_request, task_id)
    ↓
LangGraph 工作流执行
    ↓
返回 final_state
    ↓
RoadmapService 从 final_state 提取数据
    ↓
【关键步骤】保存到数据库：
  - roadmap_metadata
  - tutorial_metadata (batch)
  - resource_recommendation_metadata (batch)
  - quiz_metadata (batch)
```

### 恢复流程（问题所在）

```
TaskRecoveryService._execute_recovery()
    ↓
WorkflowExecutor.graph.ainvoke(None, config)  # 从 checkpoint 恢复
    ↓
LangGraph 工作流恢复执行
    ↓
返回 final_state
    ↓
【缺失步骤】没有保存数据到数据库！❌
    ↓
任务状态更新（在 content_runner 内完成）
```

**问题关键**：从 checkpoint 恢复时，工作流执行完成后，**缺少了将生成的内容保存到数据库的步骤**。

## 为什么会这样？

1. **数据保存责任分离**：
   - Agent 的 `execute()` 方法只负责生成数据，返回输出对象
   - ContentRunner 只负责调用 Agent 和更新 framework 中的 Concept 状态
   - **数据库保存逻辑**在 `RoadmapService.generate_roadmap()` 中

2. **恢复流程绕过了 RoadmapService**：
   - 恢复时直接调用 `WorkflowExecutor.graph.ainvoke()`
   - 工作流执行完成后没有调用保存逻辑

## 修复方案

在 `TaskRecoveryService._execute_recovery()` 方法中，工作流执行完成后，添加数据保存步骤：

```python
async def _execute_recovery(self, executor, task_id, config):
    try:
        # 1. 从 checkpoint 恢复执行
        final_state = await executor.graph.ainvoke(None, config)
        
        # 2. 【新增】保存工作流生成的数据到数据库
        await self._save_workflow_results(task_id, final_state)
        
        # 3. 清理缓存
        executor.state_manager.clear_live_step(task_id)
    except Exception as e:
        await self._mark_task_failed(task_id, str(e))
```

### 新增方法：`_save_workflow_results()`

该方法负责保存工作流生成的所有数据：

1. **更新路线图元数据**（`roadmap_metadata`）
   - 使用 `roadmap_repo.save_roadmap()` 方法（内部自动判断更新还是插入）

2. **保存教程元数据**（`tutorial_metadata`）
   - 如果 `final_state` 中有 `tutorial_refs`，调用 `tutorial_repo.save_tutorials_batch()`

3. **保存资源推荐元数据**（`resource_recommendation_metadata`）
   - 如果 `final_state` 中有 `resource_refs`，调用 `resource_repo.save_resources_batch()`

4. **保存测验元数据**（`quiz_metadata`）
   - 如果 `final_state` 中有 `quiz_refs`，调用 `quiz_repo.save_quizzes_batch()`

## 修复的文件

1. **`backend/app/services/task_recovery_service.py`**
   - `_execute_recovery()`: 添加数据保存调用
   - `_save_workflow_results()`: 新增方法，负责保存所有数据

## 验证方法

### 测试步骤

1. 创建一个路线图生成任务
2. 在任务执行到 `content_generation` 步骤时，强制停止后端服务（Ctrl+C）
3. 重启后端服务
4. 观察日志，确认任务自动恢复
5. 检查数据库：

```sql
-- 检查路线图元数据是否更新
SELECT roadmap_id, title, created_at 
FROM roadmap_metadata 
WHERE roadmap_id = 'python-design-patterns-a4b5c6d7';

-- 检查教程元数据
SELECT tutorial_id, concept_id, title 
FROM tutorial_metadata 
WHERE roadmap_id = 'python-design-patterns-a4b5c6d7';

-- 检查资源推荐元数据
SELECT id, concept_id, resources_count 
FROM resource_recommendation_metadata 
WHERE roadmap_id = 'python-design-patterns-a4b5c6d7';

-- 检查测验元数据
SELECT quiz_id, concept_id, total_questions 
FROM quiz_metadata 
WHERE roadmap_id = 'python-design-patterns-a4b5c6d7';
```

### 预期结果

所有表都应该有数据记录，与正常流程生成的结果一致。

## 日志示例

修复后，从 checkpoint 恢复时会看到以下日志：

```
[info] task_recovery_execution_completed task_id=xxx roadmap_id=xxx
[info] task_recovery_roadmap_metadata_saved task_id=xxx roadmap_id=xxx
[info] task_recovery_saving_tutorials task_id=xxx count=10
[info] task_recovery_tutorials_saved task_id=xxx count=10
[info] task_recovery_saving_resources task_id=xxx count=10
[info] task_recovery_resources_saved task_id=xxx count=10
[info] task_recovery_saving_quizzes task_id=xxx count=10
[info] task_recovery_quizzes_saved task_id=xxx count=10
[info] task_recovery_data_saved_successfully task_id=xxx roadmap_id=xxx
```

## 影响范围

- **向后兼容**：✅ 完全兼容，不影响正常流程
- **性能影响**：最小（只在恢复时执行，且是异步后台任务）
- **数据一致性**：✅ 修复后保证数据完整性

## 相关文件

- `backend/app/services/task_recovery_service.py` - 任务恢复服务
- `backend/app/services/roadmap_service.py` - 路线图服务（参考数据保存逻辑）
- `backend/app/core/orchestrator/node_runners/content_runner.py` - 内容生成节点
- `backend/app/db/repositories/roadmap_meta_repo.py` - 路线图元数据仓库
- `backend/app/db/repositories/tutorial_repo.py` - 教程元数据仓库
- `backend/app/db/repositories/resource_repo.py` - 资源推荐元数据仓库
- `backend/app/db/repositories/quiz_repo.py` - 测验元数据仓库

## 总结

这个问题的根源是**恢复流程缺少了数据持久化步骤**。修复后，从 checkpoint 恢复的任务会像正常流程一样，将所有生成的内容保存到数据库中，确保数据完整性和一致性。
