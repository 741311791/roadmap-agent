# 后端代码重构方案

## 📊 现状分析

### 1. 代码规模统计

| 文件 | 行数 | 主要问题 |
|:---|:---:|:---|
| `api/v1/roadmap.py` | 3,446 | **严重超标**，包含过多端点和业务逻辑 |
| `core/orchestrator.py` | 1,643 | **过度复杂**，承担太多职责（23个方法） |
| `db/repositories/roadmap_repo.py` | 1,040 | **数据访问层过重**，包含业务逻辑 |
| `services/roadmap_service.py` | 616 | 职责不清，与 Orchestrator 重叠 |
| `agents/` 目录 | 4,457 | Agent 实现分散，缺少统一抽象 |
| **总计** | **11,202** | **可维护性差，测试困难** |

### 2. 架构问题诊断

#### 🔴 严重问题

##### A. **单一职责违反 (SRP Violation)**

```python
# 问题：Orchestrator 承担太多职责
class RoadmapOrchestrator:
    # 1. 工作流编排
    def _build_graph(self): ...
    
    # 2. Agent 执行
    async def _run_intent_analysis(self): ...
    async def _run_curriculum_design(self): ...
    async def _run_tutorial_generation(self): ...
    
    # 3. 状态管理
    def _set_live_step(self): ...
    def _clear_live_step(self): ...
    
    # 4. 进度通知
    # 散落在各个方法中：notification_service.publish_*()
    
    # 5. 数据库操作
    # 直接调用 repo：await repo.update_task_status(...)
    
    # 6. roadmap_id 唯一性验证
    async def ensure_unique_roadmap_id(self): ...
```

**影响**：
- 单个文件 1643 行，难以理解和修改
- 修改一个功能可能影响其他功能
- 测试困难，需要 mock 大量依赖

##### B. **职责重叠 (Responsibility Overlap)**

```
RoadmapService          ⟷   RoadmapOrchestrator
     ↓                              ↓
- 执行工作流              - 编排工作流
- 保存元数据              - 调用 Agent
- 发布通知                - 更新状态
- 处理错误                - 发布通知
                          - 处理错误
```

**问题**：
- `RoadmapService.generate_roadmap()` 和 `RoadmapOrchestrator.execute()` 职责不清
- 通知服务调用分散在两者中
- 错误处理重复
- 状态更新不一致

##### C. **巨型 API 文件 (God File)**

`api/v1/roadmap.py` **3,446 行** 包含：
- 13+ 个路由端点
- 业务逻辑混杂
- 数据转换逻辑
- 错误处理代码
- 文档字符串冗长

**影响**：
- 代码审查困难
- 合并冲突频繁
- 导航和查找困难
- 新增端点需要修改巨型文件

##### D. **数据访问层过重 (Fat Repository)**

`roadmap_repo.py` **1,040 行** 包含业务逻辑：
- 路线图状态计算
- 失败重试逻辑
- 版本管理
- 复杂的 JOIN 查询

**问题**：
- Repository 应该只负责数据访问
- 业务逻辑应该在 Service 层
- 难以复用和测试

#### 🟡 中等问题

##### E. **缺少接口抽象**

```python
# 没有接口定义
class IntentAnalyzerAgent(BaseAgent):
    async def analyze(self, request): ...

class CurriculumArchitectAgent(BaseAgent):
    async def design(self, ...): ...

class TutorialGeneratorAgent(BaseAgent):
    async def execute(self, input_data): ...
```

**问题**：
- 方法名不统一（`analyze`, `design`, `execute`）
- 缺少类型协议（Protocol）
- 难以替换实现
- 测试时难以 mock

##### F. **依赖注入不完整**

```python
# 问题：硬编码依赖
class RoadmapOrchestrator:
    async def _run_intent_analysis(self, state):
        agent = IntentAnalyzerAgent()  # ❌ 硬编码创建
        result = await agent.analyze(...)
```

**应该**：
```python
class RoadmapOrchestrator:
    def __init__(self, agent_factory: AgentFactory):
        self.agent_factory = agent_factory
    
    async def _run_intent_analysis(self, state):
        agent = self.agent_factory.create_intent_analyzer()
        result = await agent.analyze(...)
```

##### G. **错误处理混乱**

```python
# 多处重复的错误处理
try:
    result = await agent.execute(...)
except Exception as e:
    logger.error("xxx_failed", error=str(e))
    await execution_logger.error(...)
    await notification_service.publish_failed(...)
    await repo.update_task_status(..., status="failed")
    raise
```

**问题**：
- 错误处理代码重复
- 日志记录冗余
- 状态更新不一致
- 难以统一管理

#### 🟢 轻微问题

##### H. **类型注解不完整**

部分函数缺少返回类型注解，影响类型检查和 IDE 提示。

