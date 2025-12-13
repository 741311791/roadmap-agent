# Workflow Brain 架构分析文档

> **文档类型**: 架构分析 & 重构提案  
> **创建日期**: 2024-12-13  
> **状态**: 待评审

---

## 1. Executive Summary

本文档分析了当前 Orchestrator 架构中 Runner 组件直接操作数据库的问题，并提出引入 **WorkflowBrain（工作流大脑）** 作为统一协调者的重构方案。

**核心问题**：每个 Runner 都在内部创建独立的数据库会话进行状态更新，导致事务原子性无法保证、代码重复、错误恢复困难。

**推荐方案**：引入 WorkflowBrain 组件，统一管理全局状态、checkpoint 更新、日志记录和数据库操作，Runner 仅负责执行 Agent 并返回纯结果。

---

## 2. 当前架构分析

### 2.1 组件结构

```
┌─────────────────────────────────────────────────────────────────┐
│                        WorkflowExecutor                         │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                    LangGraph Graph                       │  │
│    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │  │
│    │  │ Intent  │→ │Curricul │→ │Validat- │→ │   Content   │ │  │
│    │  │ Runner  │  │ Runner  │  │  Runner │  │   Runner    │ │  │
│    │  └────┬────┘  └────┬────┘  └────┬────┘  └──────┬──────┘ │  │
│    └───────│────────────│────────────│──────────────│────────┘  │
│            │            │            │              │           │
│            ▼            ▼            ▼              ▼           │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                   直接数据库操作                          │  │
│    │   每个 Runner 都有: _update_task_status()               │  │
│    │   每个操作使用独立的 AsyncSessionLocal()                 │  │
│    └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │    PostgreSQL   │
                    │  (多个独立事务)  │
                    └─────────────────┘
```

### 2.2 各 Runner 数据库操作统计

| Runner | 数据库操作 | 独立 Session 数 | 涉及表 |
|--------|-----------|----------------|--------|
| IntentAnalysisRunner | `_ensure_unique_roadmap_id()`, `_update_database()` | 2 | RoadmapTask, RoadmapMetadata |
| CurriculumDesignRunner | `_update_task_status()`, `_save_roadmap_framework()` | 2 | RoadmapTask, RoadmapMetadata |
| ValidationRunner | `_update_task_status()` | 1 | RoadmapTask |
| EditorRunner | `_update_task_status()`, `_update_roadmap_framework()` | 2 | RoadmapTask, RoadmapMetadata |
| ReviewRunner | 直接在 run() 中操作 | 2 | RoadmapTask |
| ContentRunner | `_update_task_status()`, 最终状态更新 | 2+ | RoadmapTask |

### 2.3 代码证据

#### IntentAnalysisRunner 中的典型模式

```python
# 文件: backend/app/core/orchestrator/node_runners/intent_runner.py

async def _update_database(self, task_id: str, roadmap_id: str):
    """更新数据库记录"""
    async with AsyncSessionLocal() as session:  # ← 独立 session
        repo = RoadmapRepository(session)
        await repo.update_task_status(
            task_id=task_id,
            status="processing",
            current_step="intent_analysis",
            roadmap_id=roadmap_id,
        )
        await session.commit()  # ← 独立提交
```

#### CurriculumDesignRunner 中的重复模式

```python
# 文件: backend/app/core/orchestrator/node_runners/curriculum_runner.py

async def _update_task_status(self, task_id: str, current_step: str, roadmap_id: str | None):
    """更新任务状态到数据库"""
    async with AsyncSessionLocal() as session:  # ← 又一个独立 session
        repo = RoadmapRepository(session)
        await repo.update_task_status(
            task_id=task_id,
            status="processing",
            current_step=current_step,
            roadmap_id=roadmap_id,
        )
        await session.commit()  # ← 又一个独立提交
```

#### ContentRunner 中的复杂操作

```python
# 文件: backend/app/core/orchestrator/node_runners/content_runner.py

async def run(self, state: RoadmapState) -> dict:
    # 开始时更新状态
    await self._update_task_status(task_id, "content_generation", roadmap_id)  # ← 事务1
    
    # ... 执行内容生成 ...
    
    # 结束时再次更新状态
    async with AsyncSessionLocal() as session:  # ← 事务2
        repo = RoadmapRepository(session)
        await repo.update_task_status(
            task_id=task_id,
            status=final_status,  # "completed" 或 "partial_failure"
            ...
        )
        await session.commit()
```

---

