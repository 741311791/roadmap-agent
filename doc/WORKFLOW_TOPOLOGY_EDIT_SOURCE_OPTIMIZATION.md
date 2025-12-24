# 工作流拓扑图编辑来源字段优化

## 改造背景

之前的工作流拓扑图通过检查执行日志中的特定步骤名称（`validation_edit_plan_analysis` 和 `edit_plan_analysis`）来判断分支是否被触发。但这种方式存在问题：

- **步骤名称歧义**：两个分支都会执行 `roadmap_edit` 步骤，仅靠步骤名称无法区分
- **判断不精确**：无法准确判断 `roadmap_edit` 步骤属于哪个分支

## 改造方案

在数据库 `roadmap.public.execution_logs` 的 `details` 字段（JSON 类型）中增加 `edit_source` 键，用以标记编辑来源：

- `edit_source: "validation_failed"` - 验证分支（验证失败触发的自动修复）
- `edit_source: "human_review"` - 审核分支（人工审核拒绝触发的修改）

## 实施细节

### 后端修改

#### 1. EditPlanRunner（人工审核分支的计划分析）

**文件**: `backend/app/core/orchestrator/node_runners/edit_plan_runner.py`

在 `edit_plan_analysis` 步骤的执行日志 `details` 中添加 `edit_source: "human_review"`：

```python
await execution_logger.info(
    task_id=state["task_id"],
    category=LogCategory.AGENT,
    step="edit_plan_analysis",
    agent_name="EditPlanAnalyzerAgent",
    roadmap_id=state.get("roadmap_id"),
    message=f"🔍 Analyzed your feedback: {len(result.edit_plan.intents)} modification(s) identified",
    details={
        "log_type": "edit_plan_analyzed",
        "feedback_summary": result.edit_plan.feedback_summary,
        "intents_count": len(result.edit_plan.intents),
        "intents_preview": intents_summary[:3],
        "confidence": result.confidence,
        "preservation_requirements": result.edit_plan.preservation_requirements,
        "needs_clarification": result.needs_clarification,
        "edit_source": "human_review",  # 标记编辑来源
    },
    duration_ms=duration_ms,
)
```

#### 2. ValidationEditPlanRunner（验证分支的计划分析）

**文件**: `backend/app/core/orchestrator/node_runners/validation_edit_plan_runner.py`

在 `validation_edit_plan_analysis` 步骤的执行日志 `details` 中添加 `edit_source: "validation_failed"`：

```python
await execution_logger.info(
    task_id=state["task_id"],
    category=LogCategory.AGENT,
    step="validation_edit_plan_analysis",
    agent_name="EditPlanAnalyzerAgent",
    roadmap_id=state.get("roadmap_id"),
    message=f"🔍 Analyzed validation issues: {len(result.edit_plan.intents)} modification(s) identified",
    details={
        "log_type": "validation_edit_plan_analyzed",
        "feedback_summary": result.edit_plan.feedback_summary,
        "intents_count": len(result.edit_plan.intents),
        "intents_preview": intents_summary[:5],
        "confidence": result.confidence,
        "scope_analysis": result.edit_plan.scope_analysis,
        "preservation_requirements": result.edit_plan.preservation_requirements,
        "source": "structure_validation",
        "edit_source": "validation_failed",  # 标记编辑来源
    },
    duration_ms=duration_ms,
)
```

#### 3. EditorRunner（路线图编辑）

**文件**: `backend/app/core/orchestrator/node_runners/editor_runner.py`

在 `roadmap_edit` 步骤的执行日志 `details` 中添加 `edit_source`（从 state 中获取）：

```python
# 从状态中获取 edit_source（由上游的 EditPlanRunner 或 ValidationEditPlanRunner 设置）
edit_source = state.get("edit_source")
log_details = {
    "log_type": "edit_completed",
    "modification_count": modification_count + 1,
    "changes_summary": result.modification_summary if hasattr(result, 'modification_summary') else "Roadmap structure updated",
}
if edit_source:
    log_details["edit_source"] = edit_source

await execution_logger.info(
    task_id=state["task_id"],
    category=LogCategory.AGENT,
    step="roadmap_edit",
    agent_name="RoadmapEditorAgent",
    roadmap_id=result.framework.roadmap_id,
    message="✅ Roadmap updated based on your feedback",
    details=log_details,
    duration_ms=duration_ms,
)
```

### 前端修改

**文件**: `frontend-next/components/task/workflow-topology.tsx`

#### 1. 更新执行日志类型定义

```typescript
/** 执行日志类型（简化版） */
interface ExecutionLog {
  step: string | null;
  details?: {
    edit_source?: EditSource;
    [key: string]: any;
  };
  [key: string]: any;
}
```

#### 2. 更新分支触发判断逻辑

