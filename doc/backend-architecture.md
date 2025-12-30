# 个性化学习路线图生成系统 - 后端架构设计文档

> **架构版本**: v2.0.0  
> **Agent 数量**: 5 个（Intent Analyzer, Curriculum Architect, Roadmap Editor, Structure Validator, Tutorial Generator）  
> **Tool 数量**: 2 个（Web Search, S3 Storage）  
> **Checkpointer**: AsyncPostgresSaver (LangGraph 官方组件)

## 1. 技术栈概览

### 1.1 核心技术栈

| 领域分类 | 组件/库名称 | 版本要求 | 决策理由 (Rationale) |
| :--- | :--- | :--- | :--- |
| **核心语言** | **Python** | 3.12+ | AI 生态首选。3.12 版本对 AsyncIO 有显著性能提升，且错误提示更友好。 |
| **Web 框架** | **FastAPI** | Latest | 现代异步框架标准。原生支持 AsyncIO，自动生成 OpenAPI 文档，与 Pydantic 完美结合。 |
| **Agent 编排** | **LangGraph** | Latest | 专为有状态、多 Agent、循环工作流设计的编排引擎，支持 Persistence 和 Human-in-the-Loop。 |
| **模型接口** | **LiteLLM** | Latest | 统一了 OpenAI, Azure, Anthropic 等百种模型的 I/O 格式，极大简化模型切换成本。 |
| **ORM** | **SQLModel** | Latest | **最佳实践**。结合 SQLAlchemy 2.0 与 Pydantic，避免了 API 模型与 DB 模型重复定义的问题，支持异步。 |
| **数据库 (SQL)** | **PostgreSQL** | 15+ | 工业级关系型数据库，用于存储用户、任务元数据及结构化产出。 |
| **数据库 (K/V)** | **Redis** | 7.0+ | 用于分布式锁、API 缓存（Checkpointer 已迁移至 PostgreSQL）。 |
| **日志系统** | **structlog** | Latest | **结构化日志标准**。支持上下文绑定（自动携带 `task_id`, `user_id`），完美适配异步环境与 ELK/Loki。 |
| **容错重试** | **tenacity** | Latest | 声明式重试库。用于处理 LLM API 限流、网络抖动等不稳定因素，增强系统韧性。 |
| **配置管理** | **pydantic-settings** | 2.0+ | 遵循 12-Factor App 原则，将环境变量（.env）安全地映射并校验为 Python 对象。 |
| **HTTP 客户端** | **httpx** | Latest | 下一代 HTTP 客户端，支持 HTTP/2 和完全异步调用，用于 Tool 层的外部 API 请求。 |
| **测试数据** | **polyfactory** | Dev Only | 基于 Pydantic 模型自动生成复杂的 Mock 数据，极大简化单元测试编写。 |
| **存储客户端** | **aioboto3** | Latest | **异步 S3 客户端**。标准 `boto3` 是同步阻塞的，会卡住 FastAPI 线程。R2 兼容 S3 协议，配合 `aioboto3` 可在异步架构中实现非阻塞的文件上传与下载。 |
| **Web 搜索** | **Tavily API** | Latest | 专业的 AI 搜索 API，提供高质量的搜索结果，用于 Agent 的联网搜索功能。 |

---

## 2. 项目结构

```text
/learning-roadmap-backend
├── pyproject.toml                    # Poetry/PDM 项目配置
├── .env.example                      # 环境变量模板
├── .env                              # 本地环境变量（Git忽略）
├── alembic.ini                       # 数据库迁移配置
├── docker-compose.yml                # 本地开发环境
│
├── /alembic                          # 数据库迁移脚本
│   ├── env.py
│   └── /versions
│
├── /app                              # 主应用目录
│   ├── __init__.py
│   ├── main.py                       # FastAPI 应用入口
│   │
│   ├── /config                       # 配置管理
│   │   ├── __init__.py
│   │   ├── settings.py               # Pydantic Settings
│   │   └── logging_config.py         # structlog 配置
│   │
│   ├── /api                          # API 路由层
│   │   ├── __init__.py
│   │   ├── dependencies.py           # FastAPI 依赖注入
│   │   ├── /v1                       # API v1
│   │   │   ├── __init__.py
│   │   │   ├── router.py             # 路由汇总
│   │   │   ├── roadmap.py            # 路线图相关端点
│   │   │   ├── tasks.py              # 任务状态查询
│   │   │   └── websocket.py          # WebSocket 实时推送
│   │
│   ├── /core                         # 核心引擎层
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # LangGraph 工作流编排器
│   │   ├── dependencies.py           # 依赖注入（Orchestrator 初始化）
│   │   ├── tool_registry.py          # 工具注册中心
│   │   └── /checkpointers            # 状态检查点
│   │       └── __init__.py           # 导出 AsyncPostgresSaver
│   │
│   ├── /agents                       # Agent 实现层 (5个Agent)
│   │   ├── __init__.py
│   │   ├── base.py                   # Agent 基类（封装 LiteLLM + LangGraph）
│   │   ├── intent_analyzer.py        # A1: 需求分析师 Agent
│   │   ├── curriculum_architect.py   # A2: 课程架构师 Agent
│   │   ├── roadmap_editor.py         # A2E: 路线图编辑师 Agent
│   │   ├── structure_validator.py    # A3: 结构审查员 Agent
│   │   └── tutorial_generator.py     # A4: 教程生成器 Agent
│   │
│   ├── /tools                        # 工具实现层 (2个Tool)
│   │   ├── __init__.py
│   │   ├── base.py                   # Tool 基类（统一接口）
│   │   ├── /search
│   │   │   └── web_search.py         # Web 搜索工具
│   │   └── /storage
│   │       └── s3_client.py          # S3/R2 存储客户端
│   │
│   ├── /models                       # 数据模型层
│   │   ├── __init__.py
│   │   ├── domain.py                 # 业务领域模型（Pydantic）
│   │   ├── database.py               # 数据库模型（SQLModel）
│   │   └── protocol.py               # 通信协议模型
│   │
│   ├── /services                     # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── roadmap_service.py        # 路线图生成服务
│   │   ├── task_service.py           # 任务管理服务
│   │   └── notification_service.py   # 通知服务（WebSocket）
│   │
│   ├── /db                           # 数据库操作层
│   │   ├── __init__.py
│   │   ├── session.py                # 数据库会话管理
│   │   ├── repositories              # 仓储模式
│   │   │   ├── __init__.py
│   │   │   ├── roadmap_repo.py
│   │   │   └── user_repo.py
│   │   └── redis_client.py           # Redis 客户端封装
│   │
│   ├── /middleware                   # 中间件
│   │   ├── __init__.py
│   │   ├── logging.py                # 请求日志中间件
│   │   ├── error_handler.py          # 统一异常处理
│   │   └── rate_limiter.py           # 限流中间件
│   │
│   └── /utils                        # 工具函数
│       ├── __init__.py
│       ├── tracing.py                # OpenTelemetry 追踪
│       ├── cost_tracker.py           # LLM 成本追踪
│       └── prompt_loader.py          # Prompt 模板加载器
│
├── /specs                            # 声明式 Agent/Workflow 配置（YAML）
│   ├── /agents
│   │   ├── intent_analyzer.yaml
│   │   ├── curriculum_architect.yaml
│   │   ├── roadmap_editor.yaml
│   │   ├── structure_validator.yaml
│   │   └── tutorial_generator.yaml
│   ├── /workflows
│   │   ├── main_flow.yaml
│   │   └── tutorial_generation.yaml
│   └── /tools
│       ├── web_search.yaml
│       └── s3_storage.yaml
│
├── /prompts                          # Prompt 模板（Jinja2）
│   ├── intent_analyzer.j2
│   ├── curriculum_architect.j2
│   ├── roadmap_editor.j2
│   ├── structure_validator.j2
│   └── tutorial_generator.j2
│
├── /tests                            # 测试套件
│   ├── /unit
│   │   ├── test_agents.py
│   │   └── test_tools.py
│   ├── /integration
│   │   ├── test_workflow.py
│   │   └── test_api.py
│   ├── /e2e
│   │   └── test_roadmap_generation.py
│   └── /fixtures
│       └── mock_data.py              # 使用 polyfactory 生成
│
└── /scripts                          # 运维脚本
    ├── init_db.py                    # 初始化数据库
    └── run_dev.sh                    # 本地开发启动脚本
```

