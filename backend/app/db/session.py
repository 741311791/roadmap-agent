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
    echo=settings.DEBUG,
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
        "command_timeout": 60,  # 命令超时 60 秒
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
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

