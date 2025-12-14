"""
FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog

from app.api.v1.router import router as api_router_v1
from app.api.v1.websocket import router as websocket_router
from app.core.dependencies import init_orchestrator, cleanup_orchestrator
from app.db.minio_init import ensure_bucket_exists
from app.services.task_recovery_service import recover_interrupted_tasks_on_startup


logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("application_startup")
    
    # 初始化全局 orchestrator 和 Redis 连接
    await init_orchestrator()
    
    # 初始化 MinIO bucket（如果不存在则创建）
    await ensure_bucket_exists()
    
    # 恢复被中断的任务（服务器重启后自动恢复）
    try:
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
    
    yield
    
    logger.info("application_shutdown")
    # 清理 orchestrator 和关闭 Redis 连接
    await cleanup_orchestrator()


app = FastAPI(
    title="Learning Roadmap Generation System",
    description="基于 Multi-Agent 的个性化学习路线图生成系统",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
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
    """健康检查端点"""
    return {"status": "healthy", "version": "1.0.0"}