---

## 3. 核心模块设计

### 3.1 FastAPI 应用入口 (`app/main.py`)

```python
"""
FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.config.settings import settings
from app.config.logging_config import setup_logging
from app.api.v1.router import api_router_v1
from app.middleware.logging import StructlogMiddleware
from app.middleware.error_handler import ExceptionHandlerMiddleware
from app.db.session import engine, init_db
from app.db.redis_client import redis_client

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    setup_logging()
    logger.info("application_startup", environment=settings.ENVIRONMENT)
    
    # 初始化数据库
    await init_db()
    
    # 预热 Redis 连接
    await redis_client.ping()
    logger.info("redis_connected")
    
    yield
    
    # 关闭时清理
    logger.info("application_shutdown")
    await engine.dispose()
    await redis_client.close()


app = FastAPI(
    title="Learning Roadmap Generation System",
    description="基于 Multi-Agent 的个性化学习路线图生成系统",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# 中间件注册
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(StructlogMiddleware)
app.add_middleware(ExceptionHandlerMiddleware)

# 注册路由
app.include_router(api_router_v1, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }
```

---

### 3.2 配置管理 (`app/config/settings.py`)

```python
"""
应用配置（基于 pydantic-settings）
"""
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ==================== 应用配置 ====================
    ENVIRONMENT: str = Field("development", description="运行环境")
    DEBUG: bool = Field(False, description="调试模式")
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Learning Roadmap System"
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"],
        description="允许的跨域来源"
    )
    
    # ==================== 数据库配置 ====================
    POSTGRES_HOST: str = Field("localhost", description="PostgreSQL 主机")
    POSTGRES_PORT: int = Field(5432, description="PostgreSQL 端口")
    POSTGRES_USER: str = Field(..., description="数据库用户名")
    POSTGRES_PASSWORD: str = Field(..., description="数据库密码")
    POSTGRES_DB: str = Field("roadmap_db", description="数据库名称")
    
    @property
    def DATABASE_URL(self) -> str:
        """构建异步数据库连接 URL"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # ==================== Redis 配置 ====================
    REDIS_HOST: str = Field("localhost", description="Redis 主机")
    REDIS_PORT: int = Field(6379, description="Redis 端口")
    REDIS_DB: int = Field(0, description="Redis 数据库编号")
    REDIS_PASSWORD: str | None = Field(None, description="Redis 密码")
    
    @property
    def REDIS_URL(self) -> str:
        """构建 Redis 连接 URL"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ==================== S3/R2 配置 ====================
    S3_ENDPOINT_URL: str = Field(..., description="S3 兼容端点（支持 Cloudflare R2）")
    S3_ACCESS_KEY_ID: str = Field(..., description="访问密钥 ID")
    S3_SECRET_ACCESS_KEY: str = Field(..., description="访问密钥")
    S3_BUCKET_NAME: str = Field("roadmap-content", description="存储桶名称")
    S3_REGION: str = Field("auto", description="区域（R2 使用 'auto'）")
    
    # ==================== LLM 配置 ====================
    # Intent Analyzer
    ANALYZER_PROVIDER: str = Field("openai", description="模型提供商")
    ANALYZER_MODEL: str = Field("gpt-4o-mini", description="模型名称")
    ANALYZER_BASE_URL: str | None = Field(None, description="自定义 API 端点")
    ANALYZER_API_KEY: str = Field(..., description="API 密钥")
    
    # Curriculum Architect
    ARCHITECT_PROVIDER: str = Field("anthropic", description="模型提供商")
    ARCHITECT_MODEL: str = Field("claude-3-5-sonnet-20241022", description="模型名称")
    ARCHITECT_BASE_URL: str | None = None
    ARCHITECT_API_KEY: str = Field(..., description="API 密钥")
    
    # Structure Validator
    VALIDATOR_PROVIDER: str = Field("openai", description="模型提供商")
    VALIDATOR_MODEL: str = Field("gpt-4o-mini", description="模型名称")
    VALIDATOR_BASE_URL: str | None = None
    VALIDATOR_API_KEY: str = Field(..., description="API 密钥")
    
    # Tutorial Generator
    GENERATOR_PROVIDER: str = Field("anthropic", description="模型提供商")
    GENERATOR_MODEL: str = Field("claude-3-5-sonnet-20241022", description="模型名称")
    GENERATOR_BASE_URL: str | None = None
    GENERATOR_API_KEY: str = Field(..., description="API 密钥")
    
    # Roadmap Editor (路线图编辑师)
    EDITOR_PROVIDER: str = Field("anthropic", description="模型提供商")
    EDITOR_MODEL: str = Field("claude-3-5-sonnet-20241022", description="模型名称")
    EDITOR_BASE_URL: str | None = None
    EDITOR_API_KEY: str = Field(..., description="API 密钥")
    
    # ==================== Checkpointer 配置 ====================
    @property
    def CHECKPOINTER_DATABASE_URL(self) -> str:
        """构建 Checkpointer 使用的数据库连接 URL（使用 psycopg）"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # ==================== 跳过开关（用于测试/调试） ====================
    SKIP_STRUCTURE_VALIDATION: bool = Field(False, description="跳过结构验证")
    SKIP_HUMAN_REVIEW: bool = Field(False, description="跳过人工审核")
    SKIP_TUTORIAL_GENERATION: bool = Field(False, description="跳过教程生成")
    
    # ==================== 外部服务配置 ====================
    TAVILY_API_KEY: str = Field(..., description="Tavily API 密钥（用于 Web 搜索）")
    
    # ==================== 观测性配置 ====================
    OTEL_ENABLED: bool = Field(False, description="是否启用 OpenTelemetry")
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = Field(None, description="OTLP 导出端点")
    
    # ==================== 业务配置 ====================
    MAX_FRAMEWORK_RETRY: int = Field(3, description="框架设计最大重试次数")
    MAX_TUTORIAL_RETRY: int = Field(2, description="教程生成最大重试次数")
    HUMAN_REVIEW_TIMEOUT_HOURS: int = Field(24, description="人工审核超时时间（小时）")
    PARALLEL_TUTORIAL_LIMIT: int = Field(10, description="并发生成教程的最大数量")


settings = Settings()
```

