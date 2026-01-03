"""
Request ID 中间件集成测试

测试 app.middleware.request_id 模块中的 Request ID 中间件。
"""
import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.middleware.request_id import RequestIDMiddleware


@pytest.fixture
def app():
    """创建测试 FastAPI 应用"""
    app = FastAPI()
    
    # 添加 Request ID 中间件
    app.add_middleware(RequestIDMiddleware)
    
    # 添加测试路由
    @app.get("/test")
    async def test_endpoint():
        return {"message": "test"}
    
    @app.get("/test/request-id")
    async def get_request_id(request: "Request"):
        from fastapi import Request as FastAPIRequest
        return {"request_id": getattr(request.state, "request_id", None)}
    
    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


class TestRequestIDGeneration:
    """测试 Request ID 自动生成"""
    
    def test_generates_uuid(self, client):
        """测试自动生成 UUID"""
        response = client.get("/test")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        
        request_id = response.headers["X-Request-ID"]
        # 验证是有效的 UUID
        try:
            uuid.UUID(request_id)
        except ValueError:
            pytest.fail(f"Invalid UUID: {request_id}")
    
    def test_different_requests_get_different_ids(self, client):
        """测试不同请求获得不同的 Request ID"""
        response1 = client.get("/test")
        response2 = client.get("/test")
        
        id1 = response1.headers["X-Request-ID"]
        id2 = response2.headers["X-Request-ID"]
        
        assert id1 != id2


class TestRequestIDFromHeader:
    """测试从请求头读取 Request ID"""
    
    def test_uses_client_provided_id(self, client):
        """测试使用客户端提供的 Request ID"""
        custom_id = "custom-request-id-123"
        
        response = client.get("/test", headers={"X-Request-ID": custom_id})
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == custom_id
    
    def test_preserves_uuid_format(self, client):
        """测试保留 UUID 格式的 Request ID"""
        custom_uuid = str(uuid.uuid4())
        
        response = client.get("/test", headers={"X-Request-ID": custom_uuid})
        
        assert response.headers["X-Request-ID"] == custom_uuid


class TestRequestIDInResponseHeader:
    """测试响应头包含 Request ID"""
    
    def test_response_includes_request_id(self, client):
        """测试响应头包含 X-Request-ID"""
        response = client.get("/test")
        
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0
    
    def test_response_returns_same_id_as_request(self, client):
        """测试响应返回与请求相同的 Request ID"""
        custom_id = "my-request-id"
        
        response = client.get("/test", headers={"X-Request-ID": custom_id})
        
        assert response.headers["X-Request-ID"] == custom_id


class TestRequestIDInRequestState:
    """测试 Request ID 注入到 request.state"""
    
    def test_injects_to_request_state(self, client):
        """测试 Request ID 被注入到 request.state"""
        response = client.get("/test/request-id")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "request_id" in data
        assert data["request_id"] is not None
        
        # 验证是有效的 UUID
        try:
            uuid.UUID(data["request_id"])
        except ValueError:
            pytest.fail(f"Invalid UUID in request.state: {data['request_id']}")
    
    def test_request_state_matches_response_header(self, client):
        """测试 request.state 中的 ID 与响应头匹配"""
        response = client.get("/test/request-id")
        
        data = response.json()
        state_id = data["request_id"]
        header_id = response.headers["X-Request-ID"]
        
        assert state_id == header_id


class TestRequestIDWithStructlog:
    """测试 Request ID 与 structlog 集成"""
    
    @pytest.mark.asyncio
    async def test_adds_to_structlog_context(self):
        """测试 Request ID 被添加到 structlog 上下文"""
        import structlog
        from starlette.requests import Request
        from starlette.responses import Response
        
        middleware = RequestIDMiddleware(app=Mock())
        
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.state = Mock()
        
        # Mock call_next
        async def mock_call_next(request):
            # 验证 structlog 上下文包含 request_id
            from structlog.contextvars import get_contextvars
            context = get_contextvars()
            assert "request_id" in context
            return Response(content=b"test")
        
        with patch('structlog.contextvars.bound_contextvars') as mock_bind:
            await middleware.dispatch(mock_request, mock_call_next)
            
            # 验证 bound_contextvars 被调用
            mock_bind.assert_called_once()
            call_kwargs = mock_bind.call_args.kwargs
            assert "request_id" in call_kwargs


class TestRequestIDMiddlewareEdgeCases:
    """测试 Request ID 中间件边界情况"""
    
    def test_handles_empty_header(self, client):
        """测试处理空的 X-Request-ID 请求头"""
        response = client.get("/test", headers={"X-Request-ID": ""})
        
        # 应该生成新的 ID
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) > 0
    
    def test_handles_malformed_uuid(self, client):
        """测试处理格式错误的 UUID"""
        # 即使是格式错误的 ID，也应该被接受（不验证格式）
        malformed_id = "not-a-valid-uuid"
        
        response = client.get("/test", headers={"X-Request-ID": malformed_id})
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == malformed_id
    
    def test_handles_very_long_id(self, client):
        """测试处理非常长的 Request ID"""
        long_id = "x" * 1000
        
        response = client.get("/test", headers={"X-Request-ID": long_id})
        
        assert response.status_code == 200
        assert response.headers["X-Request-ID"] == long_id


class TestRequestIDMiddlewareIntegration:
    """测试 Request ID 中间件集成场景"""
    
    def test_works_with_multiple_requests(self, client):
        """测试处理多个并发请求"""
        num_requests = 10
        responses = [client.get("/test") for _ in range(num_requests)]
        
        # 所有请求都应该有 Request ID
        for response in responses:
            assert "X-Request-ID" in response.headers
        
        # 所有 ID 应该唯一
        ids = [r.headers["X-Request-ID"] for r in responses]
        assert len(set(ids)) == num_requests
    
    def test_preserves_id_through_error_responses(self, client):
        """测试错误响应也保留 Request ID"""
        custom_id = "error-request-id"
        
        # 访问不存在的路由触发 404
        response = client.get("/nonexistent", headers={"X-Request-ID": custom_id})
        
        assert response.status_code == 404
        assert response.headers["X-Request-ID"] == custom_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

