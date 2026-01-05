"""
生产环境模式端到端测试

测试生产环境下的异常处理行为（堆栈跟踪隐藏、敏感信息清理）。
"""
import pytest
from unittest.mock import patch
import importlib


class TestProductionModeStackTraceHiding:
    """测试生产环境隐藏堆栈跟踪"""
    
    def test_production_mode_hides_traceback_in_error_response(self, monkeypatch):
        """测试生产环境错误响应不包含堆栈跟踪"""
        # 设置生产环境
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "False")
        
        # 重新加载 settings
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.exceptions import format_error_response, ErrorCode
        
        # 创建异常
        try:
            raise ValueError("Production test error")
        except Exception as e:
            response = format_error_response(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Internal error",
                exception=e,
            )
        
        # 验证不包含调试信息
        assert response.error.debug_info is None
    
    def test_development_mode_includes_traceback(self, monkeypatch):
        """测试开发环境错误响应包含堆栈跟踪"""
        # 设置开发环境
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("DEBUG", "True")
        
        # 重新加载 settings
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.exceptions import format_error_response, ErrorCode
        
        # 创建异常
        try:
            raise ValueError("Development test error")
        except Exception as e:
            response = format_error_response(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Internal error",
                exception=e,
            )
        
        # 验证包含调试信息
        assert response.error.debug_info is not None
        assert response.error.debug_info.exception_type == "ValueError"
        assert "Development test error" in response.error.debug_info.traceback


class TestSensitiveInformationSanitization:
    """测试敏感信息清理"""
    
    def test_sanitize_database_connection_string(self, monkeypatch):
        """测试清理数据库连接字符串"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        # 重新加载 settings
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.exceptions import sanitize_error_message
        
        message = "Connection failed to postgresql://user:password@localhost:5432/db"
        sanitized = sanitize_error_message(message)
        
        # 生产环境应返回通用错误消息
        assert "password" not in sanitized.lower()
        assert "postgresql://" not in sanitized
        assert sanitized == "An internal error occurred. Please contact support."
    
    def test_sanitize_api_key(self, monkeypatch):
        """测试清理 API 密钥"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        # 重新加载 settings
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.exceptions import sanitize_error_message
        
        message = "Failed to authenticate with api_key: sk-abc123def456"
        sanitized = sanitize_error_message(message)
        
        assert "api_key" not in sanitized.lower()
        assert "sk-abc123" not in sanitized
    
    def test_sanitize_redis_url(self, monkeypatch):
        """测试清理 Redis URL"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        # 重新加载 settings
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.exceptions import sanitize_error_message
        
        message = "Cannot connect to redis://default:secret@redis.example.com:6379"
        sanitized = sanitize_error_message(message)
        
        assert "secret" not in sanitized
        assert "redis://" not in sanitized
    
    def test_no_sanitization_for_normal_messages(self):
        """测试普通消息不被清理"""
        from app.core.exceptions import sanitize_error_message
        
        message = "User not found"
        sanitized = sanitize_error_message(message)
        
        assert sanitized == message
    
    def test_development_mode_preserves_sensitive_info(self, monkeypatch):
        """测试开发环境保留敏感信息（用于调试）"""
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        # 重新加载 settings
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.exceptions import sanitize_error_message
        
        message = "Connection failed to postgresql://user:password@localhost:5432/db"
        sanitized = sanitize_error_message(message)
        
        # 开发环境保留原始消息
        assert sanitized == message


class TestCeleryProductionMode:
    """测试 Celery 在生产环境下的行为"""
    
    def test_celery_task_failure_hides_traceback_in_production(self, monkeypatch):
        """测试 Celery 任务失败在生产环境隐藏堆栈"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "False")
        
        # 重新加载 settings
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.celery_error_handler import handle_task_failure
        
        mock_task = type('Task', (), {'name': 'prod.task'})()
        test_exception = ValueError("Production task error")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            handle_task_failure(
                sender=mock_task,
                task_id='prod-task-123',
                exception=test_exception,
            )
            
            call_kwargs = mock_logger.error.call_args.kwargs
            # 生产环境不应包含 traceback
            assert 'traceback' not in call_kwargs or call_kwargs['traceback'] is None
    
    def test_celery_task_failure_includes_traceback_in_development(self, monkeypatch):
        """测试 Celery 任务失败在开发环境包含堆栈"""
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("DEBUG", "True")
        
        # 重新加载 settings
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.celery_error_handler import handle_task_failure
        
        mock_task = type('Task', (), {'name': 'dev.task'})()
        test_exception = ValueError("Development task error")
        
        with patch('app.core.celery_error_handler.logger') as mock_logger:
            handle_task_failure(
                sender=mock_task,
                task_id='dev-task-456',
                exception=test_exception,
            )
            
            call_kwargs = mock_logger.error.call_args.kwargs
            # 开发环境应包含 traceback
            assert 'traceback' in call_kwargs
            assert call_kwargs['traceback'] is not None


