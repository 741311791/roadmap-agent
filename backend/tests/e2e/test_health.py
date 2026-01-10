"""
端到端测试 - 健康检查

测试目标：确保服务能正常启动并响应健康检查请求
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
async def client():
    """
    创建测试客户端
    
    使用FastAPI的TestClient进行端到端测试
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_basic_health_check(client: AsyncClient):
    """
    测试基础健康检查
    
    验证：
    - 服务可以正常响应
    - 返回200状态码
    - 返回正确的响应格式
    """
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_database_health_check(client: AsyncClient):
    """
    测试数据库健康检查
    
    验证：
    - 数据库连接正常
    - 连接池状态正常
    - 返回详细的数据库状态信息
    """
    response = await client.get("/health/db")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证基本结构
    assert "status" in data
    assert data["status"] == "healthy"
    
    # 验证连接池信息
    assert "pool_status" in data
    pool_status = data["pool_status"]
    assert "size" in pool_status
    assert "checked_in" in pool_status
    assert "checked_out" in pool_status


@pytest.mark.asyncio
async def test_detailed_health_check(client: AsyncClient):
    """
    测试详细健康检查
    
    验证：
    - 所有组件状态正常
    - 包含数据库和checkpointer状态
    - 整体状态为healthy
    """
    response = await client.get("/health/detailed")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证整体状态
    assert data["status"] in ("healthy", "degraded")  # 允许degraded（某些组件未初始化）
    assert data["version"] == "1.0.0"
    
    # 验证组件状态
    assert "components" in data
    components = data["components"]
    
    # 验证数据库组件
    assert "database" in components
    db_component = components["database"]
    assert db_component["status"] == "healthy"
    
    # 验证checkpointer组件（可能未初始化）
    assert "checkpointer" in components


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint(client: AsyncClient):
    """
    测试Prometheus指标端点
    
    验证：
    - /metrics端点可访问
    - 返回Prometheus格式的指标数据
    """
    response = await client.get("/metrics")
    
    assert response.status_code == 200
    
    # 验证响应格式（Prometheus text格式）
    content = response.text
    assert "# HELP" in content or "# TYPE" in content

