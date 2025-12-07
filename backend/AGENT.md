# 后端开发规范文档

> **版本**: v2.0 (重构后)  
> **更新日期**: 2025-12-06  
> **状态**: ✅ 生产就绪  
> **维护者**: Backend Team

---

## 📖 文档说明

本文档是后端项目的**统一开发规范文档**,包含:
- ✅ 技术架构说明
- ✅ 完整架构图和流程图
- ✅ 开发规范和最佳实践
- ✅ 代码示例和使用指南
- ✅ 常见问题解答

---

## 技术架构概览

### 核心技术栈

| 组件 | 技术选型 | 版本 | 说明 |
|:---|:---|:---:|:---|
| **Web 框架** | FastAPI | 0.104+ | 异步高性能 API 框架 |
| **Agent 框架** | LangGraph | 0.2+ | 状态机编排，支持 Human-in-the-Loop |
| **状态持久化** | AsyncPostgresSaver | - | PostgreSQL 异步状态存储 |
| **ORM** | SQLAlchemy | 2.0+ | 数据库操作抽象层（异步） |
| **LLM 调用** | LiteLLM | 1.0+ | 统一的多模型 API 接口 |
| **数据验证** | Pydantic | 2.0+ | 类型安全的数据模型 |
| **模板引擎** | Jinja2 | 3.0+ | Prompt 模板渲染 |
| **对象存储** | aioboto3 | - | S3 兼容的异步对象存储客户端 |
| **日志系统** | structlog | - | 结构化日志记录 |

### 架构特点

✅ **完全异步**: 所有I/O操作使用 async/await  
✅ **模块化**: 代码按职责拆分为小模块（< 200行/文件）  
✅ **工厂模式**: 使用工厂管理对象创建和依赖注入  
✅ **统一接口**: Agent 使用 Protocol 统一接口规范  
✅ **错误集中**: 统一的错误处理和日志记录  

### 架构分层（重构后 v2.0）

```
┌──────────────────────────────────────────────────────────────┐
│                   API Layer (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Endpoints (拆分后 - 8个独立文件)                   │   │
│  │  - generation.py      (生成/状态查询)              │   │
│  │  - retrieval.py       (路线图获取)                 │   │
│  │  - approval.py        (人工审核)                   │   │
│  │  - tutorial.py        (教程管理)                   │   │
│  │  - resource.py        (资源管理)                   │   │
│  │  - quiz.py            (测验管理)                   │   │
│  │  - modification.py    (内容修改)                   │   │
│  │  - retry.py           (失败重试)                   │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│              Orchestration Layer (重构后)                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │  OrchestratorFactory (工厂模式 - 单例)             │    │
│  │  ├─ StateManager (状态管理)                       │    │
│  │  ├─ AgentFactory (Agent工厂)                      │    │
│  │  ├─ Checkpointer (LangGraph检查点)                │    │
│  │  └─ WorkflowExecutor (工作流执行器)               │    │
│  │      ├─ WorkflowBuilder (图构建)                  │    │
│  │      ├─ WorkflowRouter (路由)                     │    │
│  │      └─ Node Runners (6个独立执行器)              │    │
│  │          ├─ IntentAnalysisRunner                   │    │
│  │          ├─ CurriculumDesignRunner                 │    │
│  │          ├─ ValidationRunner                       │    │
│  │          ├─ EditorRunner                           │    │
│  │          ├─ ReviewRunner                           │    │
│  │          └─ ContentRunner                          │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│              Agent Layer (统一接口)                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Agent Protocol (统一接口规范)                     │    │
│  │  ├─ execute(input) -> output                       │    │
│  │  └─ agent_id: str                                  │    │
│  │                                                     │    │
│  │  AgentFactory 管理 10个Agent实现:                  │    │
│  │  - IntentAnalyzerAgent        (需求分析)           │    │
│  │  - CurriculumArchitectAgent   (课程设计)           │    │
│  │  - StructureValidatorAgent    (结构验证)           │    │
│  │  - RoadmapEditorAgent         (路线图编辑)         │    │
│  │  - TutorialGeneratorAgent     (教程生成)           │    │
│  │  - ResourceRecommenderAgent   (资源推荐)           │    │
│  │  - QuizGeneratorAgent         (测验生成)           │    │
│  │  - TutorialModifierAgent      (教程修改)           │    │
│  │  - ResourceModifierAgent      (资源修改)           │    │
│  │  - QuizModifierAgent          (测验修改)           │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│              Service & Repository Layer (重构后)             │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Services (业务逻辑层)                             │    │
│  │  ├─ RoadmapService (核心业务逻辑)                  │    │
│  │  ├─ NotificationService (实时通知)                 │    │
│  │  └─ ExecutionLogger (执行日志)                     │    │
│  │                                                     │    │
│  │  RepositoryFactory (数据访问工厂)                  │    │
│  │  ├─ TaskRepository                                 │    │
│  │  ├─ RoadmapMetadataRepository                      │    │
│  │  ├─ TutorialRepository                             │    │
│  │  ├─ ResourceRepository                             │    │
│  │  ├─ QuizRepository                                 │    │
│  │  ├─ IntentAnalysisRepository                       │    │
│  │  ├─ UserProfileRepository                          │    │
│  │  └─ ExecutionLogRepository                         │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│              Error Handling (统一错误处理)                   │
│  ┌────────────────────────────────────────────────────┐    │
│  │  WorkflowErrorHandler (全局单例)                   │    │
│  │  └─ handle_node_execution() 上下文管理器           │    │
│  │      ├─ 自动日志记录 (structlog + ExecutionLogger) │    │
│  │      ├─ 自动通知发送 (NotificationService)         │    │
│  │      ├─ 自动状态更新 (TaskRepository)              │    │
│  │      └─ 异常重新抛出 (保留调用链)                  │    │
│  └────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────┐
│                Tool & Infrastructure Layer                    │
│  - Web Search (DuckDuckGo Search API)                        │
│  - S3 Storage (MinIO/Aliyun OSS - 异步)                     │
│  - PostgreSQL (数据持久化 + LangGraph Checkpointer)          │
│  - Redis (实时通知缓存, 可选)                                │
└──────────────────────────────────────────────────────────────┘
```


## 📐 完整系统架构

