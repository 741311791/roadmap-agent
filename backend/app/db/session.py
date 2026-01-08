"""
数据库会话管理（生产级极简版 - 符合架构指南）

核心原则：
- 简洁直接：依赖 SQLAlchemy 的健壮性
- 零防御性编程：信任成熟的底层库
- 职责边界清晰：session.py 只提供会话
- 读写分离：GET 用只读会话，POST/PUT/DELETE 用事务会话
"""
from typing import AsyncGenerator, Annotated
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy import event, text
from fastapi import Depends
import structlog
import time

from app.config.settings import settings

logger = structlog.get_logger()

# ============================================================
# Prometheus 指标定义（可选监控）
# ============================================================
try:
    from prometheus_client import Histogram, Gauge, Counter
    
    db_connection_hold_time = Histogram(
        'db_connection_hold_seconds',
        'Duration a connection is held before return to pool',
        buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120]
    )
    
    db_pool_connections_in_use = Gauge(
        'db_pool_connections_in_use',
        'Number of database connections currently checked out'
    )
    
    db_pool_size_gauge = Gauge(
        'db_pool_size',
        'Current size of the connection pool'
    )
    
    db_pool_connection_timeouts = Counter(
        'db_pool_connection_timeouts_total',
        'Number of connection pool timeout errors'
    )
    
    db_query_duration = Histogram(
        'db_query_duration_seconds',
        'Database query execution time',
        labelnames=['operation'],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
    )
    
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
# 数据库引擎（单例模式）
# ============================================================

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,  # 启用连接健康检查
    pool_recycle=300,  # 5分钟回收连接
    pool_timeout=60,
    pool_use_lifo=True,
    connect_args={
        "server_settings": {
            "application_name": "roadmap_agent",
            "jit": "off",
        },
        "command_timeout": 120,
        "timeout": 30,
    },
)

# ============================================================
# 连接池事件监听器（诊断和监控）
# ============================================================

