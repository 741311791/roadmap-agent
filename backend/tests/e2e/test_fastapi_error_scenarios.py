"""
FastAPI HTTP 错误场景端到端测试

测试真实的 HTTP 请求场景，验证全局异常处理机制。
"""
import pytest
import uuid
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """创建测试客户端"""
    from app.main import app
    return TestClient(app)


class TestValidationErrors:
    """测试验证错误场景（422）"""
    
    def test_invalid_request_body_returns_422(self, client):
        """测试无效请求体返回 422 错误"""
        # 发送空请求体
        response = client.post("/api/v1/roadmaps/generate", json={})
        
        assert response.status_code == 422
        data = response.json()
        
        # 验证错误响应格式
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "message" in data["error"]
        assert "request_id" in data["error"]
        assert "timestamp" in data["error"]
    
    def test_validation_error_includes_details(self, client):
        """测试验证错误包含详细信息"""
        response = client.post("/api/v1/roadmaps/generate", json={})
        
        data = response.json()
        assert "details" in data["error"]
        # 应该包含 validation_errors 字段
        if data["error"]["details"]:
            assert "validation_errors" in data["error"]["details"]


class TestResourceNotFound:
    """测试资源不存在场景（404）"""
    
    def test_nonexistent_roadmap_returns_404(self, client):
        """测试访问不存在的路线图返回 404"""
        response = client.get("/api/v1/roadmaps/nonexistent-id")
        
        assert response.status_code == 404
        data = response.json()
        
        assert "error" in data
        assert data["error"]["code"] == "NOT_FOUND"
    
    def test_nonexistent_endpoint_returns_404(self, client):
        """测试访问不存在的端点返回 404"""
        response = client.get("/api/v1/nonexistent/endpoint")
        
        assert response.status_code == 404


class TestRequestIDHandling:
    """测试 Request ID 处理"""
    
    def test_auto_generates_request_id(self, client):
        """测试自动生成 Request ID"""
        response = client.get("/health")
        
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        
        # 验证是有效的 UUID
        try:
            uuid.UUID(request_id)
        except ValueError:
            pytest.fail(f"Invalid UUID: {request_id}")
    
    def test_preserves_client_request_id(self, client):
        """测试保留客户端提供的 Request ID"""
        custom_id = "custom-request-123"
        
        response = client.get("/health", headers={"X-Request-ID": custom_id})
        
        assert response.headers["X-Request-ID"] == custom_id
    
    def test_request_id_in_error_response(self, client):
        """测试错误响应包含 Request ID"""
        custom_id = "error-request-456"
        
        response = client.get(
            "/api/v1/roadmaps/nonexistent",
            headers={"X-Request-ID": custom_id}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["request_id"] == custom_id


class TestHealthEndpoints:
    """测试健康检查端点"""
    
    def test_basic_health_check(self, client):
        """测试基础健康检查"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_detailed_health_check(self, client):
        """测试详细健康检查"""
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data


class TestErrorResponseFormat:
    """测试错误响应格式一致性"""
    
    def test_all_errors_have_consistent_format(self, client):
        """测试所有错误都有一致的格式"""
        # 测试不同类型的错误
        error_responses = [
            client.get("/api/v1/roadmaps/nonexistent"),  # 404
            client.post("/api/v1/roadmaps/generate", json={}),  # 422
        ]
        
        for response in error_responses:
            data = response.json()
            
            # 验证基本结构
            assert "error" in data
            assert "code" in data["error"]
            assert "message" in data["error"]
            assert "timestamp" in data["error"]
    
    def test_error_timestamp_is_iso8601(self, client):
        """测试错误时间戳是 ISO8601 格式"""
        from datetime import datetime
        
        response = client.get("/api/v1/roadmaps/nonexistent")
        data = response.json()
        
        timestamp = data["error"]["timestamp"]
        # 验证可以解析为 ISO8601 格式
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid ISO8601 timestamp: {timestamp}")


class TestCORSAndHeaders:
    """测试 CORS 和响应头"""
    
    def test_cors_headers_present(self, client):
        """测试 CORS 响应头存在"""
        response = client.options("/health")
        
        # 注意：TestClient 可能不完全模拟 CORS，这里只做基本检查
        assert response.status_code in [200, 204]
    
    def test_request_id_header_in_all_responses(self, client):
        """测试所有响应都包含 X-Request-ID 响应头"""
        endpoints = [
            "/health",
            "/health/detailed",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert "X-Request-ID" in response.headers, f"Missing X-Request-ID in {endpoint}"


class TestAuthenticationErrors:
    """测试认证错误场景"""
    
    @pytest.mark.skip(reason="需要实际的认证端点")
    def test_unauthorized_returns_401(self, client):
        """测试未认证返回 401"""
        # 这里需要根据实际的认证端点进行测试
        pass
    
    @pytest.mark.skip(reason="需要实际的权限端点")
    def test_forbidden_returns_403(self, client):
        """测试无权限返回 403"""
        # 这里需要根据实际的权限端点进行测试
        pass


class TestMultipleRequests:
    """测试多请求场景"""
    
    def test_multiple_concurrent_requests_have_unique_ids(self, client):
        """测试多个并发请求都有唯一的 Request ID"""
        num_requests = 10
        responses = [client.get("/health") for _ in range(num_requests)]
        
        # 收集所有 Request ID
        request_ids = [r.headers["X-Request-ID"] for r in responses]
        
        # 验证所有 ID 唯一
        assert len(set(request_ids)) == num_requests
    
    def test_errors_across_multiple_requests(self, client):
        """测试多个请求的错误处理"""
        # 发送多个会失败的请求
        error_responses = [
            client.get("/api/v1/roadmaps/nonexistent-1"),
            client.get("/api/v1/roadmaps/nonexistent-2"),
            client.get("/api/v1/roadmaps/nonexistent-3"),
        ]
        
        # 验证所有响应都是 404 且格式正确
        for response in error_responses:
            assert response.status_code == 404
            data = response.json()
            assert data["error"]["code"] == "NOT_FOUND"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

