# WebSocket 消息推送格式一致性检查报告

**检查日期**: 2025-12-23  
**检查范围**: 后端各节点 WebSocket 消息推送 vs 前端 WorkflowTopology 需求  
**检查人**: AI Assistant

---

## ⚠️ 发现的问题

### 🔴 严重问题：`edit_source` 字段未正确传递到前端

**问题描述**:  
前端 `WorkflowTopology` 组件依赖 `edit_source` 字段来区分当前处于哪个分支（验证分支 vs 审核分支），但后端 `WorkflowBrain` 在发送 WebSocket 进度通知时**未传递**此字段。

**影响范围**:  
- 前端无法正确识别当前分支
- 拓扑图无法高亮显示正确的分支节点
- 用户体验受到严重影响（无法区分自动修复 vs 用户反馈修改）

**具体代码位置**:

#### 1. 前端期望（✅ 正确）

**文件**: `frontend-next/lib/api/websocket.ts`

```typescript
export interface WSProgressEvent extends WSEvent {
  type: 'progress';
  step: string;
  status: string;
  data?: {
    edit_source?: 'validation_failed' | 'human_review';  // ✅ 定义了
  };
}
```

**文件**: `frontend-next/app/(app)/tasks/[taskId]/page.tsx`

```typescript
onProgress: async (event) => {
  // 更新 edit_source（用于区分分支）
  if (event.data?.edit_source) {
    setEditSource(event.data.edit_source);  // ✅ 使用了
  }
}
```

**文件**: `frontend-next/components/task/workflow-topology.tsx`

```typescript
// 通过 edit_source 判断当前分支
const stepLocation = getStepLocation(currentStep, editSource);

// roadmap_edit 是共享步骤，必须通过 edit_source 区分
if (currentStep === 'roadmap_edit') {
  if (editSource === 'validation_failed') {
    return { stageId: node.id, isOnBranch: true, branchType: 'validation' };
  }
  if (editSource === 'human_review') {
    return { stageId: node.id, isOnBranch: true, branchType: 'review' };
  }
}
```

#### 2. 后端状态管理（✅ 正确）

**文件**: `backend/app/core/orchestrator/node_runners/validation_edit_plan_runner.py`

```python
# Line 150-158
return {
    "edit_plan": result.edit_plan,
    "user_feedback": user_feedback,
    "edit_source": "validation_failed",  # ✅ 设置了
    "current_step": "validation_edit_plan_analysis",
    "execution_history": [
        f"验证问题分析完成（识别 {len(result.edit_plan.intents)} 个修改意图）"
    ],
}
```

**文件**: `backend/app/core/orchestrator/node_runners/edit_plan_runner.py`

```python
# Line 199-210
state_update = {
    "edit_plan": result.edit_plan,
    "edit_source": "human_review",  # ✅ 设置了
    "current_step": "edit_plan_analysis",
    "execution_history": [f"修改计划分析完成（识别 {len(result.edit_plan.intents)} 个修改意图）"],
}
```

**文件**: `backend/app/core/orchestrator/base.py`

```python
# Line 84
class RoadmapState(TypedDict, total=False):
    edit_source: str | None  # "validation_failed" 或 "human_review"  # ✅ 定义了
```

#### 3. WebSocket 通知发送（❌ 缺失 `edit_source`）

**文件**: `backend/app/core/orchestrator/workflow_brain.py`

```python
# Line 256-261
await self.notification_service.publish_progress(
    task_id=task_id,
    step=node_name,
    status="processing",
    message=f"正在执行: {node_name}...",
    # ❌ 未传递 extra_data，导致 edit_source 丢失！
)
```

**预期修复**:

```python
await self.notification_service.publish_progress(
    task_id=task_id,
    step=node_name,
    status="processing",
    message=f"正在执行: {node_name}...",
    extra_data={
        "edit_source": state.get("edit_source"),  # ✅ 从 state 中提取
    },
)
```

---

## ✅ 正确的部分

### 1. 步骤名称（Step Name）枚举

#### 前端定义

