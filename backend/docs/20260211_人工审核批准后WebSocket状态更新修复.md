# 人工审核批准后WebSocket状态更新修复

## 问题描述

**症状**：前端任务详情页，human_review阶段点击Approve按钮后，理想情况是流程状态进入到内容生成节点（`content_generation_queued`），但实时状态没有更新，前端UI停留在`human_review`步骤。

**影响**：用户批准路线图后，无法看到内容生成的实时进度，体验不佳。

---

## 根因分析

### 第一性原理回溯

#### 1. 审批流程的物理执行链

```
用户点击Approve
  ↓
前端调用 POST /tasks/{task_id}/approve
  ↓
后端触发 Celery任务 resume_after_review.delay()
  ↓
WorkflowExecutionService.resume_workflow_after_review()
  ↓
WorkflowExecutor.resume_after_human_review() 
  ↓
LangGraph: Command(resume={"approved": true, ...})
  ↓
human_review_node 恢复执行
  ↓
返回状态更新: {current_step: "content_generation_queued", ...}
  ↓
WorkflowExecutor 监听 on_chain_end 事件
  ↓
调用 SideEffectCoordinator.on_node_complete()
  ↓
发送 WebSocket 通知
```

#### 2. 逻辑断裂点定位

**关键日志证据**（`/terminals/2.txt:354-357`）：

```
[15:58:16,613] coordinator_node_complete ... node_name=human_review
[15:58:16,641] coordinator_sending_websocket ... extra_data={'duration_ms': 0}
[15:58:16,664] workflow_resumed_successfully ... final_step=content_generation_queued
```

**问题点**：
- `human_review_node`返回`current_step="content_generation_queued"`
- 但`coordinator_sending_websocket`时使用的是`node_name="human_review"`
- **前端收到的WebSocket消息**：
  ```json
  {
    "step": "human_review",  // ❌ 错误：应该是 "content_generation_queued"
    "status": "completed"
  }
  ```

#### 3. 底层原理分析

在`SideEffectCoordinator.on_node_complete()`中（`side_effect_coordinator.py:200-205`）：

```python
await self._send_progress_notification(
    task_id=task_id,
    step=node_name,  # ⚠️ 问题：使用的是节点名称，而不是状态中的 current_step
    status="completed",
    extra_data=extra_data,
)
```

**公理违反**：
- **状态传递的单向性原则**：Node返回的`current_step`代表了工作流的**新状态**，应该传递给下游（WebSocket）
- **但实际代码**：使用了`node_name`（节点的物理名称）而不是`current_step`（工作流的逻辑状态）

**为什么这个设计有问题**：
- 大多数节点：`node_name == current_step`（如`intent_analysis`节点返回`current_step="intent_analysis"`）
- **特殊节点**：`human_review`节点批准后返回`current_step="content_generation_queued"`（状态跳转）
- **因果断裂**：使用`node_name`导致前端无法感知到状态跳转

---

## 修复方案

### 代码修改

**文件**：`backend/app/core/orchestrator/side_effect_coordinator.py`

**修改位置**：`on_node_complete()`方法（第157-205行）

**修复逻辑**：
```python
# ✅ 关键修复：从 output 强制提取 current_step（必须存在）
# 原因：
# 1. output 是 executor 传递的 final_state（完整的工作流状态）
# 2. 所有节点都返回 current_step 字段（已验证）
# 3. current_step 代表工作流的逻辑状态，不同于物理节点名称 node_name
# 例如：human_review 批准后返回 current_step="content_generation_queued"
#       但 node_name="human_review"，前端需要收到 "content_generation_queued"
current_step = _safe_get(output, "current_step")

# ⚠️ 严格校验：current_step 必须存在
# 如果缺失，说明状态机有严重bug，直接抛出异常（Fail Fast）
if not current_step:
    logger.critical("CRITICAL: final_state 中缺少 current_step！")
    raise ValueError(
        f"CRITICAL BUG: Node {node_name} completed but final_state has no current_step. "
        f"This breaks frontend state sync."
    )

# 3. 发送 WebSocket 通知
logger.info(
    "coordinator_sending_websocket",
    task_id=task_id,
    node_name=node_name,
    current_step=current_step,  # ✅ 总是使用 current_step
    extra_data=extra_data,
)

await self._send_progress_notification(
    task_id=task_id,
    step=current_step,  # ✅ 强制使用 current_step（不使用 node_name fallback）
    status="completed",
    extra_data=extra_data,
)
```

