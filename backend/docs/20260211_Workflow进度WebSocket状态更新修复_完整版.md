# Workflow Progress WebSocket 状态更新修复（完整版）

**日期**: 2026-02-11  
**问题**: 验证失败后自动修复分支（Plan/Edit）的节点状态没有实时更新到前端  
**影响**: 用户无法在 Workflow Progress 组件中看到验证失败后的自动修复流程进度

---

## 一、问题现象

### 1.1 用户反馈

在任务详情页 `http://localhost:3000/tasks/{taskId}` 的 Workflow Progress 组件中：
- **Validate** 节点失败后触发验证分支（validation_failed）
- **Plan**（edit_plan_analysis）和 **Edit**（roadmap_edit）节点实际已经运行
- 但前端 Workflow 拓扑图**没有高亮显示这些节点**
- execution_logs 中的 details 可以看到 `edit_source: "validation_failed"`
- 说明日志记录正常，但 **WebSocket 实时消息没有正确传递状态**

### 1.2 预期行为

- 当 Validate 失败时，应该自动进入验证分支
- Plan 节点（edit_plan_analysis）运行时，前端应该高亮显示
- Edit 节点（roadmap_edit）运行时，前端应该高亮显示
- 拓扑图应该显示当前激活的分支（validation_failed 或 human_review）

---

## 二、问题根源分析

### 2.1 前端判断逻辑

**文件**: `frontend-next/components/task/workflow-topology.tsx` (第378-390行)

```typescript
// 检查分支是否被触发过（通过执行日志的 details.edit_source 判断）
const validationBranchTriggered = executionLogs.some(
  log => 
    (log.step === 'edit_plan_analysis' || log.step === 'roadmap_edit') &&
    log.details?.edit_source === 'validation_failed'
);

const reviewBranchTriggered = executionLogs.some(
  log => 
    (log.step === 'edit_plan_analysis' || log.step === 'roadmap_edit') &&
    log.details?.edit_source === 'human_review'
);
```

**说明**：前端通过检查 execution_logs 中的 `details.edit_source` 来判断哪个分支被触发过。

### 2.2 前端实时状态更新

**文件**: `frontend-next/app/(app)/tasks/[taskId]/page.tsx` (第571-573行)

```typescript
// 更新 edit_source（用于区分分支）
if (event.data?.edit_source) {
  setEditSource(event.data.edit_source);
}
```

**说明**：前端监听 WebSocket 消息中的 `event.data?.edit_source`，用这个值更新 `editSource` state。

### 2.3 WorkflowTopology 组件依赖

**文件**: `frontend-next/components/task/workflow-topology.tsx` (第293-296行)

```typescript
export function WorkflowTopology({
  currentStep,
  status,
  editSource,  // ✅ 从 page.tsx 传入
  ...
}) {
  // 获取当前步骤位置（需要 editSource 来判断分支）
  const stepLocation = getStepLocation(currentStep, editSource);
  ...
}
```

**说明**：WorkflowTopology 组件需要 `editSource` 来正确判断当前激活的分支。

### 2.4 问题所在

**关键发现**：
1. execution_logs 中有 `edit_source`（说明日志记录正常）
2. 但前端 Workflow Progress 没有更新（说明 WebSocket 实时消息缺失 `edit_source`）

**结论**：WebSocket 消息中没有正确传递 `edit_source` 字段。

---

## 三、数据流追踪

### 3.1 后端数据流

```
Node 执行完成（edit_plan_analysis/roadmap_edit）
  ↓ 返回 {"edit_source": "validation_failed", ...}
Executor.on_chain_end
  ↓ 合并 node_output 到 final_state
SideEffectCoordinator.on_node_complete(output=final_state)
  ↓ 提取 edit_source 并添加到 extra_data
NotificationService.publish_progress(extra_data={"edit_source": "validation_failed"})
  ↓ 发送 WebSocket 消息
Redis Pub/Sub
  ↓
WebSocket 端点 → 前端
```

### 3.2 前端数据流

```
WebSocket.onmessage
  ↓ 解析 JSON 消息
onProgress handler (page.tsx)
  ↓ if (event.data?.edit_source) setEditSource(...)
WorkflowTopology 组件
  ↓ 使用 editSource 判断分支激活状态
拓扑图更新
```