```mermaid
graph TB
    subgraph "客户端层"
        FE[前端应用<br/>Next.js]
    end
    
    subgraph "API层"
        API[FastAPI<br/>REST + SSE]
        GEN[generation.py<br/>生成/状态]
        RET[retrieval.py<br/>获取]
        APP[approval.py<br/>审核]
        TUT[tutorial.py<br/>教程]
        RES[resource.py<br/>资源]
        QZ[quiz.py<br/>测验]
        MOD[modification.py<br/>修改]
        RETRY[retry.py<br/>重试]
    end
    
    subgraph "编排层"
        OF[OrchestratorFactory<br/>工厂]
        WE[WorkflowExecutor<br/>执行器]
        WB[WorkflowBuilder<br/>构建器]
        WR[WorkflowRouter<br/>路由器]
        SM[StateManager<br/>状态管理]
        
        subgraph "Node Runners"
            IR[IntentRunner]
            CR[CurriculumRunner]
            VR[ValidationRunner]
            ER[EditorRunner]
            RR[ReviewRunner]
            CTR[ContentRunner]
        end
    end
    
    subgraph "Agent层"
        AF[AgentFactory]
        
        subgraph "7 Agents"
            A1[IntentAnalyzer]
            A2[CurriculumArchitect]
            A3[StructureValidator]
            A4[RoadmapEditor]
            A5[TutorialGenerator]
            A6[ResourceRecommender]
            A7[QuizGenerator]
        end
    end
    
    subgraph "服务层"
        RS[RoadmapService<br/>业务逻辑]
        NS[NotificationService<br/>通知]
        EL[ExecutionLogger<br/>日志]
        EH[ErrorHandler<br/>错误处理]
    end
    
    subgraph "数据访问层"
        RF[RepositoryFactory]
        
        subgraph "Repositories"
            TR[TaskRepo]
            RMR[RoadmapMetaRepo]
            TUR[TutorialRepo]
            RSR[ResourceRepo]
            QR[QuizRepo]
            IAR[IntentRepo]
            UPR[UserProfileRepo]
            ELR[ExecutionLogRepo]
        end
    end
    
    subgraph "基础设施层"
        PG[(PostgreSQL<br/>数据+Checkpoint)]
        S3[(S3/OSS<br/>内容存储)]
        RD[(Redis<br/>缓存)]
        LLM[LiteLLM<br/>大模型]
    end
    
    %% 连接关系
    FE -->|HTTP/SSE| API
    API --> GEN
    API --> RET
    API --> APP
    API --> TUT
    API --> RES
    API --> QZ
    API --> MOD
    API --> RETRY
    
    GEN --> RS
    RET --> RS
    APP --> RS
    RS --> OF
    OF --> WE
    WE --> WB
    WE --> WR
    WE --> SM
    
    WE --> IR
    WE --> CR
    WE --> VR
    WE --> ER
    WE --> RR
    WE --> CTR
    
    IR --> AF
    CR --> AF
    VR --> AF
    ER --> AF
    RR --> AF
    CTR --> AF
    
    AF --> A1
    AF --> A2
    AF --> A3
    AF --> A4
    AF --> A5
    AF --> A6
    AF --> A7
    
    IR --> EH
    CR --> EH
    VR --> EH
    ER --> EH
    RR --> EH
    CTR --> EH
    
    EH --> NS
    EH --> EL
    
    RS --> RF
    IR --> RF
    CR --> RF
    CTR --> RF
    
    RF --> TR
    RF --> RMR
    RF --> TUR
    RF --> RSR
    RF --> QR
    RF --> IAR
    RF --> UPR
    RF --> ELR
    
    TR --> PG
    RMR --> PG
    TUR --> PG
    A5 --> S3
    A6 --> LLM
    NS --> RD
    WE --> PG
    
    style API fill:#e1f5ff
    style OF fill:#fff3e0
    style AF fill:#f3e5f5
    style RF fill:#e8f5e9
    style EH fill:#ffebee
```

---

## 🔄 工作流状态机

```mermaid
stateDiagram-v2
    [*] --> init
    init --> intent_analysis
    
    intent_analysis --> curriculum_design: 成功
    intent_analysis --> failed: 失败
    
    curriculum_design --> structure_validation: 成功(skip=false)
    curriculum_design --> human_review: 成功(skip=true)
    curriculum_design --> failed: 失败
    
    structure_validation --> human_review: 验证通过
    structure_validation --> edit_roadmap: 验证失败且重试未超限
    structure_validation --> human_review: 验证失败但重试超限
    
    edit_roadmap --> structure_validation: 编辑完成
    
    human_review --> tutorial_generation: 审核通过(skip=false)
    human_review --> content_generation: 审核通过(skip=true)
    human_review --> edit_roadmap: 审核拒绝
    
    tutorial_generation --> resource_recommendation: 完成
    
    resource_recommendation --> quiz_generation: 完成
    
    quiz_generation --> content_generation: 完成
    
    content_generation --> completed: 全部成功
    content_generation --> partial_failure: 部分失败
    
    failed --> [*]
    completed --> [*]
    partial_failure --> [*]
```

---

## 📦 模块依赖关系

```mermaid
graph LR
    subgraph "API层"
        EP[Endpoints]
    end
    
    subgraph "服务层"
        SVC[Services]
    end
    
    subgraph "编排层"
        ORCH[Orchestrator]
    end
    
    subgraph "Agent层"
        AGT[Agents]
    end
    
    subgraph "数据层"
        REPO[Repositories]
        MODEL[Models]
    end
    
    subgraph "工具层"
        TOOL[Tools]
    end
    
    EP --> SVC
    SVC --> ORCH
    ORCH --> AGT
    ORCH --> REPO
    AGT --> TOOL
    AGT --> MODEL
    REPO --> MODEL
    SVC --> REPO
    
    style EP fill:#e3f2fd
    style SVC fill:#f3e5f5
    style ORCH fill:#fff9c4
    style AGT fill:#e8f5e9
    style REPO fill:#fce4ec
    style TOOL fill:#ede7f6
```

---

## 🏗️ Orchestrator内部结构

```mermaid
graph TB
    subgraph "OrchestratorFactory"
        Init[initialize<br/>初始化单例]
        Create[create_workflow_executor<br/>创建执行器]
        SM[StateManager<br/>单例]
        AF[AgentFactory<br/>单例]
        CP[Checkpointer<br/>单例]
    end
    
    subgraph "WorkflowExecutor"
        Build[WorkflowBuilder<br/>构建图]
        Exec[execute<br/>执行工作流]
        Resume[resume_after_human_review<br/>恢复执行]
    end
    
    subgraph "WorkflowBuilder"
        Graph[build<br/>构建LangGraph]
        Nodes[add_nodes<br/>添加节点]
        Edges[add_edges<br/>添加边]
    end
    
    subgraph "WorkflowRouter"
        RV[route_after_validation<br/>验证后路由]
        RH[route_after_human_review<br/>审核后路由]
    end
    
    subgraph "Node Runners"
        R1[IntentAnalysisRunner]
        R2[CurriculumDesignRunner]
        R3[ValidationRunner]
        R4[EditorRunner]
        R5[ReviewRunner]
        R6[ContentRunner]
    end
    
    Init --> SM
    Init --> AF
    Init --> CP
    Create --> Build
    Build --> Nodes
    Build --> Edges
    Build --> RV
    Build --> RH
    Exec --> Graph
    Exec --> R1
    Exec --> R2
    Exec --> R3
    Exec --> R4
    Exec --> R5
    Exec --> R6
    
    style OrchestratorFactory fill:#fff3e0
    style WorkflowExecutor fill:#e1f5ff
    style WorkflowBuilder fill:#f3e5f5
    style WorkflowRouter fill:#e8f5e9
```

---

## 🔐 错误处理流程

```mermaid
sequenceDiagram
    participant Runner as Node Runner
    participant EH as ErrorHandler
    participant Logger as ExecutionLogger
    participant Notif as NotificationService
    participant Repo as Repository
    
    Runner->>EH: 进入错误处理上下文
    EH->>Logger: 记录开始日志
    EH->>Notif: 发送进度通知
    
    alt 执行成功
        Runner->>Runner: 执行业务逻辑
        Runner->>EH: 返回结果
        EH->>Logger: 记录成功日志
        EH->>Notif: 发送成功通知
    else 执行失败
        Runner->>EH: 抛出异常
        EH->>Logger: 记录错误日志
        EH->>Notif: 发送失败通知
        EH->>Repo: 更新任务状态为failed
        EH->>Runner: 重新抛出异常
    end
```

---

## 📊 数据流图

