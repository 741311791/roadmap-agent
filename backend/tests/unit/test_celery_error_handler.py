"""
Celery 错误处理工具单元测试

测试 app.core.celery_error_handler 模块中的工具函数。
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.celery_error_handler import (
    should_retry,
    exponential_backoff,
    update_task_status_failed,
)


class TestShouldRetry:
    """测试 should_retry 函数"""
    
    def test_connection_error_should_retry(self):
        """测试 ConnectionError 应该重试"""
        exc = ConnectionError("Failed to connect")
        assert should_retry(exc) is True
    
    def test_timeout_error_should_retry(self):
        """测试 TimeoutError 应该重试"""
        exc = TimeoutError("Request timed out")
        assert should_retry(exc) is True
    
    def test_value_error_should_not_retry(self):
        """测试 ValueError 不应该重试"""
        exc = ValueError("Invalid input")
        assert should_retry(exc) is False
    
    def test_runtime_error_should_not_retry(self):
        """测试 RuntimeError 不应该重试"""
        exc = RuntimeError("Something went wrong")
        assert should_retry(exc) is False
    
    def test_generic_exception_should_not_retry(self):
        """测试通用异常不应该重试"""
        exc = Exception("Generic error")
        assert should_retry(exc) is False


class TestExponentialBackoff:
    """测试 exponential_backoff 函数"""
    
    def test_first_retry(self):
        """测试第一次重试延迟"""
        delay = exponential_backoff(retry_count=0)
        assert delay == 60  # 基础延迟 60 秒
    
    def test_second_retry(self):
        """测试第二次重试延迟"""
        delay = exponential_backoff(retry_count=1)
        assert delay == 120  # 60 * 2^1 = 120 秒
    
    def test_third_retry(self):
        """测试第三次重试延迟"""
        delay = exponential_backoff(retry_count=2)
        assert delay == 240  # 60 * 2^2 = 240 秒
    
    def test_custom_base_delay(self):
        """测试自定义基础延迟"""
        delay = exponential_backoff(retry_count=0, base_delay=30)
        assert delay == 30
        
        delay = exponential_backoff(retry_count=1, base_delay=30)
        assert delay == 60
        
        delay = exponential_backoff(retry_count=2, base_delay=30)
        assert delay == 120
    
    def test_large_retry_count(self):
        """测试大重试次数"""
        delay = exponential_backoff(retry_count=5)
        assert delay == 60 * (2 ** 5)  # 1920 秒


class TestUpdateTaskStatusFailed:
    """测试 update_task_status_failed 函数"""
    
    @pytest.mark.asyncio
    async def test_update_task_status_success(self):
        """测试成功更新任务状态"""
        task_id = "test-task-123"
        error = ValueError("Test error")
        
        # Mock 数据库会话和仓库
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_task_status = AsyncMock()
        
        with patch('app.core.celery_error_handler.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            with patch('app.core.celery_error_handler.RoadmapRepository') as mock_repo_class:
                mock_repo_class.return_value = mock_repo
                
                # 执行函数
                await update_task_status_failed(task_id, error)
                
                # 验证调用
                mock_repo.update_task_status.assert_called_once()
                call_kwargs = mock_repo.update_task_status.call_args.kwargs
                
                assert call_kwargs['task_id'] == task_id
                assert call_kwargs['status'] == 'failed'
                assert call_kwargs['current_step'] == 'failed'
                assert 'Test error' in call_kwargs['error_message']
                
                # 验证提交
                mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_task_status_truncates_long_message(self):
        """测试长错误消息被截断"""
        task_id = "test-task-456"
        long_message = "X" * 1000
        error = ValueError(long_message)
        
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_task_status = AsyncMock()
        
        with patch('app.core.celery_error_handler.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            with patch('app.core.celery_error_handler.RoadmapRepository') as mock_repo_class:
                mock_repo_class.return_value = mock_repo
                
                await update_task_status_failed(task_id, error)
                
                # 验证错误消息被截断
                call_kwargs = mock_repo.update_task_status.call_args.kwargs
                assert len(call_kwargs['error_message']) <= 500
    
    @pytest.mark.asyncio
    async def test_update_task_status_handles_db_error(self):
        """测试数据库更新失败时的处理"""
        task_id = "test-task-789"
        error = ValueError("Test error")
        
        mock_session = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_task_status.side_effect = Exception("DB connection failed")
        
        with patch('app.core.celery_error_handler.AsyncSessionLocal') as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            with patch('app.core.celery_error_handler.RoadmapRepository') as mock_repo_class:
                mock_repo_class.return_value = mock_repo
                
                with patch('app.core.celery_error_handler.logger') as mock_logger:
                    # 执行函数，不应该抛出异常
                    await update_task_status_failed(task_id, error)
                    
                    # 验证记录了错误日志
                    mock_logger.error.assert_called_once()
                    call_kwargs = mock_logger.error.call_args.kwargs
                    assert call_kwargs['task_id'] == task_id
                    assert 'failed_to_update_task_status' in call_kwargs.get('event', '')


class TestHandleTaskFailure:
    """测试 handle_task_failure 函数"""
    
    def test_handle_task_failure_logs_error(self):
        """测试任务失败处理记录日志"""
        from app.core.celery_error_handler import handle_task_failure
        
        # Mock 任务
        mock_task = type('Task', (), {'name': 'test_task'})()
        test_exception = ValueError("Test error")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            handle_task_failure(
                sender=mock_task,
                task_id='test-123',
                exception=test_exception
            )
            
            # 验证日志
            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args.kwargs
            assert call_kwargs['task_id'] == 'test-123'
            assert call_kwargs['task_name'] == 'test_task'
            assert call_kwargs['error_type'] == 'ValueError'
            assert call_kwargs['error_message'] == 'Test error'
    
    def test_handle_task_failure_with_debug_mode(self, monkeypatch):
        """测试开发环境包含堆栈跟踪"""
        from app.core.celery_error_handler import handle_task_failure
        
        # 设置开发环境
        monkeypatch.setenv("DEBUG", "True")
        
        # 重新加载 settings
        import importlib
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        mock_task = type('Task', (), {'name': 'test_task'})()
        test_exception = ValueError("Test error")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            handle_task_failure(
                sender=mock_task,
                task_id='test-123',
                exception=test_exception
            )
            
            call_kwargs = mock_logger.error.call_args.kwargs
            # 开发环境应包含 traceback
            assert 'traceback' in call_kwargs


class TestHandleTaskRetry:
    """测试 handle_task_retry 函数"""
    
    def test_handle_task_retry_logs_info(self):
        """测试任务重试处理记录日志"""
        from app.core.celery_error_handler import handle_task_retry
        
        mock_task = type('Task', (), {'name': 'test_task'})()
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            handle_task_retry(
                sender=mock_task,
                task_id='test-456',
                reason='Connection timeout'
            )
            
            # 验证日志
            mock_logger.info.assert_called_once()
            call_kwargs = mock_logger.info.call_args.kwargs
            assert call_kwargs['task_id'] == 'test-456'
            assert call_kwargs['task_name'] == 'test_task'
            assert call_kwargs['reason'] == 'Connection timeout'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

