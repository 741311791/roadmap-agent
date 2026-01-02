"""
Celery Worker 专用数据库会话管理

设计原则：
1. 完全独立于 FastAPI 的模块级 engine，避免 Fork 进程继承问题
2. 使用 NullPool 避免连接池状态跨进程共享
3. 每次创建 session 都建立新连接，用完即弃

问题背景：
- Celery 使用 prefork 模式，子进程继承父进程的连接池引用
- asyncpg 在建立连接时需要设置 JSON codec（异步操作）
- Fork 后的进程中，底层网络资源可能已损坏，导致超时
- 解决方案：为 Celery Worker 使用独立的连接管理，每次创建新连接
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager
import asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IllegalStateChangeError
import structlog

from app.config.settings import settings

logger = structlog.get_logger(__name__)


def create_celery_engine() -> AsyncEngine:
    """
    创建 Celery 专用数据库引擎
    
    关键配置：
    1. 使用 NullPool：每次连接请求都创建新连接，避免连接池状态跨进程共享
    2. asyncpg 默认启用预编译语句缓存，提升重复查询性能
    3. 不注册任何事件监听器：NullPool 每次创建新连接，无需额外清理
    
    Returns:
        AsyncEngine: Celery 专用数据库引擎
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        # 关键：使用 NullPool，避免连接池状态跨进程共享
        poolclass=NullPool,
        connect_args={
            # 应用级配置
            "server_settings": {
                "application_name": "roadmap_agent_celery",
                "jit": "off",
            },
            "command_timeout": 120,
            "timeout": 60,  # 连接超时增加到 60 秒
        },
    )
    
    logger.debug(
        "celery_engine_created",
        engine_id=id(engine),
        pool_class="NullPool",
    )
    
    return engine


# Celery 专用引擎（懒加载）
_celery_engine: AsyncEngine | None = None


def reset_celery_engine_cache() -> None:
    """
    重置 Celery 专用 engine 缓存
    
    ⚠️ 用于 Celery Worker 进程初始化时调用
    
    即使使用 NullPool，子进程仍可能继承父进程的 engine 引用。
    重置确保每个子进程创建自己的 engine。
    """
    global _celery_engine
    if _celery_engine is not None:
        logger.info(
            "celery_engine_cache_reset",
            engine_id=id(_celery_engine),
            message="Celery 专用引擎缓存已重置",
        )
        _celery_engine = None


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


