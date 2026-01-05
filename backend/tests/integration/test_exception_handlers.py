"""
FastAPI 异常处理器集成测试

测试 app.core.global_exception_handlers 模块中的异常处理器。
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import OperationalError
from pydantic import ValidationError

from app.core.global_exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    sqlalchemy_exception_handler,
    generic_exception_handler,
)


def create_mock_request(request_id="test-123", url="http://test.com/api/test", method="GET"):
    """创建 Mock 的 FastAPI Request 对象"""
    request = Mock(spec=Request)
    request.url = Mock()
    request.url.__str__ = Mock(return_value=url)
    request.method = method
    request.state = Mock()
    request.state.request_id = request_id
    request.client = Mock()
    request.client.host = "127.0.0.1"
    return request


class TestHttpExceptionHandler:
    """测试 HTTP 异常处理器"""
    
    @pytest.mark.asyncio
    async def test_handles_404_not_found(self):
        """测试处理 404 Not Found 错误"""
        request = create_mock_request()
        exc = StarletteHTTPException(status_code=404, detail="Resource not found")
        
        response = await http_exception_handler(request, exc)
        
        assert response.status_code == 404
        data = response.body.decode()
        assert "NOT_FOUND" in data
        assert "Resource not found" in data
        assert "test-123" in data
    
    @pytest.mark.asyncio
    async def test_handles_401_unauthorized(self):
        """测试处理 401 Unauthorized 错误"""
        request = create_mock_request()
        exc = StarletteHTTPException(status_code=401, detail="Unauthorized")
        
        response = await http_exception_handler(request, exc)
        
        assert response.status_code == 401
        data = response.body.decode()
        assert "UNAUTHORIZED" in data
    
    @pytest.mark.asyncio
    async def test_handles_500_internal_server_error(self):
        """测试处理 500 Internal Server Error"""
        request = create_mock_request()
        exc = StarletteHTTPException(status_code=500, detail="Internal server error")
        
        response = await http_exception_handler(request, exc)
        
        assert response.status_code == 500
        data = response.body.decode()
        assert "INTERNAL_SERVER_ERROR" in data
    
    @pytest.mark.asyncio
    async def test_includes_request_id(self):
        """测试响应包含 request_id"""
        request = create_mock_request(request_id="custom-request-id")
        exc = StarletteHTTPException(status_code=404, detail="Not found")
        
        response = await http_exception_handler(request, exc)
        
        data = response.body.decode()
        assert "custom-request-id" in data


class TestValidationExceptionHandler:
    """测试验证错误处理器"""
    
    @pytest.mark.asyncio
    async def test_handles_validation_error(self):
        """测试处理 Pydantic 验证错误"""
        request = create_mock_request()
        
        # 创建验证错误
        from pydantic import BaseModel, Field
        
        class TestModel(BaseModel):
            email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
        
        try:
            TestModel(email="invalid-email")
        except ValidationError as ve:
            # 将 Pydantic ValidationError 转换为 FastAPI RequestValidationError
            exc = RequestValidationError(errors=ve.errors())
            
            response = await validation_exception_handler(request, exc)
            
            assert response.status_code == 422
            data = response.body.decode()
            assert "VALIDATION_ERROR" in data
            assert "email" in data
            assert "test-123" in data
    
    @pytest.mark.asyncio
    async def test_includes_validation_details(self):
        """测试响应包含验证错误详情"""
        request = create_mock_request()
        
        # 创建验证错误
        from pydantic import BaseModel
        
        class TestModel(BaseModel):
            age: int
        
        try:
            TestModel(age="not-a-number")
        except ValidationError as ve:
            exc = RequestValidationError(errors=ve.errors())
            
            response = await validation_exception_handler(request, exc)
            
            data = response.body.decode()
            assert "validation_errors" in data
            assert "age" in data


class TestSqlalchemyExceptionHandler:
    """测试数据库异常处理器"""
    
    @pytest.mark.asyncio
    async def test_handles_sqlalchemy_error(self):
        """测试处理 SQLAlchemy 错误"""
        request = create_mock_request()
        exc = OperationalError("connection failed", None, None)
        
        with patch('app.core.global_exception_handlers.logger') as mock_logger:
            response = await sqlalchemy_exception_handler(request, exc)
            
            assert response.status_code == 500
            data = response.body.decode()
            assert "DATABASE_ERROR" in data
            assert "database error occurred" in data
            
            # 验证日志记录
            mock_logger.error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hides_sql_details(self):
        """测试隐藏 SQL 语句等敏感信息"""
        request = create_mock_request()
        exc = OperationalError(
            "SELECT * FROM users WHERE password = 'secret123'", 
            None, 
            None
        )
        
        response = await sqlalchemy_exception_handler(request, exc)
        
        data = response.body.decode()
        # 响应中不应包含 SQL 语句
        assert "SELECT" not in data
        assert "password" not in data
        assert "secret123" not in data
        # 应该返回通用错误消息
        assert "database error occurred" in data


class TestGenericExceptionHandler:
    """测试通用异常处理器"""
    
    @pytest.mark.asyncio
    async def test_handles_generic_exception(self):
        """测试处理通用异常"""
        request = create_mock_request()
        exc = ValueError("Something went wrong")
        
        with patch('app.core.global_exception_handlers.logger') as mock_logger:
            response = await generic_exception_handler(request, exc)
            
            assert response.status_code == 500
            data = response.body.decode()
            assert "INTERNAL_SERVER_ERROR" in data
            assert "test-123" in data
            
            # 验证日志记录
            mock_logger.error.assert_called_once()
            call_kwargs = mock_logger.error.call_args.kwargs
            assert call_kwargs['request_id'] == 'test-123'
            assert call_kwargs['url'] == 'http://test.com/api/test'
            assert call_kwargs['method'] == 'GET'
            assert call_kwargs['error_type'] == 'ValueError'
    
    @pytest.mark.asyncio
    async def test_extracts_client_ip(self):
        """测试提取客户端 IP"""
        request = create_mock_request()
        request.client.host = "192.168.1.100"
        exc = ValueError("Test error")
        
        with patch('app.core.global_exception_handlers.logger') as mock_logger:
            await generic_exception_handler(request, exc)
            
            call_kwargs = mock_logger.error.call_args.kwargs
            assert call_kwargs['client_ip'] == '192.168.1.100'
    
    @pytest.mark.asyncio
    async def test_handles_missing_request_id(self):
        """测试处理缺少 request_id 的情况"""
        request = create_mock_request()
        delattr(request.state, 'request_id')
        exc = ValueError("Test error")
        
        # 不应该抛出异常
        response = await generic_exception_handler(request, exc)
        
        assert response.status_code == 500
    
    @pytest.mark.asyncio
    async def test_extracts_user_id_if_authenticated(self):
        """测试提取已认证用户 ID"""
        request = create_mock_request()
        mock_user = Mock()
        mock_user.id = "user-123"
        request.state.user = mock_user
        exc = ValueError("Test error")
        
        with patch('app.core.global_exception_handlers.logger') as mock_logger:
            await generic_exception_handler(request, exc)
            
            call_kwargs = mock_logger.error.call_args.kwargs
            assert call_kwargs['user_id'] == 'user-123'


class TestExceptionHandlersIntegration:
    """测试异常处理器的集成场景"""
    
    @pytest.mark.asyncio
    async def test_all_handlers_include_timestamp(self):
        """测试所有处理器都包含时间戳"""
        request = create_mock_request()
        
        # 测试 HTTP 异常
        exc1 = StarletteHTTPException(status_code=404, detail="Not found")
        response1 = await http_exception_handler(request, exc1)
        assert "timestamp" in response1.body.decode()
        
        # 测试数据库异常
        exc2 = OperationalError("DB error", None, None)
        response2 = await sqlalchemy_exception_handler(request, exc2)
        assert "timestamp" in response2.body.decode()
        
        # 测试通用异常
        exc3 = ValueError("Test error")
        response3 = await generic_exception_handler(request, exc3)
        assert "timestamp" in response3.body.decode()
    
    @pytest.mark.asyncio
    async def test_json_response_format(self):
        """测试所有响应都是有效的 JSON 格式"""
        import json
        request = create_mock_request()
        
        exc = StarletteHTTPException(status_code=404, detail="Not found")
        response = await http_exception_handler(request, exc)
        
        # 验证可以解析为 JSON
        data = json.loads(response.body.decode())
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "timestamp" in data["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

