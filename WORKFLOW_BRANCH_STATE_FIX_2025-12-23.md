# 工作流分支状态显示修复 (2025-12-23)

## 问题描述

**用户反馈**：
前端任务详情页的工作流拓扑图节点状态更新不正确。后端正处于 `roadmap_edit` 阶段，但前端显示 **Review 节点正在转圈加载**，而不是显示对应分支的 Edit 节点。

**现象**：
- 后端状态：`current_step = "roadmap_edit"`
- 预期前端：应该显示审核分支（Review Branch）或验证分支（Validation Branch）的 Edit 节点为加载状态
- 实际前端：显示主路的 Review 节点为加载状态

## 根本原因分析

### 工作流分支设计

根据 `WORKFLOW_ROUTING_UPDATE_2025-12-22.md` 和前端 `workflow-topology.tsx` 的设计，工作流有两个修复分支：

1. **验证分支（Validation Branch）**：
   - 触发条件：结构验证失败 (`edit_source = 'validation_failed'`)
   - 流程：`Validate → Plan1 (validation_edit_plan_analysis) → Edit1 (roadmap_edit) → 回到 Validate`

2. **审核分支（Review Branch）**：
   - 触发条件：人工审核拒绝 (`edit_source = 'human_review'`)
   - 流程：`Review → Plan2 (edit_plan_analysis) → Edit2 (roadmap_edit) → 回到 Review`

### 前端状态判断逻辑

**`workflow-topology.tsx` 中的 `getStepLocation()` 函数** (第181-230行)：

```typescript
export function getStepLocation(
  currentStep: string,
  editSource?: EditSource
): {
  stageId: string;
  isOnBranch: boolean;
  branchType?: 'validation' | 'review';
  branchNodeIndex?: number;
} {
  // ... 检查主路节点 ...

  // 检查验证分支
  for (let i = 0; i < VALIDATION_BRANCH.nodes.length; i++) {
    const node = VALIDATION_BRANCH.nodes[i];
    if (node.steps.includes(currentStep)) {
      // 特殊处理 roadmap_edit：需要根据 editSource 判断
      if (currentStep === 'roadmap_edit') {
        if (editSource === 'validation_failed') {
          return { stageId: node.id, isOnBranch: true, branchType: 'validation', branchNodeIndex: i };
        }
        continue; // 如果是 human_review，继续检查审核分支
      }
      return { stageId: node.id, isOnBranch: true, branchType: 'validation', branchNodeIndex: i };
    }
  }

  // 检查审核分支
  for (let i = 0; i < REVIEW_BRANCH.nodes.length; i++) {
    const node = REVIEW_BRANCH.nodes[i];
    if (node.steps.includes(currentStep)) {
      // 特殊处理 roadmap_edit：需要根据 editSource 判断
      if (currentStep === 'roadmap_edit') {
        if (editSource === 'human_review') {
          return { stageId: node.id, isOnBranch: true, branchType: 'review', branchNodeIndex: i };
        }
        continue;
      }
      return { stageId: node.id, isOnBranch: true, branchType: 'review', branchNodeIndex: i };
    }
  }

  // 默认返回第一个主路节点
  return { stageId: 'analysis', isOnBranch: false };
}
```

**关键点**：
- 由于两个分支都包含 `roadmap_edit` 步骤，前端**必须依赖 `editSource` 参数**来区分
- 如果 `editSource` 缺失或错误，前端无法正确判断当前在哪个分支上

### 后端状态传递链路

1. **`EditPlanRunner`** (人工审核场景) 设置 `edit_source = "human_review"` ✅
   ```python
   state_update = {
       "edit_plan": result.edit_plan,
       "edit_source": "human_review",  # ✅
       ...
   }
   ```

2. **`ValidationEditPlanRunner`** (验证失败场景) 设置 `edit_source = "validation_failed"` ✅
   ```python
   return {
       "edit_plan": result.edit_plan,
       "edit_source": "validation_failed",  # ✅
       ...
   }
   ```

3. **`EditorRunner`** (执行路线图编辑) **❌ 没有保持 `edit_source`**
   ```python
   return {
       "roadmap_framework": result.framework,
       "modification_count": modification_count + 1,
       "validation_round": validation_round,
       "current_step": "roadmap_edit",
       "execution_history": [f"路线图修改完成（第 {edit_round} 次）"],
       # ❌ 缺少 "edit_source"，导致状态丢失
   }
   ```

4. **`WorkflowBrain`** 从 state 中提取 `edit_source` 并发送到前端 ✅
   ```python
   # 从 state 中提取 edit_source（用于前端区分分支）
   extra_data = {}
   edit_source = state.get("edit_source")
   if edit_source:
       extra_data["edit_source"] = edit_source
   
   await self.notification_service.publish_progress(
       task_id=task_id,
       step=node_name,
       status="processing",
       data=extra_data,
   )
   ```

### 问题根源

**状态丢失发生在 `EditorRunner`**：

虽然上游的 `EditPlanRunner` 或 `ValidationEditPlanRunner` 正确设置了 `edit_source`，但 `EditorRunner` 在返回状态更新时**没有保持这个值**，导致：

1. LangGraph 工作流状态中的 `edit_source` 被覆盖为 `None`
2. `WorkflowBrain` 从 state 中获取 `edit_source` 时得到 `None`
3. WebSocket 消息中没有 `edit_source` 字段
4. 前端 `getStepLocation()` 收到 `editSource = undefined`
5. 前端无法判断 `roadmap_edit` 属于哪个分支，回退到默认行为（显示主路节点）

## 修复方案

### 修复 `EditorRunner` 保持 `edit_source`

**文件**：`backend/app/core/orchestrator/node_runners/editor_runner.py`

