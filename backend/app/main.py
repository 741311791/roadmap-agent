"""
FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.api.v1.router import router as api_router_v1
from app.api.v1.websocket import router as websocket_router
from app.config.settings import settings
from app.core.dependencies import init_orchestrator, cleanup_orchestrator
from app.db.s3_init import ensure_bucket_exists
# 延迟导入避免循环依赖
def get_recover_interrupted_tasks_on_startup():
    from app.services.task_recovery_service import recover_interrupted_tasks_on_startup
    return recover_interrupted_tasks_on_startup


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("application_startup")
    
    # 初始化全局 orchestrator 和 Redis 连接
    await init_orchestrator()
    
    # 初始化 S3 兼容存储 bucket（如果不存在则创建）
    await ensure_bucket_exists()
    
    # 恢复被中断的任务（服务器重启后自动恢复）
    try:
        recover_interrupted_tasks_on_startup = get_recover_interrupted_tasks_on_startup()
        recovery_result = await recover_interrupted_tasks_on_startup()
        if recovery_result.get("total_found", 0) > 0:
            logger.info(
                "task_recovery_on_startup_completed",
                total_found=recovery_result.get("total_found"),
                recovered=recovery_result.get("recovered"),
                failed=recovery_result.get("failed"),
                no_checkpoint=recovery_result.get("no_checkpoint"),
            )
    except Exception as e:
        # 恢复失败不应阻止服务启动
        logger.error(
            "task_recovery_on_startup_error",
            error=str(e),
            error_type=type(e).__name__,
        )
    
    # 初始化技术栈测验数据（如果缺失则生成）
    try:
        from app.services.tech_assessment_initializer import initialize_tech_assessments
        init_result = await initialize_tech_assessments()
        if init_result.get("generated", 0) > 0:
            logger.info(
                "tech_assessments_initialized",
                total_expected=init_result.get("total_expected"),
                existing=init_result.get("existing"),
                generated=init_result.get("generated"),
                failed=init_result.get("failed"),
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
        from app.services.execution_logger import execution_logger
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

# 配置 CORS 中间件（从环境变量读取允许的域名）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由（新的拆分结构）
app.include_router(api_router_v1)

# 注册WebSocket路由
app.include_router(websocket_router)


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
                "size": pool.size,  # 当前连接数
                "available": pool.available,  # 可用连接数
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

