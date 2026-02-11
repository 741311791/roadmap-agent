"""
WebSocket 实时推送端点

用于接收任务进度的实时通知，支持：
- 后台任务进度更新
- 人工审核通知
- 任务完成/失败通知

客户端连接后，会实时收到与 task_id 相关的所有事件。

🔒 安全策略：
- 使用JWT Token进行身份验证（通过Query参数传递）
- 验证用户是否拥有该任务的访问权限
- 拒绝未授权的连接
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status
from starlette.websockets import WebSocketState
from typing import Optional
import json
import asyncio
import time
import structlog
from jose import jwt, JWTError

from app.services.shared.notification_service import notification_service, TaskEvent
from app.crud.crud_task import TaskCRUD, get_task_crud
from app.models.database import RoadmapTask
from app.db.session import async_session_maker
from app.config.settings import settings

router = APIRouter(prefix="/api/v1")
logger = structlog.get_logger()


class ConnectionManager:
    """
    WebSocket 连接管理器
    
    管理活跃的 WebSocket 连接，支持：
    - 按 task_id 分组的连接管理
    - 广播消息到指定任务的所有连接
    """
    
    def __init__(self):
        # task_id -> list of websocket connections
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """接受新连接"""
        await websocket.accept()
        
        if task_id not in self.active_connections:
            self.active_connections[task_id] = []
        self.active_connections[task_id].append(websocket)
        
        logger.info(
            "websocket_connected",
            task_id=task_id,
            total_connections=len(self.active_connections[task_id]),
        )
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """断开连接"""
        if task_id in self.active_connections:
            if websocket in self.active_connections[task_id]:
                self.active_connections[task_id].remove(websocket)
            
            # 清理空列表
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        
        logger.info(
            "websocket_disconnected",
            task_id=task_id,
            remaining_connections=len(self.active_connections.get(task_id, [])),
        )
    
    async def send_to_task(self, task_id: str, message: dict):
        """发送消息到指定任务的所有连接"""
        if task_id not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[task_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    "websocket_send_failed",
                    task_id=task_id,
                    error=str(e),
                )
                disconnected.append(connection)
        
        # 清理已断开的连接
        for conn in disconnected:
            self.disconnect(conn, task_id)
    
    def get_connection_count(self, task_id: str) -> int:
        """获取指定任务的连接数"""
        return len(self.active_connections.get(task_id, []))


# 全局连接管理器
manager = ConnectionManager()


@router.websocket("/ws/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(None, description="JWT Token for authentication"),
    include_history: bool = Query(False, description="是否包含历史状态"),
):
    """
    WebSocket 端点：订阅任务进度更新（带鉴权）
    
    🔒 安全机制：
    1. 必须提供有效的JWT Token（通过Query参数）
    2. 验证Token的有效性和过期时间
    3. 检查用户是否拥有该任务的访问权限
    
    连接后会实时收到以下事件：
    - progress: 任务进度更新
    - human_review_required: 人工审核请求
    - completed: 任务完成
    - failed: 任务失败
    
    Args:
        task_id: 任务 ID
        token: JWT Token（必需）
        include_history: 是否在连接时发送当前状态（默认 False）
    
    连接URL示例：
        ws://api.example.com/ws/task-123?token=eyJ...
    
    Message Format:
    ```json
    {
        "type": "progress",
        "task_id": "xxx",
        "step": "curriculum_design",
        "status": "processing",
        "timestamp": "2024-01-01T12:00:00+08:00"
    }
    ```
    """
    # ===== 步骤1: 验证Token =====
    user_id = None
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("ws_no_token", task_id=task_id)
        return
    
    try:
        # 解码JWT Token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id = payload.get("sub")
        
        # 检查Token是否过期
        exp = payload.get("exp")
        if not exp or exp < time.time():
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning("ws_token_expired", task_id=task_id)
            return
            
    except JWTError as e:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("ws_auth_failed", task_id=task_id, error=str(e))
        return
    
    # ===== 步骤2: 验证用户有权访问该任务 =====
    task_crud = get_task_crud()
    async with async_session_maker() as session:
        task = await task_crud.get_by_task_id(session, task_id)
        
        if not task:
            await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
            logger.warning("ws_task_not_found", task_id=task_id, user_id=user_id)
            return
        
        if task.user_id != user_id:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            logger.warning("ws_forbidden", task_id=task_id, user_id=user_id, task_owner=task.user_id)
            return
    
    # ===== 步骤3: 建立连接 =====
    await manager.connect(websocket, task_id)
    logger.info("ws_connected", task_id=task_id, user_id=user_id)
    
    try:
        # 如果请求包含历史状态，先发送当前状态
        if include_history:
            await _send_current_status(websocket, task_id)
        
        # 发送连接成功消息
        await websocket.send_json({
            "type": "connected",
            "task_id": task_id,
            "message": "WebSocket 连接成功，正在监听任务进度...",
        })
        
        # 创建两个并发任务：
        # 1. 从 Redis Pub/Sub 接收事件并转发
        # 2. 处理客户端发来的消息（如心跳）
        
        redis_task = asyncio.create_task(_forward_redis_events(websocket, task_id))
        client_task = asyncio.create_task(_handle_client_messages(websocket, task_id))
        
        # 等待任一任务完成（通常是客户端断开或任务结束）
        done, pending = await asyncio.wait(
            [redis_task, client_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        
        # 取消未完成的任务
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    except WebSocketDisconnect:
        logger.info("websocket_client_disconnected", task_id=task_id)
    
    except Exception as e:
        logger.error(
            "websocket_error",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
    
    finally:
        manager.disconnect(websocket, task_id)


async def _send_current_status(websocket: WebSocket, task_id: str):
    """发送任务的当前状态"""
    try:
        async with async_session_maker() as session:
            # ✅ 使用已导入的 get_task_crud() 代替未定义的 RoadmapRepository
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
            
            if task:
                await websocket.send_json({
                    "type": "current_status",
                    "task_id": task_id,
                    "status": task.status,
                    "current_step": task.current_step,
                    "roadmap_id": task.roadmap_id,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                    "updated_at": task.updated_at.isoformat() if task.updated_at else None,
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "task_id": task_id,
                    "message": "任务不存在",
                })
    
    except Exception as e:
        logger.error(
            "websocket_get_status_error",
            task_id=task_id,
            error=str(e),
        )
        # ⚠️ 不尝试发送错误消息，避免在已关闭的连接上发送导致竞态条件
        # WebSocket 连接状态在检查和发送之间可能改变


async def _forward_redis_events(websocket: WebSocket, task_id: str):
    """从 Redis Pub/Sub 接收事件并转发到 WebSocket"""
    try:
        async for event in notification_service.subscribe_with_timeout(
            task_id,
            timeout_seconds=3600,  # 1 小时超时
        ):
            await websocket.send_json(event)
            
            # 如果是终止事件，发送关闭消息
            if event.get("type") in (TaskEvent.COMPLETED, TaskEvent.FAILED, "timeout"):
                await websocket.send_json({
                    "type": "closing",
                    "task_id": task_id,
                    "reason": event.get("type"),
                    "message": "任务已结束，连接即将关闭",
                })
                break
    
    except asyncio.CancelledError:
        logger.debug("redis_forward_cancelled", task_id=task_id)
        raise
    
    except Exception as e:
        logger.error(
            "redis_forward_error",
            task_id=task_id,
            error=str(e),
        )
        # ⚠️ 不尝试发送错误消息，避免竞态条件


async def _handle_client_messages(websocket: WebSocket, task_id: str):
    """处理客户端发来的消息"""
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "ping":
                    # 心跳响应
                    await websocket.send_json({
                        "type": "pong",
                        "task_id": task_id,
                    })
                
                elif message_type == "get_status":
                    # 主动请求状态
                    await _send_current_status(websocket, task_id)
                
                else:
                    logger.debug(
                        "websocket_unknown_message",
                        task_id=task_id,
                        message_type=message_type,
                    )
            
            except json.JSONDecodeError:
                logger.warning(
                    "websocket_invalid_json",
                    task_id=task_id,
                    data=data[:100],
                )
    
    except WebSocketDisconnect:
        # 客户端正常断开连接，不需要重新抛出异常
        logger.debug("websocket_client_messages_disconnected", task_id=task_id)
    
    except asyncio.CancelledError:
        # 任务被取消（通常是因为 Redis 任务完成），正常情况
        logger.debug("websocket_client_messages_cancelled", task_id=task_id)
    
    except Exception as e:
        logger.error(
            "websocket_client_handler_error",
            task_id=task_id,
            error=str(e),
        )