##### I. **魔法数字和硬编码**

```python
semaphore = asyncio.Semaphore(settings.PARALLEL_TUTORIAL_LIMIT)
max_attempts = 10  # ❌ 魔法数字
```

---

## 🎯 重构目标

### 核心原则

1. **单一职责** (SRP)：每个类/模块只负责一件事
2. **开闭原则** (OCP)：对扩展开放，对修改关闭
3. **依赖倒置** (DIP)：依赖抽象而非具体实现
4. **接口隔离** (ISP)：接口应该小而专注
5. **DRY 原则**：避免重复代码

### 性能指标

| 指标 | 当前 | 目标 | 说明 |
|:---|:---:|:---:|:---|
| 单文件最大行数 | 3,446 | < 500 | 提高可读性 |
| 单类最大方法数 | 23 | < 10 | 职责单一 |
| 循环复杂度 | 高 | < 10 | 降低复杂度 |
| 测试覆盖率 | < 30% | > 80% | 提高质量 |
| 代码重复率 | 高 | < 5% | 消除重复 |

---

## 📐 重构方案

### 方案概览

```
┌─────────────────────────────────────────────────────────────┐
│                  New Architecture (After)                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐                                        │
│  │   API Layer      │  (< 200 lines per file)                │
│  │  - endpoints/    │  Split by feature                      │
│  │  - middleware/   │                                        │
│  │  - validators/   │                                        │
│  └────────┬─────────┘                                        │
│           │                                                   │
│  ┌────────▼─────────────────────────────────────┐           │
│  │         Application Layer                     │           │
│  │  ┌──────────────┐  ┌──────────────────────┐ │           │
│  │  │ Orchestrator │  │  Service Layer       │ │           │
│  │  │  (Workflow)  │  │  - RoadmapService    │ │           │
│  │  │              │  │  - ContentService    │ │           │
│  │  │  - Builder   │  │  - NotificationSvc   │ │           │
│  │  │  - Executor  │  └──────────────────────┘ │           │
│  │  └──────────────┘                            │           │
│  └───────────────────────────────────────────────┘           │
│           │                                                   │
│  ┌────────▼─────────────────────────────────────┐           │
│  │         Domain Layer                          │           │
│  │  ┌──────────────┐  ┌──────────────────────┐ │           │
│  │  │   Agents     │  │   Domain Models      │ │           │
│  │  │  (Protocol)  │  │   - Entities         │ │           │
│  │  │              │  │   - Value Objects    │ │           │
│  │  │  - Factory   │  │   - Domain Events    │ │           │
│  │  └──────────────┘  └──────────────────────┘ │           │
│  └───────────────────────────────────────────────┘           │
│           │                                                   │
│  ┌────────▼─────────────────────────────────────┐           │
│  │      Infrastructure Layer                     │           │
│  │  - Repositories (Data Access)                 │           │
│  │  - External Services (S3, Redis)              │           │
│  │  - LLM Clients                                │           │
│  └───────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

### 阶段 1: 拆分 Orchestrator（优先级：🔴 高）

#### 目标
将 1643 行的 `orchestrator.py` 拆分为多个专注的模块。

#### 新结构

```
app/core/
├── orchestrator/
│   ├── __init__.py
│   ├── base.py                    # 基础定义（State, Config）
│   ├── builder.py                 # 工作流构建器（_build_graph）
│   ├── executor.py                # 工作流执行器（execute, resume）
│   ├── node_runners/              # 节点执行器
│   │   ├── __init__.py
│   │   ├── intent_runner.py      # _run_intent_analysis
│   │   ├── curriculum_runner.py  # _run_curriculum_design
│   │   ├── validation_runner.py  # _run_structure_validation
│   │   ├── editor_runner.py      # _run_roadmap_edit
│   │   ├── review_runner.py      # _run_human_review
│   │   └── content_runner.py     # _run_tutorial_generation
│   ├── routers.py                 # 路由逻辑（_route_after_validation）
│   └── state_manager.py           # 状态管理（live_step_cache）
├── checkpointer.py                # Checkpointer 管理
└── tool_registry.py               # 保持不变
```

#### 实现示例

**base.py** (< 100 lines)
```python
"""工作流基础定义"""
from typing import TypedDict, Annotated
from operator import add

def merge_dicts(left: dict, right: dict) -> dict:
    return {**left, **right}

class RoadmapState(TypedDict):
    """工作流全局状态"""
    user_request: UserRequest
    trace_id: str
    roadmap_id: str | None
    intent_analysis: IntentAnalysisOutput | None
    roadmap_framework: RoadmapFramework | None
    validation_result: ValidationOutput | None
    tutorial_refs: Annotated[dict[str, TutorialGenerationOutput], merge_dicts]
    resource_refs: Annotated[dict[str, ResourceRecommendationOutput], merge_dicts]
    quiz_refs: Annotated[dict[str, QuizGenerationOutput], merge_dicts]
    failed_concepts: Annotated[list[str], add]
    current_step: str
    modification_count: int
    human_approved: bool
    execution_history: Annotated[list[str], add]

