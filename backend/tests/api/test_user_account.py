"""
用户账户设置 API 测试

覆盖以下功能点：
- GET  /api/v1/users/me — 获取当前用户信息（含 avatar_config 字段）
- PATCH /api/v1/users/me — 更新用户名
- PATCH /api/v1/users/me — 更新 avatar_config（卡通头像 JSON 配置）
- PATCH /api/v1/users/me — 修改密码

数据库迁移验证：
- users 表存在 avatar_config 列（JSON 类型，可 NULL）

技术说明：
- pytestmark loop_scope="module"：整个模块共用一个事件循环，避免 FastAPI 内部
  async_session_maker 连接池在跨事件循环时产生 "Event loop is closed" 错误
- 使用独立的 NullPool 引擎（每次测试创建新连接）避免跨测试的连接状态污染
- 通过真实登录端点 POST /auth/jwt/login 获取有效 JWT，避免手动构造 JWT 密钥不匹配问题
"""
import pytest
import pytest_asyncio
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.models.database import User
from app.core.auth.password import get_password_hash
from app.config.settings import settings

# 整个模块共用同一个事件循环，避免 FastAPI App 内部连接池跨事件循环报错
pytestmark = pytest.mark.asyncio(loop_scope="module")


# 示例 react-nice-avatar 配置（genConfig() 输出格式）
SAMPLE_AVATAR_CONFIG = {
    "sex": "man",
    "faceColor": "#F9C9B6",
    "earSize": "small",
    "hairColor": "#000",
    "hairStyle": "normal",
    "hairColorRandom": False,
    "hatColor": "#000",
    "hatStyle": "none",
    "eyeStyle": "circle",
    "glassesStyle": "none",
    "noseStyle": "short",
    "mouthStyle": "smile",
    "shirtStyle": "hoody",
    "shirtColor": "#9287FF",
    "bgColor": "#6BD9E9",
    "isGradient": False,
    "eyeBrowStyle": "up",
}

TEST_PASSWORD = "TestPassword!2026"


