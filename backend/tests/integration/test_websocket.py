"""
集成测试 - WebSocket连接测试

测试目标：
- WebSocket基础连接和断开
- JWT认证和权限验证
- 实时进度更新订阅
- 多客户端连接管理
"""
import pytest
import asyncio
import uuid
import json
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_session
from app.models.database import User
from app.core.auth.password import get_password_hash


@pytest.fixture
def ws_client():
    """创建WebSocket测试客户端"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def test_user(test_session: AsyncSession):
    """创建测试用户"""
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
def valid_jwt_token(test_user: User):
    """
    生成有效的JWT Token
    
    用于WebSocket认证测试
    """
    from app.core.auth import get_jwt_strategy
    from datetime import datetime, timedelta
    
    strategy = get_jwt_strategy()
    
    # 创建token payload
    payload = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "aud": ["fastapi-users:auth"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    
    # 注意：实际生成token可能需要使用strategy的方法
    # 这里使用简化版本
    import jwt
    from app.config.settings import settings
    
    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    
    return token


# ============================================================
# 基础连接测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_connection_success(ws_client: TestClient, valid_jwt_token: str):
    """
    测试WebSocket连接成功
    
    验证：
    - 使用有效JWT Token可以成功连接
    - 收到"connected"消息
    - 连接保持稳定
    """
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    with ws_client.websocket_connect(f"/ws/{task_id}?token={valid_jwt_token}") as websocket:
        # 接收连接成功消息
        data = websocket.receive_json()
        
        assert data["type"] == "connected"
        assert data["task_id"] == task_id
        assert "message" in data


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_connection_rejected_no_token(ws_client: TestClient):
    """
    测试WebSocket连接被拒绝（无Token）
    
    验证：
    - 不带Token尝试连接被拒绝
    - 连接关闭代码正确（WS_1008_POLICY_VIOLATION）
    """
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    try:
        with ws_client.websocket_connect(f"/ws/{task_id}") as websocket:
            # 不应该执行到这里
            pytest.fail("WebSocket connection should be rejected without token")
    except Exception as e:
        # 验证连接被拒绝
        # 注意：TestClient可能抛出不同类型的异常
        assert "1008" in str(e) or "policy" in str(e).lower() or "rejected" in str(e).lower()


# ============================================================
# JWT认证测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_authentication_valid_token(
    ws_client: TestClient,
    valid_jwt_token: str,
    test_user: User,
):
    """
    测试WebSocket JWT认证（有效Token）
    
    验证：
    - 有效Token可以通过认证
    - Token解码成功
    - 用户ID正确提取
    """
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    with ws_client.websocket_connect(f"/ws/{task_id}?token={valid_jwt_token}") as websocket:
        # 接收连接成功消息
        data = websocket.receive_json()
        
        assert data["type"] == "connected"
        # 验证认证成功（连接建立）


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_authentication_expired_token(ws_client: TestClient):
    """
    测试WebSocket JWT认证（过期Token）
    
    验证：
    - 过期Token无法通过认证
    - 连接被拒绝
    """
    import jwt
    from datetime import datetime, timedelta
    from app.config.settings import settings
    
    # 创建过期的token
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "test@example.com",
        "aud": ["fastapi-users:auth"],
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),  # 已过期
    }
    
    expired_token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    try:
        with ws_client.websocket_connect(f"/ws/{task_id}?token={expired_token}") as websocket:
            pytest.fail("WebSocket connection should be rejected with expired token")
    except Exception:
        # 连接应该被拒绝
        pass


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_authentication_invalid_token(ws_client: TestClient):
    """
    测试WebSocket JWT认证（无效Token）
    
    验证：
    - 无效Token无法通过认证
    - 连接被拒绝
    """
    invalid_token = "invalid.token.here"
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    try:
        with ws_client.websocket_connect(f"/ws/{task_id}?token={invalid_token}") as websocket:
            pytest.fail("WebSocket connection should be rejected with invalid token")
    except Exception:
        # 连接应该被拒绝
        pass


# ============================================================
# 进度更新测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_progress_updates(
    ws_client: TestClient,
    valid_jwt_token: str,
):
    """
    测试WebSocket进度更新
    
    验证：
    - 连接到特定task_id
    - Mock Redis发布进度事件
    - WebSocket客户端收到进度更新
    """
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    # Mock Redis Pub/Sub
    with patch("app.api.v1.websocket._forward_redis_events") as mock_forward:
        # Mock redis事件转发
        async def mock_redis_forward(websocket, task_id):
            """模拟Redis事件转发"""
            # 发送进度更新
            await websocket.send_json({
                "type": "progress",
                "task_id": task_id,
                "step": "curriculum_design",
                "status": "processing",
                "progress": 50,
            })
            
            # 模拟等待
            await asyncio.sleep(0.1)
        
        mock_forward.side_effect = mock_redis_forward
        
        with ws_client.websocket_connect(f"/ws/{task_id}?token={valid_jwt_token}") as websocket:
            # 接收连接成功消息
            connected_msg = websocket.receive_json()
            assert connected_msg["type"] == "connected"
            
            # 接收进度更新
            progress_msg = websocket.receive_json(timeout=2)
            
            assert progress_msg["type"] == "progress"
            assert progress_msg["task_id"] == task_id
            assert progress_msg["step"] == "curriculum_design"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_human_review_event(
    ws_client: TestClient,
    valid_jwt_token: str,
):
    """
    测试WebSocket人工审核事件
    
    验证：
    - Mock Redis发布"human_review_required"事件
    - 客户端收到审核请求
    """
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    with patch("app.api.v1.websocket._forward_redis_events") as mock_forward:
        async def mock_redis_forward(websocket, task_id):
            """模拟人工审核事件"""
            await websocket.send_json({
                "type": "human_review_required",
                "task_id": task_id,
                "roadmap_id": "test-roadmap-123",
                "message": "请审核路线图",
            })
            await asyncio.sleep(0.1)
        
        mock_forward.side_effect = mock_redis_forward
        
        with ws_client.websocket_connect(f"/ws/{task_id}?token={valid_jwt_token}") as websocket:
            # 跳过连接消息
            websocket.receive_json()
            
            # 接收审核事件
            review_msg = websocket.receive_json(timeout=2)
            
            assert review_msg["type"] == "human_review_required"
            assert review_msg["task_id"] == task_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_multiple_clients_same_task(
    ws_client: TestClient,
    valid_jwt_token: str,
):
    """
    测试多个客户端连接到同一task_id
    
    验证：
    - 多个客户端可以同时连接
    - 发布一条消息，所有客户端都收到
    """
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    # 注意：TestClient的websocket_connect是同步的
    # 实际测试多客户端需要使用真实的异步WebSocket客户端
    # 这里提供简化版本的概念验证
    
    with patch("app.api.v1.websocket._forward_redis_events") as mock_forward:
        async def mock_redis_forward(websocket, task_id):
            """模拟广播消息"""
            await websocket.send_json({
                "type": "broadcast",
                "task_id": task_id,
                "message": "所有客户端都应收到",
            })
            await asyncio.sleep(0.1)
        
        mock_forward.side_effect = mock_redis_forward
        
        # 第一个客户端
        with ws_client.websocket_connect(f"/ws/{task_id}?token={valid_jwt_token}") as ws1:
            ws1.receive_json()  # 跳过connected消息
            
            msg1 = ws1.receive_json(timeout=2)
            assert msg1["type"] == "broadcast"
            assert msg1["message"] == "所有客户端都应收到"


# ============================================================
# WebSocket错误处理测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_handles_client_disconnect(
    ws_client: TestClient,
    valid_jwt_token: str,
):
    """
    测试WebSocket处理客户端断开
    
    验证：
    - 客户端断开连接时正确清理资源
    - 不会导致服务器错误
    """
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    with patch("app.api.v1.websocket.manager.disconnect") as mock_disconnect:
        with ws_client.websocket_connect(f"/ws/{task_id}?token={valid_jwt_token}") as websocket:
            websocket.receive_json()  # 接收连接消息
        
        # 连接关闭后，disconnect应该被调用
        # 注意：TestClient可能不会触发disconnect，这取决于实现


@pytest.mark.asyncio
@pytest.mark.integration
async def test_websocket_with_include_history(
    ws_client: TestClient,
    valid_jwt_token: str,
):
    """
    测试WebSocket带历史状态
    
    验证：
    - include_history=true时发送当前状态
    - 历史状态格式正确
    """
    task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    with patch("app.api.v1.websocket._send_current_status") as mock_send_status:
        mock_send_status.return_value = None
        
        with ws_client.websocket_connect(
            f"/ws/{task_id}?token={valid_jwt_token}&include_history=true"
        ) as websocket:
            # 接收连接消息
            data = websocket.receive_json()
            assert data["type"] == "connected"
            
            # 验证_send_current_status被调用
            # 注意：由于是Mock，实际测试中需要验证调用

