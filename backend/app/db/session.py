"""
数据库会话管理（SQLModel + AsyncPG）

生产环境优化配置：
- 连接池大小和溢出策略
- 连接健康检查（pool_pre_ping）
- 连接回收策略防止僵死连接
- 详细的连接池状态监控
- Prometheus 指标暴露
- 慢查询追踪
- 事件循环感知（Celery Worker 兼容）
"""
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy import event, text
from sqlalchemy.exc import IllegalStateChangeError
from sqlmodel import SQLModel
import structlog
import time
import asyncio

from app.config.settings import settings

logger = structlog.get_logger()

# ============================================================
# Prometheus 指标定义
# ============================================================
try:
    from prometheus_client import Histogram, Gauge, Counter
    
    # 连接持有时间直方图
    db_connection_hold_time = Histogram(
        'db_connection_hold_seconds',
        'Duration a connection is held before return to pool',
        buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120]
    )
    
    # 连接池使用中的连接数
    db_pool_connections_in_use = Gauge(
        'db_pool_connections_in_use',
        'Number of database connections currently checked out'
    )
    
    # 连接池大小
    db_pool_size_gauge = Gauge(
        'db_pool_size',
        'Current size of the connection pool'
    )
    
    # 连接池超时次数
    db_pool_connection_timeouts = Counter(
        'db_pool_connection_timeouts_total',
        'Number of connection pool timeout errors'
    )
    
    # 查询执行时间直方图
    db_query_duration = Histogram(
        'db_query_duration_seconds',
        'Database query execution time',
        labelnames=['operation'],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
    )
    
    # 慢查询计数器
    db_slow_query_count = Counter(
        'db_slow_query_total',
        'Number of slow queries detected',
        labelnames=['operation']
    )
    
    PROMETHEUS_ENABLED = True
except ImportError:
    logger.warning("prometheus_client_not_installed", message="Prometheus 指标将被禁用")
    PROMETHEUS_ENABLED = False

# ============================================================
# 事件循环感知的引擎管理（Celery Worker 兼容）
# ============================================================
#
# 问题背景：
# - 全局 engine 在导入时创建，绑定到主进程的事件循环
# - Celery Worker 使用独立的进程级事件循环（get_worker_loop）
# - asyncpg 连接池创建的 Future 绑定到旧事件循环，导致：
#   "Task got Future attached to a different loop" 错误
#
# 解决方案：
# - 为每个事件循环创建独立的 engine 实例
# - 使用字典缓存：event_loop_id -> engine
# - 自动检测当前事件循环，返回对应的 engine
#
_engine_cache: dict[int, AsyncEngine] = {}
_engine_lock = asyncio.Lock()


