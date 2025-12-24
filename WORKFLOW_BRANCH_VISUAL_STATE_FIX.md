# Workflow Branch Visual State Fix

**日期**: 2025-12-23  
**类型**: 前端 UI 修复  
**优先级**: 中

## 问题描述

在路线详情页的 Workflow Progress 组件中，当任务完成后，验证分支（Validation Branch）和审核分支（Review Branch）的节点始终显示为空心颜色（skipped 状态），即使这些分支在任务执行过程中被触发执行过。

这导致用户误以为这些分支没有被执行，影响了对工作流执行历史的理解。

### 预期行为

- 如果分支被触发执行过：节点应显示为实心颜色（completed 状态），与主路节点完成后的颜色一致
- 如果分支从未被触发：节点应显示为空心颜色（skipped 状态）

## 根本原因

在 `WorkflowTopology` 组件的 `getBranchNodeStatus` 函数中：

```typescript
const getBranchNodeStatus = (...): NodeStatus => {
  // 如果任务已完成，分支显示为 skipped（未触发）或 completed（已触发过）
  if (isCompleted) return 'skipped';  // ❌ 问题：始终返回 skipped
  // ...
};
```

当任务状态为 `completed` 或 `partial_failure` 时，函数直接返回 `'skipped'` 状态，没有检查分支是否实际被触发执行过。

## 解决方案

### 1. 添加执行日志参数

在 `WorkflowTopology` 组件中添加 `executionLogs` 参数，用于检查分支执行历史：

```typescript
interface ExecutionLog {
  step: string | null;
  [key: string]: any;
}

interface WorkflowTopologyProps {
  // ... 其他参数
  /** 执行日志（用于判断分支是否被触发过） */
  executionLogs?: ExecutionLog[];
}
```

### 2. 检测分支触发状态

通过执行日志中的 `step` 字段判断分支是否被触发：

```typescript
// 检查分支是否被触发过（通过执行日志判断）
// validation_edit_plan_analysis: 验证分支的 Plan 节点
// edit_plan_analysis: 审核分支的 Plan 节点
const validationBranchTriggered = executionLogs.some(
  log => log.step === 'validation_edit_plan_analysis'
);
const reviewBranchTriggered = executionLogs.some(
  log => log.step === 'edit_plan_analysis'
);
```

### 3. 修改状态判断逻辑

在 `getBranchNodeStatus` 函数中，根据分支触发状态返回正确的节点状态：

```typescript
const getBranchNodeStatus = (
  branchType: 'validation' | 'review',
  nodeIndex: number,
  nodeId: string
): NodeStatus => {
  // 检查分支是否被触发过
  const wasBranchTriggered = 
    branchType === 'validation' ? validationBranchTriggered : reviewBranchTriggered;
  
  // 如果任务已完成
  if (isCompleted) {
    // 如果分支被触发过，显示为已完成（实心颜色）
    if (wasBranchTriggered) {
      return 'completed';  // ✅ 修复：显示为已完成
    }
    // 否则显示为跳过（空心颜色）
    return 'skipped';
  }
  // ... 其他状态逻辑
};
```

### 4. 父组件传递日志数据

在 `TaskDetailPage` 中传递 `executionLogs` 给 `WorkflowTopology`：

```typescript
<WorkflowTopology
  currentStep={taskInfo.current_step}
  status={taskInfo.status}
  editSource={editSource}
  taskId={taskId}
  roadmapId={taskInfo.roadmap_id}
  roadmapTitle={roadmapFramework?.title || taskInfo.title}
  stagesCount={roadmapFramework?.stages?.length || 0}
  executionLogs={executionLogs}  // ✅ 新增：传递执行日志
  onHumanReviewComplete={handleHumanReviewComplete}
/>
```

## 修改文件

### 前端文件

1. **`frontend-next/components/task/workflow-topology.tsx`**
   - 添加 `ExecutionLog` 接口
   - 添加 `executionLogs` props
   - 添加分支触发检测逻辑
   - 修改 `getBranchNodeStatus` 函数

2. **`frontend-next/app/(app)/tasks/[taskId]/page.tsx`**
   - 传递 `executionLogs` 给 `WorkflowTopology` 组件

## 测试验证

### 测试场景

1. **验证分支触发**
   - 创建一个路线图任务
   - 等待任务执行到结构验证阶段
   - 让验证失败，触发验证分支（Plan1 → Edit1）
   - 等待任务完成
   - 验证：验证分支的两个节点应显示为实心绿色

2. **审核分支触发**
   - 创建一个路线图任务
   - 等待任务执行到人工审核阶段
   - 点击 "Change" 拒绝并提供反馈
   - 等待任务返回审核阶段
   - 点击 "Approve" 批准
   - 等待任务完成
   - 验证：审核分支的两个节点应显示为实心绿色

3. **分支未触发**
   - 创建一个路线图任务
   - 验证通过，审核批准，一次完成
   - 验证：两个分支的节点应显示为空心灰色

## 技术细节

### 分支检测逻辑

系统通过检查执行日志中的 `step` 字段来判断分支是否被触发：

| 分支类型 | 检测 Step | 对应节点 |
|---------|----------|---------|
| 验证分支 | `validation_edit_plan_analysis` | Plan1 节点 |
| 审核分支 | `edit_plan_analysis` | Plan2 节点 |

只要执行日志中存在对应的 `step`，就说明该分支被触发过。

### 节点状态映射

| NodeStatus | 视觉效果 | 使用场景 |
|-----------|---------|---------|
| `completed` | 实心绿色 | 节点已执行完成，或分支被触发过（任务完成后） |
| `current` | 实心绿色发光 | 当前正在执行的节点 |
| `failed` | 实心红色 | 节点执行失败 |
| `skipped` | 空心灰色 | 分支未被触发（任务完成后） |
| `pending` | 空心灰色 | 节点等待执行 |

### 视觉效果示例

**分支被触发过（修复后）：**
```
实心绿色节点 → 实心绿色节点
   Plan          Edit
```

**分支未触发：**
```
空心灰色节点 → 空心灰色节点
   Plan          Edit
```

## 影响范围

- **用户体验**: ✅ 改进 - 用户可以清楚地看到哪些分支被执行过
- **向后兼容**: ✅ 完全兼容 - `executionLogs` 参数为可选，默认为空数组
- **性能影响**: ✅ 无影响 - 只是数组查找，复杂度 O(n)

## 相关文档

- [WORKFLOW_STATE_MACHINE_DIAGRAM.md](./WORKFLOW_STATE_MACHINE_DIAGRAM.md) - 工作流状态机图
- [WORKFLOW_BRANCH_STATE_FIX_2025-12-23.md](./WORKFLOW_BRANCH_STATE_FIX_2025-12-23.md) - 分支路由修复
- [EXECUTION_LOG_REDESIGN.md](./EXECUTION_LOG_REDESIGN.md) - 执行日志设计

## 总结

这次修复通过引入执行日志检测机制，解决了分支节点视觉状态不准确的问题。修改简洁、性能高效、完全向后兼容。用户现在可以清楚地看到工作流执行历史中哪些分支被触发过，提升了系统的透明度和可理解性。

