"""
集成测试 - 认证授权

测试目标：
- JWT认证流程
- Token验证
- 权限控制
- 黑名单机制
"""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch, AsyncMock
import uuid

from app.main import app
from app.db.session import get_session
from app.models.database import User
from app.core.auth import get_user_manager
from app.core.auth.password import get_password_hash


@pytest.fixture
async def client():
    """创建测试客户端"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_user(test_session: AsyncSession):
    """
    创建测试用户
    
    Returns:
        创建的测试用户对象
    """
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
    """
    创建测试超级管理员
    
    Returns:
        创建的超级管理员对象
    """
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


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_login_success(client: AsyncClient, test_user: User):
    """
    测试用户登录成功
    
    验证：
    - 正确的邮箱和密码可以登录
    - 返回有效的JWT token
    - Token包含正确的用户信息
    """
    response = await client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": test_user.email,  # FastAPI Users使用username字段
            "password": "testpassword123",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证返回的token
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_login_wrong_password(client: AsyncClient, test_user: User):
    """
    测试用户登录失败（错误密码）
    
    验证：
    - 错误的密码无法登录
    - 返回400状态码
    """
    response = await client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": test_user.email,
            "password": "wrongpassword",
        },
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_login_nonexistent_user(client: AsyncClient):
    """
    测试用户登录失败（用户不存在）
    
    验证：
    - 不存在的用户无法登录
    - 返回400状态码
    """
    response = await client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": "nonexistent@example.com",
            "password": "anypassword",
        },
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
@pytest.mark.integration
async def test_authenticated_request(client: AsyncClient, test_user: User):
    """
    测试认证请求
    
    验证：
    - 带有效token可以访问需要认证的端点
    - 返回正确的用户信息
    """
    # 1. 先登录获取token
    login_response = await client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": test_user.email,
            "password": "testpassword123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 2. 使用token访问需要认证的端点
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["is_superuser"] == test_user.is_superuser


@pytest.mark.asyncio
@pytest.mark.integration
async def test_unauthenticated_request(client: AsyncClient):
    """
    测试未认证请求
    
    验证：
    - 不带token无法访问需要认证的端点
    - 返回401状态码
    """
    response = await client.get("/api/v1/users/me")
    
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
async def test_invalid_token_request(client: AsyncClient):
    """
    测试无效token请求
    
    验证：
    - 无效token无法访问需要认证的端点
    - 返回401状态码
    """
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid_token_here"},
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
async def test_logout(client: AsyncClient, test_user: User):
    """
    测试用户登出
    
    验证：
    - 登出后token被加入黑名单
    - 黑名单中的token无法继续使用
    """
    # 1. 先登录获取token
    login_response = await client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": test_user.email,
            "password": "testpassword123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # 2. 验证token有效
    verify_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_response.status_code == 200
    
    # 3. 登出
    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200
    
    # 4. 验证token已失效
    verify_after_logout = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verify_after_logout.status_code == 401


@pytest.mark.asyncio
@pytest.mark.integration
async def test_superuser_access(client: AsyncClient, test_superuser: User):
    """
    测试超级管理员权限
    
    验证：
    - 超级管理员可以访问管理员端点
    - 返回正确的响应
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
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["is_superuser"] is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_normal_user_cannot_access_admin_endpoints(
    client: AsyncClient, test_user: User
):
    """
    测试普通用户无法访问管理员端点
    
    验证：
    - 普通用户无法访问需要超级管理员权限的端点
    - 返回403状态码
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
    
    # 2. 尝试访问管理员端点（例如：用户邀请）
    # Mock邮件服务避免实际发送邮件
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