---

### 3.3 结构化日志配置 (`app/config/logging_config.py`)

```python
"""
structlog 配置
"""
import logging
import sys
import structlog
from structlog.types import EventDict

from app.config.settings import settings


def add_app_context(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """添加应用全局上下文"""
    event_dict["environment"] = settings.ENVIRONMENT
    event_dict["service"] = "roadmap-backend"
    return event_dict


def setup_logging():
    """初始化日志系统"""
    
    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    )
    
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            add_app_context,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 配置 uvicorn 日志
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = [logging.StreamHandler(sys.stdout)]
        logger.propagate = False
```

---

### 3.4 数据库会话管理 (`app/db/session.py`)

```python
"""
数据库会话管理（SQLModel + AsyncPG）
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlmodel import SQLModel
import structlog

from app.config.settings import settings

logger = structlog.get_logger()

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db():
    """初始化数据库（创建表）"""
    async with engine.begin() as conn:
        # 生产环境应使用 Alembic 迁移
        if settings.ENVIRONMENT == "development":
            await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("database_tables_created")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入：获取数据库会话
    
    使用示例：
    @app.get("/users")
    async def get_users(db: AsyncSession = Depends(get_db)):
        ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

---

### 3.5 Redis 客户端封装 (`app/db/redis_client.py`)

```python
"""
Redis 客户端封装
"""
from typing import Any
import json
import redis.asyncio as aioredis
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class RedisClient:
    """Redis 异步客户端封装"""
    
    def __init__(self):
        self._client: aioredis.Redis | None = None
    
    async def connect(self):
        """建立连接"""
        if self._client is None:
            self._client = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("redis_client_initialized")
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            logger.info("redis_client_closed")
    
    async def ping(self) -> bool:
        """健康检查"""
        await self.connect()
        return await self._client.ping()
    
    async def set_json(self, key: str, value: Any, ex: int | None = None):
        """存储 JSON 对象"""
        await self.connect()
        await self._client.set(key, json.dumps(value), ex=ex)
    
    async def get_json(self, key: str) -> Any | None:
        """读取 JSON 对象"""
        await self.connect()
        data = await self._client.get(key)
        return json.loads(data) if data else None
    
    async def delete(self, key: str):
        """删除键"""
        await self.connect()
        await self._client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        await self.connect()
        return await self._client.exists(key) > 0


# 全局单例
redis_client = RedisClient()
```

---

### 3.6 LangGraph 工作流编排器 (`app/core/orchestrator.py`)

```python
"""
LangGraph 工作流编排器
"""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import structlog

from app.models.domain import (
    UserRequest,
    IntentAnalysisOutput,
    RoadmapFramework,
    ValidationOutput,
    RoadmapEditOutput,
)
from app.agents.intent_analyzer import IntentAnalyzerAgent
from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.agents.roadmap_editor import RoadmapEditorAgent
from app.agents.structure_validator import StructureValidatorAgent
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.config.settings import settings

logger = structlog.get_logger()


class RoadmapState(TypedDict):
    """工作流全局状态"""
    # 输入
    user_request: UserRequest
    
    # 中间产出
    intent_analysis: IntentAnalysisOutput | None
    roadmap_framework: RoadmapFramework | None
    validation_result: ValidationOutput | None
    roadmap_edit: RoadmapEditOutput | None
    
    # 流程控制
    current_step: str
    modification_count: int
    human_approved: bool
    
    # 元数据
    trace_id: str
    execution_history: list[str]


