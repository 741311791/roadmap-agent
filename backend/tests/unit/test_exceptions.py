"""
错误响应模型单元测试

测试 app.core.exceptions 模块中的所有功能。
"""
import pytest
from app.core.exceptions import (
    ErrorCode,
    ErrorResponse,
    format_error_response,
    sanitize_error_message,
    get_user_friendly_message,
)


class TestErrorCodeEnum:
    """测试错误码枚举"""
    
    def test_error_code_enum_values(self):
        """验证所有错误码枚举值"""
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.NOT_FOUND == "NOT_FOUND"
        assert ErrorCode.UNAUTHORIZED == "UNAUTHORIZED"
        assert ErrorCode.FORBIDDEN == "FORBIDDEN"
        assert ErrorCode.BAD_REQUEST == "BAD_REQUEST"
        assert ErrorCode.CONFLICT == "CONFLICT"
        assert ErrorCode.INTERNAL_SERVER_ERROR == "INTERNAL_SERVER_ERROR"
        assert ErrorCode.DATABASE_ERROR == "DATABASE_ERROR"
        assert ErrorCode.EXTERNAL_SERVICE_ERROR == "EXTERNAL_SERVICE_ERROR"
        assert ErrorCode.TIMEOUT_ERROR == "TIMEOUT_ERROR"
    
    def test_error_code_is_string(self):
        """验证错误码是字符串类型"""
        assert isinstance(ErrorCode.NOT_FOUND, str)
        assert isinstance(ErrorCode.INTERNAL_SERVER_ERROR, str)


class TestFormatErrorResponse:
    """测试 format_error_response 函数"""
    
    def test_basic_error_response(self):
        """测试基本错误响应格式"""
        response = format_error_response(
            code=ErrorCode.NOT_FOUND,
            message="Test error message",
            request_id="test-123",
            include_debug=False,
        )
        
        assert isinstance(response, ErrorResponse)
        assert response.error.code == ErrorCode.NOT_FOUND
        assert response.error.message == "Test error message"
        assert response.error.request_id == "test-123"
        assert response.error.timestamp is not None
        assert response.error.debug_info is None
    
    def test_error_response_with_debug(self):
        """测试包含调试信息的错误响应"""
        try:
            raise ValueError("Test exception")
        except Exception as e:
            response = format_error_response(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Internal error",
                exception=e,
                include_debug=True,
            )
        
        assert response.error.debug_info is not None
        assert response.error.debug_info.exception_type == "ValueError"
        assert "Test exception" in response.error.debug_info.traceback
        assert "raise ValueError" in response.error.debug_info.traceback
    
    def test_error_response_without_debug(self):
        """测试不包含调试信息的错误响应（生产环境）"""
        try:
            raise ValueError("Test exception")
        except Exception as e:
            response = format_error_response(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Internal error",
                exception=e,
                include_debug=False,
            )
        
        assert response.error.debug_info is None
    
    def test_error_response_with_details(self):
        """测试包含业务详情的错误响应"""
        details = {"field": "email", "reason": "Invalid format"}
        response = format_error_response(
            code=ErrorCode.VALIDATION_ERROR,
            message="Validation failed",
            details=details,
        )
        
        assert response.error.details == details
    
    def test_error_response_auto_debug_based_on_settings(self, monkeypatch):
        """测试根据环境变量自动决定是否包含调试信息"""
        # 设置开发环境
        monkeypatch.setenv("DEBUG", "True")
        
        # 重新加载 settings
        import importlib
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        try:
            raise ValueError("Test exception")
        except Exception as e:
            response = format_error_response(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Internal error",
                exception=e,
            )
        
        # 开发环境应包含调试信息
        assert response.error.debug_info is not None


class TestSanitizeErrorMessage:
    """测试 sanitize_error_message 函数"""
    
    def test_sanitize_password_in_message(self, monkeypatch):
        """测试清理包含密码的错误消息"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        # 重新加载 settings
        import importlib
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        message = "Connection failed to postgresql://user:password@localhost:5432/db"
        sanitized = sanitize_error_message(message)
        
        # 生产环境应返回通用错误消息
        assert "password" not in sanitized.lower()
        assert sanitized == "An internal error occurred. Please contact support."
    
    def test_sanitize_api_key_in_message(self, monkeypatch):
        """测试清理包含 API 密钥的错误消息"""
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        # 重新加载 settings
        import importlib
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        message = "Failed to authenticate with api_key: sk-abc123"
        sanitized = sanitize_error_message(message)
        
        assert sanitized == "An internal error occurred. Please contact support."
    
    def test_no_sanitization_in_development(self, monkeypatch):
        """测试开发环境不清理错误消息"""
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        # 重新加载 settings
        import importlib
        import app.config.settings as settings_module
        importlib.reload(settings_module)
        
        message = "Connection failed to postgresql://user:password@localhost:5432/db"
        sanitized = sanitize_error_message(message)
        
        # 开发环境保留原始消息
        assert sanitized == message
    
    def test_normal_message_not_sanitized(self):
        """测试普通错误消息不被清理"""
        message = "User not found"
        sanitized = sanitize_error_message(message)
        
        assert sanitized == message


class TestGetUserFriendlyMessage:
    """测试 get_user_friendly_message 函数"""
    
    def test_connection_error(self):
        """测试 ConnectionError 的用户友好消息"""
        exc = ConnectionError("Failed to connect")
        message = get_user_friendly_message(exc)
        
        assert message == "Failed to connect to the service. Please try again later."
    
    def test_timeout_error(self):
        """测试 TimeoutError 的用户友好消息"""
        exc = TimeoutError("Request timed out")
        message = get_user_friendly_message(exc)
        
        assert message == "The request timed out. Please try again."
    
    def test_unknown_exception(self):
        """测试未映射异常返回原始消息"""
        exc = RuntimeError("Something went wrong")
        message = get_user_friendly_message(exc)
        
        assert message == "Something went wrong"
    
    def test_validation_error(self):
        """测试 ValidationError 的用户友好消息"""
        from pydantic import ValidationError as PydanticValidationError
        
        try:
            # 创建一个简单的 Pydantic 验证错误
            from pydantic import BaseModel
            class TestModel(BaseModel):
                email: str
            TestModel(email=123)  # 类型错误
        except PydanticValidationError as exc:
            message = get_user_friendly_message(exc)
            # ValidationError 映射到友好消息
            assert "Invalid input data" in message or "validation" in message.lower()


class TestErrorResponseModel:
    """测试 ErrorResponse Pydantic 模型"""
    
    def test_error_response_serialization(self):
        """测试错误响应可以序列化为 JSON"""
        response = format_error_response(
            code=ErrorCode.NOT_FOUND,
            message="Test error",
            request_id="test-123",
        )
        
        json_data = response.model_dump()
        
        assert "error" in json_data
        assert json_data["error"]["code"] == "NOT_FOUND"
        assert json_data["error"]["message"] == "Test error"
        assert json_data["error"]["request_id"] == "test-123"
    
    def test_error_response_with_debug_serialization(self):
        """测试包含调试信息的错误响应序列化"""
        try:
            raise ValueError("Test exception")
        except Exception as e:
            response = format_error_response(
                code=ErrorCode.INTERNAL_SERVER_ERROR,
                message="Internal error",
                exception=e,
                include_debug=True,
            )
        
        json_data = response.model_dump()
        
        assert "debug_info" in json_data["error"]
        assert json_data["error"]["debug_info"]["exception_type"] == "ValueError"
        assert json_data["error"]["debug_info"]["traceback"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