class WorkflowConfig:
    """工作流配置"""
    skip_structure_validation: bool
    skip_human_review: bool
    skip_tutorial_generation: bool
    skip_resource_recommendation: bool
    skip_quiz_generation: bool
    max_framework_retry: int
    parallel_tutorial_limit: int
```

**builder.py** (< 200 lines)
```python
"""工作流构建器"""
from langgraph.graph import StateGraph, END
from .base import RoadmapState, WorkflowConfig
from .node_runners import (
    IntentAnalysisRunner,
    CurriculumDesignRunner,
    ValidationRunner,
    EditorRunner,
    ReviewRunner,
    ContentRunner,
)
from .routers import WorkflowRouter

class WorkflowBuilder:
    """负责构建 LangGraph 工作流"""
    
    def __init__(
        self,
        config: WorkflowConfig,
        intent_runner: IntentAnalysisRunner,
        curriculum_runner: CurriculumDesignRunner,
        validation_runner: ValidationRunner,
        editor_runner: EditorRunner,
        review_runner: ReviewRunner,
        content_runner: ContentRunner,
        router: WorkflowRouter,
    ):
        self.config = config
        self.intent_runner = intent_runner
        self.curriculum_runner = curriculum_runner
        self.validation_runner = validation_runner
        self.editor_runner = editor_runner
        self.review_runner = review_runner
        self.content_runner = content_runner
        self.router = router
    
    def build(self, checkpointer) -> CompiledStateGraph:
        """构建并编译工作流"""
        workflow = StateGraph(RoadmapState)
        
        # 添加节点
        workflow.add_node("intent_analysis", self.intent_runner.run)
        workflow.add_node("curriculum_design", self.curriculum_runner.run)
        
        if not self.config.skip_structure_validation:
            workflow.add_node("structure_validation", self.validation_runner.run)
            workflow.add_node("roadmap_edit", self.editor_runner.run)
        
        if not self.config.skip_human_review:
            workflow.add_node("human_review", self.review_runner.run)
        
        if not self.config.skip_tutorial_generation:
            workflow.add_node("tutorial_generation", self.content_runner.run)
        
        # 定义边
        self._add_edges(workflow)
        
        return workflow.compile(checkpointer=checkpointer)
    
    def _add_edges(self, workflow: StateGraph):
        """定义工作流边"""
        workflow.set_entry_point("intent_analysis")
        workflow.add_edge("intent_analysis", "curriculum_design")
        
        # ... 其余边的定义（从原 _build_graph 移动过来）
```

**node_runners/intent_runner.py** (< 150 lines)
```python
"""需求分析节点执行器"""
import time
import structlog
from app.agents.intent_analyzer import IntentAnalyzerAgent
from app.services.notification_service import notification_service
from app.services.execution_logger import execution_logger

logger = structlog.get_logger()

class IntentAnalysisRunner:
    """负责执行需求分析节点"""
    
    def __init__(
        self,
        agent_factory: AgentFactory,
        notification_service: NotificationService,
        execution_logger: ExecutionLogger,
        repo_factory: RepositoryFactory,
    ):
        self.agent_factory = agent_factory
        self.notification_service = notification_service
        self.execution_logger = execution_logger
        self.repo_factory = repo_factory
    
    async def run(self, state: RoadmapState) -> dict:
        """执行需求分析"""
        start_time = time.time()
        trace_id = state["trace_id"]
        
        logger.info("intent_analysis_started", trace_id=trace_id)
        
        # 发布进度
        await self.notification_service.publish_progress(
            task_id=trace_id,
            step="intent_analysis",
            status="processing",
            message="正在分析学习需求...",
        )
        
        try:
            # 执行 Agent
            agent = self.agent_factory.create_intent_analyzer()
            result = await agent.analyze(state["user_request"])
            
            # 确保 roadmap_id 唯一性
            roadmap_id = await self._ensure_unique_roadmap_id(
                result.roadmap_id,
                trace_id,
            )
            result.roadmap_id = roadmap_id
            
            # 更新数据库
            await self._update_database(trace_id, roadmap_id)
            
            # 记录执行日志
            duration_ms = int((time.time() - start_time) * 1000)
            await self.execution_logger.log_workflow_complete(
                trace_id=trace_id,
                step="intent_analysis",
                message="需求分析完成",
                duration_ms=duration_ms,
                roadmap_id=roadmap_id,
                details={...},
            )
            
            # 发布完成通知
            await self.notification_service.publish_progress(
                task_id=trace_id,
                step="intent_analysis",
                status="completed",
                message="需求分析完成",
                extra_data={"roadmap_id": roadmap_id},
            )
            
            return {
                "intent_analysis": result,
                "roadmap_id": roadmap_id,
                "current_step": "intent_analysis",
                "execution_history": ["需求分析完成"],
            }
            
        except Exception as e:
            await self._handle_error(trace_id, e, time.time() - start_time)
            raise
    
    async def _ensure_unique_roadmap_id(self, roadmap_id: str, trace_id: str) -> str:
        """确保 roadmap_id 唯一"""
        # ... 实现（从 orchestrator 移动过来）
    
    async def _update_database(self, trace_id: str, roadmap_id: str):
        """更新数据库记录"""
        async with self.repo_factory.create_session() as session:
            repo = self.repo_factory.create_roadmap_repo(session)
            await repo.update_task_status(
                task_id=trace_id,
                status="processing",
                current_step="intent_analysis",
                roadmap_id=roadmap_id,
            )
            await session.commit()
    
    async def _handle_error(self, trace_id: str, error: Exception, start_time: float):
        """处理错误"""
        duration_ms = int((time.time() - start_time) * 1000)
        
        logger.error("intent_analysis_failed", trace_id=trace_id, error=str(error))
        
        await self.execution_logger.error(
            trace_id=trace_id,
            category=LogCategory.WORKFLOW,
            message=f"需求分析失败: {str(error)[:100]}",
            step="intent_analysis",
            details={"error": str(error)},
        )
        
        await self.notification_service.publish_failed(
            task_id=trace_id,
            error=str(error),
            step="intent_analysis",
        )