class RoadmapOrchestrator:
    """学习路线图生成的主编排器（单例模式）"""
    
    _instance = None
    _checkpointer = None
    _checkpointer_cm = None  # Context Manager
    _graph = None
    
    @classmethod
    async def initialize(cls):
        """异步初始化 Checkpointer（使用 AsyncPostgresSaver）"""
        if cls._checkpointer is None:
            cls._checkpointer_cm = AsyncPostgresSaver.from_conn_string(
                settings.CHECKPOINTER_DATABASE_URL
            )
            cls._checkpointer = await cls._checkpointer_cm.__aenter__()
            await cls._checkpointer.setup()
            logger.info("async_postgres_saver_initialized")
    
    @classmethod
    async def shutdown(cls):
        """关闭 Checkpointer 连接"""
        if cls._checkpointer_cm is not None:
            await cls._checkpointer_cm.__aexit__(None, None, None)
            cls._checkpointer = None
            cls._checkpointer_cm = None
            logger.info("async_postgres_saver_closed")
    
    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 工作流"""
        workflow = StateGraph(RoadmapState)
        
        # 定义节点（5个Agent）
        workflow.add_node("intent_analysis", self._run_intent_analysis)
        workflow.add_node("curriculum_design", self._run_curriculum_design)
        workflow.add_node("structure_validation", self._run_structure_validation)
        workflow.add_node("roadmap_edit", self._run_roadmap_edit)
        workflow.add_node("human_review", self._run_human_review)
        workflow.add_node("tutorial_generation", self._run_tutorial_generation)
        
        # 定义边（流程控制）
        workflow.set_entry_point("intent_analysis")
        
        workflow.add_edge("intent_analysis", "curriculum_design")
        workflow.add_edge("curriculum_design", "structure_validation")
        
        # 条件路由：验证结果判断
        workflow.add_conditional_edges(
            "structure_validation",
            self._route_after_validation,
            {
                "roadmap_edit": "roadmap_edit",  # 验证失败，进入编辑
                "fail": END,
                "human_review": "human_review",
            }
        )
        
        # 编辑后重新验证
        workflow.add_edge("roadmap_edit", "structure_validation")
        
        # 人工审核后路由
        workflow.add_conditional_edges(
            "human_review",
            self._route_after_human_review,
            {
                "approved": "tutorial_generation",
                "modify": "roadmap_edit",
            }
        )
        
        workflow.add_edge("tutorial_generation", END)
        
        return workflow.compile()
    
    async def _run_intent_analysis(self, state: RoadmapState) -> dict:
        """Step 1: 需求分析"""
        logger.info("workflow_step_started", step="intent_analysis", trace_id=state["trace_id"])
        
        agent = IntentAnalyzerAgent()
        result = await agent.analyze(state["user_request"])
        
        return {
            "intent_analysis": result,
            "current_step": "intent_analysis",
            "execution_history": state["execution_history"] + ["需求分析完成"],
        }
    
    async def _run_curriculum_design(self, state: RoadmapState) -> dict:
        """Step 2: 课程设计"""
        logger.info("workflow_step_started", step="curriculum_design", trace_id=state["trace_id"])
        
        agent = CurriculumArchitectAgent()
        result = await agent.design(
            intent_analysis=state["intent_analysis"],
            user_preferences=state["user_request"].preferences,
        )
        
        return {
            "roadmap_framework": result.framework,
            "current_step": "curriculum_design",
            "execution_history": state["execution_history"] + ["课程设计完成"],
        }
    
    async def _run_structure_validation(self, state: RoadmapState) -> dict:
        """Step 3: 结构验证"""
        logger.info("workflow_step_started", step="structure_validation", trace_id=state["trace_id"])
        
        agent = StructureValidatorAgent()
        result = await agent.validate(
            framework=state["roadmap_framework"],
            user_preferences=state["user_request"].preferences,
        )
        
        return {
            "validation_result": result,
            "current_step": "structure_validation",
            "execution_history": state["execution_history"] + [
                f"结构验证完成 (有效性: {result.is_valid})"
            ],
        }
    
    def _route_after_validation(self, state: RoadmapState) -> str:
        """验证后的路由逻辑"""
        validation_result = state["validation_result"]
        modification_count = state["modification_count"]
        
        if not validation_result.is_valid:
            if modification_count < settings.MAX_FRAMEWORK_RETRY:
                logger.warning(
                    "validation_failed_retry",
                    attempt=modification_count + 1,
                    max_retries=settings.MAX_FRAMEWORK_RETRY,
                )
                return "retry_design"
            else:
                logger.error("validation_failed_max_retries_exceeded")
                return "fail"
        
        return "human_review"
    
    async def _run_human_review(self, state: RoadmapState) -> dict:
        """Step 4: 人工审核（Human-in-the-Loop）"""
        logger.info("workflow_step_started", step="human_review", trace_id=state["trace_id"])
        
        # 实际实现：通过 WebSocket 推送给前端，等待用户响应
        # 这里使用 LangGraph 的 interrupt() 功能暂停工作流
        # 参考：https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/
        
        return {
            "current_step": "human_review",
            "execution_history": state["execution_history"] + ["等待人工审核"],
        }
    
    def _route_after_human_review(self, state: RoadmapState) -> str:
        """人工审核后的路由逻辑"""
        if state["human_approved"]:
            return "approved"
        else:
            return "modify"
    
    async def _run_tutorial_generation(self, state: RoadmapState) -> dict:
        """Step 5: 并发生成教程"""
        logger.info("workflow_step_started", step="tutorial_generation", trace_id=state["trace_id"])
        
        # 这里会调用子 Workflow 进行并发生成
        # 详细实现见后续章节
        
        return {
            "current_step": "tutorial_generation",
            "execution_history": state["execution_history"] + ["教程生成完成"],
        }
    
    async def execute(self, user_request: UserRequest, trace_id: str) -> RoadmapState:
        """
        执行完整的工作流
        
        Args:
            user_request: 用户请求
            trace_id: 追踪 ID
            
        Returns:
            最终的工作流状态
        """
        initial_state: RoadmapState = {
            "user_request": user_request,
            "intent_analysis": None,
            "roadmap_framework": None,
            "validation_result": None,
            "current_step": "init",
            "modification_count": 0,
            "human_approved": False,
            "trace_id": trace_id,
            "execution_history": [],
        }
        
        # 使用 Checkpointer 执行（支持断点续传）
        config = {"configurable": {"thread_id": trace_id}}
        
        final_state = await self.graph.ainvoke(
            initial_state,
            config=config,
            checkpointer=self.checkpointer,
        )
        
        return final_state
```

---

### 3.7 Agent 基类 (`app/agents/base.py`)

```python
"""
Agent 基类（封装 LiteLLM 调用）
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import litellm
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
import structlog

