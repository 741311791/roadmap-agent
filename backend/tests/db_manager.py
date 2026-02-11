"""
测试数据库管理器

专门处理测试环境中的数据库生命周期管理，解决事件循环冲突问题。

核心功能：
- 独立的数据库引擎和连接池
- 在事件循环关闭前完成清理
- 事务级别的数据隔离
"""
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
import structlog

logger = structlog.get_logger()


class TestDatabaseManager:
    """
    测试数据库生命周期管理器
    
    使用独立的引擎和连接池，避免与应用数据库引擎冲突。
    确保在事件循环关闭前完成所有异步清理操作。
    """
    
    _engine: AsyncEngine = None
    _session_maker: async_sessionmaker = None
    _current_event_loop = None
    
    @classmethod
    async def initialize(cls, database_url: str):
        """
        初始化测试数据库管理器
        
        Args:
            database_url: 测试数据库连接字符串
        """
        if cls._engine is not None:
            logger.warning("test_db_manager_already_initialized")
            return
        
        # 记录当前事件循环
        cls._current_event_loop = asyncio.get_running_loop()
        
        # 创建测试专用引擎（使用NullPool避免连接池问题）
        cls._engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            poolclass=NullPool,  # 每次请求创建新连接，避免连接池清理问题
        )
        
        # 创建session maker
        cls._session_maker = async_sessionmaker(
            bind=cls._engine,
            class_=AsyncSession,
            expire_on_commit=False,  # 测试中可能需要访问已提交的对象
        )
        
        logger.info("test_db_manager_initialized", database_url=database_url)
    
    @classmethod
    async def cleanup(cls):
        """
        清理测试数据库资源
        
        确保在当前事件循环关闭前完成清理。
        """
        if cls._engine is None:
            return
        
        try:
            # 检查事件循环是否还在运行
            current_loop = None
            try:
                current_loop = asyncio.get_running_loop()
            except RuntimeError:
                logger.warning("test_db_cleanup_no_event_loop")
                return
            
            # 只在同一个事件循环中清理
            if current_loop == cls._current_event_loop:
                await cls._engine.dispose()
                logger.info("test_db_manager_cleaned_up")
            else:
                logger.warning(
                    "test_db_cleanup_different_loop",
                    message="事件循环已更换，跳过清理"
                )
        except Exception as e:
            logger.error(
                "test_db_cleanup_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
        finally:
            cls._engine = None
            cls._session_maker = None
            cls._current_event_loop = None
    
    @classmethod
    async def get_session(cls) -> AsyncGenerator[AsyncSession, None]:
        """
        获取测试数据库会话
        
        Yields:
            AsyncSession实例
        """
        if cls._session_maker is None:
            raise RuntimeError("TestDatabaseManager未初始化，请先调用initialize()")
        
        async with cls._session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                # 确保会话关闭
                await session.close()
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查是否已初始化
        
        Returns:
            是否已初始化
        """
        return cls._engine is not None

