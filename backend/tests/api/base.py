"""
API测试基类

提供统一的测试fixture和辅助方法。
"""
import pytest
import uuid
from typing import Dict
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.main import app
from app.models.database import User
from app.core.auth.password import get_password_hash
from jose import jwt
import time


class APITestBase:
    """
    API测试基类
    
    提供通用的测试fixture：
    - client: HTTP测试客户端
    - test_user: 普通测试用户
    - test_superuser: 超级管理员用户
    - auth_headers: 认证请求头
    - superuser_headers: 超级管理员请求头
    """
    
    @pytest.fixture
    async def client(self) -> AsyncClient:
        """
        创建HTTP测试客户端
        
        使用ASGITransport与FastAPI应用通信。
        """
        async with AsyncClient(
            transport=ASGITransport(app=app), 
            base_url="http://test"
        ) as ac:
            yield ac
    
    @pytest.fixture
    async def test_user(self, test_session: AsyncSession) -> User:
        """
        创建普通测试用户
        
        Args:
            test_session: 测试数据库会话
            
        Returns:
            创建的测试用户对象
        """
        user = User(
            id=str(uuid.uuid4()),  # 转换为字符串
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
    async def test_superuser(self, test_session: AsyncSession) -> User:
        """
        创建超级管理员测试用户
        
        Args:
            test_session: 测试数据库会话
            
        Returns:
            创建的超级管理员用户对象
        """
        user = User(
            id=str(uuid.uuid4()),  # 转换为字符串
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
    
    @pytest.fixture
    def auth_headers(self, test_user: User) -> Dict[str, str]:
        """
        生成普通用户的认证请求头
        
        Args:
            test_user: 测试用户对象
            
        Returns:
            包含Bearer Token的请求头字典
        """
        token = self._create_access_token(test_user.id)
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    def superuser_headers(self, test_superuser: User) -> Dict[str, str]:
        """
        生成超级管理员的认证请求头
        
        Args:
            test_superuser: 超级管理员用户对象
            
        Returns:
            包含Bearer Token的请求头字典
        """
        token = self._create_access_token(test_superuser.id)
        return {"Authorization": f"Bearer {token}"}
    
    @staticmethod
    def _create_access_token(user_id: str, expires_delta: timedelta = None) -> str:
        """
        创建JWT访问令牌（测试专用）
        
        Args:
            user_id: 用户ID
            expires_delta: 过期时间增量（默认1小时）
            
        Returns:
            JWT令牌字符串
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=1)
        
        expire_timestamp = int(time.time()) + int(expires_delta.total_seconds())
        
        to_encode = {
            "sub": str(user_id),
            "exp": expire_timestamp,
            "jti": str(uuid.uuid4()),  # 添加JWT ID
        }
        
        # 使用测试环境的密钥
        test_secret = "test_secret_key_12345"
        
        encoded_jwt = jwt.encode(
            to_encode,
            test_secret,
            algorithm="HS256",
        )
        
        return encoded_jwt
    
    @staticmethod
    def assert_success_response(response_data: Dict, expected_keys: list = None):
        """
        验证成功响应格式
        
        Args:
            response_data: 响应数据字典
            expected_keys: 期望的data字段中的键列表
        """
        assert "code" in response_data
        assert "msg" in response_data  # 统一响应格式使用msg字段
        assert "data" in response_data
        assert response_data["code"] == 200
        
        if expected_keys:
            data = response_data["data"]
            for key in expected_keys:
                assert key in data, f"Expected key '{key}' not found in response data"
    
    @staticmethod
    def assert_error_response(response_data: Dict, expected_code: int = None):
        """
        验证错误响应格式
        
        Args:
            response_data: 响应数据字典
            expected_code: 期望的错误码
        """
        assert "code" in response_data
        assert "msg" in response_data  # 统一响应格式使用msg字段
        
        if expected_code:
            assert response_data["code"] == expected_code