from app.utils.prompt_loader import PromptLoader
from app.utils.cost_tracker import CostTracker

logger = structlog.get_logger()


class BaseAgent(ABC):
    """
    Agent 抽象基类
    
    每个 Agent 都需要从环境变量中加载以下配置：
    - provider: 模型提供商（如 'openai', 'anthropic'）
    - model: 模型名称（如 'gpt-4o-mini', 'claude-3-5-sonnet-20241022'）
    - base_url: 自定义 API 端点（可选，用于本地部署或代理）
    - api_key: API 密钥（必需）
    
    这些配置通过 Settings 类从 .env 文件加载。
    """
    
    def __init__(
        self,
        agent_id: str,
        model_provider: str,
        model_name: str,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.agent_id = agent_id
        self.model_provider = model_provider
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self.prompt_loader = PromptLoader()
        self.cost_tracker = CostTracker()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(litellm.RateLimitError),
    )
    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict] | None = None,
    ) -> Any:
        """
        调用 LLM（通过 LiteLLM）
        
        Args:
            messages: 对话消息列表
            tools: 工具定义（可选）
            
        Returns:
            LLM 响应对象
        """
        try:
            response = await litellm.acompletion(
                model=f"{self.model_provider}/{self.model_name}",
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                api_base=self.base_url,
                api_key=self.api_key,
                tools=tools,
            )
            
            # 追踪成本
            self.cost_tracker.track(
                agent_id=self.agent_id,
                model=self.model_name,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )
            
            logger.info(
                "llm_call_success",
                agent_id=self.agent_id,
                model=self.model_name,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )
            
            return response
            
        except litellm.RateLimitError as e:
            logger.warning("llm_rate_limit", agent_id=self.agent_id, error=str(e))
            raise
        except Exception as e:
            logger.error("llm_call_failed", agent_id=self.agent_id, error=str(e))
            raise
    
    def _load_system_prompt(self, template_name: str, **kwargs) -> str:
        """加载并渲染 System Prompt"""
        return self.prompt_loader.render(template_name, **kwargs)
    
    @abstractmethod
    async def execute(self, input_data: Any) -> Any:
        """
        执行 Agent 任务（由子类实现）
        
        Args:
            input_data: 输入数据（对应 Agent 的 InputSchema）
            
        Returns:
            输出数据（对应 Agent 的 OutputSchema）
        """
        pass
```

---

### 3.8 具体 Agent 实现示例 (`app/agents/intent_analyzer.py`)

```python
"""
Intent Analyzer Agent（需求分析师）
"""
from app.agents.base import BaseAgent
from app.models.domain import UserRequest, IntentAnalysisOutput
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class IntentAnalyzerAgent(BaseAgent):
    """
    需求分析师 Agent
    
    配置从环境变量加载：
    - ANALYZER_PROVIDER: 模型提供商（默认: openai）
    - ANALYZER_MODEL: 模型名称（默认: gpt-4o-mini）
    - ANALYZER_BASE_URL: 自定义 API 端点（可选）
    - ANALYZER_API_KEY: API 密钥（必需）
    """
    
    def __init__(self):
        super().__init__(
            agent_id="intent_analyzer",
            model_provider=settings.ANALYZER_PROVIDER,
            model_name=settings.ANALYZER_MODEL,
            base_url=settings.ANALYZER_BASE_URL,
            api_key=settings.ANALYZER_API_KEY,
            temperature=0.3,
            max_tokens=2048,
        )
    
    async def analyze(self, user_request: UserRequest) -> IntentAnalysisOutput:
        """
        分析用户学习需求
        
        Args:
            user_request: 用户请求
            
        Returns:
            结构化的需求分析结果
        """
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "intent_analyzer.j2",
            agent_name="Intent Analyzer",
            user_goal=user_request.preferences.learning_goal,
        )
        
        # 构建用户消息
        user_message = f"""
请分析以下用户的学习需求：

**学习目标**: {user_request.preferences.learning_goal}
**每周可投入时间**: {user_request.preferences.available_hours_per_week} 小时
**学习动机**: {user_request.preferences.motivation}
**当前水平**: {user_request.preferences.current_level}
**职业背景**: {user_request.preferences.career_background}
**内容偏好**: {", ".join(user_request.preferences.content_preference)}
{"**期望完成时间**: " + str(user_request.preferences.target_deadline) if user_request.preferences.target_deadline else ""}

请提取关键技术栈、难度画像、时间约束，并给出学习重点建议。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 调用 LLM
        response = await self._call_llm(messages)
        
        # 解析输出（假设 LLM 返回 JSON 格式）
        content = response.choices[0].message.content
        
        # 使用 Pydantic 验证输出格式
        try:
            result = IntentAnalysisOutput.model_validate_json(content)
            logger.info("intent_analysis_success", user_id=user_request.user_id)
            return result
        except Exception as e:
            logger.error("intent_analysis_output_invalid", error=str(e), content=content)
            raise ValueError(f"LLM 输出格式不符合 Schema: {e}")
    
    async def execute(self, input_data: UserRequest) -> IntentAnalysisOutput:
        """实现基类的抽象方法"""
        return await self.analyze(input_data)
```

---

### 3.9 Tool 基类与 Web Search 实现

#### `app/tools/base.py`

```python
"""
Tool 基类
"""
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseTool(ABC, Generic[InputT, OutputT]):
    """工具抽象基类"""
    
    def __init__(self, tool_id: str):
        self.tool_id = tool_id
    
    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """
        执行工具（由子类实现）
        
        Args:
            input_data: 工具输入
            
        Returns:
            工具输出
        """
        pass
```

#### `app/tools/search/web_search.py`

```python
"""
Web Search Tool（基于 Tavily API）
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
import structlog

from app.tools.base import BaseTool
from app.models.domain import SearchQuery, SearchResult
from app.config.settings import settings

logger = structlog.get_logger()