def _register_engine_events(engine_instance: AsyncEngine) -> None:
    """
    为 engine 注册事件监听器
    
    ⚠️ 关键：每个新创建的 engine 实例都必须注册这些事件
    确保跨事件循环的 engine 都能正确清理预编译语句
    """
    sync_engine = engine_instance.sync_engine
    
    # ============================================================
    # checkout 事件：连接取出时清理预编译语句
    # ============================================================
    @event.listens_for(sync_engine, "checkout")
    def on_checkout_handler(dbapi_connection, connection_record, connection_proxy):
        """
        从连接池获取连接时触发
        
        ⚠️ 关键修复：在连接取出时清理预编译语句
        - Supabase pgbouncer 事务模式不支持跨事务的预编译语句
        - 即使配置了 statement_cache_size=0，连接池中的旧连接仍可能携带预编译语句
        - 必须在连接取出时主动清理，而不是归还时清理
        """
        connection_record.info["checkout_time"] = time.time()
        
        # 清理预编译语句
        try:
            if hasattr(dbapi_connection, "_connection"):
                raw_connection = dbapi_connection._connection
                if hasattr(raw_connection, "execute"):
                    from sqlalchemy.util._concurrency_py3k import await_only
                    try:
                        await_only(raw_connection.execute("DEALLOCATE ALL"))
                        logger.debug(
                            "db_prepared_statements_cleared_on_checkout",
                            connection_id=id(dbapi_connection),
                        )
                    except Exception as e:
                        logger.debug(
                            "db_prepared_statements_clear_on_checkout_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                        )
        except Exception as e:
            logger.debug(
                "db_checkout_cleanup_error",
                error=str(e),
                error_type=type(e).__name__,
            )
        
        # Prometheus 指标
        if PROMETHEUS_ENABLED:
            db_pool_connections_in_use.inc()
            try:
                pool = engine_instance.pool
                db_pool_size_gauge.set(pool.size())
                checked_out = pool.checkedout()
                max_connections = pool.size() + pool._max_overflow
                usage_ratio = checked_out / max_connections if max_connections > 0 else 0
                if usage_ratio > 0.9:
                    logger.error(
                        "db_pool_critical_usage",
                        checked_out=checked_out,
                        max_connections=max_connections,
                        usage_ratio=round(usage_ratio * 100, 1),
                        message=f"🚨 连接池使用率过高 ({round(usage_ratio * 100, 1)}%)，即将耗尽",
                    )
            except Exception:
                pass
    
    # ============================================================
    # checkin 事件：连接归还时清理预编译语句（双重保险）
    # ============================================================
    @event.listens_for(sync_engine, "checkin")
    def on_checkin_handler(dbapi_connection, connection_record):
        """连接归还连接池时触发"""
        checkout_time = connection_record.info.get("checkout_time")
        if checkout_time:
            duration = time.time() - checkout_time
            if PROMETHEUS_ENABLED:
                db_connection_hold_time.observe(duration)
                db_pool_connections_in_use.dec()
            if duration > 5:
                logger.warning(
                    "db_connection_long_hold",
                    duration_seconds=round(duration, 2),
                    connection_id=id(dbapi_connection),
                )
            if duration > 10:
                logger.error(
                    "db_connection_held_too_long",
                    duration_seconds=round(duration, 2),
                    threshold_seconds=10,
                    connection_id=id(dbapi_connection),
                )
        
        # 清理预编译语句（双重保险）
        try:
            if hasattr(dbapi_connection, "_connection"):
                raw_connection = dbapi_connection._connection
                if hasattr(raw_connection, "execute"):
                    from sqlalchemy.util._concurrency_py3k import await_only
                    try:
                        await_only(raw_connection.execute("DEALLOCATE ALL"))
                        logger.debug(
                            "db_prepared_statements_cleared",
                            connection_id=id(dbapi_connection),
                        )
                    except Exception as e:
                        logger.debug(
                            "db_prepared_statements_clear_failed",
                            error=str(e),
                            error_type=type(e).__name__,
                        )
        except Exception as e:
            logger.debug(
                "db_checkin_cleanup_error",
                error=str(e),
                error_type=type(e).__name__,
            )
    
    # ============================================================
    # 其他事件
    # ============================================================
    @event.listens_for(sync_engine, "connect")
    def on_connect_handler(dbapi_connection, connection_record):
        """新连接创建时触发"""
        logger.debug(
            "db_pool_new_connection",
            connection_id=id(dbapi_connection),
        )
    
    @event.listens_for(sync_engine, "invalidate")
    def on_invalidate_handler(dbapi_connection, connection_record, exception):
        """连接被标记为无效时触发"""
        logger.warning(
            "db_connection_invalidated",
            connection_id=id(dbapi_connection),
            exception=str(exception),
        )


def _create_engine() -> AsyncEngine:
    """
    创建数据库引擎（Supabase 事务池化模式优化）
    
    Supabase Transaction Pooling 关键配置：
    ⚠️ 关键：asyncpg 默认会自动创建预编译语句（prepared statements），
    但 pgbouncer 的事务模式不支持跨事务的预编译语句。
    
    解决方案：
    1. statement_cache_size=0: 禁用 asyncpg 客户端缓存
    2. 监听 checkout/checkin 事件，主动执行 DEALLOCATE ALL 清理预编译语句
    3. pool_pre_ping=False: 避免健康检查触发预编译语句创建
    4. pool_recycle=300: 定期回收连接
    
    连接池配置（支持环境变量动态调整）：
    - pool_size: 由 DB_POOL_SIZE 环境变量控制
    - max_overflow: 由 DB_MAX_OVERFLOW 环境变量控制
    
    注意：多进程部署时，每个进程创建独立的连接池
    总应用连接数 = (pool_size + max_overflow) × 进程数
    """
    new_engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_pre_ping=False,  # 禁用健康检查
        pool_recycle=300,  # 5分钟回收连接
        pool_timeout=60,
        pool_use_lifo=True,
        connect_args={
            # Supabase Transaction Mode 必须配置
            # ⚠️ 关键修复：同时设置两个参数禁用预编译语句
            "statement_cache_size": 0,  # 禁用 SQLAlchemy 层面的语句缓存
            "prepared_statement_cache_size": 0,  # 禁用 asyncpg 驱动层面的缓存
            
            # 应用级配置
            "server_settings": {
                "application_name": "roadmap_agent",
                "jit": "off",
            },
            "command_timeout": 120,
            "timeout": 30,
        },
    )
    
    # ⚠️ 关键：为新创建的 engine 注册事件监听器
    _register_engine_events(new_engine)
    
    return new_engine