### 3.3 可能的问题点

1. **Executor**: node_output 没有正确合并到 final_state？
2. **SideEffectCoordinator**: edit_source 没有正确提取？
3. **NotificationService**: extra_data 没有正确传递？
4. **前端**: WebSocket 消息解析错误？

---

## 四、修复方案

### 4.1 修复点1: Executor Resume 流程（已修复）

**文件**: `backend/app/core/orchestrator/executor.py` (第508-519行)

**问题**: `resume_after_human_review` 方法中，节点完成时没有合并 node_output 到 final_state。

**修复**:

```python
# ✅ 关键修复：先合并 node_output 到 final_state，再传递给 coordinator
# 这样 coordinator.on_node_complete() 才能获取到完整的状态（包含 edit_source 等字段）
state_snapshot = await self.graph.aget_state(config)
final_state = state_snapshot.values

if isinstance(node_output, dict):
    final_state = {**final_state, **node_output}
else:
    # 如果是 Pydantic 模型，转换为字典
    final_state = {**final_state, **node_output.model_dump()}
```

**影响范围**: 所有通过 `resume_after_human_review` 恢复的工作流。

**说明**: Execute 流程已经有合并逻辑（第276-282行），但 Resume 流程缺失。

### 4.2 修复点2: SideEffectCoordinator 调试日志（已添加）

**文件**: `backend/app/core/orchestrator/side_effect_coordinator.py` (第163-183行)

**问题**: 无法确认 `edit_source` 是否正确提取和传递。

**修复**: 添加详细的调试日志

```python
# 🔍 Debug日志：检查edit_source是否存在
logger.info(
    "coordinator_extract_edit_source",
    task_id=task_id,
    node_name=node_name,
    edit_source=edit_source,
    output_has_edit_source="edit_source" in output if isinstance(output, dict) else False,
    output_keys=list(output.keys()) if isinstance(output, dict) else "not_dict",
)

if edit_source is not None:
    extra_data["edit_source"] = edit_source
    logger.info(
        "coordinator_added_edit_source_to_extra_data",
        task_id=task_id,
        node_name=node_name,
        edit_source=edit_source,
    )

# 🔍 Debug日志：检查extra_data内容
logger.info(
    "coordinator_sending_websocket",
    task_id=task_id,
    node_name=node_name,
    extra_data=extra_data,
)
```

**作用**: 帮助排查 `edit_source` 在传递过程中是否丢失。

---

## 五、验证步骤

### 5.1 重启后端服务

```bash
# 停止 Celery Worker
pkill -f "celery -A app.core.celery_app worker"

# 重新启动
cd backend
celery -A app.core.celery_app worker --loglevel=info
```

### 5.2 创建测试任务

1. 创建一个新的路线图生成任务
2. 等待验证失败（触发 validation_failed 分支）
3. 观察任务详情页的 Workflow Progress

### 5.3 检查日志

在 Celery Worker 日志中查找：

```
coordinator_extract_edit_source
  → 检查 edit_source 的值
  → 检查 output_has_edit_source 是否为 True
  → 检查 output_keys 是否包含 edit_source

coordinator_added_edit_source_to_extra_data
  → 确认 edit_source 已添加到 extra_data

coordinator_sending_websocket
  → 确认 extra_data 包含 edit_source
```

### 5.4 检查前端

1. **浏览器 Console 应输出**:
   ```
   [WS] Message received: progress {type: 'progress', step: 'edit_plan_analysis', data: {edit_source: 'validation_failed', ...}}
   [TaskDetail] Extracted edit_source from logs: validation_failed
   ```

2. **Workflow Progress 应该**:
   - Plan 节点（edit_plan_analysis）高亮显示为"已完成"
   - Edit 节点（roadmap_edit）高亮显示为"已完成"
   - Validate 节点下方的分支路径显示电流脉冲动画

---

## 六、技术细节

### 6.1 为什么需要合并 node_output

**问题**: LangGraph 的 `aget_state()` 返回的 State 是持久化的状态，**不包含节点返回的临时字段**。