class WebSearchTool(BaseTool[SearchQuery, SearchResult]):
    """Web 搜索工具（使用 Tavily API）"""
    
    def __init__(self):
        super().__init__(tool_id="web_search_v1")
        self.api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """
        执行网络搜索（使用 Tavily API）
        
        Args:
            input_data: 搜索查询
            
        Returns:
            搜索结果
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": input_data.query,
                        "search_depth": "basic",  # basic, advanced
                        "max_results": input_data.max_results,
                        "include_answer": False,
                        "include_raw_content": False,
                        "include_images": False,
                    },
                    headers={
                        "Content-Type": "application/json",
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Tavily 返回格式：{"results": [{"title", "url", "content", "score", "published_date"}], ...}
                tavily_results = data.get("results", [])
                
                results = [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", "")[:200],  # 截取前200字符作为摘要
                        "published_date": item.get("published_date", ""),
                    }
                    for item in tavily_results[:input_data.max_results]
                ]
                
                logger.info(
                    "web_search_success",
                    query=input_data.query,
                    results_count=len(results),
                    provider="tavily",
                )
                
                return SearchResult(
                    results=results,
                    total_found=len(results),
                )
                
            except httpx.HTTPError as e:
                logger.error("web_search_failed", error=str(e), provider="tavily")
                raise
            except KeyError as e:
                logger.error("web_search_response_format_error", error=str(e), provider="tavily")
                raise ValueError(f"Tavily API 响应格式错误: {e}")
```

---

### 3.10 S3/R2 存储客户端 (`app/tools/storage/s3_client.py`)

```python
"""
S3/R2 异步存储客户端（使用 aioboto3）
"""
from contextlib import asynccontextmanager
import hashlib
from datetime import datetime
import aioboto3
import structlog

from app.tools.base import BaseTool
from app.models.domain import S3UploadRequest, S3UploadResult
from app.config.settings import settings

logger = structlog.get_logger()


class S3StorageTool(BaseTool[S3UploadRequest, S3UploadResult]):
    """S3/R2 对象存储工具"""
    
    def __init__(self):
        super().__init__(tool_id="s3_storage_v1")
        self.session = aioboto3.Session(
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
    
    @asynccontextmanager
    async def _get_client(self):
        """获取 S3 客户端（异步上下文管理器）"""
        async with self.session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION,
        ) as client:
            yield client
    
    async def execute(self, input_data: S3UploadRequest) -> S3UploadResult:
        """
        上传内容到 S3/R2
        
        Args:
            input_data: 上传请求
            
        Returns:
            上传结果
        """
        bucket = input_data.bucket or settings.S3_BUCKET_NAME
        
        async with self._get_client() as s3_client:
            try:
                # 上传对象
                response = await s3_client.put_object(
                    Bucket=bucket,
                    Key=input_data.key,
                    Body=input_data.content.encode("utf-8"),
                    ContentType=input_data.content_type,
                )
                
                # 计算内容大小
                size_bytes = len(input_data.content.encode("utf-8"))
                
                # 生成访问 URL（使用预签名 URL）
                url = await s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": input_data.key},
                    ExpiresIn=3600 * 24 * 7,  # 7 天有效期
                )
                
                logger.info(
                    "s3_upload_success",
                    key=input_data.key,
                    size_bytes=size_bytes,
                )
                
                return S3UploadResult(
                    success=True,
                    url=url,
                    key=input_data.key,
                    size_bytes=size_bytes,
                    etag=response.get("ETag"),
                )
                
            except Exception as e:
                logger.error("s3_upload_failed", key=input_data.key, error=str(e))
                raise
```

---

## 4. API 端点设计

### 4.1 路由定义 (`app/api/v1/roadmap.py`)

```python
"""
学习路线图相关 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid

from app.models.domain import UserRequest, RoadmapFramework
from app.db.session import get_db
from app.services.roadmap_service import RoadmapService

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])
logger = structlog.get_logger()


