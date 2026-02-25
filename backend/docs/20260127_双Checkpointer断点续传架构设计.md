# 双 Checkpointer 断点续传架构设计

## 📋 核心发现

### 问题：手动调用导致 Checkpointer 自动传播失效

**当前实现**：
```python
# content_generation_node.py (第 139 行)
subgraph = build_content_generation_subgraph()
result = await subgraph.ainvoke(sub_state, config)  # ❌ 手动调用
```

**关键问题**：
在这种"手动调用"模式下，LangGraph 会将子图视作节点内的**普通函数调用**，父图的自动状态管理（Checkpointer 自动传播）会失效。

### 解决方案：双 Checkpointer + 共享 Thread ID

**核心思路**：
1. **主图和子图使用相同的 `thread_id`**（逻辑关联）
2. **但 checkpointer 分别设置**（独立存储）
3. **实现效果**：
   - ✅ 主图可以断点续传（恢复到失败的节点）
   - ✅ 子图可以断点续传（只重试失败的分支）
   - ✅ 子图中已完成的节点无需再次执行

**原理**：
LangGraph Checkpointer 基于 `thread_id` 进行状态索引：
- 主图的 checkpointer 记录："我正在执行 content_generation 节点"
- 子图的 checkpointer 记录："我在并发执行 A、B、C 节点中的哪一步"
- 使用相同 `thread_id` 但不同存储空间，实现逻辑关联但状态隔离

---

## 🎯 架构设计

### 1. Checkpointer 命名空间隔离

为了避免创建多个 PostgreSQL Checkpointer 实例（连接池开销），使用**命名空间**实现逻辑隔离。

```python
# app/core/orchestrator_factory.py

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

class OrchestratorFactory:
    """编排器工厂（单例）"""
    
    def __init__(self):
        # 共享连接池的 PostgreSQL Checkpointer
        self._checkpointer: AsyncPostgresSaver | None = None
    
    async def initialize(self):
        """初始化工厂（创建共享资源）"""
        if self._checkpointer is not None:
            return
        
        # 创建共享的 Checkpointer（连接池复用）
        self._checkpointer = AsyncPostgresSaver.from_conn_string(
            settings.CHECKPOINT_DATABASE_URL
        )
        await self._checkpointer.setup()
    
    def get_parent_checkpointer(self) -> AsyncPostgresSaver:
        """
        获取父图 Checkpointer
        
        命名空间：parent_graph
        """
        if self._checkpointer is None:
            raise RuntimeError("Factory not initialized")
        
        # ✅ 使用命名空间隔离
        return self._checkpointer.with_namespace("parent_graph")
    
    def get_child_checkpointer(self) -> AsyncPostgresSaver:
        """
        获取子图 Checkpointer
        
        命名空间：child_graph
        """
        if self._checkpointer is None:
            raise RuntimeError("Factory not initialized")
        
        # ✅ 使用命名空间隔离
        return self._checkpointer.with_namespace("child_graph")
```

---

### 2. 子图构建逻辑修改

```python
# app/core/orchestrator/subgraphs/content_generation.py

def build_content_generation_subgraph(checkpointer=None):
    """
    构建外层内容生成子图
    
    Args:
        checkpointer: 子图专用的 checkpointer（独立于父图）
    
    Returns:
        编译后的子图
    """
    builder = StateGraph(ContentGenState)
    
    # 添加外层 Fan-Out 节点
    builder.add_node("outer_fan_out", outer_fan_out)
    
    # 添加单 Concept 子图包装器节点
    builder.add_node("single_concept_subgraph", single_concept_subgraph_wrapper)
    
    # 添加最终汇总节点
    builder.add_node("final_aggregation", final_aggregation)
    
    # 定义流程
    builder.add_edge(START, "outer_fan_out")
    builder.add_edge("single_concept_subgraph", "final_aggregation")
    builder.add_edge("final_aggregation", END)
    
    # ✅ 编译子图时传入独立的 checkpointer
    subgraph = builder.compile(checkpointer=checkpointer)
    
    logger.info(
        "content_generation_subgraph_built_v2",
        has_checkpointer=checkpointer is not None,
    )
    
    return subgraph
```

---

### 3. 主图节点调用逻辑修改