**解释**:
- `edit_source` 是节点函数返回的临时字段（用于路由判断和前端显示）
- 这个字段**不会**被持久化到 LangGraph Checkpoint（因为不在 State 的顶级定义中）
- 因此必须从 `event.data.output`（即 `node_output`）中获取

**对比**:
- `execute` 流程中已经有合并逻辑（第276-282行）
- `resume` 流程中缺失了这个逻辑（本次修复）

### 6.2 edit_source 的作用

#### 后端路由判断

**文件**: `backend/app/core/orchestrator/routers.py`

```python
def route_after_edit(state: RoadmapState) -> str:
    """路线图编辑后的路由"""
    edit_source = state.get("edit_source")
    
    if edit_source == "human_review":
        return "human_review"  # 返回审核
    elif edit_source == "validation_failed":
        return "structure_validation"  # 返回验证
```

#### 前端分支判断

**文件**: `frontend-next/components/task/workflow-topology.tsx`

```typescript
// 根据 edit_source 判断当前步骤位置
function getStepLocation(currentStep: string | null, editSource?: EditSource) {
  // 特殊处理 roadmap_edit：需要根据 editSource 判断
  if (currentStep === 'roadmap_edit') {
    if (editSource === 'validation_failed') {
      return { isOnBranch: true, branchType: 'validation' };
    }
    if (editSource === 'human_review') {
      return { isOnBranch: true, branchType: 'review' };
    }
  }
  ...
}
```

### 6.3 节点返回值中的 edit_source

#### structure_validation 节点

**文件**: `backend/app/core/orchestrator/nodes/structure_validation.py` (第100行)

```python
return {
    "validation_result": validation_result,
    "current_step": "structure_validation",
    "edit_source": "validation_failed" if not validation_result.is_valid else state.get("edit_source"),
    ...
}
```

#### edit_plan_analysis 节点

**文件**: `backend/app/core/orchestrator/nodes/edit_plan_analysis.py` (第135行)

```python
return {
    "edit_plan": analysis_output,
    "current_step": "edit_plan_analysis",
    "edit_source": edit_source,  # 从 state 继承或默认为 human_review
    ...
}
```

#### roadmap_edit 节点

**文件**: `backend/app/core/orchestrator/nodes/roadmap_edit.py` (第120行)

```python
return {
    "roadmap_framework": modified_framework,
    "current_step": "roadmap_edit",
    "edit_source": edit_source,  # 从 state 获取（validation_failed 或 human_review）
    ...
}
```

### 6.4 日志记录中的 edit_source

#### edit_plan_analysis 日志

**文件**: `backend/app/core/orchestrator/nodes/edit_plan_analysis.py` (第106行)

```python
await execution_logger.info(
    task_id=task_id,
    category=LogCategory.AGENT,
    step="edit_plan_analysis",
    details={
        "log_type": "edit_plan_output",
        "edit_source": edit_source,  # ✅ 记录到日志
        "confidence": analysis_output.confidence,
    },
)
```

#### roadmap_edit 日志

**文件**: `backend/app/core/orchestrator/nodes/roadmap_edit.py` (第103行)

```python
await execution_logger.info(
    task_id=task_id,
    category=LogCategory.AGENT,
    step="roadmap_edit",
    details={
        "log_type": "roadmap_edit_output",
        "edit_source": edit_source,  # ✅ 记录到日志
        "modification_count": modification_count,
    },
)
```

---

## 七、前端类型定义

### 7.1 WebSocket 消息类型

**文件**: `frontend-next/lib/api/websocket.ts` (第54行)

```typescript
export interface WSProgressEvent extends WSEvent {
  type: 'progress';
  step: string;
  status: string;
  data?: {
    edit_source?: 'validation_failed' | 'human_review';  // ✅ 编辑来源
    modified_concept_ids?: string[];
    ...
  };
}
```

### 7.2 编辑类型 vs 编辑来源

**注意区分**：

- **后端 Schema**: `edit_type`（数据库字段，用于编辑记录）
  - 文件: `backend/app/schemas/edit.py`
  - 类型: `"human_review"` | `"validation_failed"`

