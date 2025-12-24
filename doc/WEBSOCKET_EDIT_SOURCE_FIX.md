# WebSocket `edit_source` 字段传递修复

**修复日期**: 2025-12-23  
**问题**: 后端未将 `edit_source` 字段传递到前端 WebSocket 消息  
**影响**: 前端无法区分验证分支和审核分支

---

## 🔧 已应用的修复

### 文件: `backend/app/core/orchestrator/workflow_brain.py`

#### 修复 1: `_before_node()` 方法

**位置**: Line 248-267

**修改内容**: 在发布进度通知时，从 state 中提取 `edit_source` 并通过 `extra_data` 传递。

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

#### 修复 2: `_after_node()` 方法

**位置**: Line 289-310

**修改内容**: 在发布完成通知时，同样传递 `edit_source`。

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

#### 修复 3: `_on_error()` 方法

**位置**: Line 359-380

**修改内容**: 在发布错误通知时，也传递 `edit_source`。

```python
# 3. 发布错误通知
# 从 state 中提取 edit_source（用于前端区分分支）
extra_data = {"error": str(error)}
edit_source = state.get("edit_source")
if edit_source:
    extra_data["edit_source"] = edit_source

await self.notification_service.publish_progress(
    task_id=ctx.task_id,
    step=ctx.node_name,
    status="failed",
    message=f"执行失败: {ctx.node_name}",
    extra_data=extra_data,
)
```

---

## ✅ 验证

### Lint 检查

```bash
✅ No linter errors found.
```

### 代码逻辑验证

1. **状态来源**: ✅ `edit_source` 由 `ValidationEditPlanRunner` 和 `EditPlanRunner` 设置
2. **传递路径**: ✅ `state` → `WorkflowBrain` → `NotificationService` → `WebSocket` → 前端
3. **覆盖范围**: ✅ 所有三种状态（processing, completed, failed）都传递了 `edit_source`

---

## 📋 测试计划

### 测试用例 1: 验证分支（Validation Failed）

**步骤**:
1. 创建一个会验证失败的路线图（例如：循环依赖）
2. 打开浏览器开发者工具 → Network → WS 标签
3. 观察 WebSocket 消息

**预期结果**:

```json
// validation_edit_plan_analysis 步骤
{
  "type": "progress",
  "task_id": "xxx",
  "step": "validation_edit_plan_analysis",
  "status": "processing",
  "data": {
    "edit_source": "validation_failed"  // ✅ 应包含此字段
  }
}

// roadmap_edit 步骤
{
  "type": "progress",
  "task_id": "xxx",
  "step": "roadmap_edit",
  "status": "processing",
  "data": {
    "edit_source": "validation_failed"  // ✅ 应包含此字段
  }
}
```

**前端行为**:
- WorkflowTopology 组件应高亮显示验证分支（Validate → Plan1 → Edit1）
- 分支节点应使用 amber 配色（验证分支）
- 底部应显示 "↩ Validate" 标签

### 测试用例 2: 审核分支（Human Review Rejected）

**步骤**:
1. 创建路线图并等待 Human Review
2. 在审核面板中点击 "Change" 按钮
3. 输入反馈（例如：请增加更多实战项目）
4. 点击 "Submit"
5. 观察 WebSocket 消息

**预期结果**:

```json
// edit_plan_analysis 步骤
{
  "type": "progress",
  "task_id": "xxx",
  "step": "edit_plan_analysis",
  "status": "processing",
  "data": {
    "edit_source": "human_review"  // ✅ 应包含此字段
  }
}

// roadmap_edit 步骤
{
  "type": "progress",
  "task_id": "xxx",
  "step": "roadmap_edit",
  "status": "processing",
  "data": {
    "edit_source": "human_review"  // ✅ 应包含此字段
  }
}
```

**前端行为**:
- WorkflowTopology 组件应高亮显示审核分支（Review → Plan2 → Edit2）
- 分支节点应使用 blue 配色（审核分支）
- 底部应显示 "↩ Review" 标签

### 测试用例 3: 循环多次修改

**场景**: 验证失败 → 自动修复 → 再次验证失败 → 再次修复

**步骤**:
1. 创建一个复杂的路线图请求，可能需要多次修复
2. 观察是否每次进入验证分支时都正确传递 `edit_source: "validation_failed"`

**预期结果**:
- 每次进入验证分支，WebSocket 消息都包含 `edit_source: "validation_failed"`
- 前端拓扑图持续高亮验证分支，直到验证通过

### 测试用例 4: 页面刷新后状态恢复（已知限制）

**步骤**:
1. 在修改过程中（roadmap_edit）刷新页面
2. 观察前端是否正确恢复分支状态

**当前行为**:
- ❌ `edit_source` 未保存到数据库，刷新后丢失
- 前端可能无法正确识别当前分支

**解决方案**（未来优化）:
- **方案 A**: 在 `Task` 模型中添加 `edit_source` 字段
- **方案 B**: 从最近的执行日志中推断 `edit_source`

---

## 🎯 预期效果

### 修复前

```
前端行为：
- ❌ 无法区分当前处于验证分支还是审核分支
- ❌ roadmap_edit 节点显示不明确（不知道是修复验证问题还是应用用户反馈）
- ❌ 用户困惑："系统在做什么？"
```

### 修复后

```
前端行为：
- ✅ 清晰显示当前分支（验证分支 vs 审核分支）
- ✅ roadmap_edit 节点根据 edit_source 显示不同的上下文
- ✅ 用户明确："系统正在根据验证结果自动修复" 或 "系统正在应用我的反馈"
- ✅ 分支节点使用不同配色（amber = 验证，blue = 审核）
```

---

## 📊 影响评估

### 性能影响

- ✅ **无影响**: 仅在 `extra_data` 中添加一个字段（~20 bytes）
- ✅ **无额外数据库查询**
- ✅ **无额外网络请求**

### 向后兼容性

- ✅ **完全向后兼容**: 前端已经定义了 `edit_source` 为可选字段
- ✅ **降级优雅**: 如果 `edit_source` 缺失，前端会根据 `currentStep` 推断（可能不准确）

### 测试覆盖

- ✅ **单元测试**: 无需新增（逻辑简单，仅读取状态）
- ⚠️ **集成测试**: 建议添加 WebSocket 消息断言
- ⚠️ **端到端测试**: 建议手动测试（见上方测试计划）

---

## 📝 相关文档

- [WebSocket 格式一致性检查报告](./WEBSOCKET_FORMAT_CONSISTENCY_CHECK.md)
- [前端工作流重构总结](./FRONTEND_WORKFLOW_REFACTOR_SUMMARY.md)
- [工作流路由更新 2025-12-22](./WORKFLOW_ROUTING_UPDATE_2025-12-22.md)

---

## ✅ 检查清单

- [x] 修改 `WorkflowBrain._before_node()` 传递 `edit_source`
- [x] 修改 `WorkflowBrain._after_node()` 传递 `edit_source`
- [x] 修改 `WorkflowBrain._on_error()` 传递 `edit_source`
- [x] Lint 检查通过
- [ ] 集成测试验证（验证分支）
- [ ] 集成测试验证（审核分支）
- [ ] 端到端测试（浏览器）
- [ ] 生产环境部署验证

---

**修复完成时间**: 2025-12-23  
**修复作者**: AI Assistant  
**审核状态**: 待人工验证

