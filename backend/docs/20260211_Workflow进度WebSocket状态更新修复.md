# Workflow Progress WebSocket 状态更新修复

**日期**: 2026-02-11  
**问题**: 任务详情页 Workflow Progress 中 Validate 节点的 Plan/Edit 分支状态没有实时更新  
**影响**: 用户无法在前端看到验证失败后的自动修复流程进度

---

## 一、问题现象

在任务详情页 `http://localhost:3000/tasks/{taskId}` 的 Workflow Progress 组件中：
- Validate 节点的分支中 Plan 和 Edit 节点**实际已经运行**
- 但前端 WebSocket 没有收到状态更新
- 从 execution_logs 的 details 中可以看到 `edit_source: "validation_failed"`
- 但前端 Workflow 拓扑图没有高亮显示这些节点

---

## 二、问题根源

### 2.1 代码位置

**文件**: `backend/app/core/orchestrator/executor.py`  
**方法**: `resume_after_human_review`（第481-557行）

### 2.2 问题代码

```python
# ❌ 错误：resume流程中没有合并node_output到final_state
elif event_type == "on_chain_end":
    # ...获取node_output...
    if not isinstance(node_output, dict):
        continue
    
    # 获取完整State
    state_snapshot = await self.graph.aget_state(config)
    final_state = state_snapshot.values  # ⚠️ 直接使用，没有合并node_output
    
    # 调用coordinator（此时final_state缺少edit_source等临时字段）
    await self.coordinator.on_node_complete(
        task_id=task_id,
        node_name=node_name,
        output=final_state,  # ❌ 缺少node_output中的edit_source
        duration_ms=duration_ms,
    )
```

### 2.3 为什么会导致问题

1. **节点返回值**：`edit_plan_analysis_node` 返回包含 `edit_source: "validation_failed"`
2. **合并缺失**：`resume` 流程没有将 `node_output` 合并到 `final_state`
3. **coordinator 获取不到**：`SideEffectCoordinator.on_node_complete()` 的 `output` 参数缺少 `edit_source`
4. **WebSocket 消息缺失**：`publish_progress()` 的 `extra_data` 中没有 `edit_source`
5. **前端无法更新**：前端通过 `event.data?.edit_source` 判断分支，但消息中没有该字段

---

## 三、修复方案

### 3.1 修复代码

在 `executor.py` 的 `resume_after_human_review` 方法中，添加与 `execute` 方法相同的合并逻辑：

```python
# ✅ 修复后
elif event_type == "on_chain_end":
    # ...获取node_output...
    if not isinstance(node_output, dict):
        continue
    
    # 获取完整State
    state_snapshot = await self.graph.aget_state(config)
    final_state = state_snapshot.values
    
    # ✅ 关键修复：先合并 node_output 到 final_state
    # 这样 coordinator.on_node_complete() 才能获取到完整的状态（包含 edit_source 等字段）
    if isinstance(node_output, dict):
        final_state = {**final_state, **node_output}
    else:
        # 如果是 Pydantic 模型，转换为字典
        final_state = {**final_state, **node_output.model_dump()}
    
    # 调用coordinator（现在final_state包含edit_source）
    await self.coordinator.on_node_complete(
        task_id=task_id,
        node_name=node_name,
        output=final_state,  # ✅ 包含完整状态
        duration_ms=duration_ms,
    )
```

### 3.2 修复位置

**文件**: `backend/app/core/orchestrator/executor.py`  
**行数**: 第508-516行（在获取 `state_snapshot` 之后）

---

## 四、WebSocket 消息流

### 4.1 后端发送流程

```
Node完成 (edit_plan_analysis)
  ↓ 返回 {"edit_source": "validation_failed", ...}
Executor合并node_output到final_state
  ↓ final_state包含edit_source
SideEffectCoordinator.on_node_complete(output=final_state)
  ↓ 提取edit_source并添加到extra_data
NotificationService.publish_progress(extra_data={"edit_source": "validation_failed"})
  ↓ 发送WebSocket消息
Redis Pub/Sub
  ↓
WebSocket端点 → 前端
```

### 4.2 前端处理逻辑

**文件**: `frontend-next/app/(app)/tasks/[taskId]/page.tsx`

