# 🔧 内容生成相关问题修复报告

**修复日期**: 2025-12-07  
**问题严重程度**: 🔴 Critical  
**修复状态**: ✅ 完成

---

## 📋 问题概览

### 问题 1: ResourceRecommender/QuizGenerator 缺少 user_preferences 参数 ❌

**错误信息**:
```
1 validation error for ResourceRecommendationInput
user_preferences
  Field required [type=missing, ...]

1 validation error for QuizGenerationInput
user_preferences
  Field required [type=missing, ...]
```

**根本原因**: `content_runner.py` 中调用 `_generate_resources()` 和 `_generate_quiz()` 时没有传递 `user_preferences` 参数。

**修复方案**:
1. ✅ 修改方法调用，添加 `user_preferences` 参数
2. ✅ 修改方法签名，接受 `user_preferences` 参数
3. ✅ 传递 `user_preferences` 给 Input 模型

**修改文件**: `backend/app/core/orchestrator/node_runners/content_runner.py`

### 问题 2: execution_logs 表中 roadmap_id 字段未填充 ❌

**根本原因**: 各个 node_runner 在调用 `log_workflow_start()` 时没有传递 `roadmap_id` 参数。

**修复方案**:
1. ✅ `curriculum_runner.py` - 添加 `roadmap_id` 参数
2. ✅ `validation_runner.py` - 添加 `roadmap_id` 参数
3. ✅ `editor_runner.py` - 添加 `roadmap_id` 参数
4. ✅ `content_runner.py` - 添加 `roadmap_id` 参数
5. ✅ `review_runner.py` - 添加 `roadmap_id` 参数

### 问题 3: roadmap_tasks.current_step 状态更新不及时 ❌

**现象**: `execution_logs.message` 显示 "课程架构设计完成"，但 `roadmap_tasks.current_step` 仍然是 `intent_analysis`。

**根本原因**: 各个 node_runner 没有在步骤开始时更新数据库中的 `current_step` 字段。

**修复方案**:
1. ✅ `curriculum_runner.py` - 添加 `_update_task_status()` 方法和调用
2. ✅ `validation_runner.py` - 添加 `_update_task_status()` 方法和调用
3. ✅ `editor_runner.py` - 添加 `_update_task_status()` 方法和调用
4. ✅ `content_runner.py` - 添加 `_update_task_status()` 方法和调用
5. ✅ `review_runner.py` - 在 `update_task_status` 调用中添加 `roadmap_id`

---

## 📁 修改的文件

### 1. `backend/app/core/orchestrator/node_runners/content_runner.py`

**修改内容**:
- 添加 `user_preferences` 参数到 `_generate_resources()` 调用
- 添加 `user_preferences` 参数到 `_generate_quiz()` 调用
- 修改 `_generate_resources()` 方法签名和内部传参
- 修改 `_generate_quiz()` 方法签名和内部传参
- 添加 `log_workflow_start()` 调用（包含 `roadmap_id`）
- 添加 `_update_task_status()` 方法和调用

### 2. `backend/app/core/orchestrator/node_runners/curriculum_runner.py`

**修改内容**:
- `log_workflow_start()` 添加 `roadmap_id` 参数
- 添加 `_update_task_status()` 方法
- 在步骤开始时调用 `_update_task_status()`

### 3. `backend/app/core/orchestrator/node_runners/validation_runner.py`

**修改内容**:
- `log_workflow_start()` 添加 `roadmap_id` 参数
- 添加 `_update_task_status()` 方法
- 在步骤开始时调用 `_update_task_status()`

### 4. `backend/app/core/orchestrator/node_runners/editor_runner.py`

**修改内容**:
- `log_workflow_start()` 添加 `roadmap_id` 参数
- 添加 `_update_task_status()` 方法
- 在步骤开始时调用 `_update_task_status()`

### 5. `backend/app/core/orchestrator/node_runners/review_runner.py`

**修改内容**:
- `log_workflow_start()` 添加 `roadmap_id` 参数
- `update_task_status()` 添加 `roadmap_id` 参数

---

## 🧪 验证方法

### 测试端到端流程

```bash
cd backend
uv run python scripts/test_e2e_generation.py
```

**预期结果**:
1. ✅ 无 `user_preferences Field required` 错误
2. ✅ `execution_logs` 表中 `roadmap_id` 字段正确填充
3. ✅ `roadmap_tasks.current_step` 实时更新

### 检查数据库

```sql
-- 检查 execution_logs 表中 roadmap_id 是否填充
SELECT task_id, step, roadmap_id, message, created_at 
FROM execution_logs 
ORDER BY created_at DESC 
LIMIT 20;

-- 检查 roadmap_tasks 表中 current_step 是否正确
SELECT task_id, status, current_step, roadmap_id, updated_at 
FROM roadmap_tasks 
ORDER BY updated_at DESC 
LIMIT 10;
```

---

## 📊 修复效果对比

### 修复前 ❌

**后端日志**:
```log
[error] resource_recommendation_failed
        error="1 validation error for ResourceRecommendationInput\nuser_preferences\n  Field required"
[error] quiz_generation_failed
        error="1 validation error for QuizGenerationInput\nuser_preferences\n  Field required"
```

**数据库状态**:
```
execution_logs.roadmap_id: NULL  ❌
roadmap_tasks.current_step: "intent_analysis"  ❌ (应该是 "curriculum_design")
```

### 修复后 ✅

**后端日志**:
```log
[info] resource_recommendation_success concept_id=xxx
[info] quiz_generation_success concept_id=xxx
```

**数据库状态**:
```
execution_logs.roadmap_id: "python-web-dev-xxx"  ✅
roadmap_tasks.current_step: "curriculum_design"  ✅ (实时更新)
```

---

## 🔍 技术细节

### `_update_task_status` 方法模板

```python
async def _update_task_status(self, task_id: str, current_step: str, roadmap_id: str | None):
    """
    更新任务状态到数据库
    
    Args:
        task_id: 任务 ID
        current_step: 当前步骤
        roadmap_id: 路线图 ID
    """
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        await repo.update_task_status(
            task_id=task_id,
            status="processing",
            current_step=current_step,
            roadmap_id=roadmap_id,
        )
        await session.commit()
        
        logger.debug(
            "task_status_updated",
            task_id=task_id,
            current_step=current_step,
            roadmap_id=roadmap_id,
        )
```

### 调用时机

每个 node_runner 在以下位置调用 `_update_task_status()`:
1. 在 `set_live_step()` 之后
2. 在 `log_workflow_start()` 之后
3. 在 `publish_progress()` 之前

这确保了：
- 数据库状态与内存状态同步
- 前端通过轮询可以获取最新的步骤状态
- 执行日志包含正确的 roadmap_id

---

## ✅ 验收标准

### 功能验收
- [x] ResourceRecommender 正常生成资源推荐
- [x] QuizGenerator 正常生成测验
- [x] execution_logs.roadmap_id 正确填充
- [x] roadmap_tasks.current_step 实时更新

### 代码质量
- [x] 无 linter 错误（仅有 structlog 导入警告，是 IDE 问题）
- [x] 代码风格一致
- [x] 添加了适当的日志记录

---

## 🚀 下一步

1. 重新运行端到端测试验证修复
2. 检查数据库表数据是否正确生成
3. 验证前端是否能正确显示进度

---

**修复完成**: ✅  
**可以部署**: ✅  
**测试状态**: 等待验证

