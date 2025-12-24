# Review 后状态同步问题修复报告
**日期**: 2025-12-23  
**任务**: 修复 Human Review 之后前端节点状态跳转错误

---

## 问题描述

用户在前端看到 Review 之后节点状态跳转错误，表现为前端WorkflowTopology显示的节点状态与实际工作流进度不一致。

---

## 根本原因分析

### 问题1: `update_task_after_review` 设置了前端未定义的步骤

**位置**: `backend/app/core/orchestrator/workflow_brain.py:1050`

**问题代码**:
```python
await repo.update_task_status(
    task_id=task_id,
    status="processing",
    current_step="human_review_completed",  # ⚠️ 前端未定义此步骤
)
```

**影响**:
1. 后端设置 `current_step="human_review_completed"`
2. WebSocket 推送此步骤给前端
3. 前端 `WorkflowTopology` 中没有定义 `human_review_completed` 步骤
4. `getStepLocation()` 函数无法识别，返回默认的 `analysis` 节点
5. 导致节点状态跳转混乱

**前端步骤定义**:
```typescript
const MAIN_STAGES = [
  { id: 'analysis', steps: ['init', 'queued', 'starting', 'intent_analysis'] },
  { id: 'design', steps: ['curriculum_design', 'framework_generation'] },
  { id: 'validate', steps: ['structure_validation'] },
  { id: 'review', steps: ['human_review', 'human_review_pending'] }, // ❌ 没有 human_review_completed
  { id: 'content', steps: ['content_generation', ...] },
];
```

### 问题2: `edit_source` 标记未在 ReviewRunner 中设置

**位置**: `backend/app/core/orchestrator/node_runners/review_runner.py:274-279`

**问题**:
- ReviewRunner 在用户拒绝时，返回了 `user_feedback` 和 `human_approved=False`
- 但没有返回 `edit_source="human_review"` 标记
- 导致前端无法正确区分是验证分支还是审核分支的 `roadmap_edit`

**前端依赖**:
```typescript
// frontend-next/components/task/workflow-topology.tsx:217-220
if (currentStep === 'roadmap_edit') {
  if (editSource === 'human_review') {
    return { stageId: node.id, isOnBranch: true, branchType: 'review', branchNodeIndex: i };
  }
  // 如果没有 editSource，无法判断属于哪个分支
}
```

---

## 修复方案

### 修复1: 移除 `update_task_after_review` 中的 `current_step` 设置

**文件**: `backend/app/core/orchestrator/workflow_brain.py`

**修改前**:
```python
async def update_task_after_review(self, task_id: str):
    """人工审核后将任务状态恢复为 "processing" """
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        await repo.update_task_status(
            task_id=task_id,
            status="processing",
            current_step="human_review_completed",  # ❌ 问题
        )
        await session.commit()
```

**修改后**:
```python
async def update_task_after_review(self, task_id: str):
    """
    人工审核后将任务状态恢复为 "processing"
    
    注意：
    - 不设置 current_step，因为下一个节点的 _before_node 会自动设置
    - 避免推送前端未定义的步骤导致状态混乱
    """
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        await repo.update_task_status(
            task_id=task_id,
            status="processing",
            # 不更新 current_step，让下一个节点的 _before_node 自动设置
        )
        await session.commit()
```

**设计原理**:
1. 每个节点执行前，`WorkflowBrain._before_node()` 会自动设置 `current_step`
2. 同时更新数据库、WebSocket推送、日志记录
3. 无需在 `update_task_after_review` 中重复设置
4. 避免引入前端未定义的中间步骤

### 修复2: 在 ReviewRunner 中添加 `edit_source` 标记

**文件**: `backend/app/core/orchestrator/node_runners/review_runner.py`

**修改前**:
```python
state_update = {
    "human_approved": approved,
    "user_feedback": feedback if not approved and feedback else None,
    "current_step": "human_review",
    "execution_history": [f"人工审核完成 - {'批准' if approved else '拒绝'}"],
}
```

**修改后**:
```python
state_update = {
    "human_approved": approved,
    "user_feedback": feedback if not approved and feedback else None,
    "current_step": "human_review",
    "execution_history": [f"人工审核完成 - {'批准' if approved else '拒绝'}"],
}

# 当用户拒绝时，添加 edit_source 标记
if not approved:
    state_update["edit_source"] = "human_review"
```

**作用**:
- 前端 `WorkflowTopology` 使用 `editSource` 区分 `roadmap_edit` 属于哪个分支
- 确保审核拒绝触发的编辑在上方分支显示
- 与验证失败触发的编辑（下方分支）区分开

---

## 状态流转时序图

### 修复前（错误流程）

```
用户点击 Reject
    ↓
ReviewRunner.run() 执行
    ↓
update_task_after_review()
    ├─ 设置 status="processing"
    └─ 设置 current_step="human_review_completed" ❌
    ↓
WebSocket 推送 { step: "human_review_completed" }
    ↓
前端 getStepLocation("human_review_completed")
    └─ 找不到定义，返回 { stageId: 'analysis' } ❌
    ↓
前端显示错误的节点状态 ❌
```

### 修复后（正确流程）

