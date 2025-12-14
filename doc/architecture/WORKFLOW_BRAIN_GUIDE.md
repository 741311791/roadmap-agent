# WorkflowBrain 架构指南

> **版本**: 1.0  
> **最后更新**: 2024-12-13  
> **状态**: ✅ 生产就绪

---

## 📖 目录

1. [概述](#概述)
2. [核心概念](#核心概念)
3. [架构设计](#架构设计)
4. [API 参考](#api-参考)
5. [最佳实践](#最佳实践)
6. [故障排查](#故障排查)
7. [性能优化](#性能优化)
8. [迁移指南](#迁移指南)

---

## 概述

### 什么是 WorkflowBrain？

WorkflowBrain 是一个**统一的工作流协调者**，负责管理 LangGraph 工作流执行过程中的所有基础设施操作：

- ✅ **状态管理**: 维护 live_step 缓存
- ✅ **数据库操作**: 统一事务管理，确保原子性
- ✅ **日志记录**: 结构化日志和执行历史
- ✅ **通知发布**: WebSocket 进度推送
- ✅ **错误处理**: 统一的异常处理和状态回滚

### 为什么需要 WorkflowBrain？

**重构前的问题**:
```python
# 每个 Runner 都包含大量重复代码
async def run(self, state):
    # 1. 手动更新状态
    await self._update_task_status(...)
    
    # 2. 手动记录日志
    await execution_logger.log_workflow_start(...)
    
    # 3. 手动发布通知
    await notification_service.publish_progress(...)
    
    # 4. 执行 Agent
    result = await agent.execute(...)
    
    # 5. 再次记录日志
    await execution_logger.log_workflow_complete(...)
    
    # 6. 再次发布通知
    await notification_service.publish_progress(...)
    
    # 7. 手动更新数据库
    await self._save_to_database(...)
```

**重构后（使用 WorkflowBrain）**:
```python
# Runner 只关注业务逻辑
async def run(self, state):
    async with self.brain.node_execution("node_name", state):
        # 只需执行 Agent
        result = await agent.execute(...)
        
        # brain 自动处理所有基础设施操作
        return {"result": result}
```

**收益**:
- 代码减少 **50%**
- 职责清晰：Runner 只关注 Agent 执行
- 事务原子性保证
- 易于维护和扩展

---

## 核心概念

### 1. WorkflowBrain

**定义**: 工作流的"大脑"，统一协调所有基础设施操作。

**职责**:
- 在节点执行前：更新状态、记录日志、发布通知
- 在节点执行后：记录完成日志、发布完成通知
- 发生异常时：错误处理、状态更新、错误通知

**位置**: `backend/app/core/orchestrator/workflow_brain.py`

### 2. NodeContext

**定义**: 节点执行期间的上下文信息。

**包含**:
```python
@dataclass
class NodeContext:
    node_name: str           # 节点名称
    task_id: str             # 任务 ID
    roadmap_id: str | None   # 路线图 ID
    start_time: float        # 开始时间
    state_snapshot: dict     # 状态快照
```

### 3. node_execution 上下文管理器

**定义**: 自动管理节点执行生命周期的上下文管理器。

**使用示例**:
```python
async with brain.node_execution("intent_analysis", state):
    result = await agent.execute(...)
    return {"intent_analysis": result}
```

**自动处理**:
- ✅ 更新 live_step 缓存
- ✅ 更新数据库 task 状态
- ✅ 记录开始/完成日志
- ✅ 发布进度/完成通知
- ✅ 异常时错误处理和状态回滚

### 4. Unit of Work 模式

**定义**: 统一管理数据库事务边界，确保原子性。

**使用示例**:
```python
async with UnitOfWork() as uow:
    await uow.repo.update_task_status(...)
    await uow.repo.save_roadmap_metadata(...)
    # 退出时自动 commit
```

**特性**:
- ✅ 支持嵌套事务（savepoint）
- ✅ 智能回滚策略
- ✅ 事务超时处理
- ✅ 自动提交/回滚

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│                  LangGraph Workflow                 │
├─────────────────────────────────────────────────────┤
│  IntentAnalysis → CurriculumDesign → Validation ... │
└─────────────────────────────────────────────────────┘
                        ↓
        ┌───────────────────────────────┐
        │      WorkflowBrain            │  ← 统一协调者
        ├───────────────────────────────┤
        │ • 状态管理 (StateManager)      │
        │ • 数据库操作 (Repository)      │
        │ • 日志记录 (ExecutionLogger)   │
        │ • 通知发布 (NotificationService)│
        │ • 错误处理 (自动回滚)          │
        └───────────────────────────────┘
                        ↓
        ┌───────────────────────────────┐
        │         Runners               │  ← 只关注业务逻辑
        ├───────────────────────────────┤
        │ • ValidationRunner            │
        │ • EditorRunner                │
        │ • IntentAnalysisRunner        │
        │ • CurriculumDesignRunner      │
        │ • ReviewRunner                │
        │ • ContentRunner               │
        └───────────────────────────────┘
```

### 执行流程

```
1. Runner.run(state) 调用
   ↓
2. brain.node_execution("node_name", state)
   ↓
3. brain._before_node() 执行
   ├─ 更新 live_step
   ├─ 更新数据库状态
   ├─ 记录开始日志
   └─ 发布进度通知
   ↓
4. Agent 执行（Runner 的业务逻辑）
   ↓
5. brain._after_node() 执行
   ├─ 记录完成日志
   ├─ 发布完成通知
   └─ 清理上下文
   ↓
6. 返回结果给 LangGraph

如果发生异常：
   ↓
7. brain._on_error() 执行
   ├─ 更新状态为 "failed"
   ├─ 记录错误日志
   ├─ 发布错误通知
   └─ 清理上下文
```

---

## API 参考

### WorkflowBrain

#### 构造函数

```python
def __init__(
    self,
    state_manager: StateManager,
    notification_service: NotificationService,
    execution_logger: ExecutionLogger,
):
    """
    初始化 WorkflowBrain
    
    Args:
        state_manager: 状态管理器
        notification_service: 通知服务
        execution_logger: 执行日志服务
    """
```

#### node_execution()

```python
@asynccontextmanager
async def node_execution(
    self,
    node_name: str,
    state: RoadmapState,
):
    """
    节点执行上下文管理器
    
    Args:
        node_name: 节点名称（如 "intent_analysis"）
        state: 当前工作流状态
    
    Yields:
        NodeContext: 节点执行上下文
    """
```

**使用示例**:
```python
async with self.brain.node_execution("structure_validation", state):
    result = await agent.execute(input)
    return {"validation_result": result}
```

#### ensure_unique_roadmap_id()

```python
async def ensure_unique_roadmap_id(self, roadmap_id: str) -> str:
    """
    确保 roadmap_id 唯一性
    
    Args:
        roadmap_id: Agent 生成的 roadmap_id
    
    Returns:
        唯一的 roadmap_id
    """
```

#### save_intent_analysis()

```python
async def save_intent_analysis(
    self,
    task_id: str,
    intent_analysis: IntentAnalysisOutput,
    unique_roadmap_id: str,
):
    """
    保存需求分析结果（事务性操作）
    
    在同一事务中执行:
    1. 保存 IntentAnalysisMetadata
    2. 更新 task 的 roadmap_id
    """
```

#### save_roadmap_framework()

```python
async def save_roadmap_framework(
    self,
    task_id: str,
    roadmap_id: str,
    user_id: str,
    framework: RoadmapFramework,
):
    """
    保存路线图框架（事务性操作）
    
    在同一事务中执行:
    1. 保存 RoadmapMetadata
    2. 更新 task 状态
    """
```

#### save_content_results()

```python
async def save_content_results(
    self,
    task_id: str,
    roadmap_id: str,
    tutorial_refs: dict,
    resource_refs: dict,
    quiz_refs: dict,
    failed_concepts: list,
):
    """
    保存内容生成结果（批量事务操作）
    
    在同一事务中执行:
    1. 批量保存 TutorialMetadata
    2. 批量保存 ResourceRecommendationMetadata
    3. 批量保存 QuizMetadata
    4. 更新 task 最终状态
    """
```

### UnitOfWork

#### 基本用法

```python
async with UnitOfWork() as uow:
    await uow.repo.update_task_status(...)
    await uow.repo.save_roadmap_metadata(...)
    # 退出时自动 commit
```

#### 嵌套事务

```python
async with UnitOfWork() as uow:
    await uow.repo.update_task_status(...)
    
    async with uow.nested() as nested_uow:
        # 这里的操作可以独立回滚
        await nested_uow.repo.save_optional_metadata(...)
```

#### 事务超时

```python
async with UnitOfWork(timeout=30) as uow:
    # 超过 30 秒自动回滚
    await uow.repo.batch_operation(...)
```

---

## 最佳实践

### 1. Runner 开发

#### ✅ 推荐做法

```python
class MyRunner:
    def __init__(self, brain: WorkflowBrain, agent_factory: AgentFactory):
        self.brain = brain
        self.agent_factory = agent_factory
    
    async def run(self, state: RoadmapState) -> dict:
        async with self.brain.node_execution("my_node", state):
            # 1. 创建 Agent
            agent = self.agent_factory.create_my_agent()
            
            # 2. 准备输入
            input_data = self._prepare_input(state)
            
            # 3. 执行 Agent
            result = await agent.execute(input_data)
            
            # 4. 保存结果（如果需要）
            if needs_save:
                await self.brain.save_xxx(...)
            
            # 5. 返回纯结果
            return {
                "my_result": result,
                "current_step": "my_node",
                "execution_history": ["完成 xxx"],
            }
```

#### ❌ 避免做法

```python
# ❌ 不要直接操作数据库
async with AsyncSessionLocal() as session:
    await repo.update_task_status(...)

# ❌ 不要直接记录日志
await execution_logger.log_workflow_start(...)

# ❌ 不要直接发布通知
await notification_service.publish_progress(...)

# ✅ 这些都由 brain 自动处理
```

### 2. 事务管理

#### ✅ 使用 WorkflowBrain 的保存方法

```python
# brain 的保存方法已经包含事务管理
await self.brain.save_roadmap_framework(...)
```

#### ✅ 需要自定义事务时使用 UnitOfWork

```python
async with UnitOfWork() as uow:
    # 多个操作在同一事务中
    await uow.repo.operation1(...)
    await uow.repo.operation2(...)
```

### 3. 错误处理

#### ✅ 让异常自然传播

```python
async with self.brain.node_execution("my_node", state):
    result = await agent.execute(input)
    # 如果 agent.execute() 抛出异常，brain 会自动处理
    return {"result": result}
```

#### ✅ 捕获并处理业务异常

```python
async with self.brain.node_execution("my_node", state):
    try:
        result = await agent.execute(input)
    except ValidationError as e:
        # 业务异常可以捕获并转换
        logger.warning("validation_failed", error=str(e))
        return {"result": None, "validation_error": str(e)}
    
    return {"result": result}
```

---

## 故障排查

### 常见问题

#### 1. "UnitOfWork 未初始化"

**错误信息**:
```
RuntimeError: UnitOfWork 未初始化，请在 async with 块中使用
```

**原因**: 在 `async with` 块外访问 `uow.session` 或 `uow.repo`

**解决方案**:
```python
# ❌ 错误
uow = UnitOfWork()
await uow.repo.update_task_status(...)  # 未进入 async with

# ✅ 正确
async with UnitOfWork() as uow:
    await uow.repo.update_task_status(...)
```

#### 2. 事务超时

**错误信息**:
```
TransactionTimeoutError: 事务超时 (35.2s > 30s)
```

**原因**: 操作时间超过默认 30 秒超时

**解决方案**:
```python
# 增加超时时间
async with UnitOfWork(timeout=60) as uow:
    await uow.repo.long_running_operation(...)

# 或者优化操作，减少执行时间
```

#### 3. 节点执行日志缺失

**症状**: 看不到 `workflow_brain_before_node` 日志

**原因**: 可能是日志级别设置过高

**解决方案**:
```python
# 检查 structlog 配置
import structlog
logger = structlog.get_logger()
logger.setLevel("DEBUG")
```

---

## 性能优化

### 1. 批量操作

**问题**: 逐个保存元数据导致大量数据库往返

**解决方案**: 使用批量保存方法

```python
# ❌ 低效
for concept_id, tutorial in tutorial_refs.items():
    await repo.save_tutorial_metadata(...)

# ✅ 高效
await repo.save_tutorials_batch(tutorial_refs, roadmap_id)
```

### 2. 并发控制

**问题**: ContentRunner 同时处理大量概念导致资源耗尽

**解决方案**: 使用信号量限制并发

```python
max_concurrent = 5
semaphore = asyncio.Semaphore(max_concurrent)

async def process_concept(concept):
    async with semaphore:
        return await agent.execute(concept)

results = await asyncio.gather(*[process_concept(c) for c in concepts])
```

### 3. 事务范围最小化

**原则**: 事务应该尽可能短，只包含必要的数据库操作

```python
# ✅ 好：事务只包含数据库操作
async with UnitOfWork() as uow:
    await uow.repo.update_task_status(...)
    await uow.repo.save_metadata(...)

# ❌ 坏：事务包含长时间运行的 Agent 执行
async with UnitOfWork() as uow:
    result = await agent.execute(...)  # 可能需要 10 秒
    await uow.repo.save_result(result)
```

---

## 迁移指南

### 从旧 Runner 迁移到新 Runner

#### Step 1: 更新构造函数

```python
# 旧版
def __init__(self, state_manager: StateManager, agent_factory: AgentFactory):
    self.state_manager = state_manager
    self.agent_factory = agent_factory

# 新版
def __init__(self, brain: WorkflowBrain, agent_factory: AgentFactory):
    self.brain = brain
    self.agent_factory = agent_factory
```

#### Step 2: 使用 brain.node_execution

```python
# 旧版
async def run(self, state):
    await self._update_task_status(...)
    await execution_logger.log_workflow_start(...)
    
    result = await agent.execute(...)
    
    await execution_logger.log_workflow_complete(...)
    return {...}

# 新版
async def run(self, state):
    async with self.brain.node_execution("node_name", state):
        result = await agent.execute(...)
        return {...}
```

#### Step 3: 使用 brain 的保存方法

```python
# 旧版
async with AsyncSessionLocal() as session:
    repo = RoadmapRepository(session)
    await repo.save_roadmap_metadata(...)
    await session.commit()

# 新版
await self.brain.save_roadmap_framework(...)
```

#### Step 4: 删除辅助方法

```python
# 删除这些方法（brain 自动处理）
async def _update_task_status(self, ...): ...
async def _save_to_database(self, ...): ...
```

---

## 附录

### 相关文档

- [架构分析文档](WORKFLOW_BRAIN_ARCHITECTURE_ANALYSIS.md)
- [Phase 1 完成报告](../implementation/WORKFLOW_BRAIN_PHASE1_COMPLETE.md)
- [Phase 2 完成报告](../implementation/WORKFLOW_BRAIN_PHASE2_COMPLETE.md)
- [Phase 3 完成报告](../implementation/WORKFLOW_BRAIN_PHASE3_COMPLETE.md)
- [任务清单](../implementation/WORKFLOW_BRAIN_TASK_BREAKDOWN.md)

### 代码统计

| 组件 | 文件 | 行数 | 测试覆盖率 |
|------|------|------|-----------|
| WorkflowBrain | `workflow_brain.py` | ~598 行 | ~85% |
| UnitOfWork | `unit_of_work.py` | ~350 行 | ~95% |
| ValidationRunner | `validation_runner.py` | ~95 行 | N/A |
| EditorRunner | `editor_runner.py` | ~103 行 | N/A |
| ReviewRunner | `review_runner.py` | ~97 行 | N/A |
| IntentAnalysisRunner | `intent_runner.py` | ~99 行 | N/A |
| CurriculumDesignRunner | `curriculum_runner.py` | ~94 行 | N/A |
| ContentRunner | `content_runner.py` | ~295 行 | N/A |

---

**版本历史**:
- v1.0 (2024-12-13): 初始版本

*文档维护者: WorkflowBrain 开发团队*

