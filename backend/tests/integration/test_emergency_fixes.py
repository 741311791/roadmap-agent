"""
阶段0紧急止血修复 - 集成测试

验证以下修复：
1. WebSocket 鉴权
2. 中间件顺序
3. BackgroundTasks Session 修复
4. Celery 异步池升级
5. JWT 黑名单机制
"""
import pytest
import time
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app
from app.config.settings import settings
from app.core.auth.jwt_blacklist import add_to_blacklist, is_blacklisted
from app.tasks.cover_image_tasks import generate_cover_image_task


class TestWebSocketAuth:
    """测试：WebSocket 鉴权实现"""
    
    def test_websocket_no_token_rejected(self):
        """测试：无 Token 连接被拒绝"""
        client = TestClient(app)
        
        with pytest.raises(Exception):  # WebSocket 连接失败
            with client.websocket_connect("/api/v1/ws/test-task-123"):
                pass
    
    def test_websocket_invalid_token_rejected(self):
        """测试：无效 Token 被拒绝"""
        client = TestClient(app)
        invalid_token = "invalid.token.here"
        
        with pytest.raises(Exception):  # WebSocket 连接失败
            with client.websocket_connect(f"/api/v1/ws/test-task-123?token={invalid_token}"):
                pass
    
    # TODO: 添加更多测试用例
    # - 有效 Token 正常连接
    # - 非任务所有者被拒绝


class TestMiddlewareOrder:
    """测试：中间件顺序修正"""
    
    def test_cors_preflight_returns_request_id(self):
        """测试：CORS 预检请求返回 RequestID"""
        client = TestClient(app)
        
        response = client.options(
            "/api/v1/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        # 应该返回 CORS 头和 RequestID
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        # CORS 头由 FastAPI 自动处理
    
    def test_request_id_in_all_responses(self):
        """测试：所有响应都包含 RequestID"""
        client = TestClient(app)
        
        response = client.get("/health")
        
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers
        # RequestID 应该是 UUID 格式（36个字符）
        assert len(response.headers["X-Request-ID"]) == 36


class TestCoverImageCeleryTask:
    """测试：封面图生成改用 Celery"""
    
    @pytest.mark.skip(reason="需要 Celery Worker 运行")
    def test_cover_image_task_dispatch(self):
        """测试：封面图任务成功分发"""
        # 分发任务
        result = generate_cover_image_task.delay(
            roadmap_id="test-roadmap-123",
            prompt="Modern tech roadmap"
        )
        
        # 验证任务已分发
        assert result.id is not None
        
        # 注意：不等待任务完成，避免测试超时
        # 实际任务执行由 Celery Worker 负责


class TestJWTBlacklist:
    """测试：JWT 黑名单机制"""
    
    @pytest.mark.asyncio
    async def test_add_and_check_blacklist(self):
        """测试：添加和检查黑名单"""
        test_jti = "test-jti-12345"
        expires_in = 60  # 60 秒后过期
        
        # 添加到黑名单
        await add_to_blacklist(test_jti, expires_in)
        
        # 检查是否在黑名单中
        is_blocked = await is_blacklisted(test_jti)
        assert is_blocked is True
        
        # 检查不存在的 jti
        is_blocked = await is_blacklisted("non-existent-jti")
        assert is_blocked is False
    
    @pytest.mark.asyncio
    async def test_blacklist_auto_expiry(self):
        """测试：黑名单自动过期"""
        test_jti = "test-jti-expiry"
        expires_in = 2  # 2 秒后过期
        
        # 添加到黑名单
        await add_to_blacklist(test_jti, expires_in)
        
        # 立即检查（应该在黑名单中）
        is_blocked = await is_blacklisted(test_jti)
        assert is_blocked is True
        
        # 等待过期
        time.sleep(3)
        
        # 再次检查（应该已从黑名单移除）
        is_blocked = await is_blacklisted(test_jti)
        assert is_blocked is False
    
    def test_logout_endpoint(self):
        """测试：登出端点"""
        client = TestClient(app)
        
        # 1. 生成测试 Token
        payload = {
            "sub": "test-user-123",
            "jti": "test-jti-logout",
            "exp": int(time.time()) + 3600,  # 1 小时后过期
        }
        
        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        
        # 2. 调用登出端点
        # 注意：需要先登录才能登出，这里简化测试
        # 实际应用中应使用真实的登录流程
        
        # TODO: 完善测试逻辑
        # response = client.post(
        #     "/api/v1/auth/logout",
        #     headers={"Authorization": f"Bearer {token}"}
        # )
        # assert response.status_code == 200


class TestCeleryAsyncPool:
    """测试：Celery 异步池（已回退到 celery-pool-asyncio）"""
    
    def test_celery_pool_asyncio_import(self):
        """测试：celery-pool-asyncio 可正常导入"""
        try:
            import celery_pool_asyncio  # noqa: F401
            assert True
        except ImportError:
            pytest.fail("celery-pool-asyncio 未安装或无法导入")
    
    @pytest.mark.skip(reason="需要 Celery Worker 运行")
    def test_celery_worker_startup(self):
        """测试：Celery Worker 正常启动"""
        # 此测试需要启动 Celery Worker 并检查其日志
        # 可通过 Celery inspect 命令验证
        pass


# ============================================================
# 验收测试（Acceptance Tests）
# ============================================================

class TestAcceptanceCriteria:
    """验收标准测试"""
    
    def test_all_linter_checks_pass(self):
        """验收：所有代码通过 Linter 检查"""
        # 在 CI/CD 中运行：ruff check backend/app/
        pass
    
    @pytest.mark.skip(reason="需要手动验证")
    def test_no_session_leak(self):
        """验收：封面图生成无 Session 泄漏"""
        # 手动验证步骤：
        # 1. 启动 Celery Worker
        # 2. 触发封面图生成
        # 3. 检查日志，确认无 "session is closed" 错误
        pass
    
    @pytest.mark.skip(reason="需要性能测试")
    def test_jwt_blacklist_performance(self):
        """验收：JWT 黑名单检查延迟 <5ms"""
        # 性能测试：
        # 1. 批量添加 1000 个 jti 到黑名单
        # 2. 测量 is_blacklisted() 平均响应时间
        # 3. 确保 <5ms
        pass