```
用户点击 Reject
    ↓
ReviewRunner.run() 执行
    ├─ 返回 state_update: {
    │    human_approved: false,
    │    user_feedback: "...",
    │    current_step: "human_review",
    │    edit_source: "human_review"  ✅ 新增
    │  }
    └─ update_task_after_review()
         └─ 仅设置 status="processing" ✅
    ↓
LangGraph 路由到下一节点: edit_plan_analysis
    ↓
EditPlanRunner._before_node() 执行
    ├─ 设置 current_step="edit_plan_analysis" ✅
    └─ WebSocket 推送 { 
         step: "edit_plan_analysis", 
         edit_source: "human_review" ✅
       }
    ↓
前端 getStepLocation("edit_plan_analysis", "human_review")
    └─ 返回 { stageId: 'plan2', branchType: 'review' } ✅
    ↓
前端正确显示在审核分支（上方）✅
```

---

## 工作流路由流程

### 用户批准（Approved）

```
human_review
    ↓
route_after_human_review() 返回 "approved"
    ↓
tutorial_generation (ContentRunner)
    ↓
END
```

### 用户拒绝（Rejected）

```
human_review
    ├─ 设置 edit_source="human_review"
    └─ 返回 user_feedback
    ↓
route_after_human_review() 返回 "modify"
    ↓
edit_plan_analysis (EditPlanRunner)
    ├─ 解析用户反馈
    └─ 生成 EditPlan
    ↓
roadmap_edit (EditorRunner)
    └─ 根据 EditPlan 修改路线图
    ↓
route_after_edit() 检查 edit_source
    ├─ 如果 edit_source="human_review" → 返回 human_review
    └─ 如果 edit_source="validation_failed" → 返回 structure_validation
    ↓
human_review (再次审核)
```

---

## 前端步骤映射完整定义

### 主路节点

| 节点 ID   | 步骤列表 |
|-----------|---------|
| analysis  | `init`, `queued`, `starting`, `intent_analysis` |
| design    | `curriculum_design`, `framework_generation` |
| validate  | `structure_validation` |
| review    | `human_review`, `human_review_pending` |
| content   | `content_generation`, `tutorial_generation`, `resource_recommendation`, `quiz_generation` |

### 验证分支（下方）

| 节点 ID | 步骤列表 | edit_source |
|---------|---------|-------------|
| plan1   | `validation_edit_plan_analysis` | `validation_failed` |
| edit1   | `roadmap_edit` | `validation_failed` |

### 审核分支（上方）

| 节点 ID | 步骤列表 | edit_source |
|---------|---------|-------------|
| plan2   | `edit_plan_analysis` | `human_review` |
| edit2   | `roadmap_edit` | `human_review` |

---

## 验证要点

### 后端验证

1. **WebSocket 消息流**
   - [ ] Review 拒绝后，下一条消息应该是 `edit_plan_analysis`，而不是 `human_review_completed`
   - [ ] WebSocket 消息应包含 `edit_source: "human_review"`

2. **数据库状态**
   ```sql
   SELECT task_id, status, current_step, updated_at 
   FROM roadmap_generations 
   WHERE task_id = 'xxx'
   ORDER BY updated_at DESC;
   ```
   - [ ] 不应该出现 `current_step="human_review_completed"`

3. **日志检查**
   ```bash
   # 查找是否还有 human_review_completed
   grep "human_review_completed" logs/*.log
   ```

### 前端验证

1. **节点状态**
   - [ ] Review 拒绝后，上方审核分支的 Plan2 和 Edit2 节点应该变为 `current` 状态
   - [ ] 主路的 Review 节点应保持 `current` 状态（因为会回到这里）

2. **edit_source 传递**
   - [ ] 检查 WebSocket 接收到的消息是否包含 `edit_source`
   - [ ] 检查 `WorkflowTopology` 组件的 `editSource` prop 是否正确传递

3. **状态跳转顺序**
   ```
   human_review (waiting)
       ↓ 用户点击 Reject
   human_review (current) 
       ↓
   edit_plan_analysis (current) ← 审核分支的 Plan2
       ↓
   roadmap_edit (current) ← 审核分支的 Edit2
       ↓
   human_review (current) ← 回到 Review 节点
   ```

---

## 相关文件

### 后端
- `backend/app/core/orchestrator/workflow_brain.py` - 修复 `update_task_after_review`
- `backend/app/core/orchestrator/node_runners/review_runner.py` - 添加 `edit_source`
- `backend/app/core/orchestrator/routers.py` - 路由逻辑（无需修改）
- `backend/app/core/orchestrator/builder.py` - 工作流图定义（无需修改）

### 前端
- `frontend-next/components/task/workflow-topology.tsx` - 节点状态渲染
- `frontend-next/components/task/core-display-area.tsx` - 前面已修复（添加 `edit_plan` 步骤）

---

## 其他发现的问题（已修复）

### `edit_plan` 步骤缺失

在修复主要问题的同时，发现前端 `CoreDisplayArea` 组件的步骤白名单中缺少 `edit_plan` 和 `validation_edit_plan`，已在 `EDIT_PLAN_BUGS_FIX_2025-12-23.md` 中记录并修复。

---

## 总结

本次修复解决了 Human Review 后状态同步的核心问题：

1. ✅ **移除了前端未定义的中间步骤** (`human_review_completed`)
2. ✅ **添加了分支区分标记** (`edit_source="human_review"`)
3. ✅ **确保了 WebSocket 推送的步骤与前端定义一致**
4. ✅ **保证了状态流转的清晰性和可预测性**

修复后，前端可以正确识别和显示 Review 后的工作流状态，审核分支和验证分支的节点能够准确区分和渲染。