```

**executor.py** (< 200 lines)
```python
"""工作流执行器"""
from langgraph.types import Command
import structlog

logger = structlog.get_logger()

class WorkflowExecutor:
    """负责执行和恢复工作流"""
    
    def __init__(
        self,
        builder: WorkflowBuilder,
        state_manager: StateManager,
    ):
        self.builder = builder
        self.state_manager = state_manager
        self._graph = None
    
    @property
    def graph(self):
        """延迟构建工作流图"""
        if self._graph is None:
            self._graph = self.builder.build()
        return self._graph
    
    async def execute(
        self,
        user_request: UserRequest,
        trace_id: str,
    ) -> RoadmapState:
        """执行完整工作流"""
        logger.info("workflow_executing", trace_id=trace_id)
        
        initial_state = self._create_initial_state(user_request, trace_id)
        config = {"configurable": {"thread_id": trace_id}}
        
        try:
            final_state = await self.graph.ainvoke(initial_state, config=config)
            
            logger.info(
                "workflow_completed",
                trace_id=trace_id,
                final_step=final_state.get("current_step"),
            )
            
            self.state_manager.clear_live_step(trace_id)
            return final_state
            
        except Exception as e:
            logger.error("workflow_failed", trace_id=trace_id, error=str(e))
            self.state_manager.clear_live_step(trace_id)
            raise
    
    async def resume_after_human_review(
        self,
        trace_id: str,
        approved: bool,
        feedback: str | None = None,
    ) -> RoadmapState:
        """在人工审核后恢复工作流"""
        config = {"configurable": {"thread_id": trace_id}}
        resume_value = {"approved": approved, "feedback": feedback or ""}
        
        logger.info("workflow_resuming", trace_id=trace_id, approved=approved)
        
        final_state = await self.graph.ainvoke(
            Command(resume=resume_value),
            config=config,
        )
        
        return final_state
    
    def _create_initial_state(
        self,
        user_request: UserRequest,
        trace_id: str,
    ) -> RoadmapState:
        """创建初始状态"""
        return {
            "user_request": user_request,
            "trace_id": trace_id,
            "roadmap_id": None,
            "intent_analysis": None,
            "roadmap_framework": None,
            "validation_result": None,
            "tutorial_refs": {},
            "resource_refs": {},
            "quiz_refs": {},
            "failed_concepts": [],
            "current_step": "init",
            "modification_count": 0,
            "human_approved": False,
            "execution_history": [],
        }