@event.listens_for(engine.sync_engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    """从连接池获取连接时触发"""
    connection_record.info["checkout_time"] = time.time()
    
    if PROMETHEUS_ENABLED:
        db_pool_connections_in_use.inc()
        try:
            pool = engine.pool
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


@event.listens_for(engine.sync_engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
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
        
        # 提取操作类型
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
        
        if PROMETHEUS_ENABLED:
            db_query_duration.labels(operation=operation).observe(duration)
        
        # 慢查询阈值：100ms
        SLOW_QUERY_THRESHOLD = 0.1
        
        if duration > SLOW_QUERY_THRESHOLD:
            logger.warning(
                "slow_query_detected",
                duration_ms=round(duration * 1000, 2),
                operation=operation,
                statement=statement_cached[:500] if statement_cached else "N/A",
                threshold_ms=round(SLOW_QUERY_THRESHOLD * 1000, 2),
            )
            
            if PROMETHEUS_ENABLED:
                db_slow_query_count.labels(operation=operation).inc()
    
    except Exception as e:
        logger.debug(
            "query_tracking_error",
            error=str(e),
            error_type=type(e).__name__,
        )

# ============================================================
# 会话工厂
# ============================================================

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# ============================================================
# Session 依赖注入（读写分离）
# ============================================================


async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """
    只读 Session（GET 请求使用）
    
    使用场景：
    - GET 请求
    - 查询操作
    - 不需要事务的场景
    
    特性：
    - 不自动 commit
    - 异常时 SQLAlchemy 自动关闭会话
    
    使用示例:
        from app.db.session import CurrentSession
        
        @router.get("/roadmaps/{roadmap_id}")
        async def get_roadmap(
            roadmap_id: str,
            session: CurrentSession,
        ):
            result = await session.execute(select(Roadmap))
            return result.scalar_one_or_none()
    """
    async with async_session_maker() as session:
        yield session
        # ✅ SQLAlchemy 自动处理会话关闭


async def get_db_transaction() -> AsyncGenerator[AsyncSession, None]:
    """
    事务 Session（POST/PUT/DELETE 使用）
    
    使用场景：
    - POST/PUT/DELETE 请求
    - 需要修改数据的操作
    - 需要明确事务边界的场景
    
    特性：
    - 成功自动 commit
    - 异常自动 rollback
    - 异常时 SQLAlchemy 自动关闭会话
    
    使用示例:
        from app.db.session import CurrentSessionTransaction
        
        @router.post("/roadmaps")
        async def create_roadmap(
            request: RoadmapCreate,
            session: CurrentSessionTransaction,
        ):
            roadmap = Roadmap(**request.dict())
            session.add(roadmap)
            # ✅ 函数结束时自动 commit
            return roadmap
    """
    async with async_session_maker.begin() as session:
        yield session
        # ✅ SQLAlchemy 自动处理 commit/rollback


# ============================================================
# 向后兼容：保留旧的 get_db() 名称
# ============================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    向后兼容的会话获取函数
    
    ⚠️ 新代码请使用：
    - GET 请求 → get_db_readonly()
    - POST/PUT/DELETE → get_db_transaction()
    """
    async for session in get_db_transaction():
        yield session


# ============================================================
# 便捷的手动会话获取（用于非 FastAPI 上下文）
# ============================================================

def get_session() -> AsyncSession:
    """
    获取一个新的数据库会话（手动管理）
    
    ⚠️ 注意：调用方负责关闭会话
    
    使用示例:
        session = get_session()
        try:
            result = await session.execute(query)
            await session.commit()
        finally:
            await session.close()
    
    ⚠️ 推荐使用上下文管理器:
        async with async_session_maker() as session:
            ...
    """
    return async_session_maker()


# ============================================================
# 类型别名（用于依赖注入）
# ============================================================

# 只读 Session（用于 GET 请求和查询操作）
CurrentSession = Annotated[
    AsyncSession,
    Depends(get_db_readonly),
]

# 写 Session（用于 POST/PUT/DELETE 请求和事务操作）
CurrentSessionTransaction = Annotated[
    AsyncSession,
    Depends(get_db_transaction),
]

# ============================================================
# 监控和健康检查工具
# ============================================================


async def get_pool_status() -> dict:
    """
    获取连接池状态（用于健康检查和监控）
    
    Returns:
        包含连接池状态信息的字典
    """
    pool = engine.pool
    
    checked_out = pool.checkedout()
    pool_size = pool.size()
    max_overflow = pool._max_overflow
    max_connections = pool_size + max_overflow
    
    usage_ratio = checked_out / max_connections if max_connections > 0 else 0
    
    if usage_ratio > 0.8:
        logger.warning(
            "db_pool_high_usage",
            checked_out=checked_out,
            max_connections=max_connections,
            usage_ratio=round(usage_ratio * 100, 1),
            message=f"⚠️ 连接池使用率过高 ({round(usage_ratio * 100, 1)}%)，可能导致连接耗尽",
        )
    
    invalid_count = 0
    try:
        if hasattr(pool, 'invalidatedcount'):
            invalid_count = pool.invalidatedcount()
    except Exception:
        pass
    
    return {
        "pool_size": pool_size,
        "checked_out": checked_out,
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
        "invalid": invalid_count,
        "max_overflow": max_overflow,
        "max_connections": max_connections,
        "usage_ratio": round(usage_ratio * 100, 2),
    }


async def check_db_health() -> dict:
    """
    检查数据库连接健康状态
    
    Returns:
        健康状态信息
    """
    start_time = time.time()
    try:
        async with async_session_maker() as session:
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


# ============================================================
# 初始化函数
# ============================================================

async def init_db():
    """初始化数据库（创建表）"""
    from sqlmodel import SQLModel
    
    async with engine.begin() as conn:
        # 生产环境应使用 Alembic 迁移
        if settings.ENVIRONMENT == "development":
            await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("database_tables_created")


# ============================================================
# Celery Worker 专用重置函数
# ============================================================

def reset_engine_cache() -> None:
    """
    重置数据库引擎（Celery Worker 进程初始化时调用）
    
    ⚠️ 注意：Celery Worker 应该使用专门的 celery_session.py
    此函数保留用于向后兼容。
    """
    logger.info(
        "db_engine_reset_called",
        message="⚠️ reset_engine_cache() 已被调用，但当前实现使用单例引擎。"
                "Celery Worker 应该使用 app.db.celery_session",
    )