```mermaid
graph LR
    subgraph "用户请求"
        UR[UserRequest]
    end
    
    subgraph "Intent Analysis"
        IA[IntentAnalysisOutput<br/>roadmap_id生成]
    end
    
    subgraph "Curriculum Design"
        RF[RoadmapFramework<br/>完整结构]
    end
    
    subgraph "Validation"
        VR[ValidationResult<br/>验证结果]
    end
    
    subgraph "Human Review"
        HR[HumanReview<br/>审核反馈]
    end
    
    subgraph "Content Generation"
        TUT[Tutorials]
        RES[Resources]
        QZ[Quizzes]
    end
    
    subgraph "数据库"
        TASK[RoadmapTask]
        META[RoadmapMetadata]
        CONTENT[Content Tables]
    end
    
    UR --> IA
    IA --> RF
    IA --> TASK
    RF --> VR
    RF --> META
    VR --> HR
    HR --> TUT
    HR --> RES
    HR --> QZ
    TUT --> CONTENT
    RES --> CONTENT
    QZ --> CONTENT
    
    style UR fill:#e3f2fd
    style IA fill:#fff9c4
    style RF fill:#e8f5e9
    style VR fill:#f3e5f5
    style HR fill:#ffecb3
    style TASK fill:#ffcdd2
    style META fill:#ffcdd2
    style CONTENT fill:#ffcdd2
```

---

## 🎯 Agent调用链

```mermaid
sequenceDiagram
    participant Runner
    participant Factory as AgentFactory
    participant Agent
    participant LLM as LiteLLM
    participant Tool
    
    Runner->>Factory: create_xxx_agent()
    Factory->>Agent: 创建Agent实例
    Factory-->>Runner: 返回Agent
    
    Runner->>Agent: execute(input_data)
    Agent->>Agent: 构建Prompt
    Agent->>LLM: 调用LLM
    
    alt 需要Tool调用
        LLM-->>Agent: tool_calls
        Agent->>Tool: 执行Tool
        Tool-->>Agent: Tool结果
        Agent->>LLM: 传递结果
    end
    
    LLM-->>Agent: LLM响应
    Agent->>Agent: 解析输出
    Agent-->>Runner: 返回结构化结果
```

---

## 💾 Repository模式

```mermaid
graph TB
    subgraph "Service Layer"
        SVC[RoadmapService]
    end
    
    subgraph "Repository Factory"
        RF[RepositoryFactory]
    end
    
    subgraph "Base Repository"
        BASE[BaseRepository&lt;T&gt;<br/>泛型基类]
    end
    
    subgraph "Concrete Repositories"
        TR[TaskRepository]
        RMR[RoadmapMetadataRepository]
        TUR[TutorialRepository]
        RSR[ResourceRepository]
        QR[QuizRepository]
    end
    
    subgraph "Database"
        DB[(PostgreSQL)]
    end
    
    SVC --> RF
    RF --> BASE
    BASE --> TR
    BASE --> RMR
    BASE --> TUR
    BASE --> RSR
    BASE --> QR
    
    TR --> DB
    RMR --> DB
    TUR --> DB
    RSR --> DB
    QR --> DB
    
    style SVC fill:#e3f2fd
    style RF fill:#fff9c4
    style BASE fill:#e8f5e9
    style DB fill:#ffcdd2
```
---

## 状态与阶段枚举定义

### 任务状态枚举 (Task Status)

**表:** `roadmap_tasks.status`

| 状态值 | 说明 | 使用场景 |
|:---|:---|:---|
| `pending` | 待处理 | 任务已创建，等待开始执行 |
| `processing` | 处理中 | 任务正在执行工作流 |
| `human_review_pending` | 等待人工审核 | 工作流在 Human-in-the-Loop 节点暂停 |
| `completed` | 已完成 | 任务成功完成（所有内容生成成功） |
| `partial_failure` | 部分失败 | 框架生成成功，部分内容生成失败 |
| `failed` | 失败 | 任务执行失败（框架生成或关键步骤失败） |

### 内容状态枚举 (Content Status)

**表:** `tutorial_metadata.content_status`, `resource_recommendation_metadata.status`, `quiz_metadata.status`

| 状态值 | 说明 | 使用场景 |
|:---|:---|:---|
| `pending` | 待生成 | 内容尚未开始生成 |
| `generating` | 生成中 | 内容正在生成（前端实时状态，不存储到数据库） |
| `completed` | 已完成 | 内容生成成功 |
| `failed` | 失败 | 内容生成失败 |

### 工作流步骤枚举 (Workflow Steps)

**字段:** `roadmap_tasks.current_step`

以下步骤按工作流执行顺序排列：

| 步骤值 | 说明 | 对应 Node Runner | 使用的 Agent |
|:---|:---|:---|:---|
| `init` | 初始化 | - | - |
| `queued` | 已入队 | - | - |
| `starting` | 启动中 | - | - |
| `intent_analysis` | 需求分析 | IntentAnalysisRunner | IntentAnalyzerAgent |
| `curriculum_design` | 课程设计 | CurriculumDesignRunner | CurriculumArchitectAgent |
| `structure_validation` | 结构验证 | ValidationRunner | StructureValidatorAgent |
| `human_review` | 人工审核 | ReviewRunner | - |
| `roadmap_edit` | 路线图修正 | EditorRunner | RoadmapEditorAgent |
| `content_generation` | 内容生成 | ContentRunner | 3个Agent并行 |
| `tutorial_generation` | 教程生成 | (ContentRunner) | TutorialGeneratorAgent |
| `resource_recommendation` | 资源推荐 | (ContentRunner) | ResourceRecommenderAgent |
| `quiz_generation` | 测验生成 | (ContentRunner) | QuizGeneratorAgent |
| `finalizing` | 收尾中 | - | - |
| `completed` | 已完成 | - | - |
| `failed` | 失败 | - | - |

### 工作流节点说明

| Node Runner | 职责 | 输入 | 输出 | 跳过条件 |
|:---|:---|:---|:---|:---|
| **IntentAnalysisRunner** | 分析用户需求 | UserRequest | IntentAnalysisOutput + roadmap_id | - |
| **CurriculumDesignRunner** | 设计课程框架 | IntentAnalysisOutput | RoadmapFramework | - |
| **ValidationRunner** | 验证结构合理性 | RoadmapFramework | ValidationResult | SKIP_STRUCTURE_VALIDATION=true |
| **EditorRunner** | 修正路线图 | RoadmapFramework + feedback | RoadmapFramework | (条件触发) |
| **ReviewRunner** | 等待人工审核 | RoadmapFramework | approved/rejected | SKIP_HUMAN_REVIEW=true |
| **ContentRunner** | 并行生成内容 | RoadmapFramework | ContentResults | SKIP_*_GENERATION |

---

## Agent 架构设计

### Agent 统一接口 (Protocol)

所有 Agent 必须实现统一的 `Agent` Protocol:

```python
from typing import Protocol, TypeVar, Generic

InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')

class Agent(Protocol[InputT, OutputT]):
    """Agent 统一接口规范"""
    agent_id: str
    
    async def execute(self, input_data: InputT) -> OutputT:
        """执行 Agent 逻辑
        
        Args:
            input_data: Agent 输入数据
            
        Returns:
            Agent 输出结果
        """
        ...
```

### 10 个 Agent 职责列表