**文件**: `frontend-next/components/task/workflow-topology.tsx`

```typescript
// 主路节点 steps
['init', 'queued', 'starting', 'intent_analysis']         // Analysis
['curriculum_design', 'framework_generation']              // Design
['structure_validation']                                   // Validate
['human_review', 'human_review_pending']                   // Review
['content_generation', 'tutorial_generation', 
 'resource_recommendation', 'quiz_generation']             // Content

// 验证分支 steps
['validation_edit_plan_analysis']  // Plan1
['roadmap_edit']                   // Edit1

// 审核分支 steps
['edit_plan_analysis']             // Plan2
['roadmap_edit']                   // Edit2 (共享)
```

#### 后端实现

**文件**: `backend/app/core/orchestrator/node_runners/intent_runner.py`

```python
# Line 70
async with self.brain.node_execution("intent_analysis", state):
    # ✅ 步骤名称匹配前端
```

**文件**: `backend/app/core/orchestrator/node_runners/curriculum_runner.py`

```python
# Line 67
async with self.brain.node_execution("curriculum_design", state):
    # ✅ 步骤名称匹配前端
```

**文件**: `backend/app/core/orchestrator/node_runners/validation_runner.py`

```python
# Line 68
async with self.brain.node_execution("structure_validation", state):
    # ✅ 步骤名称匹配前端
```

**文件**: `backend/app/core/orchestrator/node_runners/review_runner.py`

```python
# Line 124
async with self.brain.node_execution("human_review", state):
    # ✅ 步骤名称匹配前端
```

**文件**: `backend/app/core/orchestrator/node_runners/validation_edit_plan_runner.py`

```python
# Line 83
async with self.brain.node_execution("validation_edit_plan_analysis", state):
    # ✅ 步骤名称匹配前端
```

**文件**: `backend/app/core/orchestrator/node_runners/edit_plan_runner.py`

```python
# Line 85
async with self.brain.node_execution("edit_plan_analysis", state):
    # ✅ 步骤名称匹配前端
```

**文件**: `backend/app/core/orchestrator/node_runners/editor_runner.py`

```python
# Line 117
async with self.brain.node_execution("roadmap_edit", state):
    # ✅ 步骤名称匹配前端
```

**结论**: ✅ 所有步骤名称与前端定义完全一致。

---

### 2. 执行日志配置（Step Config）

#### 前端配置

**文件**: `frontend-next/components/task/execution-log-timeline.tsx`

```typescript
const STEP_CONFIG: Record<string, { label: string; color: string; bgColor: string }> = {
  intent_analysis: { label: 'Intent Analysis', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  curriculum_design: { label: 'Curriculum Design', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  structure_validation: { label: 'Structure Validation', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  human_review: { label: 'Human Review', color: 'text-amber-700', bgColor: 'bg-amber-50' },
  
  // 验证分支节点
  validation_edit_plan_analysis: { label: 'Validation Edit Plan', color: 'text-amber-700', bgColor: 'bg-amber-50' },
  
  // 审核分支节点
  edit_plan_analysis: { label: 'Review Edit Plan', color: 'text-blue-700', bgColor: 'bg-blue-50' },
  
  // 共享编辑节点
  roadmap_edit: { label: 'Roadmap Edit', color: 'text-purple-700', bgColor: 'bg-purple-50' },
  
  content_generation: { label: 'Content Generation', color: 'text-sage-700', bgColor: 'bg-sage-50' },
  // ...
};
```

**后端对应**:

所有后端 runner 都通过 `self.brain.node_execution(step_name, state)` 发送进度通知，步骤名称与前端配置的 key 完全匹配。

**结论**: ✅ 前端执行日志配置覆盖了所有后端步骤。

---

### 3. 状态枚举（Status）

#### 前端期望

**文件**: `frontend-next/lib/api/websocket.ts`

```typescript
export interface WSCurrentStatusEvent extends WSEvent {
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'human_review_pending';
}
```

#### 后端实现

**文件**: `backend/app/core/orchestrator/workflow_brain.py`