def get_celery_session_maker() -> async_sessionmaker:
    """
    获取 Celery 专用会话工厂
    
    Returns:
        async_sessionmaker: Celery 专用会话工厂
    """
    return async_sessionmaker(
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
    
    使用示例：
    ```python
    async with get_celery_session() as session:
        result = await session.execute(query)
        await session.commit()
    ```
    
    Yields:
        AsyncSession: 数据库会话
    """
    session_maker = get_celery_session_maker()
    session = session_maker()
    
    try:
        yield session
        # 自动提交成功的事务
        await session.commit()
    except Exception:
        # 回滚失败的事务
        await session.rollback()
        raise
    finally:
        # 关闭会话
        await session.close()


async def cleanup_celery_engine() -> None:
    """
    清理 Celery 专用数据库引擎
    
    在 Worker 进程退出时调用。
    由于使用 NullPool，没有连接需要清理，但保留此方法以备将来扩展。
    """
    global _celery_engine
    
    if _celery_engine is not None:
        await _celery_engine.dispose()
        _celery_engine = None
        logger.info("celery_engine_disposed")


# ============================================================
# Celery 专用 Repository Factory
# ============================================================

class CeleryRepositoryFactory:
    """
    Celery 专用 Repository 工厂
    
    与 RepositoryFactory 功能相同，但使用 Celery 专用的数据库连接。
    避免继承 FastAPI 进程的连接池状态。
    """
    
    @asynccontextmanager
    async def create_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        创建 Celery 专用数据库会话
        
        Yields:
            AsyncSession: 数据库会话
        """
        async with get_celery_session() as session:
            yield session
    
    # 导入 Repository 类（避免循环导入，使用延迟导入）
    def create_task_repo(self, session: AsyncSession):
        """创建任务 Repository"""
        from app.db.repositories.task_repo import TaskRepository
        return TaskRepository(session)
    
    def create_roadmap_meta_repo(self, session: AsyncSession):
        """创建路线图元数据 Repository"""
        from app.db.repositories.roadmap_meta_repo import RoadmapMetadataRepository
        return RoadmapMetadataRepository(session)
    
    def create_tutorial_repo(self, session: AsyncSession):
        """创建教程 Repository"""
        from app.db.repositories.tutorial_repo import TutorialRepository
        return TutorialRepository(session)
    
    def create_resource_repo(self, session: AsyncSession):
        """创建资源 Repository"""
        from app.db.repositories.resource_repo import ResourceRepository
        return ResourceRepository(session)
    
    def create_quiz_repo(self, session: AsyncSession):
        """创建测验 Repository"""
        from app.db.repositories.quiz_repo import QuizRepository
        return QuizRepository(session)
    
    def create_intent_analysis_repo(self, session: AsyncSession):
        """创建意图分析 Repository"""
        from app.db.repositories.intent_analysis_repo import IntentAnalysisRepository
        return IntentAnalysisRepository(session)
    
    def create_execution_log_repo(self, session: AsyncSession):
        """创建执行日志 Repository"""
        from app.db.repositories.execution_log_repo import ExecutionLogRepository
        return ExecutionLogRepository(session)
    
    def create_validation_repo(self, session: AsyncSession):
        """创建验证记录 Repository"""
        from app.db.repositories.validation_repo import ValidationRepository
        return ValidationRepository(session)
    
    def create_edit_repo(self, session: AsyncSession):
        """创建编辑记录 Repository"""
        from app.db.repositories.edit_repo import EditRepository
        return EditRepository(session)


# ============================================================
# Celery 专用的 safe_session_with_retry
# ============================================================

def _is_connection_error(error: Exception) -> bool:
    """
    判断是否为数据库连接相关错误
    """
    error_type = type(error).__name__
    error_msg = str(error).lower()
    
    connection_error_types = {
        "InterfaceError",
        "PostgresConnectionError",
        "ConnectionDoesNotExistError",
        "ConnectionRefusedError",
        "TimeoutError",
        "OperationalError",
    }
    
    if error_type in connection_error_types:
        return True
    
    connection_keywords = [
        "connection",
        "timeout",
        "closed",
        "does not exist",
        "terminated",
        "connection refused",
        "pool timeout",
    ]
    
    return any(keyword in error_msg for keyword in connection_keywords)


@asynccontextmanager
async def celery_safe_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Celery 专用的安全数据库会话上下文管理器（无重试）
    
    使用 Celery 专用的 NullPool 引擎，避免 Fork 进程继承问题。
    
    Yields:
        AsyncSession: 数据库会话
    """
    session_maker = get_celery_session_maker()
    session = session_maker()
    
    try:
        yield session
    except (GeneratorExit, IllegalStateChangeError):
        pass
    finally:
        if session is not None:
            try:
                await asyncio.sleep(0)
                await asyncio.shield(session.close())
            except Exception:
                pass


@asynccontextmanager
async def celery_safe_session_with_retry(
    max_retries: int = 3,
    base_backoff: float = 0.5,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Celery 专用的带重试机制的安全会话上下文管理器
    
    与 session.py 中的 safe_session_with_retry 功能相同，
    但使用 Celery 专用的 NullPool 引擎，避免 Fork 进程继承问题。
    
    Args:
        max_retries: 最大重试次数（默认 3 次）
        base_backoff: 基础退避时间（秒）
    
    Yields:
        AsyncSession: 数据库会话
    """
    session = None
    last_error = None
    session_maker = get_celery_session_maker()
    
    # Phase 1: 带重试的连接获取
    for attempt in range(max_retries):
        try:
            session = session_maker()
            break
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            
            is_pool_timeout = "pool timeout" in error_msg or "timeout" in error_msg
            is_conn_error = _is_connection_error(e)
            
            if (is_pool_timeout or is_conn_error) and attempt < max_retries - 1:
                wait_time = base_backoff * (attempt + 1)
                logger.warning(
                    "celery_db_session_create_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    wait_seconds=wait_time,
                    error=str(e)[:200],
                    error_type=type(e).__name__,
                )
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(
                    "celery_db_session_create_failed",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise
    
    if session is None:
        if last_error:
            raise last_error
        raise RuntimeError("Failed to create Celery database session after retries")
    
    # Phase 2: yield 会话
    request_cancelled = False
    
    try:
        yield session
    except asyncio.CancelledError:
        request_cancelled = True
        logger.warning(
            "celery_db_session_cancelled",
            message="Celery 会话：请求被取消，强制清理数据库会话",
        )
        raise
    except (GeneratorExit, IllegalStateChangeError):
        pass
    finally:
        if session is not None:
            try:
                await asyncio.sleep(0)
                await asyncio.shield(session.close())
                logger.debug("celery_db_session_closed_successfully")
            except IllegalStateChangeError:
                pass
            except asyncio.CancelledError:
                logger.error(
                    "celery_db_session_close_cancelled_despite_shield",
                    message="⚠️ Celery 会话关闭在 shield 保护下仍被取消",
                )
            except Exception as e:
                logger.warning(
                    "celery_db_session_close_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
            finally:
                session = None