```python
# app/core/orchestrator/nodes/content_generation.py

async def content_generation_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    内容生成节点（纯函数 - 重构版）
    
    使用双 Checkpointer 架构：
    1. 主图 checkpointer 记录："我正在执行 content_generation 节点"
    2. 子图 checkpointer 记录："我在并发执行哪些 Concept"
    3. 共享 thread_id，实现逻辑关联
    """
    # 从 config 获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    task_id = state["task_id"]
    roadmap_id = state.get("roadmap_id")
    framework = state.get("roadmap_framework")
    user_request = state["user_request"]
    
    if not framework:
        raise ValueError("路线图框架不存在，无法生成内容")
    
    if not roadmap_id:
        raise ValueError("roadmap_id 不存在，无法生成内容")
    
    # 提取所有 Concept
    concepts = extract_concepts_from_framework(framework)
    
    logger.info(
        "content_generation_node_start_v3",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_count=len(concepts),
        architecture="dual_checkpointer",
    )
    
    # ✅ 获取子图专用的 checkpointer
    child_checkpointer = ctx.child_checkpointer
    
    # ✅ 构建子图时传入独立的 checkpointer
    subgraph = build_content_generation_subgraph(checkpointer=child_checkpointer)
    
    # 准备子图输入状态
    sub_state = {
        "roadmap_id": roadmap_id,
        "concepts": concepts,
        "user_preferences": user_request.preferences,
        "task_id": task_id,
        "concept": None,
        "concept_results": [],
    }
    
    # ✅ 关键：传入相同的 thread_id，但子图会使用自己的 checkpointer
    # - config 中的 thread_id 保持不变（与父图相同）
    # - 子图通过自己的 checkpointer 查找这个 thread_id 的进度
    result = await subgraph.ainvoke(sub_state, config)
    
    # 统计结果
    concept_results = result.get("concept_results", [])
    successful_count = len([
        r for r in concept_results
        if r.get("save_status", {}).get("metadata_saved", False)
    ])
    failed_count = len(concept_results) - successful_count
    
    logger.info(
        "content_generation_node_completed_v3",
        task_id=task_id,
        roadmap_id=roadmap_id,
        total_concepts=len(concept_results),
        successful_count=successful_count,
        failed_count=failed_count,
    )
    
    # 返回状态更新
    return {
        "roadmap_id": roadmap_id,
        "concept_results": concept_results,
        "current_step": "content_generation",
        "execution_history": [
            f"内容生成完成：成功 {successful_count}，失败 {failed_count}"
        ],
    }
```

---

### 4. RuntimeContext 修改

```python
# app/core/orchestrator/runtime_context.py

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.shared.notification_service import NotificationService
    from app.services.shared.execution_logger import ExecutionLogger
    from app.core.orchestrator.handlers import HandlerRegistry
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


@dataclass
class RuntimeContext:
    """
    运行时上下文（包含所有依赖）
    
    新增：
    - child_checkpointer: 子图专用的 checkpointer
    """
    notification_service: "NotificationService"
    execution_logger: "ExecutionLogger"
    handler_registry: "HandlerRegistry"
    child_checkpointer: "AsyncPostgresSaver"  # ✅ 新增
```

---

### 5. OrchestratorFactory 修改

```python
# app/core/orchestrator_factory.py

class OrchestratorFactory:
    def create_workflow_executor(self) -> WorkflowExecutor:
        """创建工作流执行器"""
        
        # ✅ 创建 RuntimeContext 时传入子图 checkpointer
        runtime_context = RuntimeContext(
            notification_service=self._notification_service,
            execution_logger=self._execution_logger,
            handler_registry=self._handler_registry,
            child_checkpointer=self.get_child_checkpointer(),  # ✅ 新增
        )
        
        # 创建副作用协调器
        side_effect_coordinator = get_side_effect_coordinator(
            notification_service=self._notification_service,
            execution_logger=self._execution_logger,
            state_manager=self._state_manager,
        )
        
        # 创建工作流执行器
        executor = WorkflowExecutor(
            builder=self._workflow_builder,
            state_manager=self._state_manager,
            checkpointer=self.get_parent_checkpointer(),  # ✅ 父图 checkpointer
            execution_logger=self._execution_logger,
            runtime_context=runtime_context,
            handler_registry=self._handler_registry,
            side_effect_coordinator=side_effect_coordinator,
        )
        
        return executor
```

---

## 🔄 断点续传流程

### 场景 1：主图恢复（从 Human Review 继续）

```python
# app/services/workflows/execution/workflow_execution_service.py

async def resume_workflow_after_review(
    self,
    task_id: str,
    approved: bool,
    feedback: str | None = None,
) -> dict:
    """
    人工审核后恢复工作流
    
    主图 checkpointer 记录：
    - 上次执行到 human_review 节点
    - 等待用户批准
    
    恢复时：
    - 使用相同的 thread_id（task_id）
    - 主图从 human_review 继续执行
    - 如果进入 content_generation，子图会检查自己的进度
    """
    factory = OrchestratorFactory()
    await factory.initialize()
    
    executor = factory.create_workflow_executor()
    
    # ✅ 使用相同的 thread_id 恢复
    final_state = await executor.resume_after_human_review(
        task_id=task_id,
        approved=approved,
        feedback=feedback,
    )
    
    return {"success": True, "final_state": final_state}
```