| Agent ID | 名称 | 职责 | 依赖工具 | 输入类型 | 输出类型 |
|:---|:---|:---|:---|:---|:---|
| **A1** | IntentAnalyzerAgent<br/>需求分析师 | 解析用户学习需求，提取关键技术栈、难度画像 | Web Search | UserRequest | IntentAnalysisOutput |
| **A2** | CurriculumArchitectAgent<br/>课程架构师 | 设计三层学习路线图框架（Stage → Module → Concept） | Web Search | dict | CurriculumDesignOutput |
| **A3** | StructureValidatorAgent<br/>结构审查员 | 验证路线图的逻辑性、完整性和合理性 | 无 | RoadmapFramework | ValidationOutput |
| **A4** | RoadmapEditorAgent<br/>路线图编辑师 | 基于验证问题或人工反馈修正路线图框架 | Web Search | dict | CurriculumDesignOutput |
| **A5** | TutorialGeneratorAgent<br/>教程生成器 | 为每个 Concept 生成详细教程内容（Markdown） | Web Search, S3 | dict | TutorialGenerationOutput |
| **A6** | ResourceRecommenderAgent<br/>资源推荐师 | 为每个 Concept 搜索推荐学习资源（文章、视频等） | Web Search | dict | ResourceRecommendationOutput |
| **A7** | QuizGeneratorAgent<br/>测验生成器 | 为每个 Concept 生成测验题目（选择题、问答题） | 无 | dict | QuizGenerationOutput |
| **A8** | TutorialModifierAgent<br/>教程修改器 | 根据用户反馈修改教程内容 | Web Search, S3 | dict | TutorialGenerationOutput |
| **A9** | ResourceModifierAgent<br/>资源修改器 | 根据用户反馈修改推荐资源 | Web Search | dict | ResourceRecommendationOutput |
| **A10** | QuizModifierAgent<br/>测验修改器 | 根据用户反馈修改测验题目 | 无 | dict | QuizGenerationOutput |

### Agent 创建方式

使用 `AgentFactory` 创建 Agent 实例（推荐）:

```python
from app.agents.factory import AgentFactory

# 创建工厂实例
agent_factory = AgentFactory(settings)

# 创建具体 Agent
intent_agent = agent_factory.create_intent_analyzer()
curriculum_agent = agent_factory.create_curriculum_architect()
tutorial_agent = agent_factory.create_tutorial_generator()

# 执行 Agent
result = await intent_agent.execute(user_request)
```

---

## 开发规范

### 1. Agent 开发规范

#### 1.1 Agent 基类

所有 Agent 必须继承 `BaseAgent` 基类:

```python
from app.agents.base import BaseAgent
from app.models.domain import MyInput, MyOutput

class MyAgent(BaseAgent):
    """自定义 Agent 示例"""
    
    def __init__(self, settings):
        super().__init__(
            agent_id="my_agent",
            model_provider=settings.MY_AGENT_PROVIDER,
            model_name=settings.MY_AGENT_MODEL,
            base_url=settings.MY_AGENT_BASE_URL,
            api_key=settings.MY_AGENT_API_KEY,
            temperature=0.7,
            max_tokens=4096,
        )
    
    async def execute(self, input_data: MyInput) -> MyOutput:
        """Agent 核心处理逻辑（统一接口方法）"""
        # 1. 加载 Prompt 模板
        prompt = await self.load_prompt("my_agent.j2", **input_data.model_dump())
        
        # 2. 调用 LLM
        response = await self.call_llm(prompt, tools=self._get_tools())
        
        # 3. 解析输出并验证
        return MyOutput.model_validate_json(response)
```

#### 1.2 Agent 接口规范

所有 Agent 必须实现统一的 `Agent` Protocol:

```python
from app.agents.protocol import Agent

class MyAgent(BaseAgent, Agent[MyInput, MyOutput]):
    """实现 Protocol 接口"""
    agent_id = "my_agent"  # 必须定义
    
    async def execute(self, input_data: MyInput) -> MyOutput:
        """必须实现 execute 方法"""
        pass
```

#### 1.3 Agent 职责原则

✅ **单一职责**: 每个 Agent 只负责一个明确的任务  
✅ **输入输出明确**: 使用 Pydantic 模型定义类型  
✅ **工具使用规范**: 通过 LiteLLM 的 tool_calls 机制调用工具  
✅ **错误处理**: 使用 `tenacity` 实现重试机制（已在 BaseAgent 中）  
✅ **日志记录**: 使用 `structlog` 记录关键操作  

#### 1.4 Agent 配置

Agent 配置通过环境变量加载（每个 Agent 独立配置）:

```bash
# Intent Analyzer
ANALYZER_PROVIDER=openai
ANALYZER_MODEL=gpt-4o-mini
ANALYZER_BASE_URL=
ANALYZER_API_KEY=sk-...

# Curriculum Architect
ARCHITECT_PROVIDER=anthropic
ARCHITECT_MODEL=claude-3-5-sonnet-20241022
ARCHITECT_BASE_URL=
ARCHITECT_API_KEY=sk-ant-...

# Tutorial Generator
TUTORIAL_PROVIDER=openai
TUTORIAL_MODEL=gpt-4o
TUTORIAL_BASE_URL=
TUTORIAL_API_KEY=sk-...
```

---

### 2. Prompt 开发规范

#### 2.1 Prompt 模板位置

所有 Prompt 模板存放在 `backend/prompts/` 目录，使用 `.j2` 扩展名（Jinja2 模板）。

**命名规范**:
- Agent Prompt: `<agent_name>.j2`（如 `intent_analyzer.j2`）
- 修改类 Prompt: `<agent_name>_modify.j2`（如 `tutorial_modifier.j2`）

#### 2.2 Prompt 模板结构

标准 Prompt 模板应包含以下7个部分:

```jinja2
{# 1. Role Definition - 角色定义 #}
你是 {{ agent_name }}，{{ role_description }}

{# 2. Context Injection - 上下文注入 #}
当前任务上下文：
- 用户学习目标：{{ user_goal }}
- 已完成步骤：{{ execution_history | join(", ") }}
- 当前阶段：{{ current_step }}

{# 3. Constraints & Rules - 约束和规则 #}
工作规范：
{{ constraints | to_list }}

{# 4. Input Data - 输入数据 #}
用户输入：
{{ input_data | tojson(indent=2) }}

{# 5. Output Format - 输出格式 #}
输出必须严格遵循以下 JSON Schema：
```json
{{ output_schema | tojson(indent=2) }}
```

{# 6. Tool Usage Guide - 工具使用指南 #}
可用工具：
{% for tool in tools %}
- {{ tool.name }}: {{ tool.description }}
{% endfor %}

{# 7. Examples (Few-shot) - 示例 #}
{% if examples %}
参考示例：
{{ examples | to_markdown }}
{% endif %}
```

#### 2.3 Prompt 加载

使用 `BaseAgent.load_prompt()` 方法加载模板:

```python
# 在 Agent 的 execute 方法中
prompt = await self.load_prompt(
    template_name="my_agent.j2",
    agent_name="我的 Agent",
    user_goal=input_data.learning_goal,
    input_data=input_data.model_dump(),
    # ... 其他模板变量
)
```

#### 2.4 Prompt 最佳实践

✅ **明确角色**: 清晰定义 Agent 的角色和职责  
✅ **结构化输出**: 使用 JSON Schema 严格约束输出格式  
✅ **Few-shot 学习**: 提供 2-3 个高质量示例  
✅ **工具使用说明**: 明确说明何时、如何使用工具  
✅ **错误预防**: 在 Prompt 中列举常见错误和避免方法  

---

### 3. Node Runner 开发规范

#### 3.1 Runner 基本结构

所有 Node Runner 应遵循统一结构:

