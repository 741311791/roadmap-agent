# 工作流分支 edit_source 提取修复

## 问题描述

在任务详情页面 (`/tasks/[taskId]`)，工作流拓扑图 (`WorkflowTopology`) 无法正确显示分支节点的触发状态（如验证分支和审核分支）。

### 症状

- 验证分支和审核分支在被触发后，前端拓扑图中仍显示为未触发状态
- 分支节点没有显示为"已完成"（实心颜色），而是显示为"跳过"（空心颜色）

## 问题根因

### 后端数据

后端正确记录了 `edit_source` 字段在执行日志中：

```json
{
  "step": "roadmap_edit",
  "details": {
    "log_type": "edit_completed",
    "edit_source": "human_review",
    ...
  }
}
```

```json
{
  "step": "edit_plan_analysis",
  "details": {
    "log_type": "edit_plan_analyzed",
    "edit_source": "human_review",
    ...
  }
}
```

### 前端问题

前端存在两个 `edit_source` 数据来源：

1. **WebSocket 实时推送**：后端在节点完成时通过 WebSocket 发送 `edit_source`
2. **执行日志 API**：前端加载任务详情时获取包含 `details.edit_source` 的完整执行日志

**问题点**：

- 前端只监听 WebSocket 事件来更新 `editSource` state
- 当用户刷新页面或重新进入任务详情页时，`editSource` 会重置为 `null`
- 虽然前端已经通过 API 获取了完整的执行日志（包含 `details.edit_source`），但没有从中提取 `edit_source`

```typescript
// 之前的代码：只从 WebSocket 更新 editSource
if (event.data?.edit_source) {
  setEditSource(event.data.edit_source);
}
```

## 解决方案

### 修复内容

在 `frontend-next/app/(app)/tasks/[taskId]/page.tsx` 的 `loadTaskData` 函数中，添加从执行日志提取 `edit_source` 的逻辑：

```typescript
// 从执行日志中提取最新的 edit_source（用于区分工作流分支）
// 优先从 roadmap_edit 或 edit_plan_analysis 日志中读取 edit_source
const latestEditSource = allLogs
  .filter(log => 
    (log.step === 'roadmap_edit' || log.step === 'edit_plan_analysis') && 
    log.details?.edit_source
  )
  .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
  [0]?.details?.edit_source || null;

if (latestEditSource) {
  setEditSource(latestEditSource);
  console.log('[TaskDetail] Extracted edit_source from logs:', latestEditSource);
}
```

### 工作原理

1. **筛选相关日志**：从所有执行日志中筛选出 `step` 为 `roadmap_edit` 或 `edit_plan_analysis` 且包含 `details.edit_source` 的日志
2. **按时间排序**：按 `created_at` 降序排序，确保获取最新的 `edit_source`
3. **提取并设置**：取第一条日志的 `details.edit_source` 并更新 state

### 数据流

```
页面加载/刷新
    ↓
获取执行日志 (API: /trace/{taskId}/logs)
    ↓
提取 edit_source 从日志中
    ↓
设置 editSource state
    ↓
传递给 WorkflowTopology 组件
    ↓
正确显示分支触发状态
```

## 验证方式

### 测试步骤

1. 打开任务详情页面：`/tasks/87ebd107-9517-4515-959f-9bb453ecb7ca`
2. 查看 Console 日志，应该看到：
   ```
   [TaskDetail] Extracted edit_source from logs: human_review
   ```
3. 工作流拓扑图应该正确显示：
   - 审核分支（Review 上方）的节点显示为已完成（实心颜色）
   - 验证分支（Validate 下方）根据是否被触发显示相应状态

### API 验证

```bash
curl -s "http://localhost:8000/api/v1/trace/87ebd107-9517-4515-959f-9bb453ecb7ca/logs?limit=2000" | \
jq '.logs[] | select((.step == "roadmap_edit" or .step == "edit_plan_analysis") and .details.edit_source != null) | {step, edit_source: .details.edit_source, created_at}'
```

**期望输出**：

```json
{
  "step": "roadmap_edit",
  "edit_source": "human_review",
  "created_at": "2025-12-24T09:18:15.322023"
}
{
  "step": "edit_plan_analysis",
  "edit_source": "human_review",
  "created_at": "2025-12-24T09:15:08.214588"
}
```

## 影响范围

### 修改文件

- `frontend-next/app/(app)/tasks/[taskId]/page.tsx`（新增 10 行代码）

### 受益功能

- **工作流拓扑图**：正确显示验证分支和审核分支的触发状态
- **页面刷新**：刷新后状态不丢失
- **直接访问**：直接访问任务详情 URL 也能正确显示状态

## 技术要点

### edit_source 类型

```typescript
type EditSource = 'validation_failed' | 'human_review' | null;
```

- `'validation_failed'`：验证失败触发的自动修复分支
- `'human_review'`：人工审核拒绝触发的修改分支
- `null`：未触发任何分支

### WorkflowTopology 组件逻辑

组件通过 `executionLogs` 和 `editSource` 两个 prop 来判断分支状态：

```typescript
// 检查分支是否被触发过
const validationBranchTriggered = executionLogs.some(
  log => 
    (log.step === 'validation_edit_plan_analysis' || log.step === 'roadmap_edit') &&
    log.details?.edit_source === 'validation_failed'
);

const reviewBranchTriggered = executionLogs.some(
  log => 
    (log.step === 'edit_plan_analysis' || log.step === 'roadmap_edit') &&
    log.details?.edit_source === 'human_review'
);
```

- `executionLogs`：判断分支是否被触发过（历史状态）
- `editSource`：判断当前正在执行的是哪个分支（当前状态）

## 相关文档

- 工作流状态机图：`WORKFLOW_STATE_MACHINE_DIAGRAM.md`
- 工作流拓扑编辑来源优化：`WORKFLOW_TOPOLOGY_EDIT_SOURCE_OPTIMIZATION.md`
- WebSocket 编辑来源修复：`WEBSOCKET_EDIT_SOURCE_FIX.md`

## 总结

此修复确保了前端能够从执行日志中正确提取 `edit_source` 信息，解决了页面刷新或直接访问时分支状态丢失的问题。这样一来，无论用户通过何种方式进入任务详情页，都能看到正确的工作流分支状态。

