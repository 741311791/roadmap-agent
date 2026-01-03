"""
Tavily 配额刷新 API 端点测试

测试手动刷新配额功能的基本流程
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.database import User, TavilyAPIKey


@pytest.mark.asyncio
async def test_refresh_tavily_quota_success(
    async_client: AsyncClient,
    superuser_token_headers: dict,
    db_session,
):
    """
    测试成功刷新配额
    
    验证：
    1. 只有超级管理员可以访问
    2. 成功调用 Tavily API 并更新数据库
    3. 返回正确的统计信息
    """
    # 创建测试用的 API Key
    test_key = TavilyAPIKey(
        api_key="tvly-test-key-123456789",
        plan_limit=1000,
        remaining_quota=500,
    )
    db_session.add(test_key)
    await db_session.commit()
    
    # Mock Tavily API 响应
    mock_usage_response = {
        "account": {
            "plan_usage": 300,
            "plan_limit": 1000,
        }
    }
    
    with patch("app.api.v1.endpoints.admin.httpx.AsyncClient") as mock_client_class:
        # 配置 mock
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = mock_usage_response
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client
        
        # 调用刷新端点
        response = await async_client.post(
            "/api/v1/admin/tavily-keys/refresh-quota",
            headers=superuser_token_headers,
        )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == 1
    assert data["failed"] == 0
    assert data["total_keys"] == 1
    assert "elapsed_seconds" in data
    
    # 验证数据库已更新
    await db_session.refresh(test_key)
    assert test_key.remaining_quota == 700  # 1000 - 300


@pytest.mark.asyncio
async def test_refresh_tavily_quota_unauthorized(
    async_client: AsyncClient,
):
    """
    测试未授权访问
    
    验证：非超级管理员无法访问此端点
    """
    response = await async_client.post(
        "/api/v1/admin/tavily-keys/refresh-quota",
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_tavily_quota_no_keys(
    async_client: AsyncClient,
    superuser_token_headers: dict,
):
    """
    测试无 API Keys 的情况
    
    验证：当数据库中没有 Key 时，返回空结果
    """
    response = await async_client.post(
        "/api/v1/admin/tavily-keys/refresh-quota",
        headers=superuser_token_headers,
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == 0
    assert data["failed"] == 0
    assert data["total_keys"] == 0
    assert data["elapsed_seconds"] == 0.0


@pytest.mark.asyncio
async def test_refresh_tavily_quota_partial_failure(
    async_client: AsyncClient,
    superuser_token_headers: dict,
    db_session,
):
    """
    测试部分失败的情况
    
    验证：单个 Key 更新失败不影响其他 Key
    """
    # 创建两个测试 Key
    key1 = TavilyAPIKey(
        api_key="tvly-test-key-1",
        plan_limit=1000,
        remaining_quota=500,
    )
    key2 = TavilyAPIKey(
        api_key="tvly-test-key-2",
        plan_limit=2000,
        remaining_quota=1000,
    )
    db_session.add_all([key1, key2])
    await db_session.commit()
    
    # Mock Tavily API：第一个成功，第二个失败
    call_count = 0
    
    async def mock_get(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        
        mock_response = MagicMock()
        if call_count == 1:
            # 第一个 Key 成功
            mock_response.json.return_value = {
                "account": {
                    "plan_usage": 300,
                    "plan_limit": 1000,
                }
            }
            mock_response.raise_for_status = MagicMock()
        else:
            # 第二个 Key 失败
            from httpx import HTTPStatusError
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            
            def raise_error():
                raise HTTPStatusError(
                    "Unauthorized",
                    request=MagicMock(),
                    response=mock_response
                )
            mock_response.raise_for_status = raise_error
        
        return mock_response
    
    with patch("app.api.v1.endpoints.admin.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get = mock_get
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client_class.return_value = mock_client
        
        response = await async_client.post(
            "/api/v1/admin/tavily-keys/refresh-quota",
            headers=superuser_token_headers,
        )
    
    # 验证响应
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == 1
    assert data["failed"] == 1
    assert data["total_keys"] == 2

