"""
聊天 CRUD 操作

纯数据访问层，遵循企业级架构规范
"""
from typing import List, Optional
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import structlog

from app.crud.base import BaseCRUD
from app.models.database import ChatSession, ChatMessage

logger = structlog.get_logger()


# 临时Create/Update schemas
class ChatSessionCreate(BaseModel):
    pass

class ChatSessionUpdate(BaseModel):
    pass

class ChatMessageCreate(BaseModel):
    pass

class ChatMessageUpdate(BaseModel):
    pass


class ChatSessionCRUD(BaseCRUD[ChatSession, ChatSessionCreate, ChatSessionUpdate]):
    """聊天会话 CRUD 操作"""
    
    async def get_by_id(
        self, 
        session: AsyncSession, 
        session_id: str
    ) -> Optional[ChatSession]:
        """
        根据会话ID获取会话
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            
        Returns:
            ChatSession 或 None
        """
        stmt = select(ChatSession).where(ChatSession.session_id == session_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_sessions(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatSession]:
        """
        获取用户在指定路线图下的所有会话
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            会话列表（按更新时间倒序）
        """
        stmt = (
            select(ChatSession)
            .where(
                ChatSession.user_id == user_id,
                ChatSession.roadmap_id == roadmap_id
            )
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_metadata(
        self,
        session: AsyncSession,
        session_id: str,
        message_count: Optional[int] = None,
        last_message_preview: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[ChatSession]:
        """
        更新会话元数据
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            message_count: 消息数量
            last_message_preview: 最后消息预览
            title: 会话标题
            
        Returns:
            更新后的 ChatSession
        """
        chat_session = await self.get_by_id(session, session_id)
        if not chat_session:
            return None
        
        if message_count is not None:
            chat_session.message_count = message_count
        if last_message_preview is not None:
            chat_session.last_message_preview = last_message_preview
        if title is not None:
            chat_session.title = title
        
        from app.models.database import beijing_now
        chat_session.updated_at = beijing_now()
        
        await session.flush()
        return chat_session


class ChatMessageCRUD(BaseCRUD[ChatMessage, ChatMessageCreate, ChatMessageUpdate]):
    """聊天消息 CRUD 操作"""
    
    async def get_by_session(
        self,
        session: AsyncSession,
        session_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatMessage]:
        """
        获取会话的所有消息
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            消息列表（按创建时间正序）
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_recent_messages(
        self,
        session: AsyncSession,
        session_id: str,
        limit: int = 10
    ) -> List[ChatMessage]:
        """
        获取会话的最近N条消息（用于上下文）
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            limit: 返回数量限制
            
        Returns:
            消息列表（按创建时间倒序，最新的在前）
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        result = await session.execute(stmt)
        messages = list(result.scalars().all())
        # 反转列表，使最早的消息在前（符合对话顺序）
        messages.reverse()
        return messages
    
    async def count_by_session(
        self,
        session: AsyncSession,
        session_id: str
    ) -> int:
        """
        统计会话的消息数量
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            
        Returns:
            消息数量
        """
        stmt = (
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.session_id == session_id)
        )
        result = await session.execute(stmt)
        return result.scalar() or 0


# 单例实例
chat_session_crud = ChatSessionCRUD(ChatSession)
chat_message_crud = ChatMessageCRUD(ChatMessage)