```

#### 依赖注入容器

**app/core/container.py**
```python
"""依赖注入容器"""
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    """应用依赖注入容器"""
    
    # 配置
    config = providers.Configuration()
    
    # 基础设施
    checkpointer = providers.Singleton(...)
    db_session_factory = providers.Factory(...)
    
    # Agent Factory
    agent_factory = providers.Singleton(
        AgentFactory,
        config=config.agents,
    )
    
    # Repository Factory
    repo_factory = providers.Factory(
        RepositoryFactory,
        session_factory=db_session_factory,
    )
    
    # Services
    notification_service = providers.Singleton(NotificationService)
    execution_logger = providers.Singleton(ExecutionLogger)
    
    # Node Runners
    intent_runner = providers.Factory(
        IntentAnalysisRunner,
        agent_factory=agent_factory,
        notification_service=notification_service,
        execution_logger=execution_logger,
        repo_factory=repo_factory,
    )
    
    curriculum_runner = providers.Factory(...)
    # ... 其他 runners
    
    # Workflow Builder
    workflow_builder = providers.Singleton(
        WorkflowBuilder,
        config=providers.Object(WorkflowConfig.from_settings()),
        intent_runner=intent_runner,
        curriculum_runner=curriculum_runner,
        # ... 其他 runners
    )
    
    # Workflow Executor
    workflow_executor = providers.Singleton(
        WorkflowExecutor,
        builder=workflow_builder,
        state_manager=providers.Singleton(StateManager),
    )
```

---

### 阶段 2: 拆分 API 层（优先级：🔴 高）

#### 目标
将 3446 行的 `roadmap.py` 按功能拆分为多个小文件。

#### 新结构

```
app/api/v1/
├── __init__.py
├── router.py                      # 主路由注册
├── endpoints/
│   ├── __init__.py
│   ├── generation.py              # 路线图生成 (< 200 lines)
│   ├── retrieval.py               # 路线图查询 (< 200 lines)
│   ├── approval.py                # 人工审核 (< 150 lines)
│   ├── tutorial.py                # 教程管理 (< 250 lines)
│   ├── resource.py                # 资源管理 (< 200 lines)
│   ├── quiz.py                    # 测验管理 (< 200 lines)
│   ├── modification.py            # 内容修改 (< 200 lines)
│   └── retry.py                   # 失败重试 (< 150 lines)
├── schemas/
│   ├── __init__.py
│   ├── request.py                 # 请求模型
│   └── response.py                # 响应模型
└── websocket.py                   # WebSocket 端点（保持独立）
```

#### 实现示例

**endpoints/generation.py**
```python
"""路线图生成相关端点"""
from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.domain import UserRequest
from app.services.roadmap_service import RoadmapService
from app.core.dependencies import get_roadmap_service

router = APIRouter(prefix="/roadmaps", tags=["generation"])

@router.post("/generate")
async def generate_roadmap(
    request: UserRequest,
    background_tasks: BackgroundTasks,
    service: RoadmapService = Depends(get_roadmap_service),
):
    """生成学习路线图（异步任务）"""
    result = await service.generate_roadmap_async(request, background_tasks)
    return result

@router.get("/{task_id}/status")
async def get_generation_status(
    task_id: str,
    service: RoadmapService = Depends(get_roadmap_service),
):
    """查询生成任务状态"""
    status = await service.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status
```

**endpoints/retrieval.py**
```python
"""路线图查询相关端点"""
from fastapi import APIRouter, Depends, HTTPException
from app.services.roadmap_service import RoadmapService
from app.core.dependencies import get_roadmap_service

router = APIRouter(prefix="/roadmaps", tags=["retrieval"])