## 3. 问题分析

### 3.1 事务原子性问题

**场景**: CurriculumDesignRunner 执行过程中发生异常

```
Timeline:
─────────────────────────────────────────────────────────────────
T1: _update_task_status() → status="processing" → COMMIT ✓
T2: agent.execute() → LLM 调用中...
T3: _save_roadmap_framework() → 网络错误！→ ROLLBACK
T4: 异常抛出，工作流终止
─────────────────────────────────────────────────────────────────

结果:
- RoadmapTask.status = "processing" (已提交)
- RoadmapTask.current_step = "curriculum_design" (已提交)
- RoadmapMetadata = NULL (未创建)

问题: 数据库状态与实际执行状态不一致
```

### 3.2 数据一致性风险矩阵

| 风险场景 | 影响表 | 严重程度 | 发生概率 |
|---------|-------|---------|---------|
| Intent 分析成功但状态更新失败 | RoadmapTask | 高 | 低 |
| Framework 保存失败但状态已更新 | RoadmapTask, RoadmapMetadata | 高 | 中 |
| Content 生成部分成功 | RoadmapTask, TutorialMetadata | 中 | 高 |
| LangGraph checkpoint 与 DB 不同步 | checkpoint, RoadmapTask | 高 | 中 |

### 3.3 代码维护问题

```python
# 问题: 几乎相同的代码在 6 个文件中重复

# intent_runner.py
async def _update_task_status(self, task_id, current_step, roadmap_id):
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        await repo.update_task_status(...)
        await session.commit()

# curriculum_runner.py - 完全相同
# validation_runner.py - 完全相同
# editor_runner.py - 完全相同
# review_runner.py - 相似但内联
# content_runner.py - 完全相同
```