```python
from app.core.orchestrator.base import RoadmapState
from app.core.error_handler import error_handler

class MyRunner:
    """自定义 Node Runner"""
    
    def __init__(self, agent_factory, settings):
        self.agent_factory = agent_factory
        self.settings = settings
    
    async def run(self, state: RoadmapState) -> dict:
        """执行节点逻辑（统一入口方法）"""
        trace_id = state["trace_id"]
        
        # 使用统一错误处理器
        async with error_handler.handle_node_execution(
            node_name="my_node",
            trace_id=trace_id,
            step_display_name="我的节点"
        ) as ctx:
            # 1. 创建 Agent
            agent = self.agent_factory.create_my_agent()
            
            # 2. 执行 Agent
            result = await agent.execute(state["input_data"])
            
            # 3. 更新数据库（如需要）
            await self._update_database(trace_id, result)
            
            # 4. 存储结果
            ctx["result"] = {
                "my_output": result,
                "current_step": "my_node",
            }
        
        return ctx["result"]
    
    async def _update_database(self, trace_id: str, result) -> None:
        """数据库更新逻辑"""
        pass
```

#### 3.2 Runner 职责划分

| Runner | 职责 | 不应该做 |
|:---|:---|:---|
| **IntentAnalysisRunner** | 调用 Agent、更新任务状态 | ❌ 业务逻辑计算 |
| **CurriculumDesignRunner** | 调用 Agent、保存框架到 DB | ❌ 数据验证（由 Validator） |
| **ValidationRunner** | 调用 Validator Agent、判断重试 | ❌ 修改框架（由 Editor） |
| **EditorRunner** | 调用 Editor Agent、更新框架 | ❌ 路由逻辑（由 Router） |
| **ReviewRunner** | 等待人工审核（Interrupt） | ❌ 自动审核逻辑 |
| **ContentRunner** | 并行生成3种内容、汇总结果 | ❌ 内容生成逻辑（由 Agent） |

#### 3.3 错误处理规范

**必须使用统一的 ErrorHandler**:

```python
# ✅ 正确：使用统一错误处理器
async with error_handler.handle_node_execution("my_node", trace_id, "节点名") as ctx:
    result = await agent.execute(input_data)
    ctx["result"] = result
return ctx["result"]

# ❌ 错误：自己写 try-except
try:
    result = await agent.execute(input_data)
    await logger.log(...)
    await notification_service.publish(...)
    return result
except Exception as e:
    await logger.error(...)
    await notification_service.publish_failed(...)
    raise
```

---

### 4. Repository 开发规范

#### 4.1 Repository 基本结构

所有 Repository 必须继承 `BaseRepository`:

```python
from app.db.repositories.base import BaseRepository
from app.models.database import MyModel

class MyRepository(BaseRepository[MyModel]):
    """自定义 Repository"""
    
    async def get_by_custom_field(self, field_value: str) -> MyModel | None:
        """自定义查询方法"""
        query = select(MyModel).where(MyModel.custom_field == field_value)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_list_with_filter(
        self, 
        filter_field: str,
        limit: int = 10
    ) -> list[MyModel]:
        """批量查询"""
        query = (
            select(MyModel)
            .where(MyModel.filter_field == filter_field)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return result.scalars().all()
```

#### 4.2 Repository 使用规范

**使用 RepositoryFactory 创建**:

```python
from app.db.repository_factory import RepositoryFactory

repo_factory = RepositoryFactory()

# 方式1：使用上下文管理器（推荐）
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    task = await task_repo.get_by_task_id(task_id)
    await session.commit()

# 方式2：手动管理 session
from app.db.session import AsyncSessionLocal
async with AsyncSessionLocal() as session:
    task_repo = repo_factory.create_task_repo(session)
    await task_repo.update_status(task_id, "completed")
    await session.commit()
```

#### 4.3 Repository 职责边界

✅ **应该做**:
- CRUD 操作（增删改查）
- 简单的过滤和排序
- 数据库事务管理
- SQL 查询构建

❌ **不应该做**:
- 业务逻辑计算
- 数据转换和聚合
- 外部服务调用
- 通知发送

---

### 5. API 开发规范

#### 5.1 API 端点结构

**拆分后的 API 结构**（8个独立文件）:

```python
# app/api/v1/endpoints/generation.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.roadmap_service import RoadmapService

router = APIRouter(prefix="/roadmaps", tags=["Generation"])

@router.post("/generate")
async def generate_roadmap(
    request: UserRequest,
    service: RoadmapService = Depends(get_roadmap_service),
) -> RoadmapGenerationResponse:
    """生成学习路线图
    
    Args:
        request: 用户请求（包含学习目标、偏好等）
        service: 路线图服务（依赖注入）
        
    Returns:
        RoadmapGenerationResponse: 生成结果（包含 task_id）
        
    Raises:
        HTTPException: 400 - 参数错误
        HTTPException: 500 - 服务器错误
    """
    try:
        result = await service.generate_roadmap(request)
        return RoadmapGenerationResponse(**result)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("generate_roadmap_failed", error=str(e))
        raise HTTPException(status_code=500, detail="路线图生成失败")
```

#### 5.2 数据模型规范

所有 API 输入输出必须使用 Pydantic 模型:

```python
from pydantic import BaseModel, Field

class MyRequest(BaseModel):
    """API 请求模型"""
    user_id: str = Field(..., description="用户 ID", min_length=1)
    data: str = Field(..., description="数据内容", min_length=1, max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user-123",
                "data": "example data"
            }
        }
```

#### 5.3 错误处理规范

```python
from fastapi import HTTPException, status

# ✅ 正确：使用标准 HTTP 状态码
@router.get("/roadmaps/{roadmap_id}")
async def get_roadmap(roadmap_id: str):
    roadmap = await roadmap_repo.get(roadmap_id)
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"路线图 {roadmap_id} 不存在"
        )
    return roadmap

# ✅ 正确：捕获特定异常
try:
    result = await service.process(data)
except ValidationError as e:
    raise HTTPException(status_code=400, detail=str(e))
except DatabaseError as e:
    logger.error("database_error", error=str(e))
    raise HTTPException(status_code=500, detail="数据库错误")
```

#### 5.4 API 文档规范

- ✅ 使用完整的 docstring（Args、Returns、Raises）
- ✅ 使用 `Field()` 的 `description` 参数
- ✅ 提供 `json_schema_extra` 示例
- ✅ 使用 OpenAPI tags 分组端点

---

### 6. 测试规范

#### 6.1 单元测试

```python
# tests/unit/test_my_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.my_agent import MyAgent

@pytest.mark.asyncio
async def test_my_agent_execute():
    """测试 Agent 执行逻辑"""
    # Mock dependencies
    mock_llm = AsyncMock(return_value='{"result": "test"}')
    
    # Create agent
    agent = MyAgent(settings)
    agent.call_llm = mock_llm
    
    # Execute
    result = await agent.execute(input_data)
    
    # Assert
    assert result.field == expected_value
    mock_llm.assert_called_once()
```

#### 6.2 集成测试

```python
# tests/integration/test_workflow.py
@pytest.mark.asyncio
async def test_full_workflow():
    """测试完整工作流"""
    # Initialize
    await OrchestratorFactory.initialize()
    executor = OrchestratorFactory.create_workflow_executor()
    
    # Execute
    result = await executor.execute(user_request, trace_id)
    
    # Assert
    assert result is not None
    assert state["roadmap_id"] is not None
```

#### 6.3 测试最佳实践

✅ **使用 pytest 和 pytest-asyncio**  
✅ **Mock 外部依赖**（LLM API、S3、Redis）  
✅ **使用测试数据库**（与生产环境隔离）  
✅ **测试覆盖率目标 > 80%**（核心模块 100%）  
✅ **测试文件命名**: `test_<module_name>.py`  
✅ **测试方法命名**: `test_<功能描述>`  

---

### 7. 代码质量标准

#### 7.1 文件大小限制

