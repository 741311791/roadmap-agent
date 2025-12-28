"""
数据库会话管理（SQLModel + AsyncPG）

生产环境优化配置：
- 连接池大小和溢出策略
- 连接健康检查（pool_pre_ping）
- 连接回收策略防止僵死连接
- 详细的连接池状态监控
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event, text
from sqlalchemy.exc import IllegalStateChangeError
from sqlmodel import SQLModel
import structlog
import time

from app.config.settings import settings

logger = structlog.get_logger()

# ============================================================
# 连接池配置（优化版 - 减少连接占用，增加超时容忍度）
# ============================================================
#
# 关键参数说明（针对 Railway PostgreSQL，最大连接数 200）：
#
# 1. pool_size=40: 基础连接池大小
#    - 从 60 降至 40，减少基础连接占用
#    - 配合分批保存策略，不再需要大量并发连接
#
# 2. max_overflow=20: 溢出连接数
#    - 从 60 降至 20，限制峰值连接数
#    - 总计: 40 + 20 = 60 个连接（预算：SQLAlchemy 60 + Checkpointer 10 = 70/200）
#
# 3. pool_recycle=300: 5分钟回收连接
#    - 从 600 秒缩短至 300 秒
#    - 更快释放闲置连接，减少僵死连接风险
#
# 4. pool_pre_ping=True: 每次获取连接前测试
#    - 自动剔除已断开的连接
#    - 略有性能开销但大幅提升稳定性
#
# 5. pool_timeout=60: 增加获取连接超时
#    - 从 30 秒提升到 60 秒
#    - 配合重试机制，给予更多等待时间
#
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 关闭 SQL 查询日志输出
    # 注意：异步引擎会自动使用 AsyncAdaptedQueuePool，不需要显式指定
    pool_size=40,  # 基础连接池大小（降低以减少占用）
    max_overflow=20,  # 溢出连接数（总计 60 个连接）
    pool_pre_ping=True,  # 连接前 ping 检查（关键！防止使用已断开的连接）
    pool_recycle=300,  # 5分钟回收连接（缩短以快速释放）
    pool_timeout=60,  # 获取连接超时 60 秒（增加以应对高峰期）
    pool_use_lifo=True,  # LIFO 模式，优先复用最近使用的连接
    connect_args={
        "server_settings": {
            "application_name": "roadmap_agent",
            "jit": "off",  # 禁用 JIT，提高稳定性
        },
        "command_timeout": 120,  # 命令超时 120 秒
        "timeout": 30,  # 连接超时 30 秒
    },
)


# ============================================================
# 连接池事件监听器（诊断用）
# ============================================================

@event.listens_for(engine.sync_engine, "connect")
def on_connect(dbapi_connection, connection_record):
    """新连接创建时触发（用于诊断）"""
    logger.debug(
        "db_pool_new_connection",
        connection_id=id(dbapi_connection),
    )


@event.listens_for(engine.sync_engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """从连接池获取连接时触发"""
    connection_record.info["checkout_time"] = time.time()


@event.listens_for(engine.sync_engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    """连接归还连接池时触发"""
    checkout_time = connection_record.info.get("checkout_time")
    if checkout_time:
        duration = time.time() - checkout_time
        # 只记录长时间持有连接的情况（超过 5 秒）
        if duration > 5:
            logger.warning(
                "db_connection_long_hold",
                duration_seconds=round(duration, 2),
                connection_id=id(dbapi_connection),
            )


@event.listens_for(engine.sync_engine, "invalidate")
def on_invalidate(dbapi_connection, connection_record, exception):
    """连接被标记为无效时触发（重要诊断信息）"""
    logger.warning(
        "db_connection_invalidated",
        connection_id=id(dbapi_connection),
        exception=str(exception) if exception else None,
        exception_type=type(exception).__name__ if exception else None,
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


async def get_pool_status() -> dict:
    """
    获取连接池状态（用于健康检查和监控）
    
    Returns:
        包含连接池状态信息的字典
    """
    pool = engine.pool
    return {
        "pool_size": pool.size(),  # 当前池中的连接数
        "checked_out": pool.checkedout(),  # 正在使用的连接数
        "overflow": pool.overflow(),  # 溢出连接数
        "checked_in": pool.checkedin(),  # 空闲连接数
        "invalid": pool.invalidatedcount(),  # 已失效的连接数
        "max_overflow": pool._max_overflow,  # 最大溢出配置
        "pool_max_size": pool._pool.maxsize if hasattr(pool, "_pool") else None,
    }


async def check_db_health() -> dict:
    """
    检查数据库连接健康状态
    
    执行简单查询验证连接是否可用。
    
    Returns:
        健康状态信息
    """
    start_time = time.time()
    try:
        async with AsyncSessionLocal() as session:
            # 执行简单查询验证连接
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        
        latency_ms = round((time.time() - start_time) * 1000, 2)
        pool_status = await get_pool_status()
        
        return {
            "status": "healthy",
            "latency_ms": latency_ms,
            "pool": pool_status,
        }
    except Exception as e:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(
            "db_health_check_failed",
            error=str(e),
            error_type=type(e).__name__,
            latency_ms=latency_ms,
        )
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__,
            "latency_ms": latency_ms,
        }


def _is_connection_error(error: Exception) -> bool:
    """
    判断是否为数据库连接相关错误
    
    支持的错误类型：
    - asyncpg.InterfaceError: 连接已关闭
    - asyncpg.PostgresConnectionError: 连接错误
    - sqlalchemy.exc.DBAPIError: 底层驱动错误
    - 以及包含特定关键字的其他错误
    
    Args:
        error: 异常对象
        
    Returns:
        True 如果是连接相关错误
    """
    error_type = type(error).__name__
    error_msg = str(error).lower()
    
    # 检查异常类型名称（避免直接导入 asyncpg）
    connection_error_types = {
        "InterfaceError",  # asyncpg: 连接已关闭
        "PostgresConnectionError",  # asyncpg: 连接错误
        "ConnectionDoesNotExistError",  # asyncpg: 连接不存在
        "ConnectionRefusedError",  # 连接被拒绝
        "TimeoutError",  # 超时
        "OperationalError",  # SQLAlchemy: 操作错误（通常是连接问题）
    }
    
    if error_type in connection_error_types:
        return True
    
    # 检查错误信息中的关键字
    connection_keywords = [
        "connection",
        "timeout",
        "closed",
        "does not exist",
        "terminated",
        "connection refused",
        "pool timeout",
        "canceling statement",
        "server closed the connection",
    ]
    
    return any(keyword in error_msg for keyword in connection_keywords)


from contextlib import asynccontextmanager
import asyncio


@asynccontextmanager
async def safe_session_with_retry(
    max_retries: int = 3,
    base_backoff: float = 0.5,
):
    """
    带重试机制的安全会话上下文管理器（增强版 - 防止连接泄漏）
    
    在连接池压力大时，自动重试获取连接。
    使用指数退避策略，避免同时大量重试导致更大压力。
    
    ✨ 连接泄漏防护：
    - 确保在所有路径（正常、异常、重试）下都关闭会话
    - 在会话关闭前等待所有挂起的异步操作完成
    - 使用强制清理机制，防止连接被垃圾回收时还未归还
    
    Args:
        max_retries: 最大重试次数（默认 3 次）
        base_backoff: 基础退避时间（秒），实际等待时间 = base_backoff * (attempt + 1)
    
    使用示例:
        async with safe_session_with_retry() as session:
            result = await session.execute(query)
            await session.commit()
    
    重试策略:
        - 第 1 次失败: 等待 0.5 秒后重试
        - 第 2 次失败: 等待 1.0 秒后重试
        - 第 3 次失败: 抛出异常
    """
    last_error = None
    session = None  # ✅ 在外层初始化，确保 finally 中可访问
    
    for attempt in range(max_retries):
        try:
            session = AsyncSessionLocal()
            try:
                yield session
                return  # 成功执行，直接返回
            except (GeneratorExit, IllegalStateChangeError):
                # SSE 流中断或并发状态冲突，静默处理
                return
            finally:
                # ✅ 增强的清理逻辑：确保连接归还到池
                if session is not None:
                    try:
                        # 等待所有挂起的异步操作完成
                        await asyncio.sleep(0)
                        
                        # 关闭会话（归还连接到池）
                        await session.close()
                    except IllegalStateChangeError:
                        # 并发状态冲突，静默处理
                        pass
                    except Exception as e:
                        logger.debug(
                            "db_session_close_error",
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                    finally:
                        # ✅ 防止会话被意外重用
                        session = None
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            
            # 只有连接池超时等可重试错误才进行重试
            is_pool_timeout = "pool timeout" in error_msg or "timeout" in error_msg
            is_connection_error = _is_connection_error(e)
            
            if (is_pool_timeout or is_connection_error) and attempt < max_retries - 1:
                wait_time = base_backoff * (attempt + 1)
                logger.warning(
                    "db_session_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    wait_seconds=wait_time,
                    error=str(e)[:200],
                    error_type=type(e).__name__,
                )
                await asyncio.sleep(wait_time)
                continue
            else:
                # 非连接相关错误或已达最大重试次数，直接抛出
                raise
    
    # 达到最大重试次数仍失败
    if last_error:
        logger.error(
            "db_session_retry_exhausted",
            max_retries=max_retries,
            error=str(last_error),
            error_type=type(last_error).__name__,
        )
        raise last_error


@asynccontextmanager
async def safe_session():
    """
    安全的数据库会话上下文管理器（增强版 - 防止连接泄漏）
    
    特别处理 SSE 流中断导致的并发状态冲突问题。
    当 session 正在执行操作时被强制关闭，会触发 IllegalStateChangeError，
    这在 SSE 场景下是正常的，应该被静默处理。
    
    ✨ 连接泄漏防护：
    - 在会话关闭前等待所有挂起的异步操作完成
    - 使用强制清理机制，防止连接被垃圾回收时还未归还
    
    使用示例:
        async with safe_session() as session:
            result = await session.execute(query)
            await session.commit()
    """
    session = None
    try:
        session = AsyncSessionLocal()
        yield session
    except (GeneratorExit, IllegalStateChangeError):
        # SSE 流中断或并发状态冲突，静默处理
        pass
    finally:
        # ✅ 增强的清理逻辑：确保连接归还到池
        if session is not None:
            try:
                # 等待所有挂起的异步操作完成
                await asyncio.sleep(0)
                
                # 关闭会话（归还连接到池）
                await session.close()
            except IllegalStateChangeError:
                # Session 关闭时另一操作正在进行，静默处理
                # 这种情况下连接最终会被连接池回收
                pass
            except Exception as e:
                # 其他关闭错误，记录但不抛出
                logger.debug(
                    "db_session_close_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
            finally:
                # ✅ 防止会话被意外重用
                session = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入：获取数据库会话
    
    使用示例:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            ...
        
    异常处理策略：
    1. 正常请求结束：自动 commit
    2. 连接错误：记录警告，跳过 commit/rollback（数据库会自动回滚）
    3. GeneratorExit（SSE 中断）：静默处理，不尝试 commit/rollback
    4. IllegalStateChangeError（并发状态冲突）：静默处理
    5. 其他异常：尝试 rollback，然后重新抛出
    
    连接错误被静默处理的原因：
    - 查询操作通常已完成，数据已返回
    - 写操作会被数据库自动回滚
    - 抛出连接错误只会掩盖真正的业务错误
    """
    async with safe_session() as session:
        try:
            yield session
            
            # 尝试 commit
            try:
                await session.commit()
            except IllegalStateChangeError:
                # 并发状态冲突，静默处理
                pass
            except Exception as commit_error:
                if _is_connection_error(commit_error):
                    # 连接错误：静默处理
                    logger.warning(
                        "db_session_commit_connection_error",
                        error=str(commit_error),
                        error_type=type(commit_error).__name__,
                    )
                else:
                    # 其他错误：记录并重新抛出
                    logger.error(
                        "db_session_commit_failed",
                        error=str(commit_error),
                        error_type=type(commit_error).__name__,
                    )
                    raise
        
        except GeneratorExit:
            # SSE 流式传输中断
            # 不尝试 commit/rollback，直接让会话关闭
            logger.debug("db_session_generator_exit")
            
        except IllegalStateChangeError:
            # 并发状态冲突（SSE 中断时常见）
            # 静默处理，数据库会自动处理未完成的事务
            pass
            
        except Exception as e:
            # 其他异常：尝试回滚
            if _is_connection_error(e):
                # 连接已断开，无法回滚
                logger.warning(
                    "db_session_error_connection_lost",
                    error=str(e),
                    error_type=type(e).__name__,
                )
            else:
                # 尝试回滚
                try:
                    await session.rollback()
                except (IllegalStateChangeError, GeneratorExit):
                    # 并发状态冲突或 SSE 中断，静默处理
                    pass
                except Exception as rollback_error:
                    logger.error(
                        "db_session_rollback_failed",
                        original_error=str(e),
                        rollback_error=str(rollback_error),
                    )
            
            raise