```typescript
// 检查分支是否被触发过（通过执行日志的 details.edit_source 判断）
// edit_source === 'validation_failed': 验证分支
// edit_source === 'human_review': 审核分支
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

## 数据流转

### 验证分支流程

1. **ValidationRunner** 验证失败
2. **ValidationEditPlanRunner** 执行 `validation_edit_plan_analysis`
   - 写入日志：`details.edit_source = "validation_failed"`
   - 设置状态：`state.edit_source = "validation_failed"`
3. **EditorRunner** 执行 `roadmap_edit`
   - 从 state 获取 `edit_source`
   - 写入日志：`details.edit_source = "validation_failed"`
4. 返回 **ValidationRunner** 重新验证

### 审核分支流程

1. **ReviewRunner** 等待人工审核
2. 用户拒绝（提供反馈）
3. **EditPlanRunner** 执行 `edit_plan_analysis`
   - 写入日志：`details.edit_source = "human_review"`
   - 设置状态：`state.edit_source = "human_review"`
4. **EditorRunner** 执行 `roadmap_edit`
   - 从 state 获取 `edit_source`
   - 写入日志：`details.edit_source = "human_review"`
5. 返回 **ReviewRunner** 等待重新审核

## 优势

### 改造前

- ❌ 仅靠步骤名称判断，无法区分 `roadmap_edit` 属于哪个分支
- ❌ 判断逻辑依赖步骤名称的唯一性
- ❌ 扩展性差，增加新分支需要修改多处代码

### 改造后

- ✅ 通过 `details.edit_source` 精确判断分支归属
- ✅ 对于共享步骤（如 `roadmap_edit`）也能准确识别
- ✅ 扩展性强，新增分支只需定义新的 `edit_source` 值
- ✅ 数据库中永久记录编辑来源，便于追溯和分析

## 测试建议

### 验证分支测试

1. 创建一个包含逻辑错误的路线图（例如：循环依赖）
2. 验证失败后，检查执行日志中 `validation_edit_plan_analysis` 和 `roadmap_edit` 步骤的 `details.edit_source` 是否为 `"validation_failed"`
3. 检查前端拓扑图是否正确高亮显示验证分支（底部分支）

### 审核分支测试

1. 创建一个路线图并通过验证
2. 在人工审核阶段点击 "Reject" 并提供反馈
3. 检查执行日志中 `edit_plan_analysis` 和 `roadmap_edit` 步骤的 `details.edit_source` 是否为 `"human_review"`
4. 检查前端拓扑图是否正确高亮显示审核分支（顶部分支）

### 混合场景测试

1. 触发验证分支修复 → 通过验证 → 审核拒绝 → 触发审核分支修改
2. 检查执行日志中是否同时存在两种 `edit_source` 的记录
3. 检查前端拓扑图是否能正确区分和显示两个分支的状态

## 数据库查询示例

查询某个任务的所有编辑来源记录：

```sql
SELECT 
    id,
    task_id,
    step,
    details->>'edit_source' as edit_source,
    message,
    created_at
FROM execution_logs
WHERE task_id = 'your-task-id'
    AND step IN ('edit_plan_analysis', 'validation_edit_plan_analysis', 'roadmap_edit')
    AND details->>'edit_source' IS NOT NULL
ORDER BY created_at;
```

统计各分支的使用频率：

```sql
SELECT 
    details->>'edit_source' as edit_source,
    COUNT(*) as count
FROM execution_logs
WHERE step = 'roadmap_edit'
    AND details->>'edit_source' IS NOT NULL
GROUP BY details->>'edit_source';
```

## 兼容性说明

- **向后兼容**：旧的执行日志没有 `edit_source` 字段，前端判断逻辑使用可选链操作符 `?.`，不会报错
- **数据库无需迁移**：`details` 是 JSON 字段，动态添加键无需修改表结构
- **渐进式生效**：新生成的日志会包含 `edit_source`，旧数据不受影响

## 总结

本次改造通过在执行日志的 `details` 字段中添加 `edit_source` 标记，解决了工作流拓扑图中分支节点归属判断的问题。改造遵循以下原则：

1. **最小侵入**：只修改必要的日志记录点
2. **数据驱动**：通过数据字段而非代码逻辑区分分支
3. **向后兼容**：不影响现有数据和逻辑
4. **可追溯**：所有编辑操作的来源都永久记录在数据库中

---

**改造日期**: 2025-12-23  
**相关文件**: 
- `backend/app/core/orchestrator/node_runners/edit_plan_runner.py`
- `backend/app/core/orchestrator/node_runners/validation_edit_plan_runner.py`
- `backend/app/core/orchestrator/node_runners/editor_runner.py`
- `frontend-next/components/task/workflow-topology.tsx`

