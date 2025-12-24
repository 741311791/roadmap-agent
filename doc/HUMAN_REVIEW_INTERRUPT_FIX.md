# Human Review Interrupt 异常处理修复

## 📅 修复日期
2025-12-17

## 🐛 问题描述

### 现象
重试路线图任务时，在 Human Review 阶段失败，显示以下错误：

```
[error] workflow_brain_on_error
error="(Interrupt(value={'pause_reason': 'human_review_required'}, id='839ef0c6982d86365b0642987294d972'),)"
error_type=GraphInterrupt
node_name=human_review
```

随后出现数据库连接超时：
```
TimeoutError: [Errno 60] Operation timed out
asyncpg.exceptions.ConnectionDoesNotExistError: connection was closed in the middle of operation
```

### 根本原因

1. **LangGraph 的暂停机制被误判为错误**
   - `interrupt()` 函数会抛出 `Interrupt` 或 `GraphInterrupt` 异常来暂停工作流
   - 这是 LangGraph 的**正常暂停机制**，不是真正的错误

2. **WorkflowBrain 异常处理逻辑缺陷**
   - `WorkflowBrain.node_execution()` 上下文管理器捕获所有异常
   - 将 `GraphInterrupt` 当作错误处理，调用 `_on_error()` 
   - 任务状态被错误标记为 `failed`
   - 触发数据库事务错误和连接超时

3. **状态不一致**
   - 虽然异常被重新抛出，LangGraph 正确暂停了工作流
   - 但数据库中的任务状态已被错误修改为 `failed`
   - 前端显示任务失败，实际上工作流处于正确的暂停状态

## ✅ 修复方案

### 修改文件
`backend/app/core/orchestrator/workflow_brain.py`

### 修改内容

在 `node_execution` 上下文管理器中特殊处理 `GraphInterrupt`：

```python
@asynccontextmanager
async def node_execution(self, node_name: str, state: RoadmapState):
    from langgraph.errors import GraphInterrupt
    
    ctx = await self._before_node(node_name, state)
    try:
        yield ctx
        await self._after_node(ctx, state)
    except (GraphInterrupt, Exception) as e:
        # 检查是否是 GraphInterrupt（LangGraph 暂停机制）
        if isinstance(e, GraphInterrupt) or type(e).__name__ == "Interrupt":
            # GraphInterrupt/Interrupt 是 LangGraph 的正常暂停机制，不是错误
            # 不调用 _on_error，直接重新抛出让 LangGraph 处理
            logger.info(
                "workflow_brain_graph_interrupt",
                node_name=ctx.node_name,
                task_id=ctx.task_id,
                message="工作流暂停等待人工审核（正常流程）",
            )
            self._current_context = None
            raise
        else:
            # 真正的错误
            await self._on_error(ctx, state, e)
            raise
```

### 核心改进

1. **识别 GraphInterrupt**
   - 使用 `isinstance(e, GraphInterrupt)` 检查类型
   - 使用 `type(e).__name__ == "Interrupt"` 兼容不同版本的 LangGraph

2. **区分正常暂停和真实错误**
   - `GraphInterrupt/Interrupt`: 正常暂停机制，记录 info 日志，清理上下文，重新抛出
   - 其他异常: 真正的错误，调用 `_on_error()` 处理

3. **保持状态一致性**
   - 不将任务状态改为 `failed`
   - 保持 `human_review_pending` 状态（由 ReviewRunner 设置）
   - 避免数据库事务冲突

## 🎯 测试验证

修复后需要测试以下场景：

### 场景 1: 新建路线图（包含 Human Review）
1. 创建新路线图任务
2. 工作流执行到 Human Review 阶段
3. ✅ 任务状态应为 `human_review_pending`
4. ✅ 不应有错误日志
5. ✅ 前端显示"等待审核"状态

### 场景 2: 从 Checkpoint 重试
1. 重试一个在 Human Review 前失败的任务
2. 工作流恢复到 Human Review 阶段
3. ✅ 任务状态应为 `human_review_pending`
4. ✅ 不应标记为 `failed`
5. ✅ 可以正常进行人工审核

### 场景 3: Human Review 恢复
1. 在暂停的任务上进行审核（批准/拒绝）
2. ✅ 工作流应正常恢复
3. ✅ 状态变为 `processing`
4. ✅ 继续执行后续步骤

## 📝 相关文件

- `backend/app/core/orchestrator/workflow_brain.py` - 修复文件
- `backend/app/core/orchestrator/node_runners/review_runner.py` - Human Review 节点执行器
- `backend/app/core/orchestrator/executor.py` - 工作流执行器（包含 resume 逻辑）
- `backend/tests/e2e/test_real_workflow.py` - 已有 GraphInterrupt 测试用例

## 🔄 影响范围

- ✅ Human Review 流程正常工作
- ✅ Checkpoint 恢复机制不受影响
- ✅ 其他节点的错误处理不受影响
- ✅ 所有 LangGraph interrupt 场景都能正确处理

## 🚀 部署注意事项

1. 重启后端服务以加载新代码
2. 清除可能处于错误状态的任务（可选）
3. 测试完整的 Human Review 流程
4. 监控日志中的 `workflow_brain_graph_interrupt` 信息日志

## 📊 监控指标

修复后应观察：
- `workflow_brain_on_error` 日志中不应再出现 `GraphInterrupt`
- `workflow_brain_graph_interrupt` 日志应正常出现（info 级别）
- Human Review 任务的状态应保持为 `human_review_pending`
- 数据库连接超时错误应消失