# ─────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def fresh_session():
    """
    使用 NullPool 的独立异步 DB session（模块级别，整个测试模块共用）。

    NullPool 确保每个连接在使用后立即关闭，不缓存到连接池，
    从根本上避免跨测试的连接状态污染。
    loop_scope="module" 保证与 pytestmark 的模块级事件循环一致。
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def http_client():
    """ASGI 测试 HTTP 客户端（模块级别，整个测试模块共用）"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def _register_and_login(
    http_client: AsyncClient,
    session: AsyncSession,
    email: str,
    password: str,
) -> tuple[User, str]:
    """
    在数据库中创建用户并通过登录端点获取真实 JWT Token。

    Returns:
        (用户对象, access_token)
    """
    username = f"user_{uuid.uuid4().hex[:6]}"
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        hashed_password=await get_password_hash(password),
        username=username,
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    resp = await http_client.post(
        "/api/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, f"登录失败 ({resp.status_code}): {resp.text}"
    token = resp.json()["access_token"]
    return user, token


async def _cleanup(session: AsyncSession, user: User):
    """清理测试用户"""
    try:
        # 重新绑定到当前 session
        merged = await session.merge(user)
        await session.delete(merged)
        await session.commit()
    except Exception:
        await session.rollback()


# ─────────────────────────────────────────────────────────
# 1. 数据库迁移验证
# ─────────────────────────────────────────────────────────

class TestDatabaseMigration:
    """验证 avatar_config 数据库迁移是否正确执行（只读 SQL 查询）"""

    async def test_avatar_config_column_exists(self, fresh_session: AsyncSession):
        """
        验证 users 表中存在 avatar_config 列。

        迁移 a1b2c3d4e5f6 必须已执行成功。
        """
        result = await fresh_session.execute(
            text(
                """
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'users'
                  AND column_name = 'avatar_config'
                """
            )
        )
        rows = result.fetchall()

        assert len(rows) == 1, "avatar_config 列不存在，请先执行 alembic upgrade head"
        column_name, data_type, is_nullable = rows[0]
        assert column_name == "avatar_config"
        assert data_type in ("json", "jsonb"), f"期望 json/jsonb 类型，实际: {data_type}"
        assert is_nullable == "YES", "avatar_config 列应允许 NULL"

    async def test_avatar_config_column_has_null_default(self, fresh_session: AsyncSession):
        """
        验证新创建用户的 avatar_config 默认值为 NULL（通过 ORM 插入验证）
        """
        user = User(
            id=str(uuid.uuid4()),
            email=f"migration_test_{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=await get_password_hash("password123"),
            username="migration_tester",
            is_active=True,
            is_verified=True,
            is_superuser=False,
        )
        fresh_session.add(user)
        await fresh_session.flush()
        await fresh_session.refresh(user)

        assert user.avatar_config is None, "新用户的 avatar_config 默认应为 NULL"

        # 清理
        await fresh_session.delete(user)
        await fresh_session.commit()


# ─────────────────────────────────────────────────────────
# 2. GET /api/v1/users/me
# ─────────────────────────────────────────────────────────

class TestGetCurrentUser:
    """测试 GET /api/v1/users/me"""

    async def test_get_me_returns_avatar_config_field(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """
        验证 GET /users/me 响应体包含 avatar_config 字段，新用户值为 null
        """
        email = f"getme_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)

        try:
            response = await http_client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "avatar_config" in data, "响应中缺少 avatar_config 字段"
            assert data["avatar_config"] is None, "新用户的 avatar_config 应为 null"
        finally:
            await _cleanup(fresh_session, user)

    async def test_get_me_unauthenticated(self, http_client: AsyncClient):
        """未认证请求应返回 401"""
        response = await http_client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_get_me_returns_correct_email(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证 GET /users/me 返回正确的 email"""
        email = f"email_check_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)

        try:
            response = await http_client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert response.json()["email"] == email
        finally:
            await _cleanup(fresh_session, user)


# ─────────────────────────────────────────────────────────
# 3. PATCH /api/v1/users/me — 更新用户名
# ─────────────────────────────────────────────────────────

class TestUpdateUsername:
    """测试 PATCH /api/v1/users/me — 更新用户名"""

    async def test_update_username_success(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证成功更新用户名：返回 200，响应体 username 等于新用户名"""
        email = f"username_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)
        new_username = f"new_name_{uuid.uuid4().hex[:6]}"

        try:
            response = await http_client.patch(
                "/api/v1/users/me",
                json={"username": new_username},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert response.json()["username"] == new_username
        finally:
            await _cleanup(fresh_session, user)

    async def test_update_username_reflected_in_get_me(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证更新用户名后，GET /users/me 返回新用户名（持久化验证）"""
        email = f"username_persist_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)
        new_username = f"persisted_{uuid.uuid4().hex[:6]}"

        try:
            await http_client.patch(
                "/api/v1/users/me",
                json={"username": new_username},
                headers={"Authorization": f"Bearer {token}"},
            )
            get_response = await http_client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert get_response.status_code == 200
            assert get_response.json()["username"] == new_username
        finally:
            await _cleanup(fresh_session, user)


# ─────────────────────────────────────────────────────────
# 4. PATCH /api/v1/users/me — 更新 avatar_config
# ─────────────────────────────────────────────────────────

class TestUpdateAvatarConfig:
    """测试 PATCH /api/v1/users/me — 更新 avatar_config"""

    async def test_save_avatar_config_success(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证成功保存卡通头像配置：返回 200，响应体 avatar_config 等于发送的 JSON"""
        email = f"avatar_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)

        try:
            response = await http_client.patch(
                "/api/v1/users/me",
                json={"avatar_config": SAMPLE_AVATAR_CONFIG},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["avatar_config"] is not None
            assert data["avatar_config"]["sex"] == SAMPLE_AVATAR_CONFIG["sex"]
            assert data["avatar_config"]["bgColor"] == SAMPLE_AVATAR_CONFIG["bgColor"]
        finally:
            await _cleanup(fresh_session, user)

    async def test_avatar_config_persisted_via_get_me(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证 avatar_config 保存后，GET /users/me 也能读取到（持久化验证）"""
        email = f"avatar_persist_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)

        try:
            await http_client.patch(
                "/api/v1/users/me",
                json={"avatar_config": SAMPLE_AVATAR_CONFIG},
                headers={"Authorization": f"Bearer {token}"},
            )
            get_response = await http_client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert get_response.status_code == 200
            saved = get_response.json()["avatar_config"]
            assert saved is not None
            assert saved["sex"] == SAMPLE_AVATAR_CONFIG["sex"]
            assert saved["bgColor"] == SAMPLE_AVATAR_CONFIG["bgColor"]
        finally:
            await _cleanup(fresh_session, user)

    async def test_clear_avatar_config_with_null(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证可以将 avatar_config 重置为 null"""
        email = f"avatar_clear_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)

        try:
            # 先设置
            await http_client.patch(
                "/api/v1/users/me",
                json={"avatar_config": SAMPLE_AVATAR_CONFIG},
                headers={"Authorization": f"Bearer {token}"},
            )
            # 再清除
            response = await http_client.patch(
                "/api/v1/users/me",
                json={"avatar_config": None},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            assert response.json()["avatar_config"] is None
        finally:
            await _cleanup(fresh_session, user)

    async def test_update_avatar_config_preserves_username(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证只更新 avatar_config 时，username 保持不变"""
        email = f"avatar_username_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)

        try:
            # 获取初始 username
            get_resp = await http_client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            original_username = get_resp.json()["username"]

            # 只更新 avatar_config
            patch_resp = await http_client.patch(
                "/api/v1/users/me",
                json={"avatar_config": SAMPLE_AVATAR_CONFIG},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["username"] == original_username
        finally:
            await _cleanup(fresh_session, user)


# ─────────────────────────────────────────────────────────
# 5. PATCH /api/v1/users/me — 修改密码
# ─────────────────────────────────────────────────────────

class TestUpdatePassword:
    """测试 PATCH /api/v1/users/me — 修改密码"""

    async def test_update_password_success(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证成功修改密码：返回 200，响应体不含密码明文"""
        email = f"passwd_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)

        try:
            response = await http_client.patch(
                "/api/v1/users/me",
                json={"password": "NewStrongPassword!999"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert "password" not in data
            assert "hashed_password" not in data
        finally:
            await _cleanup(fresh_session, user)

    async def test_new_password_can_login(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证修改密码后，可以用新密码重新登录并获取有效 Token"""
        email = f"passwd_login_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)
        new_password = "NewLoginPassword!2026"

        try:
            # 修改密码
            await http_client.patch(
                "/api/v1/users/me",
                json={"password": new_password},
                headers={"Authorization": f"Bearer {token}"},
            )
            # 用新密码登录
            login_response = await http_client.post(
                "/api/v1/auth/jwt/login",
                data={"username": email, "password": new_password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            assert login_response.status_code == 200
            assert "access_token" in login_response.json()
        finally:
            await _cleanup(fresh_session, user)

    async def test_old_password_fails_after_change(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证修改密码后，旧密码无法登录"""
        email = f"passwd_old_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)
        new_password = "NewPassword!Different2026"

        try:
            # 修改密码
            await http_client.patch(
                "/api/v1/users/me",
                json={"password": new_password},
                headers={"Authorization": f"Bearer {token}"},
            )
            # 旧密码登录
            old_login_response = await http_client.post(
                "/api/v1/auth/jwt/login",
                data={"username": email, "password": TEST_PASSWORD},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            assert old_login_response.status_code == 400, "旧密码应无法登录"
        finally:
            await _cleanup(fresh_session, user)

    async def test_update_password_unauthenticated(self, http_client: AsyncClient):
        """未认证时修改密码应返回 401"""
        response = await http_client.patch(
            "/api/v1/users/me",
            json={"password": "SomePassword123"},
        )
        assert response.status_code == 401


# ─────────────────────────────────────────────────────────
# 6. 组合更新测试
# ─────────────────────────────────────────────────────────

class TestCombinedUpdate:
    """测试同时更新多个字段"""

    async def test_update_username_and_avatar_together(
        self,
        fresh_session: AsyncSession,
        http_client: AsyncClient,
    ):
        """验证可以在同一个 PATCH 请求中同时更新 username 和 avatar_config"""
        email = f"combo_{uuid.uuid4().hex[:8]}@test.com"
        user, token = await _register_and_login(http_client, fresh_session, email, TEST_PASSWORD)
        new_username = f"combo_{uuid.uuid4().hex[:6]}"

        try:
            response = await http_client.patch(
                "/api/v1/users/me",
                json={
                    "username": new_username,
                    "avatar_config": SAMPLE_AVATAR_CONFIG,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == new_username
            assert data["avatar_config"] is not None
            assert data["avatar_config"]["sex"] == SAMPLE_AVATAR_CONFIG["sex"]
        finally:
            await _cleanup(fresh_session, user)