| 文件类型 | 最大行数 | 说明 |
|:---|:---:|:---|
| API Endpoint | 250 | 单个端点文件 |
| Node Runner | 200 | 单个 Runner 文件 |
| Repository | 200 | 单个 Repository 文件 |
| Agent | 300 | 单个 Agent 文件 |
| Service | 400 | 业务逻辑复杂度较高 |

#### 7.2 代码复杂度

- **循环复杂度**: < 10（单个函数/方法）
- **嵌套深度**: < 4 层
- **函数长度**: < 50 行（推荐 < 30 行）

#### 7.3 类型注解

**所有公共方法必须有完整类型注解**:

```python
# ✅ 正确
async def process_data(
    user_id: str,
    data: dict[str, Any],
    options: ProcessOptions | None = None
) -> ProcessResult:
    pass

# ❌ 错误（缺少类型注解）
async def process_data(user_id, data, options=None):
    pass
```

#### 7.4 文档字符串

**所有公共类和方法必须有文档字符串**:

```python
def my_function(param1: str, param2: int) -> bool:
    """函数功能简述
    
    Args:
        param1: 参数1说明
        param2: 参数2说明
        
    Returns:
        返回值说明
        
    Raises:
        ValueError: 何时抛出此异常
    """
    pass
```

---

## 目录结构（重构后 v2.0）

```
backend/
├── AGENT.md                           # ⭐ 本文档（统一开发规范）
├── PROJECT_COMPLETION.md              # 项目完成总结
├── app/
│   ├── agents/                        # ✨ Agent 层（10个Agent）
│   │   ├── __init__.py
│   │   ├── base.py                   # Agent 基类
│   │   ├── protocol.py               # ✨ Agent Protocol 接口
│   │   ├── factory.py                # ✨ AgentFactory
│   │   ├── intent_analyzer.py        # A1: 需求分析
│   │   ├── curriculum_architect.py   # A2: 课程设计
│   │   ├── structure_validator.py    # A3: 结构验证
│   │   ├── roadmap_editor.py         # A4: 路线图编辑
│   │   ├── tutorial_generator.py     # A5: 教程生成
│   │   ├── resource_recommender.py   # A6: 资源推荐
│   │   ├── quiz_generator.py         # A7: 测验生成
│   │   ├── tutorial_modifier.py      # A8: 教程修改
│   │   ├── resource_modifier.py      # A9: 资源修改
│   │   └── quiz_modifier.py          # A10: 测验修改
│   │
│   ├── api/                           # ✨ API 层（拆分后）
│   │   └── v1/
│   │       ├── router.py             # ✨ 统一路由
│   │       ├── endpoints/            # ✨ 8个独立端点
│   │       │   ├── __init__.py
│   │       │   ├── generation.py    # 生成/状态查询
│   │       │   ├── retrieval.py     # 路线图获取
│   │       │   ├── approval.py      # 人工审核
│   │       │   ├── tutorial.py      # 教程管理
│   │       │   ├── resource.py      # 资源管理
│   │       │   ├── quiz.py          # 测验管理
│   │       │   ├── modification.py  # 内容修改
│   │       │   └── retry.py         # 失败重试
│   │       ├── schemas/              # API Schema定义
│   │       │   └── __init__.py
│   │       └── websocket.py          # WebSocket 端点
│   │
│   ├── core/                          # ✨ 编排层（重构后）
│   │   ├── orchestrator_factory.py  # ✨ Orchestrator 工厂（单例）
│   │   ├── error_handler.py         # ✨ 统一错误处理
│   │   ├── tool_registry.py
│   │   ├── dependencies.py
│   │   └── orchestrator/            # ✨ Orchestrator 模块（14个文件）
│   │       ├── __init__.py
│   │       ├── base.py              # State、Config 定义
│   │       ├── state_manager.py     # 状态管理器
│   │       ├── builder.py           # 工作流构建器
│   │       ├── executor.py          # 工作流执行器
│   │       ├── routers.py           # 工作流路由
│   │       └── node_runners/        # ✨ 6个 Node Runner
│   │           ├── __init__.py
│   │           ├── intent_runner.py
│   │           ├── curriculum_runner.py
│   │           ├── validation_runner.py
│   │           ├── editor_runner.py
│   │           ├── review_runner.py
│   │           └── content_runner.py
│   │
│   ├── services/                      # 服务层
│   │   ├── roadmap_service.py        # 核心业务逻辑
│   │   ├── notification_service.py   # 实时通知服务
│   │   └── execution_logger.py       # 执行日志服务
│   │
│   ├── db/                            # ✨ 数据访问层（重构后）
│   │   ├── session.py                # 数据库会话
│   │   ├── repository_factory.py    # ✨ Repository 工厂
│   │   └── repositories/            # ✨ 9个独立 Repository
│   │       ├── __init__.py
│   │       ├── base.py              # ✨ BaseRepository<T>
│   │       ├── task_repo.py         # 任务管理
│   │       ├── roadmap_meta_repo.py # 路线图元数据
│   │       ├── tutorial_repo.py     # 教程版本管理
│   │       ├── resource_repo.py     # 资源推荐
│   │       ├── quiz_repo.py         # 测验管理
│   │       ├── intent_analysis_repo.py
│   │       ├── user_profile_repo.py
│   │       └── execution_log_repo.py
│   │
│   ├── models/                        # 数据模型
│   │   ├── domain.py                 # Pydantic 领域模型
│   │   ├── database.py               # SQLAlchemy ORM 模型
│   │   └── protocol.py               # Protocol 接口定义
│   │
│   ├── tools/                         # 工具层
│   │   ├── base.py                   # Tool 基类
│   │   ├── search/                   # Web 搜索
│   │   │   └── web_search.py
│   │   ├── storage/                  # 对象存储
│   │   │   └── s3_client.py
│   │   └── validation/               # 数据验证
│   │
│   ├── config/                        # 配置
│   │   ├── settings.py               # 应用配置
│   │   └── logging_config.py         # 日志配置
│   │
│   ├── utils/                         # 工具函数
│   │   ├── prompt_loader.py          # Prompt 加载器
│   │   ├── cost_tracker.py           # 成本追踪
│   │   ├── tracing.py                # 链路追踪
│   │   └── async_helpers.py
│   │
│   └── main.py                        # ⭐ 应用入口
│
├── prompts/                           # Prompt 模板目录
│   ├── intent_analyzer.j2
│   ├── curriculum_architect.j2
│   ├── structure_validator.j2
│   ├── roadmap_editor.j2
│   ├── tutorial_generator.j2
│   ├── resource_recommender.j2
│   ├── quiz_generator.j2
│   ├── tutorial_modifier.j2          # ✨ 新增
│   ├── resource_modifier.j2          # ✨ 新增
│   └── quiz_modifier.j2              # ✨ 新增
│
├── tests/                             # ✨ 测试代码（重构后）
│   ├── conftest.py                   # Pytest 配置
│   ├── unit/                         # 单元测试
│   │   ├── test_error_handler.py    # ✨ 错误处理测试
│   │   ├── test_repository_base.py  # ✨ Repository 基类测试
│   │   └── test_orchestrator_components.py
│   ├── integration/                  # 集成测试
│   │   ├── test_orchestrator_workflow.py  # ✨ 工作流测试
│   │   ├── test_e2e_simple_workflow.py    # ✨ E2E 简化测试
│   │   ├── test_human_in_loop.py          # ✨ HIL 测试
│   │   └── test_repository_factory.py     # ✨ Repository 工厂测试
│   └── e2e/                          # 端到端测试
│       ├── test_real_workflow.py         # 真实环境测试
│       └── test_real_workflow_mocked.py  # ✨ Mock 环境测试
│
├── alembic/                           # 数据库迁移
│   ├── versions/
│   │   └── phase3_add_composite_indexes.py  # ✨ 数据库优化
│   └── env.py
│
├── scripts/                           # 脚本工具
│   ├── test_full_with_db_check.sh    # 完整测试脚本
│   ├── test_streaming_timestamp.py
│   ├── visualize_architecture.py     # 架构可视化
│   └── diagnose_db.py                # 数据库诊断
│
└── docs/                              # ✨ 完整文档体系（46个文档）
    ├── ARCHITECTURE_DIAGRAM.md        # ✨ 架构图集（9个图）
    ├── REFACTORING_MIGRATION_GUIDE.md # ✨ 迁移指南
    ├── REFACTORING_TASKS.md           # 重构任务清单
    ├── INTEGRATION_TEST_REPORT.md     # ✨ 集成测试报告
    ├── PHASE5_COMPLETION_SUMMARY.md   # 阶段5完成总结
    ├── REPOSITORY_USAGE_GUIDE.md      # Repository 使用指南
    ├── 重构最终完成报告.md             # ✨ 最终总结
    └── ...（其他文档）
```

