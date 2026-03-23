"""
聊天 CRUD 操作

纯数据访问层，遵循企业级架构规范
"""
from typing import List, Optional
from sqlalchemy import delete, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.crud.base import BaseCRUD
from app.models.database import ChatMessage, ChatSession, MentorMemoryJob
from app.schemas.mentor import MentorSessionCreateRequest

logger = structlog.get_logger()


# 临时Create/Update schemas
class ChatSessionCreate(MentorSessionCreateRequest):
    """聊天会话创建 Schema"""


class ChatSessionUpdate(MentorSessionCreateRequest):
    """聊天会话更新 Schema"""


class ChatMessageCreate(MentorSessionCreateRequest):
    """聊天消息创建 Schema 占位类型"""


class ChatMessageUpdate(MentorSessionCreateRequest):
    """聊天消息更新 Schema 占位类型"""


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
        roadmap_id: str | None = None,
        scope: str | None = None,
        concept_id: str | None = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[ChatSession]:
        """
        获取用户在指定路线图下的所有会话
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            scope: 会话作用域：roadmap/concept
            concept_id: 概念 ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            会话列表（按更新时间倒序）
        """
        stmt = select(ChatSession).where(ChatSession.user_id == user_id)

        if roadmap_id is not None:
            stmt = stmt.where(ChatSession.roadmap_id == roadmap_id)

        if scope == "roadmap":
            stmt = stmt.where(ChatSession.concept_id.is_(None))
        elif scope == "concept":
            stmt = stmt.where(ChatSession.concept_id == concept_id)

        stmt = stmt.order_by(desc(ChatSession.updated_at)).limit(limit).offset(offset)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_user_sessions(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str | None = None,
        scope: str | None = None,
        concept_id: str | None = None,
    ) -> int:
        """
        统计用户会话数量

        Args:
            session: 数据库会话
            user_id: 用户 ID
            roadmap_id: 路线图 ID（可选）
            scope: 会话作用域：roadmap/concept
            concept_id: 概念 ID

        Returns:
            会话总数
        """
        stmt = select(func.count()).select_from(ChatSession).where(ChatSession.user_id == user_id)
        if roadmap_id is not None:
            stmt = stmt.where(ChatSession.roadmap_id == roadmap_id)
        if scope == "roadmap":
            stmt = stmt.where(ChatSession.concept_id.is_(None))
        elif scope == "concept":
            stmt = stmt.where(ChatSession.concept_id == concept_id)

        result = await session.execute(stmt)
        return result.scalar() or 0

    async def create_session(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None = None,
        title: str | None = None,
        agent_type: str = "tutoring",
        model_id: str | None = None,
    ) -> ChatSession:
        """
        创建聊天会话

        Args:
            session: 数据库会话
            user_id: 用户 ID
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            title: 会话标题
            agent_type: AI 伴学助手模式
            model_id: 默认模型 ID

        Returns:
            创建后的会话对象
        """
        return await self.create(
            session,
            obj_in={
                "user_id": user_id,
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "title": title,
                "agent_type": agent_type,
                "model_id": model_id,
            },
        )
    
    async def update_metadata(
        self,
        session: AsyncSession,
        session_id: str,
        message_count: Optional[int] = None,
        last_message_preview: Optional[str] = None,
        title: Optional[str] = None,
        model_id: Optional[str] = None,
        agent_type: Optional[str] = None,
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
        if model_id is not None:
            chat_session.model_id = model_id
        if agent_type is not None:
            chat_session.agent_type = agent_type
        
        from app.models.database import beijing_now
        chat_session.updated_at = beijing_now()
        
        await session.flush()
        return chat_session

    async def delete_session_tree(
        self,
        session: AsyncSession,
        *,
        session_id: str,
    ) -> Optional[ChatSession]:
        """
        删除会话及其关联的消息、记忆任务

        Args:
            session: 数据库会话
            session_id: 会话 ID

        Returns:
            被删除的会话对象；不存在时返回 None
        """
        chat_session = await self.get_by_id(session, session_id)
        if chat_session is None:
            return None

        await session.execute(
            delete(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        await session.execute(
            delete(MentorMemoryJob).where(MentorMemoryJob.session_id == session_id)
        )
        await session.delete(chat_session)
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

    async def create_message(
        self,
        session: AsyncSession,
        *,
        session_id: str,
        role: str,
        content: str,
        agent_type: str | None = None,
        model_id: str | None = None,
        trace_id: str | None = None,
        token_usage_input: int | None = None,
        token_usage_output: int | None = None,
        message_metadata: dict | None = None,
        intent_type: str | None = None,
        message_id: str | None = None,
    ) -> ChatMessage:
        """
        创建聊天消息

        Args:
            session: 数据库会话
            session_id: 会话 ID
            role: 消息角色
            content: 消息内容
            agent_type: AI 伴学助手模式
            model_id: 模型 ID
            trace_id: 链路追踪 ID
            token_usage_input: 输入 Token 数
            token_usage_output: 输出 Token 数
            message_metadata: 扩展元数据
            intent_type: 意图类型
            message_id: 指定消息 ID

        Returns:
            创建后的消息对象
        """
        payload = {
            "session_id": session_id,
            "role": role,
            "content": content,
            "agent_type": agent_type,
            "model_id": model_id,
            "trace_id": trace_id,
            "token_usage_input": token_usage_input,
            "token_usage_output": token_usage_output,
            "message_metadata": message_metadata,
            "intent_type": intent_type,
        }

        if message_id is not None:
            payload["message_id"] = message_id

        return await self.create(session, obj_in=payload)


# 单例实例
chat_session_crud = ChatSessionCRUD(ChatSession)
chat_message_crud = ChatMessageCRUD(ChatMessage)
