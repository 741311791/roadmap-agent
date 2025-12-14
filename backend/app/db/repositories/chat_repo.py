"""
聊天会话 Repository

负责 ChatSession 和 ChatMessage 表的数据访问操作。

职责范围：
- 会话的 CRUD 操作
- 消息的 CRUD 操作
- 会话历史查询
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from app.models.database import ChatSession, ChatMessage, beijing_now
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class ChatRepository(BaseRepository[ChatSession]):
    """
    聊天会话数据访问层
    
    管理伴学Agent的聊天会话和消息。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ChatSession)
        self._message_model = ChatMessage
    
    # ============================================================
    # 会话管理方法
    # ============================================================
    
    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        根据 session_id 查询会话
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话记录，如果不存在则返回 None
        """
        return await self.get_by_id(session_id)
    
    async def create_session(
        self,
        user_id: str,
        roadmap_id: str,
        concept_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> ChatSession:
        """
        创建新的聊天会话
        
        Args:
            user_id: 用户 ID
            roadmap_id: 路线图 ID
            concept_id: 概念 ID（可选）
            title: 会话标题（可选）
            
        Returns:
            创建的会话记录
        """
        session_entity = ChatSession(
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            title=title,
            message_count=0,
        )
        
        created = await self.create(session_entity)
        
        logger.info(
            "chat_session_created",
            session_id=created.session_id,
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )
        
        return created
    
    async def get_user_sessions(
        self,
        user_id: str,
        roadmap_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ChatSession]:
        """
        查询用户在指定路线图下的所有会话
        
        按更新时间倒序排列（最新的在前）。
        
        Args:
            user_id: 用户 ID
            roadmap_id: 路线图 ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            会话列表
        """
        result = await self.session.execute(
            select(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.roadmap_id == roadmap_id,
            )
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
        sessions = list(result.scalars().all())
        
        logger.debug(
            "user_sessions_listed",
            user_id=user_id,
            roadmap_id=roadmap_id,
            count=len(sessions),
        )
        
        return sessions
    
    async def update_session_metadata(
        self,
        session_id: str,
        message_count: Optional[int] = None,
        last_message_preview: Optional[str] = None,
        title: Optional[str] = None,
    ) -> bool:
        """
        更新会话元数据
        
        Args:
            session_id: 会话 ID
            message_count: 消息数量
            last_message_preview: 最后一条消息预览
            title: 会话标题
            
        Returns:
            是否更新成功
        """
        update_fields = {"updated_at": beijing_now()}
        
        if message_count is not None:
            update_fields["message_count"] = message_count
        if last_message_preview is not None:
            # 截断消息预览，最多100字符
            update_fields["last_message_preview"] = last_message_preview[:100]
        if title is not None:
            update_fields["title"] = title
        
        return await self.update_by_id(session_id, **update_fields)
    
    # ============================================================
    # 消息管理方法
    # ============================================================
    
    async def create_message(
        self,
        session_id: str,
        role: str,
        content: str,
        intent_type: Optional[str] = None,
        message_metadata: Optional[dict] = None,
    ) -> ChatMessage:
        """
        创建新的聊天消息
        
        Args:
            session_id: 会话 ID
            role: 消息角色 (user/assistant/system)
            content: 消息内容
            intent_type: 意图类型
            message_metadata: 额外元数据
            
        Returns:
            创建的消息记录
        """
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            intent_type=intent_type,
            message_metadata=message_metadata,
        )
        
        self.session.add(message)
        
        logger.info(
            "chat_message_created",
            message_id=message.message_id,
            session_id=session_id,
            role=role,
            content_length=len(content),
        )
        
        return message
    
    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ChatMessage]:
        """
        查询会话的消息列表
        
        按创建时间升序排列（最早的在前）。
        
        Args:
            session_id: 会话 ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            消息列表
        """
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        
        messages = list(result.scalars().all())
        
        logger.debug(
            "session_messages_listed",
            session_id=session_id,
            count=len(messages),
        )
        
        return messages
    
    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[ChatMessage]:
        """
        获取会话的最近N条消息
        
        按创建时间倒序获取，然后翻转为升序（便于构建上下文）。
        
        Args:
            session_id: 会话 ID
            limit: 返回数量限制
            
        Returns:
            消息列表（按时间升序）
        """
        result = await self.session.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        
        messages = list(result.scalars().all())
        # 翻转为升序
        messages.reverse()
        
        return messages
    
    async def count_messages(self, session_id: str) -> int:
        """
        统计会话的消息数量
        
        Args:
            session_id: 会话 ID
            
        Returns:
            消息数量
        """
        result = await self.session.execute(
            select(func.count(ChatMessage.message_id))
            .where(ChatMessage.session_id == session_id)
        )
        
        return result.scalar_one()
