"""
Celery Worker 专用数据库会话管理（生产级极简版）

核心原则：
- 使用 NullPool：每次创建新连接，避免 Fork 进程继承问题
- 简洁直接：依赖 SQLAlchemy 的健壮性
- 零防御性编程：信任成熟的底层库
- 与主 session.py 设计一致

设计背景：
- Celery 使用 prefork 模式，子进程继承父进程的连接池引用
- NullPool 确保每个进程独立管理数据库连接
- 避免跨进程的连接池状态共享问题
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool
import structlog

from app.config.settings import settings

logger = structlog.get_logger(__name__)

# ============================================================
# Celery 专用引擎（NullPool）
# ============================================================

_celery_engine: AsyncEngine | None = None


def create_celery_engine() -> AsyncEngine:
    """
    创建 Celery 专用数据库引擎
    
    关键配置：
    - NullPool：每次连接请求都创建新连接
    - 避免连接池状态跨进程共享
    - asyncpg 默认启用预编译语句缓存
    
    Returns:
        AsyncEngine: Celery 专用数据库引擎
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=NullPool,  # ⭐ 关键：避免连接池状态跨进程共享
        connect_args={
            "server_settings": {
                "application_name": "roadmap_agent_celery",
                "jit": "off",
            },
            "command_timeout": 120,
            "timeout": 60,
        },
    )
    
    logger.debug(
        "celery_engine_created",
        engine_id=id(engine),
        pool_class="NullPool",
    )
    
    return engine


def get_celery_engine() -> AsyncEngine:
    """
    获取 Celery 专用数据库引擎（懒加载）
    
    每个 Worker 进程首次调用时创建独立的引擎实例。
    
    Returns:
        AsyncEngine: Celery 专用数据库引擎
    """
    global _celery_engine
    
    if _celery_engine is None:
        _celery_engine = create_celery_engine()
        logger.info(
            "celery_engine_initialized",
            engine_id=id(_celery_engine),
        )
    
    return _celery_engine


def reset_celery_engine_cache() -> None:
    """
    重置 Celery 专用 engine 缓存
    
    在 Celery Worker 进程初始化时调用。
    清空继承自父进程的 engine 引用，确保子进程创建新的 engine。
    """
    global _celery_engine
    if _celery_engine is not None:
        logger.info(
            "celery_engine_cache_reset",
            engine_id=id(_celery_engine),
            message="Celery 专用引擎缓存已重置",
        )
        _celery_engine = None


async def cleanup_celery_engine() -> None:
    """
    清理 Celery 专用数据库引擎
    
    在 Worker 进程退出时调用。
    由于使用 NullPool，没有连接池需要清理，但保留此方法以备将来扩展。
    """
    global _celery_engine
    
    if _celery_engine is not None:
        await _celery_engine.dispose()
        _celery_engine = None
        logger.info("celery_engine_disposed")


# ============================================================
# Celery 专用会话工厂
# ============================================================

celery_session_maker = async_sessionmaker(
    get_celery_engine(),
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@asynccontextmanager
async def get_celery_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取 Celery 专用数据库会话（上下文管理器）
    
    使用场景：
    - Celery 异步任务中的数据库操作
    - 需要独立于 FastAPI 进程的连接管理
    
    特性：
    - 使用 NullPool，每次创建新连接
    - 自动事务管理（成功 commit，失败 rollback）
    - SQLAlchemy 自动处理会话关闭
    
    使用示例：
    ```python
    @celery_app.task
    async def my_task():
        async with get_celery_session() as session:
            result = await session.execute(query)
            # ✅ 自动 commit/rollback
    ```
    
    Yields:
        AsyncSession: 数据库会话
    """
    async with celery_session_maker.begin() as session:
        yield session
        # ✅ SQLAlchemy 自动处理 commit/rollback/close