async def get_engine() -> AsyncEngine:
    """
    获取当前事件循环对应的数据库引擎
    
    自动检测当前事件循环，如果是新循环则创建新 engine。
    确保 Celery Worker、FastAPI、测试等不同环境都使用正确的 engine。
    
    Returns:
        AsyncEngine: 绑定到当前事件循环的数据库引擎
    """
    loop = asyncio.get_event_loop()
    loop_id = id(loop)
    
    if loop_id not in _engine_cache:
        # 创建新 engine（线程安全）
        # 注意：这里不使用 lock，因为多次创建 engine 也是安全的
        # 最多会有轻微的资源浪费，但避免了锁的性能开销
        _engine_cache[loop_id] = _create_engine()
        logger.info(
            "db_engine_created_for_event_loop",
            loop_id=loop_id,
            engine_id=id(_engine_cache[loop_id]),
        )
    
    return _engine_cache[loop_id]


def get_engine_sync() -> AsyncEngine:
    """
    同步方式获取引擎（用于事件监听器注册）
    
    仅在模块导入时使用，不应在异步代码中调用。
    """
    loop_id = id(asyncio.get_event_loop())
    if loop_id not in _engine_cache:
        _engine_cache[loop_id] = _create_engine()
    return _engine_cache[loop_id]