### 关键目录说明

| 目录 | 说明 | 文件数 | 特点 |
|:---|:---|:---:|:---|
| `app/agents/` | Agent 实现 | 12个 | Protocol 统一接口 |
| `app/api/v1/endpoints/` | API 端点 | 8个 | < 250 行/文件 |
| `app/core/orchestrator/` | 编排模块 | 14个 | < 200 行/文件 |
| `app/db/repositories/` | 数据访问 | 9个 | 泛型基类 BaseRepository<T> |
| `prompts/` | Prompt 模板 | 10个 | Jinja2 模板 |
| `tests/` | 测试代码 | 20+个 | 89.8% 通过率 |
| `docs/` | 项目文档 | 46个 | 包含架构图、迁移指南 |

---

## 环境变量配置

### 必需配置

#### 1. 数据库配置

```bash
# PostgreSQL 数据库
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=roadmap_agent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password

# LangGraph Checkpointer 数据库（通常与主库相同）
CHECKPOINTER_DATABASE_URL=postgresql+asyncpg://postgres:your_secure_password@localhost:5432/roadmap_agent
```

#### 2. 对象存储配置

```bash
# S3 / MinIO / Aliyun OSS
S3_ENDPOINT_URL=http://localhost:9000              # MinIO 本地开发
# S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com  # 阿里云 OSS
S3_ACCESS_KEY_ID=your_access_key
S3_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=roadmap-content
S3_REGION=us-east-1                                # 或 cn-hangzhou（阿里云）
```

#### 3. Agent LLM 配置

**每个 Agent 都需要独立配置**:

```bash
# A1: Intent Analyzer（需求分析）
ANALYZER_PROVIDER=openai
ANALYZER_MODEL=gpt-4o-mini
ANALYZER_BASE_URL=                    # 可选，默认使用官方 API
ANALYZER_API_KEY=sk-...

# A2: Curriculum Architect（课程设计）
ARCHITECT_PROVIDER=anthropic
ARCHITECT_MODEL=claude-3-5-sonnet-20241022
ARCHITECT_BASE_URL=
ARCHITECT_API_KEY=sk-ant-...

# A3: Structure Validator（结构验证）
VALIDATOR_PROVIDER=openai
VALIDATOR_MODEL=gpt-4o-mini
VALIDATOR_BASE_URL=
VALIDATOR_API_KEY=sk-...

# A4: Roadmap Editor（路线图编辑）
EDITOR_PROVIDER=openai
EDITOR_MODEL=gpt-4o
EDITOR_BASE_URL=
EDITOR_API_KEY=sk-...

# A5: Tutorial Generator（教程生成）
TUTORIAL_PROVIDER=openai
TUTORIAL_MODEL=gpt-4o
TUTORIAL_BASE_URL=
TUTORIAL_API_KEY=sk-...

# A6: Resource Recommender（资源推荐）
RESOURCE_PROVIDER=openai
RESOURCE_MODEL=gpt-4o-mini
RESOURCE_BASE_URL=
RESOURCE_API_KEY=sk-...

# A7: Quiz Generator（测验生成）
QUIZ_PROVIDER=openai
QUIZ_MODEL=gpt-4o-mini
QUIZ_BASE_URL=
QUIZ_API_KEY=sk-...

# A8-A10: Modifier Agents（修改类 Agent）
MODIFIER_PROVIDER=openai
MODIFIER_MODEL=gpt-4o
MODIFIER_BASE_URL=
MODIFIER_API_KEY=sk-...
```

---

### 可选配置

#### 1. 工作流跳过配置（开发/测试用）

```bash
# 跳过结构验证（快速测试）
SKIP_STRUCTURE_VALIDATION=false

# 跳过人工审核（自动通过）
SKIP_HUMAN_REVIEW=false

# 跳过内容生成（仅生成框架）
SKIP_TUTORIAL_GENERATION=false
SKIP_RESOURCE_RECOMMENDATION=false
SKIP_QUIZ_GENERATION=false
```

#### 2. Redis 配置（实时通知缓存）

```bash
# Redis 连接（可选，用于 WebSocket 通知）
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=                        # 可选
```

#### 3. 日志配置

```bash
# 日志级别
LOG_LEVEL=INFO                         # DEBUG, INFO, WARNING, ERROR, CRITICAL

# 结构化日志格式
LOG_FORMAT=json                        # json 或 console
```

#### 4. 性能配置

```bash
# 数据库连接池
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# LLM 超时设置
LLM_TIMEOUT=180                        # 秒
LLM_MAX_RETRIES=3

# 并发控制
MAX_CONCURRENT_TASKS=10
```

---

### 配置文件示例

**开发环境** (`.env.development`):

```bash
# 数据库
POSTGRES_HOST=localhost
POSTGRES_DB=roadmap_agent_dev
CHECKPOINTER_DATABASE_URL=postgresql+asyncpg://postgres:dev@localhost:5432/roadmap_agent_dev

# 对象存储（MinIO 本地）
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin

# 跳过配置（加速开发）
SKIP_STRUCTURE_VALIDATION=true
SKIP_HUMAN_REVIEW=true

# 日志
LOG_LEVEL=DEBUG
```

**生产环境** (`.env.production`):

```bash
# 数据库
POSTGRES_HOST=prod-db.example.com
POSTGRES_DB=roadmap_agent_prod
CHECKPOINTER_DATABASE_URL=postgresql+asyncpg://user:pass@prod-db.example.com:5432/roadmap_agent_prod

# 对象存储（阿里云 OSS）
S3_ENDPOINT_URL=https://oss-cn-hangzhou.aliyuncs.com
S3_ACCESS_KEY_ID=your_prod_key
S3_SECRET_ACCESS_KEY=your_prod_secret

# 生产配置（全部启用）
SKIP_STRUCTURE_VALIDATION=false
SKIP_HUMAN_REVIEW=false
SKIP_TUTORIAL_GENERATION=false

# 日志
LOG_LEVEL=INFO
LOG_FORMAT=json
```

---

## 常见问题 FAQ

### Q1: 如何添加新的 Agent？

**步骤**:

1. **创建 Agent 类**（继承 `BaseAgent`，实现 `Agent` Protocol）