class TestEnvironmentConfiguration:
    """测试环境配置"""
    
    def test_environment_variable_detection(self, monkeypatch):
        """测试环境变量检测"""
        # 测试生产环境
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        from app.config.settings import settings
        
        assert settings.ENVIRONMENT == "production"
        
        # 测试开发环境
        monkeypatch.setenv("ENVIRONMENT", "development")
        importlib.reload(settings_module)
        from app.config.settings import settings as settings2
        
        assert settings2.ENVIRONMENT == "development"
    
    def test_debug_flag_detection(self, monkeypatch):
        """测试 DEBUG 标志检测"""
        # 测试 DEBUG=True
        monkeypatch.setenv("DEBUG", "True")
        
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        from app.config.settings import settings
        
        assert settings.DEBUG is True
        
        # 测试 DEBUG=False
        monkeypatch.setenv("DEBUG", "False")
        importlib.reload(settings_module)
        from app.config.settings import settings as settings2
        
        assert settings2.DEBUG is False


class TestUserFriendlyMessages:
    """测试用户友好消息"""
    
    def test_technical_error_converted_to_friendly_message(self):
        """测试技术性错误转换为用户友好消息"""
        from app.core.exceptions import get_user_friendly_message
        
        exc = ConnectionError("OSError: [Errno 111] Connection refused")
        message = get_user_friendly_message(exc)
        
        # 应该返回用户友好的消息，而不是技术细节
        assert "Failed to connect to the service" in message
        assert "OSError" not in message
        assert "Errno 111" not in message
    
    def test_timeout_error_friendly_message(self):
        """测试超时错误友好消息"""
        from app.core.exceptions import get_user_friendly_message
        
        exc = TimeoutError("socket.timeout: timed out")
        message = get_user_friendly_message(exc)
        
        assert "timed out" in message.lower()
        assert "socket.timeout" not in message


class TestProductionSafetyChecklist:
    """测试生产安全检查清单"""
    
    def test_no_debug_info_in_http_responses(self, monkeypatch):
        """测试 HTTP 响应不包含调试信息"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("DEBUG", "False")
        
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.exceptions import format_error_response, ErrorCode
        
        try:
            raise RuntimeError("Critical error")
        except Exception as e:
            response = format_error_response(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Internal server error",
                exception=e,
            )
        
        json_data = response.model_dump()
        assert "debug_info" not in json_data["error"] or json_data["error"]["debug_info"] is None
    
    def test_sensitive_patterns_detected(self, monkeypatch):
        """测试敏感模式检测"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        from app.core.exceptions import sanitize_error_message
        
        sensitive_messages = [
            "password: secret123",
            "api_key: sk-abc",
            "token: eyJhbGciOiJ",
            "DATABASE_URL=postgresql://...",
        ]
        
        for msg in sensitive_messages:
            sanitized = sanitize_error_message(msg)
            # 所有敏感消息都应该被清理
            assert sanitized == "An internal error occurred. Please contact support."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