@router.post("/generate", response_model=dict)
async def generate_roadmap(
    request: UserRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    生成学习路线图（异步任务）
    
    Returns:
        任务 ID，用于后续查询状态
    """
    trace_id = str(uuid.uuid4())
    
    logger.info(
        "roadmap_generation_requested",
        user_id=request.user_id,
        trace_id=trace_id,
        learning_goal=request.preferences.learning_goal,
    )
    
    # 创建服务实例
    service = RoadmapService(db)
    
    # 在后台任务中执行工作流
    background_tasks.add_task(service.generate_roadmap, request, trace_id)
    
    return {
        "task_id": trace_id,
        "status": "processing",
        "message": "路线图生成任务已启动，请通过 WebSocket 或轮询接口查询进度",
    }


@router.get("/{task_id}/status")
async def get_roadmap_status(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """查询路线图生成状态"""
    service = RoadmapService(db)
    status = await service.get_task_status(task_id)
    
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return status


@router.get("/{roadmap_id}", response_model=RoadmapFramework)
async def get_roadmap(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取完整的路线图数据"""
    service = RoadmapService(db)
    roadmap = await service.get_roadmap(roadmap_id)
    
    if not roadmap:
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    return roadmap


@router.post("/{task_id}/approve")
async def approve_roadmap(
    task_id: str,
    approved: bool,
    feedback: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    人工审核端点（Human-in-the-Loop）
    
    Args:
        task_id: 任务 ID
        approved: 是否批准
        feedback: 用户反馈（如果未批准）
    """
    service = RoadmapService(db)
    await service.handle_human_review(task_id, approved, feedback)
    
    return {"message": "审核结果已提交，工作流将继续执行"}
```

---

### 4.2 WebSocket 实时推送 (`app/api/v1/websocket.py`)

```python
"""
WebSocket 实时推送（用于工作流进度通知）
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import structlog
import json

from app.services.notification_service import NotificationService

router = APIRouter()
logger = structlog.get_logger()


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket 端点：订阅任务进度更新
    
    客户端连接后，会实时收到任务状态变化的通知
    """
    await websocket.accept()
    logger.info("websocket_connected", task_id=task_id)
    
    notification_service = NotificationService()
    
    try:
        # 订阅 Redis Pub/Sub 频道
        async for message in notification_service.subscribe(task_id):
            await websocket.send_text(json.dumps(message))
    
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", task_id=task_id)
    
    except Exception as e:
        logger.error("websocket_error", task_id=task_id, error=str(e))
        await websocket.close()
```

---

## 5. 数据库模型设计

### 5.1 SQLModel 模型定义 (`app/models/database.py`)

```python
"""
数据库模型（SQLModel）
"""
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy import Text
import uuid


class User(SQLModel, table=True):
    """用户表"""
    __tablename__ = "users"
    
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    email: str = Field(unique=True, index=True)
    username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RoadmapTask(SQLModel, table=True):
    """路线图生成任务表"""
    __tablename__ = "roadmap_tasks"
    
    task_id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    
    # 状态跟踪
    status: str = Field(default="pending")  # pending, processing, completed, failed
    current_step: str = Field(default="init")
    
    # 输入/输出
    user_request: dict = Field(sa_column=Column(JSON))
    roadmap_id: Optional[str] = Field(default=None)
    
    # 元数据
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # 错误信息
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))


class RoadmapMetadata(SQLModel, table=True):
    """路线图元数据表（存储轻量级框架，不包含详细内容）"""
    __tablename__ = "roadmap_metadata"
    
    roadmap_id: str = Field(primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    task_id: str = Field(foreign_key="roadmap_tasks.task_id")
    
    title: str
    total_estimated_hours: float
    recommended_completion_weeks: int
    
    # 完整框架数据（JSON 格式）
    framework_data: dict = Field(sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TutorialMetadata(SQLModel, table=True):
    """教程元数据表（仅存储引用和摘要）"""
    __tablename__ = "tutorial_metadata"
    
    tutorial_id: str = Field(primary_key=True)
    concept_id: str = Field(index=True)
    roadmap_id: str = Field(foreign_key="roadmap_metadata.roadmap_id", index=True)
    
    title: str
    summary: str = Field(sa_column=Column(Text))
    
    # S3 存储引用
    content_url: str
    content_status: str = Field(default="pending")  # pending, completed, failed
    
    estimated_completion_time: int  # 分钟
    generated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 6. 部署架构

### 6.1 Docker Compose 开发环境 (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  # ==================== Backend API ====================
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
      - POSTGRES_HOST=postgres
      - REDIS_HOST=redis
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./app:/app/app
      - ./prompts:/app/prompts
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # ==================== PostgreSQL ====================
  postgres:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: roadmap_user
      POSTGRES_PASSWORD: roadmap_pass
      POSTGRES_DB: roadmap_db
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # ==================== Redis ====================
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

### 6.2 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY pyproject.toml poetry.lock ./
RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# 复制应用代码
COPY ./app /app/app
COPY ./prompts /app/prompts
COPY ./specs /app/specs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 6.3 依赖管理 (`pyproject.toml`)

```toml
[tool.poetry]
name = "learning-roadmap-backend"
version = "1.0.0"
description = "个性化学习路线图生成系统后端"
authors = ["Your Team"]
readme = "README.md"
python = "^3.12"

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115.0"
uvicorn = {extras = ["standard"], version = "^0.32.0"}
pydantic = "^2.9"
pydantic-settings = "^2.6"
sqlmodel = "^0.0.22"
asyncpg = "^0.30.0"
redis = {extras = ["hiredis"], version = "^5.2.0"}
langgraph = "^1.0.2"
litellm = "^1.52.15"
httpx = "^0.28.1"
aioboto3 = "^13.3.0"
structlog = "^24.4.0"
tenacity = "^9.0.0"
jinja2 = "^3.1.4"
opentelemetry-api = "^1.28.2"
opentelemetry-sdk = "^1.28.2"
opentelemetry-instrumentation-fastapi = "^0.49b2"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.4"
pytest-asyncio = "^0.24.0"
polyfactory = "^2.17.0"
black = "^24.10.0"
ruff = "^0.8.3"
mypy = "^1.13.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.black]
line-length = 100
target-version = ['py312']

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
```

---

## 7. 关键设计决策说明

### 7.1 为什么选择 LangGraph 而不是自研编排器？

1. **原生支持状态持久化**：LangGraph 内置 Checkpointer 机制，使用 `AsyncPostgresSaver` 将工作流状态存入 PostgreSQL，无需手动管理状态序列化。
2. **Human-in-the-Loop 开箱即用**：通过 `interrupt()` API 可优雅地暂停工作流等待人工输入。
3. **可视化与调试**：LangGraph Studio 提供工作流可视化界面，降低调试难度。
4. **社区生态**：LangChain 生态系统庞大，工具集成丰富。

### 7.2 为什么使用 AsyncPostgresSaver 而不是 Redis？

1. **统一存储**：将 Checkpoint 存储与业务数据统一在 PostgreSQL 中，简化运维。
2. **事务支持**：PostgreSQL 提供 ACID 事务保证，确保状态一致性。
3. **官方支持**：`AsyncPostgresSaver` 是 LangGraph 官方提供的异步 Checkpointer 实现。
4. **减少依赖**：减少对 Redis 的依赖，Redis 仅用于缓存和分布式锁。

### 7.3 为什么使用 SQLModel 而不是纯 Pydantic + SQLAlchemy？

1. **减少模型重复定义**：SQLModel 同时继承 Pydantic 和 SQLAlchemy，一个类既可用作 API 模型也可作为 ORM 模型。
2. **类型安全**：完全的类型提示支持，配合 mypy 可在编译期发现错误。
3. **异步支持**：原生支持 SQLAlchemy 2.0 的 AsyncIO 特性。

### 7.4 为什么选择 aioboto3 而不是标准 boto3？

1. **非阻塞 I/O**：FastAPI 是异步框架，使用同步的 `boto3` 会阻塞事件循环，导致整个 API 服务卡顿。
2. **高并发性能**：在并发生成教程时，需要同时上传多个文件到 S3，异步客户端可显著提升吞吐量。

### 7.5 为什么使用 LiteLLM 而不是直接调用 OpenAI SDK？

1. **统一接口**：支持 100+ 种 LLM 提供商（OpenAI, Anthropic, Azure, AWS Bedrock, 本地模型等），切换成本低。
2. **自动重试与容错**：内置指数退避重试、限流处理等机制。
3. **成本追踪**：自动计算每次调用的 Token 消耗和成本。

### 7.6 为什么选择 Tavily 而不是 SerpAPI？

1. **AI 优化**：Tavily 专为 AI 应用设计，返回的结果更适合 LLM 处理。
2. **结构化输出**：API 返回格式统一，包含标题、URL、内容摘要、相关性评分等。
3. **成本效益**：相比 SerpAPI，Tavily 提供更优惠的定价和更高的请求配额。
4. **实时性**：支持实时搜索，结果更新及时。
5. **可配置性**：支持调整搜索深度（basic/advanced）、结果数量等参数。

### 7.7 为什么简化了 Agent 架构（移除 Quality Reviewer 和 Tutorial Editor）？

1. **降低复杂度**：减少了质量审查循环，简化了工作流，提高了系统稳定性。
2. **减少成本**：减少了 LLM API 调用次数，降低了运营成本。
3. **加快迭代**：简化的架构更易于维护和迭代开发。
4. **聚焦核心功能**：将重点放在路线图生成和教程内容生成上。

---

## 8. 实施进度

### Phase 1: 基础设施搭建 ✅
- [x] 初始化项目结构
- [x] 配置 Docker Compose 本地开发环境
- [x] 实现配置管理（Pydantic Settings）
- [x] 搭建数据库（PostgreSQL）
- [x] 实现 structlog 日志系统

### Phase 2: 核心 Agent 开发 ✅
- [x] 实现 Agent 基类（封装 LiteLLM）
- [x] 开发 5 个 Agent（Intent Analyzer, Curriculum Architect, Roadmap Editor, Structure Validator, Tutorial Generator）
- [x] 编写 Prompt 模板（Jinja2）
- [x] 实现工具层（Web Search, S3 Storage）

### Phase 3: LangGraph 工作流集成 ✅
- [x] 实现 RoadmapOrchestrator（主工作流）
- [x] 配置 AsyncPostgresSaver（状态持久化）
- [x] 实现 Human-in-the-Loop 机制
- [x] 开发并发教程生成子工作流

### Phase 4: API 与前端对接 ✅
- [x] 实现 FastAPI 路由（路线图生成、状态查询）
- [x] 编写 API 文档（OpenAPI）
- [ ] 实现 WebSocket 实时推送
- [ ] 前后端联调

### Phase 5: 测试与优化 ✅
- [x] 单元测试（test_models.py）
- [x] 集成测试（5个 Agent 测试 + Checkpointer 测试）
- [x] 端到端测试（test_workflow.py）
- [ ] 性能优化（数据库查询、LLM 并发调用）
- [ ] 成本优化（缓存策略、模型选择）

### Phase 6: 生产部署
- [ ] 配置 CI/CD 流程
- [ ] 部署到云平台（AWS/GCP/Azure）
- [ ] 配置监控与告警（Prometheus + Grafana）
- [ ] 配置日志收集（ELK Stack）
- [ ] 性能测试与压测

---

## 9. 附录

### 9.1 环境变量配置示例 (`.env.example`)

```bash
# ==================== Application ====================
ENVIRONMENT=development
DEBUG=true
CORS_ORIGINS=["http://localhost:3000"]

# ==================== Database ====================
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=roadmap_user
POSTGRES_PASSWORD=roadmap_pass
POSTGRES_DB=roadmap_db

# ==================== Redis ====================
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# ==================== S3/R2 Storage ====================
S3_ENDPOINT_URL=https://your-account.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=your_access_key
S3_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=roadmap-content
S3_REGION=auto

# ==================== LLM API Keys ====================
# Intent Analyzer (A1)
ANALYZER_PROVIDER=openai
ANALYZER_MODEL=gpt-4o-mini
ANALYZER_BASE_URL=
ANALYZER_API_KEY=sk-xxx

# Curriculum Architect (A2)
ARCHITECT_PROVIDER=anthropic
ARCHITECT_MODEL=claude-3-5-sonnet-20241022
ARCHITECT_API_KEY=sk-ant-xxx

# Structure Validator (A3)
VALIDATOR_PROVIDER=openai
VALIDATOR_MODEL=gpt-4o-mini
VALIDATOR_API_KEY=sk-xxx

# Tutorial Generator (A4)
GENERATOR_PROVIDER=anthropic
GENERATOR_MODEL=claude-3-5-sonnet-20241022
GENERATOR_API_KEY=sk-ant-xxx

# Roadmap Editor (A2E)
EDITOR_PROVIDER=anthropic
EDITOR_MODEL=claude-3-5-sonnet-20241022
EDITOR_API_KEY=sk-ant-xxx

# ==================== External Services ====================
TAVILY_API_KEY=your_tavily_api_key

# ==================== 跳过开关（用于测试/调试） ====================
SKIP_STRUCTURE_VALIDATION=false
SKIP_HUMAN_REVIEW=false
SKIP_TUTORIAL_GENERATION=false

# ==================== Observability ====================
OTEL_ENABLED=false
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

---

## 10. 参考资源

- **LangGraph 文档**: https://langchain-ai.github.io/langgraph/
- **LiteLLM 文档**: https://docs.litellm.ai/
- **SQLModel 文档**: https://sqlmodel.tiangolo.com/
- **FastAPI 文档**: https://fastapi.tiangolo.com/
- **structlog 文档**: https://www.structlog.org/
- **Pydantic Settings**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

---

**文档版本**: v2.0.0  
**最后更新**: 2025-01-26  
**维护者**: Learning Roadmap Team

---

## 变更记录

### v2.0.0 (2025-01-26)
- **架构简化**: 移除 Quality Reviewer (A5) 和 Tutorial Editor，保留 5 个核心 Agent
- **Checkpointer 迁移**: 从 Redis 迁移到 AsyncPostgresSaver（官方 LangGraph 组件）
- **工具层精简**: 移除 Schema Validator Tool，保留 Web Search 和 S3 Storage
- **状态机优化**: 简化教程生成流程，移除质量审查循环
- **配置更新**: 移除 REVIEWER_* 配置，添加 SKIP_* 跳过开关
- **测试完善**: 添加完整的单元测试、集成测试和端到端测试