```python
# app/agents/my_new_agent.py
from app.agents.base import BaseAgent
from app.agents.protocol import Agent

class MyNewAgent(BaseAgent, Agent[MyInput, MyOutput]):
    agent_id = "my_new_agent"
    
    def __init__(self, settings):
        super().__init__(
            agent_id=self.agent_id,
            model_provider=settings.MY_NEW_AGENT_PROVIDER,
            model_name=settings.MY_NEW_AGENT_MODEL,
            # ...
        )
    
    async def execute(self, input_data: MyInput) -> MyOutput:
        prompt = await self.load_prompt("my_new_agent.j2", **input_data.model_dump())
        response = await self.call_llm(prompt)
        return MyOutput.model_validate_json(response)
```

2. **创建 Prompt 模板** (`prompts/my_new_agent.j2`)

3. **在 AgentFactory 中注册**

```python
# app/agents/factory.py
def create_my_new_agent(self) -> MyNewAgent:
    return MyNewAgent(self.settings)
```

4. **配置环境变量**

```bash
MY_NEW_AGENT_PROVIDER=openai
MY_NEW_AGENT_MODEL=gpt-4o
MY_NEW_AGENT_API_KEY=sk-...
```

5. **在 Runner 中使用**

```python
agent = self.agent_factory.create_my_new_agent()
result = await agent.execute(input_data)
```

---

### Q2: 如何调试工作流状态？

**方法1: 使用 LangGraph Checkpointer 查询状态**

```python
from app.core.orchestrator_factory import OrchestratorFactory

# 获取 StateManager
state_manager = OrchestratorFactory._state_manager

# 查询当前状态
state = await state_manager.get_state(trace_id)
print(f"Current step: {state.get('current_step')}")
print(f"Roadmap ID: {state.get('roadmap_id')}")
print(f"History: {state.get('execution_history')}")
```

**方法2: 查询数据库**

```python
from app.db.repository_factory import RepositoryFactory

repo_factory = RepositoryFactory()
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    task = await task_repo.get_by_task_id(trace_id)
    print(f"Status: {task.status}")
    print(f"Current step: {task.current_step}")
```

**方法3: 查看执行日志**

```python
from app.db.repository_factory import RepositoryFactory

repo_factory = RepositoryFactory()
async with repo_factory.create_session() as session:
    log_repo = repo_factory.create_execution_log_repo(session)
    logs = await log_repo.get_logs_by_trace_id(trace_id)
    for log in logs:
        print(f"[{log.timestamp}] {log.step}: {log.message}")
```

---

### Q3: 如何处理 Agent 输出格式错误？

**问题**: Agent 返回的 JSON 格式不符合预期。

**解决方案**:

1. **在 Prompt 中明确输出格式**

```jinja2
输出必须严格遵循以下 JSON Schema（不要添加任何其他字段）:
```json
{
  "field1": "string",
  "field2": 123,
  "field3": ["array"]
}
```
```

2. **使用 Pydantic 验证**

```python
try:
    result = MyOutput.model_validate_json(response)
except ValidationError as e:
    logger.error("agent_output_validation_failed", error=str(e))
    # 重试或返回错误
```

3. **启用重试机制**（BaseAgent 已内置）

```python
# BaseAgent 中已有 @retry 装饰器
# 如果输出格式错误，会自动重试最多3次
```

---

### Q4: 如何并行运行多个工作流？

**答**: 系统已支持并发执行，每个工作流有独立的 `trace_id`（thread_id）。

```python
from app.core.orchestrator_factory import OrchestratorFactory
import asyncio

# 初始化（仅需一次）
await OrchestratorFactory.initialize()

# 创建执行器
executor = OrchestratorFactory.create_workflow_executor()

# 并行执行多个工作流
tasks = [
    executor.execute(user_request1, trace_id1),
    executor.execute(user_request2, trace_id2),
    executor.execute(user_request3, trace_id3),
]

results = await asyncio.gather(*tasks, return_exceptions=True)
```

**注意事项**:
- 每个工作流有独立的数据库会话
- LangGraph Checkpointer 支持多线程
- 建议设置 `MAX_CONCURRENT_TASKS` 限制并发数

---

### Q5: 如何修改 LLM 模型配置？

**临时修改**（不推荐）:

```python
agent = IntentAnalyzerAgent(settings)
agent.model_name = "gpt-4o"  # 临时修改
```

**永久修改**（推荐）:

1. **修改环境变量**

```bash
# .env
ANALYZER_MODEL=gpt-4o-mini  # 改为 gpt-4o
```

2. **重启应用**

```bash
uvicorn app.main:app --reload
```

---

### Q6: 如何测试单个 Agent？

```python
# tests/unit/test_my_agent.py
import pytest
from app.agents.my_agent import MyAgent
from app.config.settings import Settings

@pytest.mark.asyncio
async def test_my_agent_execute():
    """测试 Agent 执行"""
    # 创建 Agent
    settings = Settings()
    agent = MyAgent(settings)
    
    # 准备测试数据
    input_data = MyInput(field="test")
    
    # 执行
    result = await agent.execute(input_data)
    
    # 断言
    assert result is not None
    assert result.field == expected_value
```

---

### Q7: 如何处理 Human-in-the-Loop 恢复？

```python
from app.core.orchestrator_factory import OrchestratorFactory

# 初始化
await OrchestratorFactory.initialize()

# 创建执行器
executor = OrchestratorFactory.create_workflow_executor()

# 恢复工作流（人工审核后）
final_state = await executor.resume_after_human_review(
    task_id=trace_id,
    approved=True,       # True: 通过, False: 拒绝
    feedback="审核通过"   # 可选反馈
)
```

---

### Q8: 数据库迁移失败怎么办？

**问题**: `alembic upgrade head` 失败。

**解决方案**:

1. **检查数据库连接**

```bash
psql -h localhost -U postgres -d roadmap_agent
```

2. **查看当前版本**

```bash
poetry run alembic current
```

3. **回滚到上一个版本**

```bash
poetry run alembic downgrade -1
```

4. **重新应用迁移**

```bash
poetry run alembic upgrade head
```

5. **如果仍然失败，手动修复**

```bash
# 查看迁移历史
poetry run alembic history

# 标记版本（不执行 SQL）
poetry run alembic stamp <revision>
```

---

## 相关文档

### 架构文档
- 📊 [ARCHITECTURE_DIAGRAM.md](./docs/ARCHITECTURE_DIAGRAM.md) - 完整架构图集（9个图）
- 📝 [REFACTORING_MIGRATION_GUIDE.md](./docs/REFACTORING_MIGRATION_GUIDE.md) - 重构迁移指南
- 📋 [REFACTORING_TASKS.md](./docs/REFACTORING_TASKS.md) - 重构任务清单

### 开发指南
- 📖 [REPOSITORY_USAGE_GUIDE.md](./docs/REPOSITORY_USAGE_GUIDE.md) - Repository 使用指南
- 🧪 [INTEGRATION_TEST_REPORT.md](./docs/INTEGRATION_TEST_REPORT.md) - 集成测试报告
- 📘 [API 文档](http://localhost:8000/docs) - OpenAPI 自动生成文档

### 项目总结
- 🎉 [PROJECT_COMPLETION.md](./PROJECT_COMPLETION.md) - 项目完成公告
- 📄 [重构最终完成报告.md](./docs/重构最终完成报告.md) - 最终总结报告
- 📊 [PHASE5_COMPLETION_SUMMARY.md](./docs/PHASE5_COMPLETION_SUMMARY.md) - 阶段5完成总结

---

**文档版本**: v2.0.0（重构后）  
**最后更新**: 2025-12-06  
**维护者**: Backend Team  
**状态**: ✅ 生产就绪

---

> 💡 **提示**: 本文档是后端项目的统一开发规范，所有后端开发应遵循本文档的规范和最佳实践。
> 
> 如有疑问或需要补充，请联系 Backend Team 或提交 Issue。