```typescript
// WebSocket消息处理
if (event.data?.edit_source) {
  setEditSource(event.data.edit_source);  // ✅ 更新状态
}
```

**文件**: `frontend-next/components/task/workflow-topology.tsx`

```typescript
// 根据edit_source判断分支激活状态
const isValidationBranchActive = executionLogs.some(
  log => log.details?.edit_source === 'validation_failed'
);

const isReviewBranchActive = executionLogs.some(
  log => log.details?.edit_source === 'human_review'
);
```

---

## 五、验证步骤

### 5.1 重启后端服务

```bash
# 停止Celery
pkill -f "celery -A app.core.celery_app worker"

# 重新启动
cd backend
celery -A app.core.celery_app worker --loglevel=info
```

### 5.2 创建测试任务

1. 创建一个新的路线图生成任务
2. 等待验证失败（触发 validation_failed 分支）
3. 在任务详情页观察 Workflow Progress

### 5.3 期望结果

- **Plan节点**（edit_plan_analysis）高亮显示为"已完成"
- **Edit节点**（roadmap_edit）高亮显示为"已完成"
- **Validate节点**（structure_validation）显示为"处理中"或"已完成"
- 浏览器 Console 应输出：`[TaskDetail] Extracted edit_source from logs: validation_failed`

---

## 六、相关文件

### 6.1 后端文件

- `backend/app/core/orchestrator/executor.py` - 工作流执行器（修复点）
- `backend/app/core/orchestrator/side_effect_coordinator.py` - 副作用协调器（提取edit_source）
- `backend/app/core/orchestrator/nodes/edit_plan_analysis.py` - 编辑计划分析节点（返回edit_source）
- `backend/app/services/shared/notification_service.py` - 通知服务（发送WebSocket消息）

### 6.2 前端文件

- `frontend-next/app/(app)/tasks/[taskId]/page.tsx` - 任务详情页（接收WebSocket消息）
- `frontend-next/components/task/workflow-topology.tsx` - 工作流拓扑图（根据edit_source显示分支状态）
- `frontend-next/lib/api/websocket.ts` - WebSocket消息类型定义

---

## 七、技术细节

### 7.1 为什么需要合并node_output

**问题**：LangGraph 的 `aget_state()` 返回的 State 是持久化的状态，**不包含节点返回的临时字段**。

**解释**：
- `edit_source` 是节点函数返回的临时字段（用于路由判断和前端显示）
- 这个字段**不会**被持久化到 LangGraph Checkpoint（因为不在 State 的顶级定义中）
- 因此必须从 `event.data.output`（即 `node_output`）中获取

**对比**：
- `execute` 流程中已经有合并逻辑（第277-282行）
- `resume` 流程中缺失了这个逻辑（本次修复）

### 7.2 edit_source 的作用

**后端路由**：
```python
# app/core/orchestrator/routers.py
def route_after_edit(state: RoadmapState) -> str:
    edit_source = state.get("edit_source")
    
    if edit_source == "human_review":
        return "human_review"  # 返回审核
    elif edit_source == "validation_failed":
        return "structure_validation"  # 返回验证
```

**前端分支判断**：
```typescript
// 根据 edit_source 判断当前激活的分支
if (editSource === 'validation_failed') {
  // 高亮显示验证分支的Plan/Edit节点
}
```

---

## 八、总结

### 8.1 问题总结

- **根本原因**：`resume` 流程缺少 `node_output` 合并逻辑
- **表现**：WebSocket 消息缺少 `edit_source` 字段
- **影响**：前端无法识别验证失败分支，Workflow Progress 不更新

### 8.2 修复总结

- **修复点**：1处（`executor.py` 第508-516行）
- **修复方式**：添加 `node_output` 合并逻辑（与 `execute` 流程保持一致）
- **影响范围**：所有通过 `resume_after_human_review` 恢复的工作流

### 8.3 后续优化

1. **添加单元测试**：测试 `resume` 流程中 `edit_source` 的传递
2. **添加日志**：在 `coordinator.on_node_complete()` 中记录 `edit_source` 的值
3. **前端容错**：如果 WebSocket 消息缺失，从 execution_logs 中提取 `edit_source`（已实现）

---

**修复人**: AI Assistant  
**审核人**: 待定  
**状态**: ✅ 修复完成，待测试验证
