"""
Unit of Work 模式单元测试

测试覆盖:
1. 基本事务提交
2. 异常时自动回滚
3. 嵌套事务（savepoint）
4. 智能回滚策略
5. 事务超时处理
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

from app.core.orchestrator.unit_of_work import (
    UnitOfWork,
    RollbackStrategy,
    TransactionTimeoutError,
    transaction,
)


@pytest.fixture
def mock_session():
    """Mock SQLAlchemy AsyncSession"""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.begin_nested = AsyncMock()
    return session


class TestUnitOfWorkBasic:
    """测试 UnitOfWork 基本功能"""
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal")
    async def test_commit_on_success(self, mock_session_class):
        """测试成功执行时自动提交"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # 使用 UnitOfWork
        async with UnitOfWork(timeout=None) as uow:
            assert uow.session == mock_session
            assert uow.repo is not None
        
        # 验证提交被调用
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal")
    async def test_rollback_on_exception(self, mock_session_class):
        """测试异常时自动回滚"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # 使用 UnitOfWork，抛出异常
        with pytest.raises(ValueError):
            async with UnitOfWork(timeout=None) as uow:
                raise ValueError("Test error")
        
        # 验证回滚被调用
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_transaction_convenience_function(self):
        """测试便捷函数 transaction()"""
        with patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal") as mock_session_class:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session_class.return_value = mock_session
            
            async with transaction(timeout=30) as uow:
                assert isinstance(uow, UnitOfWork)
                assert uow.session == mock_session
            
            mock_session.commit.assert_called_once()


class TestNestedTransactions:
    """测试嵌套事务（savepoint）"""
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal")
    async def test_nested_transaction_commit(self, mock_session_class):
        """测试嵌套事务提交"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.begin_nested = AsyncMock()
        mock_session_class.return_value = mock_session
        
        async with UnitOfWork(timeout=None) as uow:
            # 创建嵌套事务
            async with uow.nested() as nested_uow:
                assert nested_uow.session == mock_session
            
            # 验证 savepoint 被创建
            mock_session.begin_nested.assert_called_once()
        
        # 主事务提交
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal")
    async def test_nested_transaction_rollback(self, mock_session_class):
        """测试嵌套事务回滚不影响主事务"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.begin_nested = AsyncMock()
        mock_session_class.return_value = mock_session
        
        async with UnitOfWork(timeout=None) as uow:
            # 嵌套事务抛出异常
            try:
                async with uow.nested() as nested_uow:
                    raise ValueError("Nested error")
            except ValueError:
                pass  # 捕获异常，继续主事务
            
            # 主事务应该可以继续
            assert uow.session == mock_session
        
        # 验证回滚被调用（嵌套事务）
        mock_session.rollback.assert_called()
        # 主事务仍然提交
        mock_session.commit.assert_called_once()


class TestRollbackStrategy:
    """测试智能回滚策略"""
    
    def test_recoverable_errors(self):
        """测试可恢复错误只回滚 savepoint"""
        assert not RollbackStrategy.should_rollback_entire_transaction(ConnectionError)
        assert not RollbackStrategy.should_rollback_entire_transaction(TimeoutError)
        assert RollbackStrategy.get_rollback_scope(ConnectionError) == "savepoint"
    
    def test_validation_errors(self):
        """测试验证错误只回滚 savepoint"""
        assert not RollbackStrategy.should_rollback_entire_transaction(ValueError)
        assert not RollbackStrategy.should_rollback_entire_transaction(TypeError)
        assert RollbackStrategy.get_rollback_scope(ValueError) == "savepoint"
    
    def test_system_errors(self):
        """测试系统错误回滚整个事务"""
        assert RollbackStrategy.should_rollback_entire_transaction(MemoryError)
        assert RollbackStrategy.should_rollback_entire_transaction(SystemError)
        assert RollbackStrategy.get_rollback_scope(MemoryError) == "entire_transaction"
    
    def test_timeout_error(self):
        """测试超时错误回滚整个事务"""
        assert RollbackStrategy.should_rollback_entire_transaction(TransactionTimeoutError)
        assert RollbackStrategy.get_rollback_scope(TransactionTimeoutError) == "entire_transaction"
    
    def test_unknown_error_default_behavior(self):
        """测试未知错误默认回滚整个事务"""
        class CustomError(Exception):
            pass
        
        # 未知错误应该采用保守策略：回滚整个事务
        assert RollbackStrategy.should_rollback_entire_transaction(CustomError)
        assert RollbackStrategy.get_rollback_scope(CustomError) == "entire_transaction"


class TestTransactionTimeout:
    """测试事务超时处理"""
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal")
    async def test_transaction_timeout(self, mock_session_class):
        """测试事务超时会触发回滚"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # 设置极短的超时时间
        with pytest.raises(TransactionTimeoutError):
            async with UnitOfWork(timeout=0.1) as uow:
                # 模拟长时间操作
                await asyncio.sleep(0.2)
        
        # 验证回滚被调用
        mock_session.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal")
    async def test_transaction_no_timeout(self, mock_session_class):
        """测试正常完成不触发超时"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # 设置足够的超时时间
        async with UnitOfWork(timeout=5.0) as uow:
            await asyncio.sleep(0.1)  # 短暂操作
        
        # 正常提交
        mock_session.commit.assert_called_once()


class TestSmartRollback:
    """测试智能回滚在实际场景中的应用"""
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal")
    async def test_nested_validation_error_only_rollback_savepoint(
        self,
        mock_session_class,
    ):
        """测试嵌套事务中的验证错误只回滚 savepoint"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.begin_nested = AsyncMock()
        mock_session_class.return_value = mock_session
        
        async with UnitOfWork(timeout=None) as uow:
            # 嵌套事务中抛出验证错误
            try:
                async with uow.nested() as nested_uow:
                    raise ValueError("Validation error")
            except ValueError:
                pass  # 捕获并继续
            
            # 主事务继续执行
            pass
        
        # 嵌套事务回滚 savepoint
        mock_session.rollback.assert_called()
        # 主事务仍然提交
        mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal")
    async def test_system_error_rollback_entire_transaction(
        self,
        mock_session_class,
    ):
        """测试系统错误回滚整个事务"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session_class.return_value = mock_session
        
        # 主事务中抛出系统错误
        with pytest.raises(MemoryError):
            async with UnitOfWork(timeout=None) as uow:
                raise MemoryError("Out of memory")
        
        # 整个事务回滚
        mock_session.rollback.assert_called_once()


class TestIntegrationScenarios:
    """测试集成场景"""
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.unit_of_work.AsyncSessionLocal")
    async def test_multiple_nested_transactions(self, mock_session_class):
        """测试多层嵌套事务"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.begin_nested = AsyncMock()
        mock_session_class.return_value = mock_session
        
        async with UnitOfWork(timeout=None) as uow:
            # 第一层嵌套
            async with uow.nested() as nested1:
                # 第二层嵌套
                async with nested1.nested() as nested2:
                    pass
        
        # 验证多次创建 savepoint
        assert mock_session.begin_nested.call_count >= 2
        # 主事务提交
        mock_session.commit.assert_called_once()