```python
# Line 227-230
await repo.update_task_status(
    task_id=task_id,
    status="processing",  # ✅ 匹配前端
    current_step=node_name,
    roadmap_id=roadmap_id,
)

# Line 995-1000 (ReviewRunner 特殊状态)
await repo.update_task_status(
    task_id=task_id,
    status="human_review_pending",  # ✅ 匹配前端
    current_step="human_review",
    roadmap_id=roadmap_id,
)

# Line 339-342 (失败状态)
await repo.update_task_status(
    task_id=ctx.task_id,
    status="failed",  # ✅ 匹配前端
    current_step=ctx.node_name,
    error_message=str(error),
)

# Line 877-882 (完成状态)
final_status = "partial_failure" if failed_concepts else "completed"  # ✅ 匹配前端
await repo.update_task_status(
    task_id=task_id,
    status=final_status,
    current_step=final_step,
)
```

**结论**: ✅ 所有状态枚举值与前端定义一致。

---

## 📋 完整的一致性检查清单

### WebSocket 事件字段

| 字段 | 前端类型定义 | 后端实现 | 状态 |
|------|------------|---------|------|
| `type` | `'progress' \| 'completed' \| 'failed' \| ...` | ✅ NotificationService | ✅ 一致 |
| `task_id` | `string` | ✅ 所有事件 | ✅ 一致 |
| `step` | `string` | ✅ WorkflowBrain | ✅ 一致 |
| `status` | `string` | ✅ WorkflowBrain | ✅ 一致 |
| `message` | `string?` | ✅ WorkflowBrain | ✅ 一致 |
| `timestamp` | `string` | ✅ beijing_now().isoformat() | ✅ 一致 |
| `data.edit_source` | `'validation_failed' \| 'human_review'?` | ❌ **缺失** | 🔴 **不一致** |

### 步骤名称（Step）

| 步骤 | 前端定义 | 后端实现 | 状态 |
|------|---------|---------|------|
| 初始化 | `init`, `queued`, `starting` | ✅ | ✅ 一致 |
| Intent Analysis | `intent_analysis` | ✅ IntentRunner | ✅ 一致 |
| Curriculum Design | `curriculum_design` | ✅ CurriculumRunner | ✅ 一致 |
| Structure Validation | `structure_validation` | ✅ ValidationRunner | ✅ 一致 |
| Human Review | `human_review`, `human_review_pending` | ✅ ReviewRunner | ✅ 一致 |
| Validation Edit Plan | `validation_edit_plan_analysis` | ✅ ValidationEditPlanRunner | ✅ 一致 |
| Review Edit Plan | `edit_plan_analysis` | ✅ EditPlanRunner | ✅ 一致 |
| Roadmap Edit | `roadmap_edit` | ✅ EditorRunner | ✅ 一致 |
| Content Generation | `content_generation`, `tutorial_generation`, etc. | ✅ ContentRunner | ✅ 一致 |

### 状态枚举（Status）

| 状态 | 前端定义 | 后端实现 | 状态 |
|------|---------|---------|------|
| `pending` | ✅ | ✅ | ✅ 一致 |
| `processing` | ✅ | ✅ WorkflowBrain | ✅ 一致 |
| `completed` | ✅ | ✅ WorkflowBrain | ✅ 一致 |
| `failed` | ✅ | ✅ WorkflowBrain | ✅ 一致 |
| `human_review_pending` | ✅ | ✅ ReviewRunner | ✅ 一致 |
| `partial_failure` | ✅ | ✅ ContentRunner | ✅ 一致 |

---

## 🔧 修复建议

### 修复 1: 在 WorkflowBrain 中传递 `edit_source`

**文件**: `backend/app/core/orchestrator/workflow_brain.py`

**修改位置**: `_before_node()` 方法（Line 256-261）

**当前代码**:

```python
# 4. 发布进度通知
await self.notification_service.publish_progress(
    task_id=task_id,
    step=node_name,
    status="processing",
    message=f"正在执行: {node_name}...",
)
```

**修复后**:

