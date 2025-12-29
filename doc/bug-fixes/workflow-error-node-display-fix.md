# Bug 修复：Workflow Progress 错误节点显示不正确

## 问题描述

**症状：** 任务详情页在生成路线图过程中，错误实际发生在 `curriculum_design` 阶段，但 Workflow Progress 中的节点错误状态却显示在 Analysis 节点上。

**影响：** 用户无法准确了解哪个步骤出错，导致调试困难。

## 根本原因

### 后端问题（主要原因）

在 `backend/app/core/error_handler.py` 中，当错误发生时，`current_step` 被硬编码为 `"failed"` 字符串：

```python
# ❌ 错误代码（第 159 行）
await repo.update_task_status(
    task_id=task_id,
    status="failed",
    current_step="failed",  # 问题：写死为 "failed"
    error_message=str(error)[:500],
)
```

这导致：
- 数据库中存储的 `current_step` 值为 `"failed"`，而不是实际出错的节点名称（如 `curriculum_design`）
- 前端无法识别 `"failed"` 这个步骤值

### 前端问题（次要原因）

在 `frontend-next/components/task/workflow-topology.tsx` 中，`getStepLocation` 函数找不到匹配的步骤时，默认返回 `analysis` 节点：

```typescript
// 第 246-247 行
// 默认返回第一个主路节点
return { stageId: 'analysis', isOnBranch: false };
```

这导致：
- 当 `current_step` 为 `"failed"` 或其他未识别的值时，错误状态总是显示在 Analysis 节点上
- 缺乏防御性日志记录，难以排查问题

### 执行流程对比

**正确流程（`workflow_brain.py`）：**
```python
# ✅ workflow_brain.py 第 355 行（正确）
await repo.update_task_status(
    task_id=ctx.task_id,
    status="failed",
    current_step=ctx.node_name,  # 保留实际节点名称
    error_message=str(error),
)
```

**错误流程（`error_handler.py`）：**
```python
# ❌ error_handler.py 第 159 行（错误）
await repo.update_task_status(
    task_id=task_id,
    status="failed",
    current_step="failed",  # 丢失了节点信息
    error_message=str(error)[:500],
)
```

## 修复方案

### 后端修复（核心）

修改 `backend/app/core/error_handler.py` 第 159 行，保留实际的节点名称：

```python
# ✅ 修复后的代码
await repo.update_task_status(
    task_id=task_id,
    status="failed",
    current_step=node_name,  # 保留实际出错的节点名称
    error_message=str(error)[:500],
)
```

**理由：**
- `current_step` 应该反映实际出错的步骤，而不是状态描述
- `status` 字段已经是 `"failed"` 了，不需要在 `current_step` 中重复
- 与 `workflow_brain.py` 的错误处理逻辑保持一致

### 前端改进（防御）

在 `frontend-next/components/task/workflow-topology.tsx` 的 `getStepLocation` 函数中添加警告日志：

```typescript
// 防御性处理：未识别的步骤
console.warn(`[WorkflowTopology] Unrecognized currentStep: "${currentStep}", falling back to first node`);

// 默认返回第一个主路节点（用于兜底）
return { stageId: 'analysis', isOnBranch: false };
```

**理由：**
- 提供调试信息，便于快速定位类似问题
- 保留默认行为作为兜底（防止页面崩溃）
- 遵循防御性编程原则

## 测试验证

### 测试场景

1. **正常错误处理（`workflow_brain` 捕获）：**
   - 在 `curriculum_design` 节点触发异常
   - 验证 Workflow Progress 显示 Design 节点为 failed 状态

2. **全局错误处理（`error_handler` 捕获）：**
   - 在 `curriculum_design` 节点触发未捕获异常
   - 验证 Workflow Progress 显示 Design 节点为 failed 状态

3. **边界情况：**
   - `current_step` 为 null：应显示 START 状态
   - `current_step` 为未知值：应显示警告日志并回退到 Analysis 节点

### 验证步骤

```bash
# 1. 启动后端服务（代码热重载）
cd backend
poetry run python -m uvicorn app.main:app --reload

# 2. 触发路线图生成任务
# 3. 在 curriculum_design 阶段人为触发错误（如修改 Agent prompt 导致解析失败）
# 4. 观察任务详情页的 Workflow Progress
# 5. 验证错误节点显示为 Design 而不是 Analysis

# 6. 检查浏览器控制台是否有 Unrecognized currentStep 警告（不应该有）
```

## 相关文件

### 修改的文件

- `backend/app/core/error_handler.py` - 修复 `current_step` 的设置逻辑
- `frontend-next/components/task/workflow-topology.tsx` - 添加防御性日志

### 相关文件（参考）

- `backend/app/core/orchestrator/workflow_brain.py` - 正确的错误处理示例
- `frontend-next/app/(app)/tasks/[taskId]/page.tsx` - 任务详情页（消费 `current_step`）

## 影响范围

### 正面影响

- ✅ 用户可以准确看到哪个步骤出错
- ✅ 调试和问题排查更容易
- ✅ 前后端错误处理逻辑统一
- ✅ 提高系统可观测性

### 潜在风险

- ⚠️ 需要确保 `node_name` 参数始终正确传递给 `error_handler`
- ⚠️ 如果有其他地方硬编码 `current_step` 值，需要一并修复

### 兼容性

- ✅ **无破坏性变更**：修复后的行为符合预期设计
- ✅ **向后兼容**：不影响现有正常流程
- ✅ **数据兼容**：不需要数据迁移（历史数据可能显示不准确，但不影响功能）

## 后续建议

### 短期改进

1. **添加单元测试：**
   - 测试 `error_handler._update_task_status_failed` 正确设置 `current_step`
   - 测试 `getStepLocation` 对各种 `currentStep` 值的处理

2. **代码审查：**
   - 检查是否有其他地方硬编码 `current_step` 值
   - 确保所有错误处理路径都保留节点名称

### 长期改进

1. **类型安全：**
   - 将 `current_step` 改为枚举类型（TypeScript + Python Literal）
   - 防止意外传入非法值

2. **前端增强：**
   - 添加节点错误详情面板，显示具体错误消息
   - 支持从错误节点快速跳转到日志

3. **监控告警：**
   - 当出现 Unrecognized currentStep 警告时，发送监控告警
   - 统计各步骤的错误率

## 修复时间线

- **发现时间：** 2025-12-30
- **修复时间：** 2025-12-30
- **状态：** ✅ 已修复，待测试验证

## 参考资料

- [Workflow Progress 组件文档](../frontend-next/docs/task-detail-refactor-guide.md)
- [工作流错误处理设计](../backend/docs/ERROR_HANDLING.md)
- [前端路线图 Mermaid 图](../../AGENT.md)