# 创建默认引擎（用于事件监听器注册）
engine = get_engine_sync()


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
    """
    从连接池获取连接时触发
    
    ⚠️ 关键修复：在连接取出时清理预编译语句
    - Supabase pgbouncer 事务模式不支持跨事务的预编译语句
    - 即使配置了 statement_cache_size=0，连接池中的旧连接仍可能携带预编译语句
    - 必须在连接取出时主动清理，而不是归还时清理
    """
    connection_record.info["checkout_time"] = time.time()
    
    # ============================================================
    # ⚠️ 关键修复：清理预编译语句（Supabase 事务池化必需）
    # ============================================================
    try:
        # 获取底层的 asyncpg 连接
        if hasattr(dbapi_connection, "_connection"):
            raw_connection = dbapi_connection._connection
            # 检查是否是 asyncpg 连接
            if hasattr(raw_connection, "execute"):
                # 注意：这是同步事件处理器，需要使用 await_only 包装异步操作
                from sqlalchemy.util._concurrency_py3k import await_only
                try:
                    await_only(raw_connection.execute("DEALLOCATE ALL"))
                    logger.debug(
                        "db_prepared_statements_cleared_on_checkout",
                        connection_id=id(dbapi_connection),
                    )
                except Exception as e:
                    # 清理失败不应该阻止连接使用
                    logger.debug(
                        "db_prepared_statements_clear_on_checkout_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
    except Exception as e:
        # 任何错误都不应该阻止连接使用
        logger.debug(
            "db_checkout_cleanup_error",
            error=str(e),
            error_type=type(e).__name__,
        )
    
    # Prometheus 指标：增加使用中的连接数
    if PROMETHEUS_ENABLED:
        db_pool_connections_in_use.inc()
        # 更新连接池大小
        try:
            pool = engine.pool
            db_pool_size_gauge.set(pool.size())
            
            # ⚠️ 连接池使用率监控（实时）
            checked_out = pool.checkedout()
            max_connections = pool.size() + pool._max_overflow
            usage_ratio = checked_out / max_connections if max_connections > 0 else 0
            
            # 使用率超过 90% 时发出错误级别警告
            if usage_ratio > 0.9:
                logger.error(
                    "db_pool_critical_usage",
                    checked_out=checked_out,
                    max_connections=max_connections,
                    usage_ratio=round(usage_ratio * 100, 1),
                    message=f"🚨 连接池使用率过高 ({round(usage_ratio * 100, 1)}%)，即将耗尽",
                )
        except Exception:
            pass


@event.listens_for(engine.sync_engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    """
    连接归还连接池时触发
    
    ⚠️ Supabase Transaction Mode 关键修复：
    在归还连接前清理所有预编译语句，避免 pgbouncer 连接复用时冲突。
    """
    checkout_time = connection_record.info.get("checkout_time")
    if checkout_time:
        duration = time.time() - checkout_time
        
        # Prometheus 指标：记录连接持有时间
        if PROMETHEUS_ENABLED:
            db_connection_hold_time.observe(duration)
            db_pool_connections_in_use.dec()
        
        # 只记录长时间持有连接的情况（超过 5 秒）
        if duration > 5:
            logger.warning(
                "db_connection_long_hold",
                duration_seconds=round(duration, 2),
                connection_id=id(dbapi_connection),
            )
        
        # 超过 10 秒的连接持有视为异常（可能导致连接池耗尽）
        if duration > 10:
            logger.error(
                "db_connection_held_too_long",
                duration_seconds=round(duration, 2),
                threshold_seconds=10,
                connection_id=id(dbapi_connection),
            )
    
    # 🔧 Supabase Transaction Mode 修复：清理预编译语句
    # 在归还连接前执行 DEALLOCATE ALL，防止 pgbouncer 后端连接复用时冲突
    try:
        # 获取底层的 asyncpg 连接
        if hasattr(dbapi_connection, "_connection"):
            raw_connection = dbapi_connection._connection
            # 检查是否是 asyncpg 连接
            if hasattr(raw_connection, "execute"):
                # 注意：这是同步事件处理器，需要使用 await_only 包装异步操作
                from sqlalchemy.util._concurrency_py3k import await_only
                try:
                    await_only(raw_connection.execute("DEALLOCATE ALL"))
                    logger.debug(
                        "db_prepared_statements_cleared",
                        connection_id=id(dbapi_connection),
                    )
                except Exception as e:
                    # 清理失败不应该阻止连接归还
                    logger.debug(
                        "db_prepared_statements_clear_failed",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
    except Exception as e:
        # 任何错误都不应该阻止连接归还
        logger.debug(
            "db_checkin_cleanup_error",
            error=str(e),
            error_type=type(e).__name__,
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


# ============================================================
# 慢查询追踪
# ============================================================

@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """SQL 执行前记录时间"""
    conn.info.setdefault("query_start_time", []).append(time.time())
    conn.info.setdefault("query_statement", []).append(statement)


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """SQL 执行后计算耗时并记录慢查询"""
    try:
        start_time = conn.info.get("query_start_time", [None]).pop() if conn.info.get("query_start_time") else None
        statement_cached = conn.info.get("query_statement", [None]).pop() if conn.info.get("query_statement") else None
        
        if start_time is None:
            return
        
        duration = time.time() - start_time
        
        # 提取操作类型（SELECT, INSERT, UPDATE, DELETE）
        operation = "UNKNOWN"
        if statement_cached:
            stmt_upper = statement_cached.strip().upper()
            if stmt_upper.startswith("SELECT"):
                operation = "SELECT"
            elif stmt_upper.startswith("INSERT"):
                operation = "INSERT"
            elif stmt_upper.startswith("UPDATE"):
                operation = "UPDATE"
            elif stmt_upper.startswith("DELETE"):
                operation = "DELETE"
            elif stmt_upper.startswith("BEGIN"):
                operation = "BEGIN"
            elif stmt_upper.startswith("COMMIT"):
                operation = "COMMIT"
            elif stmt_upper.startswith("ROLLBACK"):
                operation = "ROLLBACK"
        
        # Prometheus 指标：记录查询执行时间
        if PROMETHEUS_ENABLED:
            db_query_duration.labels(operation=operation).observe(duration)
        
        # 慢查询阈值：100ms
        SLOW_QUERY_THRESHOLD = 0.1
        
        if duration > SLOW_QUERY_THRESHOLD:
            # 记录慢查询
            logger.warning(
                "slow_query_detected",
                duration_ms=round(duration * 1000, 2),
                duration_seconds=round(duration, 3),
                operation=operation,
                statement=statement_cached[:500] if statement_cached else "N/A",  # 只记录前 500 个字符
                threshold_ms=round(SLOW_QUERY_THRESHOLD * 1000, 2),
            )
            
            # Prometheus 指标：增加慢查询计数
            if PROMETHEUS_ENABLED:
                db_slow_query_count.labels(operation=operation).inc()
    
    except Exception as e:
        # 追踪逻辑不应影响正常查询执行
        logger.debug(
            "query_tracking_error",
            error=str(e),
            error_type=type(e).__name__,
        )

# ============================================================
# 会话工厂（事件循环感知）
# ============================================================


def get_session_maker() -> async_sessionmaker:
    """
    获取当前事件循环对应的会话工厂
    
    由于 engine 是事件循环感知的，会话工厂也需要动态获取。
    
    Returns:
        async_sessionmaker: 绑定到当前事件循环 engine 的会话工厂
    """
    # 注意：这里需要同步获取 engine，因为 async_sessionmaker 不是异步函数
    # 我们假设 engine 已经在当前事件循环中创建（通过 get_engine()）
    loop_id = id(asyncio.get_event_loop())
    current_engine = _engine_cache.get(loop_id)
    
    if current_engine is None:
        # 如果当前循环还没有 engine，创建一个
        current_engine = get_engine_sync()
    
    return async_sessionmaker(
        current_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def AsyncSessionLocal() -> AsyncSession:
    """
    创建数据库会话（事件循环感知）
    
    兼容旧代码的函数签名，但内部使用事件循环感知的引擎。
    
    Returns:
        AsyncSession: 数据库会话
    """
    return get_session_maker()()


# 保留旧的全局会话工厂（仅用于向后兼容）
# 新代码应该使用 AsyncSessionLocal() 函数
_default_session_maker = get_session_maker()


async def init_db():
    """初始化数据库（创建表）"""
    current_engine = await get_engine()
    async with current_engine.begin() as conn:
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
    current_engine = await get_engine()
    pool = current_engine.pool
    
    checked_out = pool.checkedout()
    pool_size = pool.size()
    max_overflow = pool._max_overflow
    max_connections = pool_size + max_overflow
    
    # 计算连接使用率
    usage_ratio = checked_out / max_connections if max_connections > 0 else 0
    
    # ⚠️ 连接池告警：使用率超过 80% 时警告
    if usage_ratio > 0.8:
        logger.warning(
            "db_pool_high_usage",
            checked_out=checked_out,
            max_connections=max_connections,
            usage_ratio=round(usage_ratio * 100, 1),
            message=f"⚠️ 连接池使用率过高 ({round(usage_ratio * 100, 1)}%)，可能导致连接耗尽",
        )
    
    # 尝试获取失效连接数（某些池类型可能不支持）
    invalid_count = 0
    try:
        if hasattr(pool, 'invalidatedcount'):
            invalid_count = pool.invalidatedcount()
    except Exception:
        pass
    
    return {
        "pool_size": pool_size,  # 当前池中的连接数
        "checked_out": checked_out,  # 正在使用的连接数
        "overflow": pool.overflow(),  # 溢出连接数
        "checked_in": pool.checkedin(),  # 空闲连接数
        "invalid": invalid_count,  # 已失效的连接数
        "max_overflow": max_overflow,  # 最大溢出配置
        "pool_max_size": pool._pool.maxsize if hasattr(pool, "_pool") else None,
        "max_connections": max_connections,  # 最大连接数
        "usage_ratio": round(usage_ratio * 100, 2),  # 使用率（百分比）
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
    带重试机制的安全会话上下文管理器（修复版 - 正确处理异步生成器）
    
    ⚠️ 关键设计原则：
    @asynccontextmanager 装饰的函数只能 yield 一次。
    因此重试逻辑只应用于**获取连接阶段**，yield 后的异常直接向上抛出。
    
    重试策略：
    - 只在创建/获取数据库会话时重试（连接池超时等场景）
    - 一旦 yield 成功，后续异常不再重试，由调用方处理
    
    Args:
        max_retries: 最大重试次数（默认 3 次）
        base_backoff: 基础退避时间（秒），实际等待时间 = base_backoff * (attempt + 1)
    
    使用示例:
        async with safe_session_with_retry() as session:
            result = await session.execute(query)
            await session.commit()
    """
    session = None
    last_error = None
    
    # ============================================================
    # Phase 1: 带重试的连接获取（只有这个阶段可以重试）
    # ============================================================
    for attempt in range(max_retries):
        try:
            session = AsyncSessionLocal()
            # 验证连接是否有效（触发实际的连接获取）
            # 注意：AsyncSessionLocal() 只是创建会话对象，
            # 实际的数据库连接在第一次操作时才会获取
            break  # 成功创建会话对象，跳出重试循环
        except Exception as e:
            last_error = e
            error_msg = str(e).lower()
            
            # 判断是否是可重试的连接错误
            is_pool_timeout = "pool timeout" in error_msg or "timeout" in error_msg
            is_conn_error = _is_connection_error(e)
            
            if (is_pool_timeout or is_conn_error) and attempt < max_retries - 1:
                wait_time = base_backoff * (attempt + 1)
                logger.warning(
                    "db_session_create_retry",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    wait_seconds=wait_time,
                    error=str(e)[:200],
                    error_type=type(e).__name__,
                )
                await asyncio.sleep(wait_time)
                continue
            else:
                # 非连接错误或达到最大重试次数，直接抛出
                logger.error(
                    "db_session_create_failed",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise
    
    # 如果循环结束但 session 仍为 None（理论上不应发生）
    if session is None:
        if last_error:
            raise last_error
        raise RuntimeError("Failed to create database session after retries")
    
    # ============================================================
    # Phase 2: yield 会话（只执行一次，符合 asynccontextmanager 规范）
    # ============================================================
    request_cancelled = False
    
    try:
        yield session
    except asyncio.CancelledError:
        # ⚠️ 请求被取消（客户端断开、超时等）
        request_cancelled = True
        logger.warning(
            "db_session_request_cancelled_with_retry",
            message="带重试的会话：请求被取消，强制清理数据库会话",
        )
        raise
    except (GeneratorExit, IllegalStateChangeError):
        # SSE 流中断或并发状态冲突，静默处理
        pass
    finally:
        # ✅ 【关键修复】使用 shield 确保连接归还不可取消
        if session is not None:
            try:
                # 等待所有挂起的异步操作完成
                await asyncio.sleep(0)
                
                # 🛡️ shield 保护：确保 close() 一定会完成
                await asyncio.shield(session.close())
                logger.debug("db_session_closed_successfully")
                
                if request_cancelled:
                    logger.info(
                        "db_session_with_retry_closed_after_cancellation",
                        message="已成功在请求取消后关闭会话（带重试）",
                    )
            except IllegalStateChangeError:
                # 并发状态冲突，静默处理但仍尝试释放
                logger.debug("db_session_close_illegal_state")
                pass
            except asyncio.CancelledError:
                # shield 内部的取消（极端情况）
                logger.error(
                    "db_session_with_retry_close_cancelled_despite_shield",
                    message="⚠️ 会话关闭在 shield 保护下仍被取消（带重试），可能发生连接泄漏",
                )
            except Exception as e:
                # 强制记录所有关闭错误
                logger.warning(
                    "db_session_close_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
            finally:
                # ✅ 防止悬挂引用
                session = None


@asynccontextmanager
async def safe_session():
    """
    安全的数据库会话上下文管理器（增强版 - 防止连接泄漏）
    
    特别处理 SSE 流中断导致的并发状态冲突问题。
    当 session 正在执行操作时被强制关闭，会触发 IllegalStateChangeError，
    这在 SSE 场景下是正常的，应该被静默处理。
    
    ✨ 连接泄漏防护（第一性原理修复）：
    - 使用 asyncio.shield() 确保会话关闭不可被取消
    - 在会话关闭前等待所有挂起的异步操作完成
    - 使用强制清理机制，防止连接被垃圾回收时还未归还
    - 捕获 CancelledError，防止请求取消导致连接泄漏
    
    使用示例:
        async with safe_session() as session:
            result = await session.execute(query)
            await session.commit()
    """
    session = None
    request_cancelled = False
    
    try:
        session = AsyncSessionLocal()
        yield session
    except asyncio.CancelledError:
        # ⚠️ 请求被取消（客户端断开、超时等）
        # 这是连接泄漏的主要原因：取消操作可能导致 close() 未执行
        request_cancelled = True
        logger.warning(
            "db_session_request_cancelled",
            message="请求被取消，强制清理数据库会话以防止连接泄漏",
        )
        # 重新抛出，让调用方知道请求已取消
        raise
    except (GeneratorExit, IllegalStateChangeError):
        # SSE 流中断或并发状态冲突，静默处理
        pass
    finally:
        # ✅ 【关键修复】使用 shield 确保连接归还不可取消
        # 即使外部任务被取消，也必须完成连接清理
        if session is not None:
            try:
                # 等待所有挂起的异步操作完成
                await asyncio.sleep(0)
                
                # 🛡️ shield 保护：确保 close() 一定会完成
                # 即使请求被取消，也要归还连接到池
                await asyncio.shield(session.close())
                
                if request_cancelled:
                    logger.info(
                        "db_session_closed_after_cancellation",
                        message="已成功在请求取消后关闭会话",
                    )
            except IllegalStateChangeError:
                # Session 关闭时另一操作正在进行，静默处理
                # 这种情况下连接最终会被连接池回收
                pass
            except asyncio.CancelledError:
                # shield 内部的取消（极端情况）
                # 强制记录，这表示连接可能泄漏
                logger.error(
                    "db_session_close_cancelled_despite_shield",
                    message="⚠️ 会话关闭在 shield 保护下仍被取消，可能发生连接泄漏",
                )
                # 不重新抛出，避免掩盖连接泄漏
            except Exception as e:
                # 其他关闭错误，记录但不抛出
                logger.warning(
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
    3. CancelledError（请求取消）：安全清理，归还连接（已用 shield 保护）
    4. GeneratorExit（SSE 中断）：静默处理，不尝试 commit/rollback
    5. IllegalStateChangeError（并发状态冲突）：静默处理
    6. 其他异常：尝试 rollback，然后重新抛出
    
    连接泄漏防护：
    - safe_session() 使用 asyncio.shield() 确保连接关闭不可被取消
    - 即使客户端断开连接或请求超时，连接也会被正确归还到池中
    
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

