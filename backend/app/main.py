"""
FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

# ✅ 在模块导入时就初始化日志系统（确保所有后续 structlog 调用都使用正确配置）
from app.config.logging_config import setup_logging
setup_logging()

import structlog

from app.api.v1.router import router as api_router_v1
from app.api.v1.websocket import router as websocket_router
from app.config.settings import settings
from app.core.dependencies import init_orchestrator, cleanup_orchestrator
from app.db.s3_init import ensure_bucket_exists
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.trace_middleware import TraceIDMiddleware
from app.middleware.opera_log_middleware import OperaLogMiddleware
from app.middleware.rbac_middleware import RBACMiddleware
from app.middleware.prometheus_middleware import PrometheusMiddleware
from app.core.prometheus.instruments import set_app_info
from app.core.global_exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    custom_api_exception_handler,
    generic_exception_handler,
)
from app.core.custom_exceptions import BaseAPIException
# 延迟导入避免循环依赖
def get_recover_interrupted_tasks_on_startup():
    from app.services.workflows.generation.task_recovery_service import recover_interrupted_tasks_on_startup
    return recover_interrupted_tasks_on_startup


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("application_startup")
    
    # 设置 Prometheus 应用信息
    set_app_info(version="1.0.0", environment=settings.ENVIRONMENT)
    
    # 初始化全局 orchestrator 和 Redis 连接
    await init_orchestrator()
    
    # ✅ 初始化 Tavily API Key Redis 缓存（从数据库加载）
    try:
        from app.core.tavily_key_cache import get_tavily_key_cache
        key_cache = get_tavily_key_cache()
        loaded_keys = await key_cache.initialize()
        logger.info(
            "tavily_key_cache_initialized_on_startup",
            loaded_keys=loaded_keys,
        )
    except Exception as e:
        # 缓存初始化失败不应阻止服务启动（降级到数据库直查）
        logger.error(
            "tavily_key_cache_init_error_on_startup",
            error=str(e),
            error_type=type(e).__name__,
        )
    
    # 初始化 S3 兼容存储 bucket（如果不存在则创建）
    await ensure_bucket_exists()
    
    # ============================================================
    # MCP Servers 初始化已废弃 (2026-01-19)
    # 原因：统一使用官方 langchain-mcp-adapters
    # 现在Agent直接在需要时加载MCP工具，无需在启动时统一初始化
    # ============================================================
    # 如需使用MCP工具，请参考：
    # - app/tools/mcp_loader.py - 官方langchain-mcp-adapters加载器
    # - app/agents/tutorial_generator.py - 使用示例（场景区分加载）
    
    # 恢复被中断的任务（服务器重启后自动恢复）
    try:
        recover_interrupted_tasks_on_startup = get_recover_interrupted_tasks_on_startup()
        recovery_result = await recover_interrupted_tasks_on_startup()
        if recovery_result.total_found > 0:
            logger.info(
                "task_recovery_on_startup_completed",
                total_found=recovery_result.total_found,
                recovered=recovery_result.recovered,
                failed=recovery_result.failed,
                no_checkpoint=recovery_result.no_checkpoint,
            )
    except Exception as e:
        # 恢复失败不应阻止服务启动
        logger.error(
            "task_recovery_on_startup_error",
            error=str(e),
            error_type=type(e).__name__,
        )
    
    # 初始化技术栈测验数据（先检查，如果已全部生成则跳过Celery任务）
    try:
        from app.services.learning.assessment_initializer import initialize_tech_assessments
        init_result = await initialize_tech_assessments()
        
        # 记录初始化结果
        if init_result.get("success"):
            if init_result.get("status") == "complete":
                # 所有测验题已存在，无需生成
                logger.info(
                    "tech_assessments_already_complete",
                    total_expected=init_result.get("total_expected"),
                    existing=init_result.get("existing"),
                    message="所有测验题已存在，跳过生成",
                )
            elif init_result.get("status") == "triggered":
                # 触发了Celery任务
                logger.info(
                    "tech_assessments_task_triggered",
                    total_expected=init_result.get("total_expected"),
                    existing=init_result.get("existing"),
                    missing=init_result.get("missing"),
                    task_id=init_result.get("task_id"),
                    message=f"发现 {init_result.get('missing')} 个缺失的测验题，已提交Celery任务",
                )
        else:
            logger.warning(
                "tech_assessments_init_check_failed",
                error=init_result.get("error"),
                message="测验题检查失败，但不影响服务启动",
            )
    except Exception as e:
        # 初始化失败不应阻止服务启动
        logger.error(
            "tech_assessments_init_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
    
    yield
    
    logger.info("application_shutdown")
    
    # 刷新所有待发送的日志
    try:
        from app.services.shared.execution_logger import execution_logger
        await execution_logger.flush()
        logger.info("execution_logger_flushed")
        
        # 等待一小段时间，确保 Celery 任务被发送
        import asyncio
        await asyncio.sleep(1)
    except Exception as e:
        logger.error(
            "execution_logger_flush_failed",
            error=str(e),
        )
    
    # 清理 orchestrator 和关闭 Redis 连接
    await cleanup_orchestrator()


app = FastAPI(
    title="Learning Roadmap Generation System",
    description="基于 Multi-Agent 的个性化学习路线图生成系统",
    version="1.0.0",
    lifespan=lifespan,
)

# ============================================================
# 中间件配置（洋葱圈模型：后添加先执行）
# ============================================================
# 
# 执行顺序（请求进入）：CORS → TraceID → RequestID → RBAC → OperaLog → 业务逻辑
# 执行顺序（响应返回）：业务逻辑 → OperaLog → RBAC → RequestID → TraceID → CORS
# 
# ⚠️ 关键原理：
# FastAPI/Starlette中间件是LIFO（后进先出）栈结构
# - 先添加的中间件在内层（后执行）
# - 后添加的中间件在外层（先执行）
# 
# ✅ 正确顺序（从内到外）：
# 1. OperaLog（最内层，记录操作日志）
# 2. RBAC（权限控制）
# 3. RequestID（请求ID追踪）
# 4. TraceID（分布式追踪）
# 5. CORS（最外层，跨域处理）
# 
# 注意：FastAPI Users 的认证通过路由依赖注入实现，不需要全局中间件
# ============================================================

# 第0步：添加连接池监控中间件（最内层，保护资源）
from app.middleware.pool_monitor_middleware import PoolMonitorMiddleware
app.add_middleware(PoolMonitorMiddleware)
logger.info("middleware_registered", name="PoolMonitorMiddleware", layer="innermost_protection")

# 第1步：添加 Prometheus 中间件（记录指标）
app.add_middleware(PrometheusMiddleware, app_name="roadmap_agent")
logger.info("middleware_registered", name="PrometheusMiddleware", layer="innermost")

# 第2步：添加 OperaLog 中间件（记录所有请求）
app.add_middleware(OperaLogMiddleware)
logger.info("middleware_registered", name="OperaLogMiddleware", layer="inner_2")

# 第3步：添加 RBAC 中间件（权限控制）
app.add_middleware(RBACMiddleware)
logger.info("middleware_registered", name="RBACMiddleware", layer="inner")

# 第3步：添加 RequestID 中间件
app.add_middleware(RequestIDMiddleware)
logger.info("middleware_registered", name="RequestIDMiddleware", layer="middle_inner")

# 第4步：添加 TraceID 中间件
app.add_middleware(TraceIDMiddleware)
logger.info("middleware_registered", name="TraceIDMiddleware", layer="middle_outer")

# 第5步：添加 CORS 中间件（最外层）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Trace-ID"],  # ✅ 暴露RequestID和TraceID给前端
)
logger.info("middleware_registered", name="CORSMiddleware", layer="outermost")

# 注册全局异常处理器（按优先级顺序）
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(BaseAPIException, custom_api_exception_handler)  # 自定义API异常
app.add_exception_handler(Exception, generic_exception_handler)  # 兜底处理器

# 注册API路由（新的拆分结构）
app.include_router(api_router_v1)

# 注册WebSocket路由
app.include_router(websocket_router)

# 暴露 Prometheus metrics 端点
from prometheus_client import make_asgi_app
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
logger.info("prometheus_metrics_endpoint_registered", path="/metrics")

# 挂载 FastAPI Voyager 可视化工具
try:
    from fastapi_voyager import create_voyager
    app.mount(
        '/voyager',
        create_voyager(
            app,
            module_prefix='app',  # 模块前缀，对应项目中的 app 包
            swagger_url="/docs",  # Swagger 文档地址
            initial_page_policy='first',  # 默认显示第一个路由
            enable_pydantic_resolve_meta=True,  # 启用 pydantic-resolve 元信息显示
        )
    )
    logger.info("voyager_visualization_registered", path="/voyager")
except ImportError:
    logger.warning("fastapi_voyager_not_installed", message="Run 'uv add fastapi-voyager' to enable API visualization")
except Exception as e:
    logger.error("voyager_mount_failed", error=str(e), error_type=type(e).__name__)


@app.get("/health")
async def health_check():
    """基础健康检查端点（快速响应，用于负载均衡器）"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/health/db")
