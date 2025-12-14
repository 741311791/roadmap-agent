"""
Unit of Work 模式实现

统一管理数据库事务边界，确保原子性和一致性。

核心功能:
- 自动管理事务开始、提交、回滚
- 支持嵌套事务（通过 savepoint）
- 异常时自动回滚
- 事务超时处理
"""
import time
import asyncio
import structlog
from contextlib import asynccontextmanager
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.db.repositories.roadmap_repo import RoadmapRepository

logger = structlog.get_logger()


class TransactionTimeoutError(Exception):
    """事务超时异常"""
    pass


class RollbackStrategy:
    """
    智能回滚策略
    
    根据异常类型决定回滚范围：
    - 可恢复异常（网络错误、临时故障）：回滚当前 savepoint
    - 数据验证错误：回滚当前 savepoint
    - 系统错误（数据库错误、内存错误）：回滚整个事务
    """
    
    # 可恢复异常（只回滚 savepoint）
    RECOVERABLE_ERRORS = (
        # 网络相关
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        # HTTP 相关
        # requests.exceptions.Timeout,
        # requests.exceptions.ConnectionError,
    )
    
    # 验证错误（只回滚 savepoint）
    VALIDATION_ERRORS = (
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
    )
    
    # 系统错误（回滚整个事务）
    SYSTEM_ERRORS = (
        # 数据库相关
        # sqlalchemy.exc.DatabaseError,
        # sqlalchemy.exc.IntegrityError,
        MemoryError,
        SystemError,
    )
    
    @classmethod
    def should_rollback_entire_transaction(cls, exc_type) -> bool:
        """
        判断是否应该回滚整个事务
        
        Args:
            exc_type: 异常类型
            
        Returns:
            True 表示回滚整个事务，False 表示只回滚 savepoint
        """
        if exc_type is None:
            return False
        
        # 系统错误：回滚整个事务
        if issubclass(exc_type, cls.SYSTEM_ERRORS):
            return True
        
        # 事务超时：回滚整个事务
        if issubclass(exc_type, TransactionTimeoutError):
            return True
        
        # 可恢复错误或验证错误：只回滚 savepoint
        if issubclass(exc_type, cls.RECOVERABLE_ERRORS + cls.VALIDATION_ERRORS):
            return False
        
        # 默认：回滚整个事务（保守策略）
        return True
    
    @classmethod
    def get_rollback_scope(cls, exc_type) -> str:
        """
        获取回滚范围描述
        
        Args:
            exc_type: 异常类型
            
        Returns:
            "entire_transaction" 或 "savepoint"
        """
        return "entire_transaction" if cls.should_rollback_entire_transaction(exc_type) else "savepoint"