---

### 场景 2：子图恢复（只重试失败的 Concept）

```python
# 执行流程示例

# 第一次执行：生成 100 个 Concept
# - 前 50 个成功
# - 第 51 个失败（网络超时）
# - 后 49 个未执行

# 子图 checkpointer 记录：
# - thread_id: task_123
# - 已完成节点：outer_fan_out, single_concept_subgraph[0..49]
# - 待重试节点：single_concept_subgraph[50..99]

# 第二次执行（断点续传）：
# 1. 主图从 parent_checkpointer 恢复，发现需要重新执行 content_generation 节点
# 2. content_generation_node 被调用，再次执行 subgraph.ainvoke(sub_state, config)
# 3. 子图从 child_checkpointer 查找 thread_id: task_123
# 4. 子图发现前 50 个已完成，跳过
# 5. 子图从第 51 个 Concept 开始执行

logger.info(
    "subgraph_resume_detected",
    task_id=task_id,
    completed_concepts=50,
    pending_concepts=50,
    message="子图检测到已完成的节点，跳过重复执行"
)
```

---

### 场景 3：子图内部并行节点恢复

```python
# 更细粒度的恢复：单个 Concept 内的并行任务

# 假设 Concept_51 的生成包含 3 个并行任务：
# - Tutorial 生成：✅ 成功
# - Resource 推荐：❌ 失败（Tavily API 超时）
# - Quiz 生成：✅ 成功

# 子图 checkpointer 记录：
# - thread_id: task_123
# - Concept_51:
#   - generate_tutorial: completed
#   - generate_resource: failed
#   - generate_quiz: completed

# 断点续传时：
# 1. 子图恢复到 Concept_51
# 2. LangGraph 检查并行任务状态
# 3. 跳过已完成的 Tutorial 和 Quiz
# 4. 只重试失败的 Resource

logger.info(
    "parallel_task_resume",
    concept_id="Concept_51",
    completed_tasks=["tutorial", "quiz"],
    retry_tasks=["resource"],
    message="LangGraph 自动跳过已完成的并行任务"
)
```

---

## 🔧 断点续传服务重构

### 新增：检查子图进度 API

```python
# app/api/v1/endpoints/tasks/trace.py

@router.get("/{task_id}/subgraph-progress")
async def get_subgraph_progress(
    task_id: str,
    current_user: CurrentUser,
) -> ResponseModel:
    """
    查询子图执行进度
    
    返回：
    - 子图总节点数
    - 已完成节点数
    - 失败节点列表
    - 可恢复性（是否可以断点续传）
    """
    factory = OrchestratorFactory()
    await factory.initialize()
    
    # ✅ 使用子图 checkpointer 查询进度
    child_checkpointer = factory.get_child_checkpointer()
    
    config = {"configurable": {"thread_id": task_id}}
    
    # 查询子图状态
    state_snapshot = await child_checkpointer.aget(config)
    
    if not state_snapshot:
        return ResponseModel(
            success=True,
            message="子图尚未执行或已完成",
            data={
                "resumable": False,
                "completed_nodes": 0,
                "total_nodes": 0,
            }
        )
    
    # 解析子图进度
    tasks = state_snapshot.tasks or []
    completed_tasks = [t for t in tasks if t.get("status") == "completed"]
    failed_tasks = [t for t in tasks if t.get("status") == "failed"]
    
    return ResponseModel(
        success=True,
        message="子图进度查询成功",
        data={
            "resumable": len(failed_tasks) > 0,
            "completed_nodes": len(completed_tasks),
            "total_nodes": len(tasks),
            "failed_nodes": [
                {
                    "node_name": t.get("name"),
                    "error": t.get("error"),
                }
                for t in failed_tasks
            ],
        }
    )
```

---

### 重构：统一断点续传接口

