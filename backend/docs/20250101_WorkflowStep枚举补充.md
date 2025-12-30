# WorkflowStep 枚举补充修复

## 问题描述

**问题现象：**
后端代码中使用了 `content_generation_queued` 步骤，但该步骤未在 `WorkflowStep` 枚举中定义，导致：
1. 代码中使用字符串字面量而非枚举值
2. 类型检查无法发现错误
3. 与前端步骤映射不一致

## 根本原因

`content_generation_queued` 是实际使用的工作流步骤，但在 `backend/app/models/constants.py` 的 `WorkflowStep` 枚举中缺失。

### 使用场景

```python
# backend/app/core/orchestrator/node_runners/content_runner.py
return {
    "content_generation_status": "queued",
    "celery_task_id": celery_task.id,
    "current_step": "content_generation_queued",  # ❌ 使用字符串字面量
    "execution_history": [
        f"内容生成任务已发送到 Celery 队列（Task ID: {celery_task.id}）"
    ],
}
```

## 解决方案

在 `WorkflowStep` 枚举中添加缺失的步骤：

```python
class WorkflowStep(str, Enum):
    # ... 其他步骤 ...
    HUMAN_REVIEW = "human_review"
    CONTENT_GENERATION_QUEUED = "content_generation_queued"  # ✅ 新增
    CONTENT_GENERATION = "content_generation"
    # ... 其他步骤 ...
```

## 修改文件

- `backend/app/models/constants.py`
  - Line 47: 添加 `CONTENT_GENERATION_QUEUED = "content_generation_queued"`

## 注意事项

### 步骤 vs 状态的区分

**工作流步骤 (WorkflowStep)**：
- `current_step` 字段使用
- 表示工作流当前执行到哪个节点
- 例如：`intent_analysis`, `curriculum_design`, `content_generation_queued`

**任务状态 (TaskStatus)**：
- `status` 字段使用
- 表示任务的整体状态
- 例如：`pending`, `processing`, `human_review_pending`, `completed`

**关键区别**：
- `human_review_pending` 是**任务状态**，不是工作流步骤
- 工作流步骤是 `human_review`
- 当任务在人工审核阶段时：
  - `current_step = "human_review"` （工作流步骤）
  - `status = "human_review_pending"` （任务状态）

### 前端步骤映射

前端 `workflow-topology.tsx` 中已经包含了 `content_generation_queued`：

```typescript
{
  id: 'content',
  label: 'Content Generation',
  shortLabel: 'Content',
  description: 'Generating materials',
  steps: ['content_generation_queued', 'content_generation', 'tutorial_generation', 'resource_recommendation', 'quiz_generation'],
}
```

现在前后端完全一致 ✅

## 后续优化建议

### 1. 使用枚举值而非字符串

修改 `content_runner.py` 使用枚举：

```python
from app.models.constants import WorkflowStep

return {
    "content_generation_status": "queued",
    "celery_task_id": celery_task.id,
    "current_step": WorkflowStep.CONTENT_GENERATION_QUEUED.value,  # ✅ 使用枚举
    "execution_history": [
        f"内容生成任务已发送到 Celery 队列（Task ID: {celery_task.id}）"
    ],
}
```

### 2. 类型检查

使用枚举后，可以通过类型检查发现错误：

```python
def update_step(step: WorkflowStep):
    pass

update_step("invalid_step")  # ❌ 类型检查报错
update_step(WorkflowStep.CONTENT_GENERATION_QUEUED)  # ✅ 正确
```

### 3. 前后端类型同步

考虑使用代码生成工具（如 `datamodel-code-generator`）从后端 Pydantic 模型生成前端 TypeScript 类型，确保枚举值始终一致。

## 影响范围

### 受影响的功能
- ✅ 内容生成队列状态显示
- ✅ 工作流拓扑图节点映射
- ✅ WebSocket 进度推送

### 不受影响
- 任务状态枚举（`TaskStatus`）保持不变
- 其他工作流步骤不受影响