**修改位置**：第185-195行（返回状态更新部分）

**修改前**：
```python
# 返回纯状态更新
return {
    "roadmap_framework": result.framework,
    "modification_count": modification_count + 1,
    "validation_round": validation_round,
    "current_step": "roadmap_edit",
    "execution_history": [f"路线图修改完成（第 {edit_round} 次）"],
}
```

**修改后**：
```python
# 返回纯状态更新
state_update = {
    "roadmap_framework": result.framework,
    "modification_count": modification_count + 1,
    "validation_round": validation_round,
    "current_step": "roadmap_edit",
    "execution_history": [f"路线图修改完成（第 {edit_round} 次）"],
}

# 关键修复：保持 edit_source 字段（用于前端区分分支）
# edit_source 由上游的 EditPlanRunner 或 ValidationEditPlanRunner 设置
if "edit_source" in state:
    state_update["edit_source"] = state["edit_source"]

return state_update
```

## 影响范围

### 修改的文件
- `backend/app/core/orchestrator/node_runners/editor_runner.py` (第185-203行)

### 不受影响的文件
- ✅ `edit_plan_runner.py` - 已正确设置 `edit_source = "human_review"`
- ✅ `validation_edit_plan_runner.py` - 已正确设置 `edit_source = "validation_failed"`
- ✅ `review_runner.py` - 已正确设置 `edit_source = "human_review"`（用户拒绝时）
- ✅ `workflow_brain.py` - 已正确从 state 中提取并发送 `edit_source`
- ✅ 前端 `workflow-topology.tsx` - 逻辑正确，只是缺少数据
- ✅ 前端 `tasks/[taskId]/page.tsx` - 已正确接收和传递 `editSource`

## 测试验证

### 验证步骤 1：验证分支（Validation Branch）

1. 启动工作流，生成路线图
2. 确保路线图有结构验证错误（触发验证分支）
3. 观察前端工作流拓扑图：
   - **验证分支应该显示为激活状态**（显示在下方）
   - Plan1 节点应该显示为 "completed"
   - Edit1 节点应该显示为 "current"（转圈加载）
   - 主路的 Review 节点应该显示为 "pending"（灰色）

### 验证步骤 2：审核分支（Review Branch）

1. 启动工作流，生成路线图
2. 在人工审核节点拒绝路线图并提供反馈
3. 观察前端工作流拓扑图：
   - **审核分支应该显示为激活状态**（显示在上方）
   - Plan2 节点应该显示为 "completed"
   - Edit2 节点应该显示为 "current"（转圈加载）
   - Review 节点应该显示为 "current"（因为分支的触发节点）

### 验证步骤 3：WebSocket 消息检查

打开浏览器控制台，查看 WebSocket 消息：

```javascript
// 当 roadmap_edit 节点开始时，应该收到：
{
  "type": "progress",
  "task_id": "...",
  "step": "roadmap_edit",
  "status": "processing",
  "data": {
    "edit_source": "human_review"  // ✅ 或 "validation_failed"
  }
}

// 当 roadmap_edit 节点完成时，应该收到：
{
  "type": "progress",
  "task_id": "...",
  "step": "roadmap_edit",
  "status": "completed",
  "data": {
    "edit_source": "human_review"  // ✅ 或 "validation_failed"
  }
}
```

### 预期结果
- ✅ WebSocket 消息中包含正确的 `edit_source` 字段
- ✅ 前端工作流拓扑图正确显示对应分支的激活状态
- ✅ `roadmap_edit` 节点在正确的分支上显示为 "current"（加载中）
- ✅ 主路节点状态正确（触发节点为 "current"，后续节点为 "pending"）

## 最佳实践总结

### LangGraph 状态管理规则

1. **状态更新必须显式包含所有需要保持的字段**：
   ```python
   # ❌ 错误：只返回部分字段，其他字段会被覆盖为默认值
   return {
       "roadmap_framework": new_framework,
   }
   
   # ✅ 正确：显式保持需要的字段
   return {
       "roadmap_framework": new_framework,
       "edit_source": state.get("edit_source"),  # 保持上游设置的值
   }
   ```

2. **关键业务字段应该在整个工作流中保持**：
   - 如果某个字段（如 `edit_source`）被用于工作流路由或前端显示
   - 每个节点返回状态更新时都应该显式包含或保持这个字段

3. **使用条件保持避免覆盖为 None**：
   ```python
   state_update = {
       # ... 其他字段 ...
   }
   
   # 只有 state 中存在该字段时才保持
   if "edit_source" in state:
       state_update["edit_source"] = state["edit_source"]
   ```

### 前后端状态同步设计

1. **后端必须通过 WebSocket 传递足够的上下文信息**：
   - 不仅传递 `current_step` 和 `status`
   - 还要传递影响前端显示的业务字段（如 `edit_source`）

2. **前端应该设计容错机制**：
   - 当 `editSource` 缺失时，提供合理的回退行为
   - 当前回退到显示主路节点（虽然不准确，但不会崩溃）

3. **关键字段应该有明确的文档和类型定义**：
   - 后端：在 `RoadmapState` 类型中明确定义 `edit_source` 字段
   - 前端：在 `WorkflowTopologyProps` 中明确定义 `editSource` 参数

## 相关文档
- `WORKFLOW_ROUTING_UPDATE_2025-12-22.md` - 工作流路由和分支设计
- `FRONTEND_WORKFLOW_REFACTOR_SUMMARY.md` - 前端工作流重构总结
- `backend/app/core/orchestrator/routers.py` - 工作流路由实现
- `frontend-next/components/task/workflow-topology.tsx` - 工作流拓扑图组件