```python
# app/services/workflows/execution/workflow_execution_service.py

async def resume_workflow_from_checkpoint(
    self,
    task_id: str,
    celery_task_id: str,
    checkpoint_id: str | None = None,
) -> dict:
    """
    从 checkpoint 恢复工作流（统一接口）
    
    支持两种恢复模式：
    1. 主图恢复：从失败的节点继续（如 validation 失败）
    2. 子图恢复：只重试失败的分支（如 Concept_51 失败）
    
    LangGraph 自动处理：
    - 主图 checkpointer 记录主图进度
    - 子图 checkpointer 记录子图进度
    - 共享 thread_id，实现逻辑关联
    """
    factory = OrchestratorFactory()
    await factory.initialize()
    
    executor = factory.create_workflow_executor()
    
    # 查询任务信息
    task_crud = get_task_crud()
    async with get_celery_session() as session:
        task = await task_crud.get_by_id(session, task_id)
        
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")
    
    # 更新任务状态为 processing
    async with get_celery_session() as session:
        await task_crud.update_task_status(
            session=session,
            task_id=task_id,
            status=TaskStatus.PROCESSING.value,
            current_step="resuming",
        )
    
    # 发送通知
    await notification_service.publish_progress(
        task_id=task_id,
        step="resuming",
        status=TaskStatus.PROCESSING.value,
        message="正在从断点恢复工作流...",
    )
    
    try:
        # ✅ 使用相同的 thread_id 恢复
        # LangGraph 会自动处理：
        # 1. 主图从 parent_checkpointer 恢复
        # 2. 如果进入 content_generation，子图从 child_checkpointer 恢复
        # 3. 跳过已完成的节点，只执行失败的部分
        
        config = {"configurable": {"thread_id": task_id}}
        
        if checkpoint_id:
            # 时间旅行模式：恢复到指定 checkpoint
            final_state = await executor.graph.ainvoke(
                None,
                config={**config, "checkpoint_id": checkpoint_id}
            )
        else:
            # 断点续传模式：从最后一个 checkpoint 恢复
            final_state = await executor.graph.ainvoke(None, config)
        
        logger.info(
            "workflow_resume_completed",
            task_id=task_id,
            final_step=final_state.get("current_step"),
        )
        
        return {
            "success": True,
            "status": "completed",
            "final_step": final_state.get("current_step"),
        }
        
    except Exception as e:
        logger.error(
            "workflow_resume_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        
        # 更新任务状态为失败
        await self.mark_task_failed(task_id, str(e), exception=e)
        
        raise
```

---

## 📊 实施效果对比

### 之前：无断点续传

| 场景 | 行为 |
|------|------|
| 主图失败 | ✅ 可以从失败节点恢复（已支持） |
| 子图失败（第 50 个 Concept） | ❌ 必须从第 1 个重新生成 |
| 子图内并行任务失败 | ❌ 必须重新生成整个 Concept |
| Worker 重启 | ❌ 所有进度丢失 |

### 之后：双 Checkpointer 断点续传

| 场景 | 行为 |
|------|------|
| 主图失败 | ✅ 可以从失败节点恢复 |
| 子图失败（第 50 个 Concept） | ✅ 跳过前 49 个，从第 50 个继续 |
| 子图内并行任务失败 | ✅ 跳过已完成任务，只重试失败的 |
| Worker 重启 | ✅ 从 checkpoint 恢复，无损失 |

---

## 🚀 实施步骤

### Phase 1：架构重构（2-3 天）

1. ✅ **修改 OrchestratorFactory**
   - 实现 `get_parent_checkpointer()` 和 `get_child_checkpointer()`
   - 使用命名空间隔离（避免多实例开销）

2. ✅ **修改 RuntimeContext**
   - 添加 `child_checkpointer` 字段

3. ✅ **修改子图构建逻辑**
   - `build_content_generation_subgraph` 接受 `checkpointer` 参数
   - 编译时传入子图 checkpointer

4. ✅ **修改主图节点**
   - `content_generation_node` 使用 `ctx.child_checkpointer`
   - 构建子图时传入独立的 checkpointer

### Phase 2：断点续传服务（1-2 天）

1. ✅ **新增子图进度查询 API**
   - `GET /api/v1/tasks/{task_id}/subgraph-progress`

2. ✅ **重构恢复接口**
   - 统一主图和子图的恢复逻辑
   - 自动检测恢复层级（主图 vs 子图）

### Phase 3：测试验证（1-2 天）

1. ✅ **单元测试**
   - 测试主图恢复
   - 测试子图恢复
   - 测试并行任务恢复

2. ✅ **集成测试**
   - 模拟 Worker 重启
   - 模拟网络超时
   - 验证状态一致性

---

## 🎯 预期效果

实施后，内容生成阶段将实现：

1. ✅ **细粒度断点续传**：Concept 级别 + 并行任务级别
2. ✅ **自动跳过已完成**：LangGraph 自动识别并跳过
3. ✅ **Worker 安全**：重启后无损失
4. ✅ **状态隔离**：主图和子图互不干扰
5. ✅ **性能优化**：避免重复执行

---

**创建时间**：2026-01-27  
**作者**：AI Assistant  
**状态**：设计完成，待实施