@router.get("/{roadmap_id}")
async def get_roadmap(
    roadmap_id: str,
    service: RoadmapService = Depends(get_roadmap_service),
):
    """获取完整路线图"""
    roadmap = await service.get_roadmap(roadmap_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap

@router.get("/{roadmap_id}/active-task")
async def get_active_task(
    roadmap_id: str,
    service: RoadmapService = Depends(get_roadmap_service),
):
    """查询路线图的活跃任务"""
    task = await service.get_roadmap_active_task(roadmap_id)
    return task
```

**router.py**
```python
"""API 路由注册"""
from fastapi import APIRouter
from .endpoints import (
    generation,
    retrieval,
    approval,
    tutorial,
    resource,
    quiz,
    modification,
    retry,
)

router = APIRouter(prefix="/api/v1")

# 注册所有子路由
router.include_router(generation.router)
router.include_router(retrieval.router)
router.include_router(approval.router)
router.include_router(tutorial.router)
router.include_router(resource.router)
router.include_router(quiz.router)
router.include_router(modification.router)
router.include_router(retry.router)
```

---

### 阶段 3: 重构 Repository 层（优先级：🟡 中）

#### 目标
将业务逻辑从 Repository 移到 Service 层，Repository 只负责数据访问。
**同时优化数据库表结构**，提升查询性能。

#### 新增：数据库优化

**3.0 数据库审计**（2-3小时）：
- 审查所有表结构（字段、索引、JSON 使用）
- 识别优化机会（规范化、索引优化、字段拆分）
- 制定表结构优化方案

**优化方向**：
1. **拆分大 JSON 字段** → 关联表（提升查询性能）
2. **添加缺失索引** → 基于实际查询模式
3. **统一字段命名** → snake_case 规范
4. **优化外键关系** → 规范化设计

#### 原则

```
❌ Repository 不应该：
- 计算业务指标
- 处理复杂业务规则
- 调用外部服务
- 包含复杂的查询逻辑

✅ Repository 应该：
- 简单的 CRUD 操作
- 数据库事务管理
- 查询构建
- ORM 映射
```

#### 拆分方案

```
app/db/repositories/
├── __init__.py
├── base.py                        # 基础 Repository
├── task_repo.py                   # 任务相关 (< 200 lines)
├── roadmap_repo.py                # 路线图相关 (< 250 lines)
├── tutorial_repo.py               # 教程相关 (< 200 lines)
├── resource_repo.py               # 资源相关 (< 150 lines)
├── quiz_repo.py                   # 测验相关 (< 150 lines)
└── user_profile_repo.py           # 用户画像 (< 100 lines)
```

#### 实现示例

**base.py**
```python
"""基础 Repository"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import TypeVar, Generic, Type, List

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """基础仓储类"""
    
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model
    
    async def get_by_id(self, id: str) -> T | None:
        """根据 ID 查询"""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, entity: T) -> T:
        """创建实体"""
        self.session.add(entity)
        await self.session.flush()
        return entity
    
    async def update_fields(self, id: str, **fields) -> bool:
        """更新指定字段"""
        result = await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**fields)
        )
        return result.rowcount > 0
    
    async def delete(self, id: str) -> bool:
        """删除实体"""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        return result.rowcount > 0
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """查询列表"""
        result = await self.session.execute(
            select(self.model).limit(limit).offset(offset)
        )
        return result.scalars().all()
```

**task_repo.py**
```python
"""任务仓储"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import Task
from .base import BaseRepository

class TaskRepository(BaseRepository[Task]):
    """任务数据访问"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Task)
    
    async def get_by_task_id(self, task_id: str) -> Task | None:
        """根据 task_id 查询"""
        result = await self.session.execute(
            select(Task).where(Task.task_id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        task_id: str,
        status: str,
        current_step: str | None = None,
        error_message: str | None = None,
        **kwargs
    ) -> bool:
        """更新任务状态"""
        update_data = {
            "status": status,
            "updated_at": func.now(),
        }
        if current_step:
            update_data["current_step"] = current_step
        if error_message:
            update_data["error_message"] = error_message
        update_data.update(kwargs)
        
        return await self.update_fields(task_id, **update_data)
    
    async def get_active_task_by_roadmap(self, roadmap_id: str) -> Task | None:
        """查询路线图的活跃任务"""
        result = await self.session.execute(
            select(Task)
            .where(Task.roadmap_id == roadmap_id)
            .where(Task.status.in_(["processing", "human_review_pending"]))
            .order_by(Task.created_at.desc())
        )
        return result.scalar_one_or_none()
```

**roadmap_repo.py** (重构后 < 250 lines)
```python
"""路线图仓储"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import RoadmapMetadata
from .base import BaseRepository

class RoadmapRepository(BaseRepository[RoadmapMetadata]):
    """路线图数据访问"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, RoadmapMetadata)
    
    async def get_by_roadmap_id(self, roadmap_id: str) -> RoadmapMetadata | None:
        """根据 roadmap_id 查询"""
        result = await self.session.execute(
            select(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == roadmap_id)
        )
        return result.scalar_one_or_none()
    
    async def roadmap_id_exists(self, roadmap_id: str) -> bool:
        """检查 roadmap_id 是否存在"""
        result = await self.session.execute(
            select(RoadmapMetadata.roadmap_id)
            .where(RoadmapMetadata.roadmap_id == roadmap_id)
        )
        return result.scalar_one_or_none() is not None
    
    async def save_roadmap(
        self,
        roadmap_id: str,
        user_id: str,
        task_id: str,
        framework_data: dict,
    ) -> RoadmapMetadata:
        """保存路线图元数据"""
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_id,
            user_id=user_id,
            task_id=task_id,
            title=framework_data.get("title"),
            topic=framework_data.get("topic"),
            framework_data=framework_data,
            status="active",
        )
        return await self.create(roadmap)
    
    async def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[RoadmapMetadata]:
        """查询用户的路线图列表"""
        result = await self.session.execute(
            select(RoadmapMetadata)
            .where(RoadmapMetadata.user_id == user_id)
            .order_by(RoadmapMetadata.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
```

---

### 阶段 4: Agent 抽象与工厂（优先级：🟡 中）

#### 目标
统一 Agent 接口，使用工厂模式创建 Agent。

#### 接口定义

**app/agents/protocol.py**
```python
"""Agent 协议定义"""
from typing import Protocol, TypeVar, Generic
from abc import abstractmethod

InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')

class Agent(Protocol[InputT, OutputT]):
    """Agent 协议（接口）"""
    
    @property
    def agent_id(self) -> str:
        """Agent 唯一标识"""
        ...
    
    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """
        执行 Agent 任务
        
        Args:
            input_data: 输入数据
            
        Returns:
            输出数据
        """
        ...

# 具体 Agent 类型
class IntentAnalyzer(Agent[UserRequest, IntentAnalysisOutput], Protocol):
    """需求分析师"""
    pass

class CurriculumArchitect(Agent[CurriculumInput, CurriculumOutput], Protocol):
    """课程架构师"""
    pass

# ... 其他 Agent 类型
```

#### Agent Factory

**app/agents/factory.py**
```python
"""Agent 工厂"""
from typing import Protocol
from app.config.settings import Settings

class AgentFactory:
    """Agent 工厂类"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def create_intent_analyzer(self) -> IntentAnalyzer:
        """创建需求分析师"""
        from .intent_analyzer import IntentAnalyzerAgent
        return IntentAnalyzerAgent(
            agent_id="intent_analyzer",
            model_provider=settings.INTENT_ANALYZER_PROVIDER,
            model_name=settings.INTENT_ANALYZER_MODEL,
            base_url=settings.INTENT_ANALYZER_BASE_URL,
            api_key=settings.INTENT_ANALYZER_API_KEY,
        )
    
    def create_curriculum_architect(self) -> CurriculumArchitect:
        """创建课程架构师"""
        from .curriculum_architect import CurriculumArchitectAgent
        return CurriculumArchitectAgent(
            agent_id="curriculum_architect",
            model_provider=settings.CURRICULUM_ARCHITECT_PROVIDER,
            model_name=settings.CURRICULUM_ARCHITECT_MODEL,
            base_url=settings.CURRICULUM_ARCHITECT_BASE_URL,
            api_key=settings.CURRICULUM_ARCHITECT_API_KEY,
        )
    
    # ... 其他 Agent 创建方法
```

#### 统一 Agent 方法名

```python
# ❌ 之前：方法名不统一
class IntentAnalyzerAgent:
    async def analyze(self, request): ...

class CurriculumArchitectAgent:
    async def design(self, ...): ...

# ✅ 之后：统一使用 execute（直接重命名，无需向后兼容）
class IntentAnalyzerAgent:
    async def execute(self, input_data: UserRequest) -> IntentAnalysisOutput: ...

class CurriculumArchitectAgent:
    async def execute(self, input_data: CurriculumInput) -> CurriculumOutput: ...
```

**迁移方式**：
- 直接重命名方法，不保留旧方法
- 批量更新所有调用点（IDE 重构工具）
- 见 `MIGRATION_GUIDE.md` 了解详细变更

---

### 阶段 5: 统一错误处理（优先级：🟢 低）

#### 目标
集中管理错误处理逻辑，避免重复代码。

#### 错误处理中间件

**app/core/error_handler.py**
```python
"""统一错误处理"""
import structlog
from contextlib import asynccontextmanager
from typing import AsyncIterator, Callable, Any

logger = structlog.get_logger()

class WorkflowErrorHandler:
    """工作流错误处理器"""
    
    def __init__(
        self,
        execution_logger,
        notification_service,
        repo_factory,
    ):
        self.execution_logger = execution_logger
        self.notification_service = notification_service
        self.repo_factory = repo_factory
    
    @asynccontextmanager
    async def handle_node_execution(
        self,
        node_name: str,
        trace_id: str,
    ) -> AsyncIterator[dict]:
        """
        处理节点执行的错误
        
        使用方式：
        async with error_handler.handle_node_execution("intent_analysis", trace_id) as ctx:
            result = await agent.execute(...)
            ctx["result"] = result
        """
        import time
        start_time = time.time()
        context = {}
        
        try:
            yield context
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 记录错误日志
            logger.error(
                f"{node_name}_failed",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            
            # 记录执行日志
            await self.execution_logger.error(
                trace_id=trace_id,
                category=LogCategory.WORKFLOW,
                message=f"{node_name} 失败: {str(e)[:100]}",
                step=node_name,
                details={"error": str(e), "error_type": type(e).__name__},
            )
            
            # 发布失败通知
            await self.notification_service.publish_failed(
                task_id=trace_id,
                error=str(e),
                step=node_name,
            )
            
            # 更新任务状态
            async with self.repo_factory.create_session() as session:
                repo = self.repo_factory.create_task_repo(session)
                await repo.update_status(
                    task_id=trace_id,
                    status="failed",
                    current_step="failed",
                    error_message=str(e)[:500],
                )
                await session.commit()
            
            raise
```

#### 使用示例

```python
class IntentAnalysisRunner:
    def __init__(self, ..., error_handler: WorkflowErrorHandler):
        self.error_handler = error_handler
    
    async def run(self, state: RoadmapState) -> dict:
        trace_id = state["trace_id"]
        
        async with self.error_handler.handle_node_execution(
            "intent_analysis",
            trace_id,
        ) as ctx:
            agent = self.agent_factory.create_intent_analyzer()
            result = await agent.execute(state["user_request"])
            
            roadmap_id = await self._ensure_unique_roadmap_id(...)
            await self._update_database(trace_id, roadmap_id)
            
            ctx["result"] = {
                "intent_analysis": result,
                "roadmap_id": roadmap_id,
                "current_step": "intent_analysis",
                "execution_history": ["需求分析完成"],
            }
        
        return ctx["result"]
```

---

## 📅 实施计划

> **重要**: 本次重构**不考虑向后兼容**，采用直接替换策略

### 时间线

| 阶段 | 预计时间 | 人力 | 风险 | 备注 |
|:---|:---:|:---:|:---|:---|
| **阶段 1**: 拆分 Orchestrator | 4-6 天 | 2人 | 🟡 中等 - 依赖关系复杂 | -1天（移除兼容层） |
| **阶段 2**: 拆分 API 层 | 3-4 天 | 1人 | 🟢 低 - 相对独立 | 含 API 设计优化 |
| **阶段 3**: 重构 Repository | 4-6 天 | 1人 | 🟡 中等 - 表结构优化 | +1天（数据库优化） |
| **阶段 4**: Agent 抽象 | 2-3 天 | 1人 | 🟢 低 - 接口改造 | -1天（直接重命名） |
| **阶段 5**: 错误处理 | 2-3 天 | 1人 | 🟢 低 - 工具类 | 不变 |
| **测试与集成** | 4-6 天 | 2人 | 🟡 中等 - 充分测试 | -1天（简化测试） |
| **总计** | **19-28 天** | **2人** | | **减少 3-5 天** |

### 并行开发策略

> **策略**: Feature Branch + 充分测试 + 直接替换（无需向后兼容）

```
Week 1-2: 核心架构重构
  - 开发者 A: 阶段 1 (Orchestrator 拆分)
  - 开发者 B: 阶段 2 (API Layer 拆分)
  - 里程碑 M1: 核心架构完成，集成测试通过

Week 3: 数据层优化
  - 开发者 A: 阶段 3 (Repository + 数据库优化)
  - 开发者 B: 阶段 4 (Agent 抽象与工厂)
  - 里程碑 M2: 数据层完成，性能提升验证

Week 4: 错误处理与集成
  - 开发者 A: 阶段 5 (统一错误处理)
  - 开发者 B: E2E 测试编写
  - 里程碑 M3: 错误处理完成，E2E 测试 > 85%

Week 5: 全面验证与发布
  - 团队协作: 性能测试、代码质量检查、文档更新
  - 里程碑 M4: 发布就绪，所有质量指标达标
```

---

## ✅ 成功标准

### 代码质量指标

| 指标 | 目标 | 验证方式 |
|:---|:---:|:---|
| 单文件最大行数 | < 500 | `wc -l` 检查 |
| 单类最大方法数 | < 10 | 代码审查 |
| 循环复杂度 | < 10 | Radon 分析 |
| 测试覆盖率 | > 80% | pytest-cov |
| 代码重复率 | < 5% | flake8-duplicated |
| Mypy 类型检查 | 0 errors | `mypy --strict` |

### 功能验证

- ✅ 所有现有 API 端点正常工作
- ✅ 路线图生成流程完整
- ✅ 人工审核流程正常
- ✅ 内容生成（教程/资源/测验）成功
- ✅ 失败重试机制生效
- ✅ WebSocket 实时通知正常

### 性能基准

- ✅ API 响应时间不增加（P95 < 500ms）
- ✅ 内存使用不增加 > 10%
- ✅ 数据库查询次数不增加
- ✅ LLM 调用次数不变

---

## 🚀 后续优化

### 长期目标

1. **微服务拆分**（可选）
   - 将 Agent 执行拆分为独立服务
   - 使用消息队列（RabbitMQ/Kafka）解耦
   - 实现水平扩展

2. **缓存层优化**
   - 路线图框架缓存（Redis）
   - 教程内容 CDN 加速
   - Agent 结果缓存

3. **监控与可观测性**
   - 分布式追踪（OpenTelemetry）
   - 实时监控（Prometheus + Grafana）
   - 日志聚合（ELK Stack）

4. **性能优化**
   - 数据库查询优化（索引、N+1问题）
   - 并发控制（限流、熔断）
   - 批量操作优化

---

## 📚 参考资料

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Python Dependency Injection](https://python-dependency-injector.ets-labs.org/)
- [Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)

---

**文档版本**：v1.0  
**创建日期**：2025-01-XX  
**作者**：Roadmap Agent Team

