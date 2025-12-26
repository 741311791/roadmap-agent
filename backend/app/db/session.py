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
# 生产环境配置（数据库最大连接数 200）
# - pool_size=40: 基础连接池（常驻连接）
# - max_overflow=60: 溢出连接（高峰期临时连接）
# - 总计: 100 个连接（预留 100 个给其他服务/管理连接）
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 关闭 SQL 查询日志输出，避免终端信息过载
    pool_size=40,  # 连接池大小（生产环境调大以应对高并发）
    max_overflow=60,  # 溢出连接数（允许更多临时连接）
    pool_pre_ping=True,  # 连接前 ping 检查（防止使用已断开的连接）
    pool_recycle=1800,  # 30分钟回收连接（缩短以避免连接过期）
    pool_timeout=60,  # 获取连接的超时时间（增加到 60 秒，应对 Railway 网络延迟）
    pool_use_lifo=True,  # 使用 LIFO 模式，优先复用最近使用的连接
    connect_args={
        "server_settings": {
            "application_name": "roadmap_agent",
            "jit": "off",  # 禁用 JIT，可能提高稳定性
        },
        "command_timeout": 300,  # 命令超时 300 秒（5分钟），避免长时间运行的查询超时
        "timeout": 60,  # 连接超时 60 秒（增加以应对 Railway 网络延迟）
    },
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
        
    特别说明：
    - 会话在请求结束时自动 commit/rollback
    - 处理连接超时异常，避免服务器关闭连接导致的错误
    - 处理流式传输中断（GeneratorExit），避免会话状态冲突
    - 使用 context manager 确保连接正确释放
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            
            # 尝试 commit，如果连接已经关闭则忽略
            try:
                await session.commit()
            except Exception as commit_error:
                # 检查是否是连接超时相关的异常
                error_msg = str(commit_error).lower()
                is_connection_error = any(
                    keyword in error_msg
                    for keyword in [
                        "connection",
                        "timeout",
                        "closed",
                        "does not exist",
                        "terminated",
                    ]
                )
                
                if is_connection_error:
                    logger.warning(
                        "db_session_commit_connection_error",
                        error=str(commit_error),
                        error_type=type(commit_error).__name__,
                        message="数据库连接已关闭，跳过 commit（数据可能已提交或无需提交）",
                    )
                    # 连接错误时不抛出异常，因为：
                    # 1. 查询操作可能已经完成并返回数据
                    # 2. 如果有写操作，数据库会自动回滚
                else:
                    # 非连接错误，正常抛出
                    logger.error(
                        "db_session_commit_failed",
                        error=str(commit_error),
                        error_type=type(commit_error).__name__,
                    )
                    raise
        
        except GeneratorExit:
            # 客户端断开连接（常见于 SSE 流式传输中断）
            # 此时不应尝试 commit/rollback，直接让会话关闭即可
            logger.info(
                "db_session_generator_exit",
                message="客户端断开连接，会话将被清理（无需 commit/rollback）",
            )
            # 不抛出异常，避免产生 "Task exception was never retrieved" 警告
            # 会话将由 context manager 自动清理
            
        except Exception as e:
            # 捕获其他异常，尝试回滚
            error_msg = str(e).lower()
            is_connection_error = any(
                keyword in error_msg
                for keyword in ["connection", "timeout", "closed", "does not exist"]
            )
            
            if is_connection_error:
                logger.warning(
                    "db_session_rollback_connection_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    message="数据库连接已关闭，跳过 rollback",
                )
            else:
                # 非连接错误，尝试回滚
                try:
                    await session.rollback()
                except Exception as rollback_error:
                    logger.error(
                        "db_session_rollback_failed",
                        original_error=str(e),
                        rollback_error=str(rollback_error),
                    )
            
            raise
        # context manager 会自动关闭会话