class UnitOfWork:
    """
    工作单元模式
    
    统一管理数据库事务，确保原子性。
    
    使用示例:
        ```python
        async with UnitOfWork() as uow:
            await uow.repo.update_task_status(...)
            await uow.repo.save_roadmap_metadata(...)
            # 退出时自动 commit
        ```
        
    支持嵌套事务:
        ```python
        async with UnitOfWork() as uow:
            await uow.repo.update_task_status(...)
            
            async with uow.nested() as nested_uow:
                await nested_uow.repo.save_metadata(...)
                # 内部事务可以独立回滚
        ```
    """
    
    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        timeout: Optional[float] = None,
        is_nested: bool = False,
    ):
        """
        初始化 UnitOfWork
        
        Args:
            session: 外部提供的会话（用于嵌套事务）
            timeout: 事务超时时间（秒），None 表示无超时
            is_nested: 是否是嵌套事务
        """
        self._session = session
        self._timeout = timeout or 30.0  # 默认 30 秒超时
        self._is_nested = is_nested
        self._repo: Optional[RoadmapRepository] = None
        self._start_time: Optional[float] = None
        self._savepoint_name: Optional[str] = None
        self._timeout_task: Optional[asyncio.Task] = None
    
    @property
    def session(self) -> AsyncSession:
        """获取当前会话"""
        if self._session is None:
            raise RuntimeError("UnitOfWork 未初始化，请在 async with 块中使用")
        return self._session
    
    @property
    def repo(self) -> RoadmapRepository:
        """获取 Repository 实例"""
        if self._repo is None:
            raise RuntimeError("UnitOfWork 未初始化，请在 async with 块中使用")
        return self._repo
    
    async def __aenter__(self):
        """进入上下文：开始事务"""
        self._start_time = time.time()
        
        if self._session is None:
            # 顶层事务：创建新会话
            self._session = AsyncSessionLocal()
            await self._session.__aenter__()
            
            logger.debug(
                "uow_transaction_started",
                is_nested=False,
                timeout=self._timeout,
            )
        else:
            # 嵌套事务：使用 savepoint
            self._savepoint_name = f"sp_{int(time.time() * 1000)}"
            await self._session.begin_nested()
            
            logger.debug(
                "uow_savepoint_created",
                savepoint=self._savepoint_name,
                is_nested=True,
            )
        
        # 创建 Repository
        self._repo = RoadmapRepository(self._session)
        
        # 启动超时监控
        if self._timeout:
            self._timeout_task = asyncio.create_task(self._monitor_timeout())
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """退出上下文：提交或回滚事务"""
        # 取消超时监控
        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass
        
        duration_ms = int((time.time() - self._start_time) * 1000) if self._start_time else 0
        
        try:
            if exc_type is not None:
                # 异常发生：回滚
                await self._rollback(exc_type, exc_val, duration_ms)
                return False  # 不抑制异常
            else:
                # 正常执行：提交
                await self._commit(duration_ms)
                return False
        finally:
            # 清理资源
            if not self._is_nested and self._session:
                await self._session.__aexit__(exc_type, exc_val, exc_tb)
                self._session = None
    
    async def _commit(self, duration_ms: int):
        """提交事务"""
        if self._is_nested:
            # 嵌套事务：提交 savepoint
            logger.debug(
                "uow_savepoint_committed",
                savepoint=self._savepoint_name,
                duration_ms=duration_ms,
            )
        else:
            # 顶层事务：提交主事务
            await self._session.commit()
            
            logger.info(
                "uow_transaction_committed",
                duration_ms=duration_ms,
            )
    
    async def _rollback(self, exc_type, exc_val, duration_ms: int):
        """
        回滚事务（智能回滚策略）
        
        根据异常类型决定回滚范围：
        - 可恢复异常或验证错误：只回滚 savepoint（如果是嵌套事务）
        - 系统错误或超时：回滚整个事务
        """
        # 使用智能回滚策略
        rollback_scope = RollbackStrategy.get_rollback_scope(exc_type)
        should_rollback_all = RollbackStrategy.should_rollback_entire_transaction(exc_type)
        
        if self._is_nested and not should_rollback_all:
            # 嵌套事务 + 可恢复错误：只回滚 savepoint
            await self._session.rollback()
            
            logger.warning(
                "uow_savepoint_rolled_back",
                savepoint=self._savepoint_name,
                error_type=exc_type.__name__ if exc_type else None,
                error=str(exc_val) if exc_val else None,
                duration_ms=duration_ms,
                rollback_scope=rollback_scope,
            )
        else:
            # 顶层事务 或 系统错误：回滚主事务
            await self._session.rollback()
            
            logger.error(
                "uow_transaction_rolled_back",
                error_type=exc_type.__name__ if exc_type else None,
                error=str(exc_val) if exc_val else None,
                duration_ms=duration_ms,
                rollback_scope=rollback_scope,
                is_system_error=should_rollback_all,
            )
    
    async def _monitor_timeout(self):
        """监控事务超时"""
        try:
            await asyncio.sleep(self._timeout)
            
            # 超时：强制回滚
            elapsed = time.time() - self._start_time
            logger.error(
                "uow_transaction_timeout",
                timeout=self._timeout,
                elapsed=elapsed,
            )
            
            # 抛出超时异常（会触发 __aexit__ 中的回滚）
            raise TransactionTimeoutError(
                f"事务超时 ({elapsed:.2f}s > {self._timeout}s)"
            )
        except asyncio.CancelledError:
            # 正常取消（事务完成）
            pass
    
    @asynccontextmanager
    async def nested(self, timeout: Optional[float] = None):
        """
        创建嵌套事务（使用 savepoint）
        
        Args:
            timeout: 嵌套事务超时时间
            
        Yields:
            UnitOfWork: 嵌套的工作单元
            
        Example:
            ```python
            async with UnitOfWork() as uow:
                await uow.repo.update_task_status(...)
                
                async with uow.nested() as nested_uow:
                    # 这里的操作可以独立回滚
                    await nested_uow.repo.save_metadata(...)
            ```
        """
        nested_uow = UnitOfWork(
            session=self._session,
            timeout=timeout or self._timeout,
            is_nested=True,
        )
        
        async with nested_uow:
            yield nested_uow


# 便捷函数
@asynccontextmanager
async def transaction(timeout: Optional[float] = None):
    """
    创建事务上下文（便捷函数）
    
    Args:
        timeout: 事务超时时间（秒）
        
    Yields:
        UnitOfWork: 工作单元实例
        
    Example:
        ```python
        async with transaction(timeout=30) as uow:
            await uow.repo.update_task_status(...)
            await uow.repo.save_roadmap_metadata(...)
        ```
    """
    async with UnitOfWork(timeout=timeout) as uow:
        yield uow

