# 人工审核拒绝后 edit_plan_analysis 显示验证分支问题分析

## 问题描述

用户在前端 Human Review 提交拒绝反馈后，工作流进入 `edit_plan_analysis` 节点时 `edit_source` 应为 `human_review`，但前端有一段时间错误地显示为**验证分支**（下方 Plan1 → Edit1）的 `edit_plan_analysis` 节点，而非**审核分支**（上方 Plan2 → Edit2）。

## 根因分析

### 1. 数据流与分支判定逻辑

前端 `getStepLocation(currentStep, editSource)` 通过 `editSource` 区分 `edit_plan_analysis` 和 `roadmap_edit` 属于哪个分支：

```typescript
// workflow-topology.tsx L265-291
// 验证分支：editSource='human_review' 时跳出，否则返回验证分支
for (const node of VALIDATION_BRANCH.nodes) {
  if (node.steps.includes(currentStep)) {
    if (editSource === 'human_review') break;  // 明确来自审核分支则跳过
    return { branchType: 'validation', ... };  // 否则视为验证分支
  }
}
// 审核分支：editSource='validation_failed' 时跳出，否则返回审核分支
for (const node of REVIEW_BRANCH.nodes) {
  if (node.steps.includes(currentStep)) {
    if (editSource === 'validation_failed') break;
    return { branchType: 'review', ... };
  }
}
```

含义：
- `editSource === 'human_review'` → 审核分支
- `editSource === 'validation_failed'` 或 **`editSource === null`** → 验证分支（默认）

因此，当 `editSource` 为 `null` 或 `validation_failed` 时，`edit_plan_analysis` 会被判为验证分支。

### 2. editSource 的前端来源

| 来源 | 时机 | 是否包含 edit_source |
|------|------|----------------------|
| **WebSocket progress** | 节点**完成**时 | ✅ `on_node_complete` 会附加 `edit_source` |
| **WebSocket progress** | 节点**开始**时 | ❌ `on_node_start` 不附带 `extra_data` |
| **loadTaskData 日志** | 初始加载/刷新 | ✅ 从 `edit_plan_analysis` / `roadmap_edit` 日志的 `details.edit_source` 提取 |

### 3. 时序与竞态

人工审核拒绝后的典型顺序：

```
1. human_review 节点完成
   → coordinator.on_node_complete(human_review, output)
   → output 含 edit_source: "human_review"
   → 发送 WS: step="human_review", data.edit_source="human_review"

2. 路由到 edit_plan_analysis，节点开始
   → coordinator.on_node_start(edit_plan_analysis)
   → 发送 WS: step="edit_plan_analysis", status="processing"
   → 无 extra_data，不包含 edit_source
```

问题出在：**若 `edit_plan_analysis` 的 on_node_start 事件先于 human_review 的 on_node_complete 到达前端**，则：

1. 前端先收到：`step=edit_plan_analysis`, 无 `edit_source`
2. `setTaskInfo`: `current_step = edit_plan_analysis`
3. `setEditSource`: 未调用（事件中无 `edit_source`）
4. `editSource` 保持：
   - `null`（若此前从未进入编辑分支）
   - `validation_failed`（若此前曾走过验证失败分支）
5. `getStepLocation("edit_plan_analysis", null | "validation_failed")` → 判定为**验证分支** ❌

### 4. editSource 为 validation_failed 的场景

流程示例：

```
structure_validation 失败
  → edit_plan_analysis (edit_source=validation_failed)
  → roadmap_edit
  → structure_validation 通过
  → human_review
```

在 `human_review` 时，`loadTaskData` 中根据日志会得到 `edit_source = "validation_failed"`，因此 `editSource` 已是 `validation_failed`。

用户拒绝后：

1. human_review 完成 → 会发 `edit_source=human_review`，但可能晚到
2. edit_plan_analysis 开始 → 只发 `step` 和 `status`，无 `edit_source`

若 2 先于 1 到达，则 `current_step = edit_plan_analysis`，`editSource = validation_failed`，仍被判为验证分支。

### 5. 后端 on_node_start 的实现

```python
# side_effect_coordinator.py L124-128
await self._send_progress_notification(
    task_id=task_id,
    step=node_name,
    status="processing",
    # 无 extra_data，因此无 edit_source
)
```

`on_node_start` 完全不传 `edit_source`，而该信息在节点开始前即可从 state 中获取（human_review 的输出已合并进 state）。

## 根因小结

| 根因 | 说明 |
|------|------|
| **1. on_node_start 缺少 edit_source** | `edit_plan_analysis` 开始时 WS 不包含 `edit_source`，前端无法提前拿到正确分支 |
| **2. 事件时序竞态** | `edit_plan_analysis` 的开始事件可能先于 human_review 的完成事件到达，此时 editSource 尚未更新 |
| **3. null/validation_failed 默认判为验证分支** | `getStepLocation` 在 editSource 为 null 或 validation_failed 时默认返回验证分支 |
| **4. 旧 editSource 未及时覆盖** | 若曾走过验证分支，`editSource` 仍为 `validation_failed`，直到收到带 `edit_source=human_review` 的事件 |

## 修复建议

### 方案 A：在 on_node_start 中传递 edit_source（推荐）

对 `edit_plan_analysis` 和 `roadmap_edit`，在节点开始时就根据 state 传递 `edit_source`：

1. 修改 `SideEffectCoordinator.on_node_start`，支持可选的 `extra_data`
2. 修改 `Executor`，在调用 `on_node_start` 时，若当前节点为 `edit_plan_analysis` 或 `roadmap_edit`，从 `final_state` 读取 `edit_source` 并传入 `extra_data`

这样即使 human_review 的完成事件稍晚到达，edit_plan_analysis 的开始事件也能带上正确的 `edit_source`。

### 方案 B：前端用 reviewBranchTriggered 做兜底

当 `currentStep` 为 `edit_plan_analysis` 且 `editSource` 为 null/validation_failed 时，若 `reviewBranchTriggered === true`，则优先判为审核分支。但 `reviewBranchTriggered` 目前是在 `roadmap_edit` 完成时设置，首次进入 edit_plan_analysis 时可能尚未为 true，效果有限，可作为辅助逻辑。

### 方案 C：前端收到“离开 human_review”时预设 edit_source

在 `handleProgress` 中，当 `prev.status === 'human_review_pending'` 且收到非 human_review 的步骤（例如 `edit_plan_analysis`）时，可暂时将 `edit_source` 设为 `human_review`，作为在未收到完整 WS 前的临时推断。

---

## 修复实施（方案 A）✅

已实施：在 `edit_plan_analysis` 和 `roadmap_edit` 的 `on_node_start` 中传递 `edit_source`。

### 修改文件

1. **backend/app/core/orchestrator/side_effect_coordinator.py**
   - `on_node_start` 增加可选参数 `extra_data: Optional[dict] = None`
   - 将 `extra_data` 传入 `_send_progress_notification`

2. **backend/app/core/orchestrator/executor.py**
   - `execute` 流程：从 `final_state` 读取 `edit_source` 传入 `on_node_start`
   - `resume_after_human_review` 流程：**直接使用 `edit_source="human_review"`**（不依赖 final_state）
   - 原因：Command(resume=...) 可能先 emit `edit_plan_analysis` 的 on_chain_start，再 emit `human_review` 的 on_chain_end，此时 final_state 仍是 checkpoint 旧值（如 `validation_failed`）
