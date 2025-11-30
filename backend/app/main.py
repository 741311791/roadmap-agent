"""
FastAPI 主应用
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
import structlog

from app.api.v1.router import api_router_v1
from app.core.dependencies import init_orchestrator, cleanup_orchestrator
from app.db.minio_init import ensure_bucket_exists

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("application_startup")
    
    # 初始化全局 orchestrator 和 Redis 连接
    await init_orchestrator()
    
    # 初始化 MinIO bucket（如果不存在则创建）
    await ensure_bucket_exists()
    
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

# 注册路由
app.include_router(api_router_v1, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "version": "1.0.0"}