- **工作流节点**: `edit_source`（临时字段，用于路由和前端显示）
  - 文件: `backend/app/core/orchestrator/nodes/*.py`
  - 类型: `"human_review"` | `"validation_failed"` | `"unknown"`

**关系**：
- `edit_source` 是工作流运行时的临时字段
- `edit_type` 是保存到数据库的持久化字段
- 两者的值通常相同，但字段名不同

---

## 八、相关文件清单

### 8.1 后端文件

| 文件 | 修改内容 |
|-----|-------|
| `backend/app/core/orchestrator/executor.py` | ✅ 添加 resume 流程的 node_output 合并逻辑 |
| `backend/app/core/orchestrator/side_effect_coordinator.py` | ✅ 添加 edit_source 提取和传递的调试日志 |
| `backend/app/core/orchestrator/nodes/structure_validation.py` | 设置 edit_source (已有) |
| `backend/app/core/orchestrator/nodes/edit_plan_analysis.py` | 返回和记录 edit_source (已有) |
| `backend/app/core/orchestrator/nodes/roadmap_edit.py` | 返回和记录 edit_source (已有) |
| `backend/app/services/shared/notification_service.py` | 发送 WebSocket 消息 (无需修改) |

### 8.2 前端文件

| 文件 | 功能 |
|-----|------|
| `frontend-next/app/(app)/tasks/[taskId]/page.tsx` | 接收 WebSocket 消息，更新 editSource state |
| `frontend-next/components/task/workflow-topology.tsx` | 根据 editSource 显示分支状态 |
| `frontend-next/lib/api/websocket.ts` | WebSocket 消息类型定义 |
| `frontend-next/lib/constants/workflow-steps.ts` | 工作流步骤常量定义 |

---

## 九、预期效果

### 9.1 日志输出（后端）

```
coordinator_extract_edit_source
  task_id=xxx
  node_name=edit_plan_analysis
  edit_source=validation_failed
  output_has_edit_source=True
  output_keys=['edit_plan', 'user_feedback', 'roadmap_id', 'user_id', 'edit_source', ...]

coordinator_added_edit_source_to_extra_data
  task_id=xxx
  node_name=edit_plan_analysis
  edit_source=validation_failed

coordinator_sending_websocket
  task_id=xxx
  node_name=edit_plan_analysis
  extra_data={'duration_ms': 1234, 'edit_source': 'validation_failed'}
```

### 9.2 Console 输出（前端）

```
[WS] Message received: progress {
  type: 'progress',
  step: 'edit_plan_analysis',
  status: 'completed',
  data: {
    edit_source: 'validation_failed',
    duration_ms: 1234
  }
}

[TaskDetail] Extracted edit_source from logs: validation_failed
```

### 9.3 UI 效果

1. **Workflow Progress 拓扑图**:
   - Validate 节点下方的分支显示
   - Plan 节点高亮显示（已完成状态）
   - Edit 节点高亮显示（已完成状态）
   - 分支路径显示电流脉冲动画

2. **Current Step Badge**:
   ```
   [edit_plan_analysis] [Auto-fix]
   ```
   （`edit_source === 'validation_failed'` 时显示 "Auto-fix"）

---

## 十、总结

### 10.1 问题根源

1. **Executor Resume 流程**: 节点完成时没有合并 node_output 到 final_state
2. **缺少调试日志**: 无法确认 edit_source 是否正确传递

### 10.2 修复总结

1. **Executor**: 添加 node_output 合并逻辑（与 execute 流程保持一致）
2. **SideEffectCoordinator**: 添加详细的调试日志（帮助排查问题）

### 10.3 影响范围

- **Resume 流程**: 所有通过 `resume_after_human_review` 恢复的工作流
- **Execute 流程**: 已有合并逻辑，无需修改

### 10.4 后续优化

1. **单元测试**: 添加测试验证 edit_source 的传递
2. **集成测试**: 测试验证失败分支的完整流程
3. **监控告警**: 添加 edit_source 缺失的告警

---

**修复人**: AI Assistant  
**审核人**: 待定  
**状态**: ✅ 修复完成，待测试验证
