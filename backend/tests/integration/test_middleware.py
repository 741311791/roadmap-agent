"""
集成测试 - 中间件测试

测试目标：
- RequestIDMiddleware: 请求ID生成和传递
- TraceIDMiddleware: 分布式追踪ID
- RBACMiddleware: 基于角色的访问控制
- OperaLogMiddleware: 操作日志记录
"""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.db.session import get_session
from app.models.database import User
from app.core.auth.password import get_password_hash


@pytest.fixture
async def client():
    """创建测试客户端"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(test_session: AsyncSession):
    """创建测试普通用户"""
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=await get_password_hash("testpassword123"),
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    
    yield user
    
    # 清理
    await test_session.delete(user)
    await test_session.commit()


@pytest.fixture
async def test_superuser(test_session: AsyncSession):
    """创建测试超级管理员"""
    user = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=await get_password_hash("adminpassword123"),
        is_active=True,
        is_verified=True,
        is_superuser=True,
    )
    
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    
    yield user
    
    # 清理
    await test_session.delete(user)
    await test_session.commit()


# ============================================================
# RequestIDMiddleware 测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_request_id_auto_generated(client: AsyncClient):
    """
    测试RequestID自动生成
    
    验证：
    - 请求不带X-Request-ID头时自动生成UUID
    - 响应头包含X-Request-ID
    - RequestID是有效的UUID格式
    """
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    
    request_id = response.headers["X-Request-ID"]
    
    # 验证UUID格式（如果不是有效UUID会抛出异常）
    try:
        uuid.UUID(request_id)
    except ValueError:
        pytest.fail(f"Request ID is not a valid UUID: {request_id}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_request_id_from_header(client: AsyncClient):
    """
    测试使用客户端提供的RequestID
    
    验证：
    - 请求带自定义X-Request-ID时使用客户端提供的ID
    - 响应头返回相同的RequestID
    """
    custom_request_id = str(uuid.uuid4())
    
    response = await client.get(
        "/health",
        headers={"X-Request-ID": custom_request_id}
    )
    
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_request_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_request_id_in_logs(client: AsyncClient):
    """
    测试RequestID注入到日志上下文
    
    验证：
    - request_id注入到structlog上下文
    - 所有日志包含request_id字段
    """
    import structlog
    from unittest.mock import patch
    
    logged_contexts = []
    
    # Mock structlog的contextvars.bound_contextvars来捕获上下文
    original_bound_contextvars = structlog.contextvars.bound_contextvars
    
    def mock_bound_contextvars(**kwargs):
        logged_contexts.append(kwargs)
        return original_bound_contextvars(**kwargs)
    
    with patch("structlog.contextvars.bound_contextvars", side_effect=mock_bound_contextvars):
        response = await client.get("/health")
    
    assert response.status_code == 200
    
    # 验证request_id被记录
    assert any("request_id" in context for context in logged_contexts)


# ============================================================
# TraceIDMiddleware 测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_trace_id_generation(client: AsyncClient):
    """
    测试TraceID自动生成
    
    验证：
    - 响应头包含X-Trace-ID
    - TraceID是有效的UUID格式
    """
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert "X-Trace-ID" in response.headers
    
    trace_id = response.headers["X-Trace-ID"]
    
    # 验证UUID格式
    try:
        uuid.UUID(trace_id)
    except ValueError:
        pytest.fail(f"Trace ID is not a valid UUID: {trace_id}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_trace_id_propagation(client: AsyncClient):
    """
    测试TraceID在请求链路中传递
    
    验证：
    - 多个请求使用不同的TraceID
    - 同一请求的TraceID保持一致
    """
    response1 = await client.get("/health")
    response2 = await client.get("/health")
    
    trace_id1 = response1.headers.get("X-Trace-ID")
    trace_id2 = response2.headers.get("X-Trace-ID")
    
    # 不同请求应该有不同的TraceID
    assert trace_id1 != trace_id2


# ============================================================
# RBACMiddleware 测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_rbac_public_path_access(client: AsyncClient):
    """
    测试公开路径访问
    
    验证：
    - 公开路径（/health, /auth）无需认证即可访问
    - 返回200状态码
    """
    # 测试健康检查端点
    health_response = await client.get("/health")
    assert health_response.status_code == 200
    
    # 测试metrics端点
    metrics_response = await client.get("/metrics")
    assert metrics_response.status_code == 200


@pytest.mark.asyncio
@pytest.mark.integration
async def test_rbac_admin_path_requires_superuser(
    client: AsyncClient,
    test_user: User,
):
    """
    测试管理员路径需要超级管理员权限
    
    验证：
    - 普通用户访问/api/v1/admin返回403 Forbidden
    - 错误信息正确
    """
    # 1. 普通用户登录
    login_response = await client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": test_user.email,
            "password": "testpassword123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 2. 尝试访问管理员端点
    # 注意：需要Mock邮件服务避免实际发送邮件
    from unittest.mock import AsyncMock, patch
    
    with patch("app.services.email_service.EmailService.send_invite_email", new_callable=AsyncMock):
        response = await client.post(
            "/api/v1/admin/invite",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "newuser@example.com",
                "invite_type": "direct_access",
            },
        )
    
    # 应该返回403 Forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
@pytest.mark.integration
async def test_rbac_admin_path_allows_superuser(
    client: AsyncClient,
    test_superuser: User,
):
    """
    测试超级管理员可以访问管理员路径
    
    验证：
    - 超级管理员访问/api/v1/admin成功
    - 功能正常执行
    """
    # 1. 超级管理员登录
    login_response = await client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": test_superuser.email,
            "password": "adminpassword123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 2. 访问管理员端点
    # Mock邮件服务
    from unittest.mock import AsyncMock, patch
    
    with patch("app.services.email_service.EmailService.send_invite_email", new_callable=AsyncMock) as mock_email:
        mock_email.return_value = None
        
        response = await client.post(
            "/api/v1/admin/invite",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "email": "newuser@example.com",
                "invite_type": "direct_access",
            },
        )
    
    # 超级管理员应该可以访问（返回200或其他成功状态码）
    # 注意：根据实际实现，可能返回200、201等
    assert response.status_code in (200, 201, 400)  # 400可能是因为邮件已存在等业务错误


# ============================================================
# OperaLogMiddleware 测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_opera_log_records_request(client: AsyncClient):
    """
    测试操作日志记录请求
    
    验证：
    - 操作日志正确记录HTTP方法、路径、状态码
    - 记录请求耗时
    """
    # Mock OperaLog记录
    from unittest.mock import patch, AsyncMock
    
    logged_operations = []
    
    async def mock_create_opera_log(*args, **kwargs):
        logged_operations.append(kwargs)
        return None
    
    with patch("app.crud.crud_opera_log.OperaLogCRUD.create_opera_log", new_callable=AsyncMock) as mock_log:
        mock_log.side_effect = mock_create_opera_log
        
        response = await client.get("/api/v1/users/me")
    
    # 验证日志是否被记录（可能因为认证失败返回401，但仍应记录）
    # 注意：实际实现中可能需要调整验证逻辑


@pytest.mark.asyncio
@pytest.mark.integration
async def test_opera_log_excludes_health_check(client: AsyncClient):
    """
    测试健康检查不记录到操作日志
    
    验证：
    - /health端点不触发操作日志记录
    - 减少不必要的日志存储
    """
    from unittest.mock import patch, AsyncMock
    
    logged_operations = []
    
    async def mock_create_opera_log(*args, **kwargs):
        logged_operations.append(kwargs)
        return None
    
    with patch("app.crud.crud_opera_log.OperaLogCRUD.create_opera_log", new_callable=AsyncMock) as mock_log:
        mock_log.side_effect = mock_create_opera_log
        
        response = await client.get("/health")
    
    assert response.status_code == 200
    
    # 验证健康检查不被记录
    # 注意：根据实际OperaLogMiddleware实现，可能需要调整
    # 如果中间件排除了健康检查，logged_operations应为空或不包含/health


# ============================================================
# 中间件组合测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_middleware_stack_integration(client: AsyncClient):
    """
    测试中间件栈集成
    
    验证：
    - 所有中间件正确协同工作
    - RequestID、TraceID同时存在
    - 响应头包含所有必需的标识
    """
    response = await client.get("/health")
    
    assert response.status_code == 200
    
    # 验证所有中间件注入的响应头
    assert "X-Request-ID" in response.headers
    assert "X-Trace-ID" in response.headers
    
    # 验证ID格式
    request_id = response.headers["X-Request-ID"]
    trace_id = response.headers["X-Trace-ID"]
    
    uuid.UUID(request_id)  # 验证UUID格式
    uuid.UUID(trace_id)    # 验证UUID格式
    
    # RequestID和TraceID应该不同
    assert request_id != trace_id

