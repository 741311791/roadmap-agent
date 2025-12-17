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
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 关闭 SQL 查询日志输出，避免终端信息过载
    pool_size=20,  # 增加连接池大小
    max_overflow=40,  # 增加溢出连接数
    pool_pre_ping=True,  # 连接前 ping 检查
    pool_recycle=3600,  # 1小时回收连接，避免长时间连接过期
    pool_timeout=30,  # 获取连接的超时时间（秒）
    connect_args={
        "server_settings": {
            "application_name": "roadmap_agent",
            "jit": "off",  # 禁用 JIT，可能提高稳定性
        },
        "command_timeout": 300,  # 命令超时 300 秒（5分钟），避免长时间运行的查询超时
        "timeout": 30,  # 连接超时 30 秒
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
    """
    session = AsyncSessionLocal()
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
        
    finally:
        # 确保会话被关闭
        try:
            await session.close()
        except Exception as close_error:
            logger.warning(
                "db_session_close_failed",
                error=str(close_error),
                error_type=type(close_error).__name__,
            )