```python
# 4. 发布进度通知
# 从 state 中提取 edit_source（用于前端区分分支）
extra_data = {}
edit_source = state.get("edit_source")
if edit_source:
    extra_data["edit_source"] = edit_source

await self.notification_service.publish_progress(
    task_id=task_id,
    step=node_name,
    status="processing",
    message=f"正在执行: {node_name}...",
    extra_data=extra_data if extra_data else None,
)
```

### 修复 2: 在 `_after_node()` 中也传递 `edit_source`

**文件**: `backend/app/core/orchestrator/workflow_brain.py`

**修改位置**: `_after_node()` 方法（Line 297-303）

**当前代码**:

```python
# 2. 发布完成通知
await self.notification_service.publish_progress(
    task_id=ctx.task_id,
    step=ctx.node_name,
    status="completed",
    message=f"完成: {ctx.node_name}",
)
```

**修复后**:

```python
# 2. 发布完成通知
# 从 state 中提取 edit_source（用于前端区分分支）
extra_data = {}
edit_source = state.get("edit_source")
if edit_source:
    extra_data["edit_source"] = edit_source

await self.notification_service.publish_progress(
    task_id=ctx.task_id,
    step=ctx.node_name,
    status="completed",
    message=f"完成: {ctx.node_name}",
    extra_data=extra_data if extra_data else None,
)
```

---

## ✅ 测试验证

### 测试 1: 验证分支 `edit_source` 传递

**步骤**:

1. 创建一个会验证失败的路线图请求
2. 观察 WebSocket 消息中 `validation_edit_plan_analysis` 和 `roadmap_edit` 步骤是否包含 `data.edit_source = "validation_failed"`
3. 检查前端拓扑图是否高亮显示验证分支（Validate → Plan1 → Edit1）

**预期结果**:

```json
{
  "type": "progress",
  "task_id": "xxx",
  "step": "validation_edit_plan_analysis",
  "status": "processing",
  "data": {
    "edit_source": "validation_failed"  // ✅ 应包含此字段
  }
}
```

### 测试 2: 审核分支 `edit_source` 传递

**步骤**:

1. 创建路线图并等待 Human Review
2. 拒绝路线图并提供反馈
3. 观察 WebSocket 消息中 `edit_plan_analysis` 和 `roadmap_edit` 步骤是否包含 `data.edit_source = "human_review"`
4. 检查前端拓扑图是否高亮显示审核分支（Review → Plan2 → Edit2）

**预期结果**:

```json
{
  "type": "progress",
  "task_id": "xxx",
  "step": "edit_plan_analysis",
  "status": "processing",
  "data": {
    "edit_source": "human_review"  // ✅ 应包含此字段
  }
}
```

### 测试 3: 状态持久性

**步骤**:

1. 在修改过程中刷新页面
2. 检查 `currentStep` 和 `editSource` 是否正确恢复
3. 验证拓扑图是否显示正确的分支状态

**注意**: 目前 `edit_source` 未保存到数据库，页面刷新后会丢失。建议：

- **短期方案**: 从最近的执行日志中推断 `edit_source`
- **长期方案**: 在 `Task` 模型中添加 `edit_source` 字段

---

## 📊 总结

### 问题严重性评估

| 问题 | 严重性 | 影响 | 是否阻塞 |
|------|-------|------|---------|
| `edit_source` 未传递到前端 | 🔴 高 | 前端无法区分分支，用户体验受损 | ✅ 是 |

### 修复优先级

1. **P0（必须修复）**: 在 `WorkflowBrain` 中传递 `edit_source` 到 WebSocket 通知
2. **P1（建议修复）**: 在 `Task` 模型中添加 `edit_source` 字段，支持页面刷新后恢复

### 其他发现

✅ **非常好的部分**:
- 所有步骤名称枚举值完全一致
- 所有状态枚举值完全一致
- 前端执行日志配置覆盖了所有后端步骤
- 工作流路由逻辑清晰，分支判断准确

---

**报告生成时间**: 2025-12-23  
**检查工具**: AI Code Analysis  
**下一步**: 应用修复建议，运行测试验证