**违反原则**:
- DRY (Don't Repeat Yourself)
- Single Responsibility Principle
- Separation of Concerns

### 3.4 错误恢复困难

当前架构下，系统崩溃后的恢复流程：

```
1. 读取 LangGraph checkpoint
2. 读取 RoadmapTask 状态
3. 发现两者可能不一致
4. 无法确定哪些操作已完成
5. 需要人工干预判断
```

---

## 4. 解决方案设计

### 4.1 目标架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        WorkflowExecutor                         │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                    LangGraph Graph                       │  │
│    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────┐ │  │
│    │  │ Intent  │→ │Curricul │→ │Validat- │→ │   Content   │ │  │
│    │  │ Runner  │  │ Runner  │  │  Runner │  │   Runner    │ │  │
│    │  └────┬────┘  └────┬────┘  └────┬────┘  └──────┬──────┘ │  │
│    └───────│────────────│────────────│──────────────│────────┘  │
│            │            │            │              │           │
│            └────────────┴────────────┴──────────────┘           │
│                              │                                   │
│                              ▼                                   │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │                    WorkflowBrain                         │  │
│    │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │  │
│    │  │  State   │ │Checkpoint│ │    DB    │ │Notification│  │  │
│    │  │ Manager  │ │  Manager │ │Operations│ │  Manager   │  │  │
│    │  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │  │
│    └──────────────────────────┬──────────────────────────────┘  │
└───────────────────────────────│──────────────────────────────────┘
                                │
                                ▼
                    ┌─────────────────┐
                    │    PostgreSQL   │
                    │   (统一事务)     │
                    └─────────────────┘
```

### 4.2 WorkflowBrain 核心设计

```python
"""
工作流大脑 - 统一协调者

职责:
1. 状态管理 (State Management)
2. Checkpoint 协调 (Checkpoint Coordination)
3. 数据库操作 (DB Operations)
4. 日志管理 (Logging)
5. 通知发布 (Notification)
"""
from dataclasses import dataclass
from typing import Protocol, TypeVar, Generic
from contextlib import asynccontextmanager

T = TypeVar("T")


class NodeResult(Protocol):
    """节点执行结果协议"""
    @property
    def state_updates(self) -> dict:
        """需要更新到工作流状态的数据"""
        ...
    
    @property
    def metadata_to_save(self) -> list[tuple[str, any]]:
        """需要保存的元数据 [(table_name, data), ...]"""
        ...


@dataclass
class NodeContext:
    """节点执行上下文"""
    node_name: str
    task_id: str
    roadmap_id: str | None
    start_time: float
    state_snapshot: dict


class WorkflowBrain:
    """
    工作流大脑
    
    统一管理工作流执行过程中的所有状态变更和持久化操作。
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        notification_service: NotificationService,
        execution_logger: ExecutionLogger,
        session_factory: AsyncSessionFactory,
    ):
        self.state_manager = state_manager
        self.notification_service = notification_service
        self.execution_logger = execution_logger
        self.session_factory = session_factory
        self._current_context: NodeContext | None = None
    
    @asynccontextmanager
    async def node_execution(
        self,
        node_name: str,
        state: RoadmapState,
    ):
        """
        节点执行上下文管理器
        
        用法:
            async with brain.node_execution("intent_analysis", state) as ctx:
                result = await agent.execute(...)
                ctx.set_result(result)
        
        自动处理:
        - 执行前: 更新状态、记录日志、发布通知
        - 执行后: 保存结果、更新数据库、记录日志
        - 异常时: 错误处理、状态回滚、错误通知
        """
        ctx = await self._before_node(node_name, state)
        try:
            yield ctx
            await self._after_node(ctx, state)
        except Exception as e:
            await self._on_error(ctx, state, e)
            raise
    
    async def _before_node(self, node_name: str, state: RoadmapState) -> NodeContext:
        """节点执行前的统一处理"""
        import time
        
        task_id = state["task_id"]
        roadmap_id = state.get("roadmap_id")
        
        # 创建执行上下文
        ctx = NodeContext(
            node_name=node_name,
            task_id=task_id,
            roadmap_id=roadmap_id,
            start_time=time.time(),
            state_snapshot=dict(state),
        )
        self._current_context = ctx
        
        # 1. 更新 live_step 缓存
        self.state_manager.set_live_step(task_id, node_name)
        
        # 2. 更新数据库状态（使用统一事务）
        async with self.session_factory() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step=node_name,
                roadmap_id=roadmap_id,
            )
            await session.commit()
        
        # 3. 记录开始日志
        await self.execution_logger.log_workflow_start(
            task_id=task_id,
            step=node_name,
            message=f"开始执行: {node_name}",
            roadmap_id=roadmap_id,
        )
        
        # 4. 发布进度通知
        await self.notification_service.publish_progress(
            task_id=task_id,
            step=node_name,
            status="processing",
            message=f"正在执行: {node_name}...",
        )
        
        return ctx
    
    async def _after_node(self, ctx: NodeContext, state: RoadmapState):
        """节点执行后的统一处理"""
        import time
        
        duration_ms = int((time.time() - ctx.start_time) * 1000)
        
        # 1. 记录完成日志
        await self.execution_logger.log_workflow_complete(
            task_id=ctx.task_id,
            step=ctx.node_name,
            message=f"完成执行: {ctx.node_name}",
            duration_ms=duration_ms,
            roadmap_id=ctx.roadmap_id,
        )
        
        # 2. 发布完成通知
        await self.notification_service.publish_progress(
            task_id=ctx.task_id,
            step=ctx.node_name,
            status="completed",
            message=f"完成: {ctx.node_name}",
        )
        
        self._current_context = None
    
    async def _on_error(self, ctx: NodeContext, state: RoadmapState, error: Exception):
        """节点执行失败的统一处理"""
        import time
        
        duration_ms = int((time.time() - ctx.start_time) * 1000)
        
        # 1. 更新数据库状态为失败
        async with self.session_factory() as session:
            repo = RoadmapRepository(session)
            await repo.update_task_status(
                task_id=ctx.task_id,
                status="failed",
                current_step=ctx.node_name,
                error_message=str(error),
            )
            await session.commit()
        
        # 2. 记录错误日志
        await self.execution_logger.log_error(
            task_id=ctx.task_id,
            step=ctx.node_name,
            error=error,
            duration_ms=duration_ms,
        )
        
        # 3. 发布错误通知
        await self.notification_service.publish_progress(
            task_id=ctx.task_id,
            step=ctx.node_name,
            status="failed",
            message=f"执行失败: {ctx.node_name}",
            extra_data={"error": str(error)},
        )
        
        self._current_context = None
    
    # ========================================
    # 特定节点的数据保存方法
    # ========================================
    
    async def save_intent_analysis(
        self,
        task_id: str,
        intent_analysis: IntentAnalysisOutput,
        unique_roadmap_id: str,
    ):
        """保存需求分析结果（事务性操作）"""
        async with self.session_factory() as session:
            repo = RoadmapRepository(session)
            
            # 同一事务中执行所有操作
            await repo.save_intent_analysis_metadata(task_id, intent_analysis)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="intent_analysis",
                roadmap_id=unique_roadmap_id,
            )
            
            await session.commit()
    
    async def save_roadmap_framework(
        self,
        task_id: str,
        roadmap_id: str,
        user_id: str,
        framework: RoadmapFramework,
    ):
        """保存路线图框架（事务性操作）"""
        async with self.session_factory() as session:
            repo = RoadmapRepository(session)
            
            # 同一事务中执行所有操作
            await repo.save_roadmap_metadata(roadmap_id, user_id, framework)
            await repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="curriculum_design",
            )
            
            await session.commit()
    
    async def save_content_results(
        self,
        task_id: str,
        roadmap_id: str,
        tutorial_refs: dict,
        resource_refs: dict,
        quiz_refs: dict,
        failed_concepts: list,
    ):
        """保存内容生成结果（批量事务操作）"""
        async with self.session_factory() as session:
            repo = RoadmapRepository(session)
            
            # 同一事务中批量保存
            if tutorial_refs:
                await repo.save_tutorials_batch(tutorial_refs, roadmap_id)
            if resource_refs:
                await repo.save_resources_batch(resource_refs, roadmap_id)
            if quiz_refs:
                await repo.save_quizzes_batch(quiz_refs, roadmap_id)
            
            # 更新最终状态
            final_status = "partial_failure" if failed_concepts else "completed"
            await repo.update_task_status(
                task_id=task_id,
                status=final_status,
                current_step="content_generation",
                failed_concepts={
                    "count": len(failed_concepts),
                    "concept_ids": failed_concepts,
                } if failed_concepts else None,
            )
            
            await session.commit()
```

### 4.3 重构后的 Runner 示例

```python
"""
重构后的需求分析 Runner

变化:
- 删除所有 _update_xxx 方法
- 删除直接数据库操作
- 只负责调用 Agent 并返回纯结果
"""

class IntentAnalysisRunner:
    """需求分析节点执行器（重构版）"""
    
    def __init__(
        self,
        brain: WorkflowBrain,
        agent_factory: AgentFactory,
    ):
        self.brain = brain
        self.agent_factory = agent_factory
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行需求分析节点
        
        只负责:
        1. 调用 Agent
        2. 处理 roadmap_id 唯一性
        3. 返回状态更新
        
        不再负责:
        - 数据库操作 (交给 brain)
        - 日志记录 (交给 brain)
        - 通知发布 (交给 brain)
        """
        async with self.brain.node_execution("intent_analysis", state):
            # 1. 执行 Agent
            agent = self.agent_factory.create_intent_analyzer()
            result = await agent.execute(state["user_request"])
            
            # 2. 确保 roadmap_id 唯一性
            unique_roadmap_id = await self.brain.ensure_unique_roadmap_id(result.roadmap_id)
            result.roadmap_id = unique_roadmap_id
            
            # 3. 保存结果（由 brain 统一事务管理）
            await self.brain.save_intent_analysis(
                task_id=state["task_id"],
                intent_analysis=result,
                unique_roadmap_id=unique_roadmap_id,
            )
            
            # 4. 返回纯状态更新
            return {
                "intent_analysis": result,
                "roadmap_id": unique_roadmap_id,
                "current_step": "intent_analysis",
                "execution_history": ["需求分析完成"],
            }
```

### 4.4 对比：重构前后

#### 代码行数对比

| Runner | 重构前 | 重构后 | 减少 |
|--------|-------|-------|------|
| IntentAnalysisRunner | 248 行 | ~80 行 | -68% |
| CurriculumDesignRunner | 240 行 | ~70 行 | -71% |
| ValidationRunner | 177 行 | ~50 行 | -72% |
| EditorRunner | 210 行 | ~60 行 | -71% |
| ReviewRunner | 162 行 | ~50 行 | -69% |
| ContentRunner | 565 行 | ~200 行 | -65% |
| **总计** | **1602 行** | **~510 行** | **-68%** |

#### 职责对比

| 职责 | 重构前 | 重构后 |
|------|-------|-------|
| Agent 调用 | Runner | Runner |
| 状态更新 | Runner | Brain |
| 数据库操作 | Runner | Brain |
| 日志记录 | Runner | Brain |
| 通知发布 | Runner | Brain |
| 事务管理 | 无 | Brain |
| 错误处理 | Runner (分散) | Brain (统一) |

---

## 5. 实施计划

### 5.1 Phase 1: 基础设施（2-3 天）

**目标**: 创建 WorkflowBrain 核心组件

**任务**:
- [ ] 创建 `WorkflowBrain` 类
- [ ] 实现 `node_execution` 上下文管理器
- [ ] 实现 `before_node`, `after_node`, `on_error` 方法
- [ ] 添加单元测试

**风险**: 低

### 5.2 Phase 2: Runner 迁移（3-5 天）

**目标**: 逐一重构每个 Runner

**迁移顺序**:
1. ValidationRunner（最简单，无复杂数据保存）
2. EditorRunner
3. ReviewRunner
4. IntentAnalysisRunner
5. CurriculumDesignRunner
6. ContentRunner（最复杂，最后处理）

**每个 Runner 迁移步骤**:
1. 创建新版 Runner（使用 brain）
2. 添加迁移测试
3. 并行运行新旧版本对比结果
4. 切换到新版本
5. 删除旧代码

**风险**: 中等

### 5.3 Phase 3: 事务增强（2-3 天）

**目标**: 添加完整事务支持

**任务**:
- [ ] 实现 Unit of Work 模式
- [ ] 添加 savepoint 支持
- [ ] 实现回滚策略
- [ ] 添加事务超时处理

**风险**: 中等

### 5.4 Phase 4: 优化与监控（1-2 天）

**目标**: 性能优化和监控完善

**任务**:
- [ ] 批量操作优化
- [ ] 添加性能指标
- [ ] 完善错误恢复机制
- [ ] 文档更新

**风险**: 低

---

## 6. 风险评估

### 6.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|-----|------|---------|
| 迁移引入 bug | 高 | 中 | 完整测试覆盖、灰度发布 |
| 性能回归 | 中 | 低 | 性能基准测试、A/B 对比 |
| LangGraph 兼容性 | 中 | 低 | 研究 LangGraph 内部机制 |

### 6.2 项目风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|-----|------|---------|
| 工期延长 | 中 | 中 | 渐进式实施、可随时暂停 |
| 需求变更 | 低 | 低 | 保持接口稳定性 |

---

## 7. 成功指标

### 7.1 代码质量指标

- [ ] 代码重复率下降 > 60%
- [ ] 单个 Runner 代码行数 < 100 行
- [ ] 测试覆盖率 > 80%

### 7.2 可靠性指标

- [ ] 事务回滚成功率 100%
- [ ] 状态一致性检查通过率 100%
- [ ] 错误恢复成功率 > 95%

### 7.3 可维护性指标

- [ ] 新增 Runner 开发时间 < 2 小时
- [ ] Bug 修复平均时间下降 > 50%

---

## 8. 结论与建议

### 8.1 结论

用户的观察是正确的：**当前架构确实存在事务原子性和代码重复问题**。

核心问题在于：
1. 每个 Runner 都独立管理数据库会话
2. 没有统一的事务边界
3. 状态管理逻辑分散在各处

### 8.2 建议

**强烈建议实施 WorkflowBrain 重构方案**，理由如下：

1. **投入产出比高**: 一次性投入可获得长期收益
2. **风险可控**: 渐进式实施，可随时回滚
3. **收益明确**: 代码简化、可靠性提升、维护成本降低

### 8.3 下一步行动

1. 团队评审本文档
2. 确认实施优先级
3. 创建实施任务并分配
4. 开始 Phase 1 开发

---

## 附录 A: 相关文件清单

```
backend/app/core/orchestrator/
├── __init__.py
├── base.py                    # RoadmapState, WorkflowConfig
├── builder.py                 # WorkflowBuilder
├── executor.py                # WorkflowExecutor
├── routers.py                 # WorkflowRouter
├── state_manager.py           # StateManager (当前版本)
└── node_runners/
    ├── __init__.py
    ├── intent_runner.py       # IntentAnalysisRunner
    ├── curriculum_runner.py   # CurriculumDesignRunner
    ├── validation_runner.py   # ValidationRunner
    ├── editor_runner.py       # EditorRunner
    ├── review_runner.py       # ReviewRunner
    └── content_runner.py      # ContentRunner
```

## 附录 B: 术语表

| 术语 | 定义 |
|------|------|
| WorkflowBrain | 工作流大脑，统一协调者组件 |
| Runner | 节点执行器，负责调用 Agent |
| Checkpoint | LangGraph 状态检查点 |
| Unit of Work | 工作单元模式，确保事务原子性 |
| Live Step | 当前执行步骤的内存缓存 |

---

*文档结束*