async def db_health_check():
    """
    数据库健康检查端点
    
    检查数据库连接池状态和连接可用性。
    用于诊断数据库连接问题。
    """
    from app.db.session import check_db_health
    return await check_db_health()


@app.get("/health/detailed")
async def detailed_health_check():
    """
    详细健康检查端点
    
    返回所有子系统的健康状态，包括：
    - 数据库连接池
    - Checkpointer 连接池
    - Redis 连接（如果有）
    """
    from app.db.session import check_db_health, get_pool_status
    
    # 检查数据库
    db_health = await check_db_health()
    
    # 检查 Checkpointer 连接池
    checkpointer_status = {"status": "unknown"}
    try:
        from app.core.orchestrator_factory import OrchestratorFactory
        if OrchestratorFactory._connection_pool:
            pool = OrchestratorFactory._connection_pool
            checkpointer_status = {
                "status": "healthy" if not pool.closed else "unhealthy",
                "min_size": pool.min_size,
                "max_size": pool.max_size,
            }
    except Exception as e:
        checkpointer_status = {
            "status": "error",
            "error": str(e),
        }
    
    overall_status = "healthy"
    if db_health.get("status") != "healthy":
        overall_status = "unhealthy"
    if checkpointer_status.get("status") not in ("healthy", "unknown"):
        overall_status = "degraded"
    
    return {
        "status": overall_status,
        "version": "1.0.0",
        "components": {
            "database": db_health,
            "checkpointer": checkpointer_status,
        },
    }