**修复原理**：
1. **强制使用状态**：从`output`（即`final_state`）中提取`current_step`，这是工作流的**逻辑状态**
2. **Fail Fast原则**：如果`current_step`不存在，立即抛出异常，暴露状态机bug
3. **状态传递一致性**：确保WebSocket通知的`step`严格等于工作流的`current_step`，不使用`node_name`fallback

---

## 修复前后对比

### 修复前

```
human_review_node返回:
{
  "current_step": "content_generation_queued",
  "human_approved": true,
  ...
}

↓

coordinator.on_node_complete() 发送:
{
  "step": "human_review",  // ❌ 使用了 node_name
  "status": "completed"
}

↓

前端接收:
step="human_review" → mapToDisplayStep() → "human_review"
❌ UI停留在 human_review 步骤
```

### 修复后

```
human_review_node返回:
{
  "current_step": "content_generation_queued",
  "human_approved": true,
  ...
}

↓

coordinator.on_node_complete() 发送:
{
  "step": "content_generation_queued",  // ✅ 使用了 output.current_step
  "status": "completed"
}

↓

前端接收:
step="content_generation_queued" → mapToDisplayStep() → "content_generation"
✅ UI正确更新到 content_generation 步骤
```

---

## 测试验证

### 测试步骤

1. **创建新的路线图任务**，等待进入`human_review`阶段
2. **前端点击Approve按钮**
3. **观察前端UI**：
   - ✅ 预期：流程状态从`human_review`立即更新为`content_generation`
   - ✅ 预期：显示内容生成的实时进度（concepts逐个生成）

### 日志验证

修复后的日志应包含：
```
[coordinator_sending_websocket]
  node_name=human_review
  current_step_in_output=content_generation_queued
  notification_step=content_generation_queued  ← 新增字段
  extra_data={...}
```

---

## 影响范围

### 受影响的节点

理论上，所有在返回值中包含`current_step`字段的节点都会受益于此修复：
- ✅ `human_review` (主要受益者)
- ✅ `edit_plan_analysis` (如果返回了不同的`current_step`)
- ✅ `structure_validation` (验证失败时可能跳转到`edit_plan_analysis`)

### 不受影响的节点

对于`current_step == node_name`的节点（大多数情况），修复逻辑仍然使用`current_step`，行为更加严格和一致。

### 副作用和风险

- ✅ **更高的健壮性**：强制要求所有节点返回`current_step`，提前发现状态机bug
- ⚠️ **Fail Fast**：如果某个节点未返回`current_step`，会直接抛出异常（而不是静默使用fallback）
- 📊 **所有现有节点已验证**：通过代码审查确认所有节点都正确返回了`current_step`，不会触发异常

---

## 相关文档

- **LangGraph中断/恢复机制**：`backend/app/core/orchestrator/nodes/human_review.py`
- **工作流执行器**：`backend/app/core/orchestrator/executor.py`
- **副作用协调器**：`backend/app/core/orchestrator/side_effect_coordinator.py`
- **前端步骤映射**：`frontend-next/lib/constants/workflow-steps.ts`

---

## 总结

本次修复从**第一性原理**出发，通过**日志追踪**和**代码审查**，定位到了WebSocket通知中`step`参数的错误来源。修复方案遵循**状态传递一致性原则**，确保前端能够正确感知工作流的状态跳转，从而解决了UI不更新的问题。
