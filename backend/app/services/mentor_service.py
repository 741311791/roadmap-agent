"""
伴学 Mentor 服务层

业务逻辑聚合层，遵循企业级架构规范
"""
from typing import List, Optional, AsyncGenerator
import json
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_chat import chat_session_crud, chat_message_crud
from app.crud.crud_note import note_crud
from app.models.database import ChatSession, ChatMessage, LearningNote, beijing_now
from app.schemas.mentor import (
    ChatSessionResponse,
    ChatMessageResponse,
    LearningNoteResponse,
    ChatStreamRequest,
    LearningNoteCreate,
    LearningNoteUpdate,
    ChatStreamEvent,
)
from app.models.domain import MentorAgentInput

logger = structlog.get_logger()


class MentorService:
    """
    伴学服务
    
    负责：
    - 聊天会话管理
    - 流式对话生成
    - 学习笔记管理
    """
    
    # ========================================
    # 聊天会话相关
    # ========================================
    
    async def get_or_create_session(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        concept_id: Optional[str],
        session_id: Optional[str] = None,
    ) -> ChatSession:
        """
        获取或创建聊天会话
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            concept_id: 概念ID
            session_id: 会话ID（如果提供）
            
        Returns:
            ChatSession
            
        Raises:
            ValueError: 会话不存在或不属于该用户
        """
        if session_id:
            # 获取现有会话
            chat_session = await chat_session_crud.get_by_id(session, session_id)
            if not chat_session:
                raise ValueError(f"会话 {session_id} 不存在")
            if chat_session.user_id != user_id:
                raise ValueError(f"会话 {session_id} 不属于用户 {user_id}")
            return chat_session
        
        # 创建新会话
        new_session = ChatSession(
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            message_count=0,
        )
        session.add(new_session)
        await session.flush()
        
        logger.info(
            "chat_session_created",
            session_id=new_session.session_id,
            user_id=user_id,
            roadmap_id=roadmap_id,
        )
        
        return new_session
    
    async def get_user_sessions(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ChatSessionResponse]:
        """
        获取用户的所有聊天会话
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            会话列表
        """
        sessions = await chat_session_crud.get_user_sessions(
            session, user_id, roadmap_id, limit, offset
        )
        return [ChatSessionResponse.model_validate(s) for s in sessions]
    
    async def save_user_message(
        self,
        session: AsyncSession,
        session_id: str,
        content: str,
    ) -> ChatMessage:
        """
        保存用户消息
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            content: 消息内容
            
        Returns:
            ChatMessage
        """
        message = ChatMessage(
            session_id=session_id,
            role="user",
            content=content,
            created_at=beijing_now(),
        )
        session.add(message)
        await session.flush()
        
        return message
    
    async def save_assistant_message(
        self,
        session: AsyncSession,
        session_id: str,
        content: str,
        intent_type: Optional[str] = None,
    ) -> ChatMessage:
        """
        保存AI响应消息
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            content: 消息内容
            intent_type: 意图类型
            
        Returns:
            ChatMessage
        """
        message = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=content,
            intent_type=intent_type,
            created_at=beijing_now(),
        )
        session.add(message)
        await session.flush()
        
        return message
    
    async def get_session_messages(
        self,
        session: AsyncSession,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[ChatMessageResponse]:
        """
        获取会话的历史消息
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            消息列表
        """
        messages = await chat_message_crud.get_by_session(
            session, session_id, limit, offset
        )
        return [ChatMessageResponse.model_validate(m) for m in messages]
    
    async def get_recent_messages_for_context(
        self,
        session: AsyncSession,
        session_id: str,
        limit: int = 10,
    ) -> List[ChatMessage]:
        """
        获取最近的消息作为上下文
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            limit: 返回数量限制
            
        Returns:
            消息列表（ORM对象）
        """
        return await chat_message_crud.get_recent_messages(
            session, session_id, limit
        )
    
    async def update_session_metadata(
        self,
        session: AsyncSession,
        session_id: str,
        last_message_preview: Optional[str] = None,
    ) -> None:
        """
        更新会话元数据
        
        Args:
            session: 数据库会话
            session_id: 会话ID
            last_message_preview: 最后消息预览
        """
        # 统计消息数量
        message_count = await chat_message_crud.count_by_session(session, session_id)
        
        # 更新会话
        await chat_session_crud.update_metadata(
            session,
            session_id,
            message_count=message_count,
            last_message_preview=last_message_preview[:100] if last_message_preview else None,
        )
    
    # ========================================
    # 流式对话
    # ========================================
    
    async def chat_stream(
        self,
        request: ChatStreamRequest,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话生成（SSE格式）
        
        该方法处理完整的聊天流程：
        1. 创建/获取会话
        2. 保存用户消息
        3. 调用MentorAgent生成响应
        4. 保存AI响应
        5. 更新会话元数据
        
        Args:
            request: 聊天请求
            
        Yields:
            SSE格式的事件字符串
        """
        from app.db.session import async_db_session
        from app.agents.mentor_agent import MentorAgent
        
        chat_session = None
        full_response = ""
        
        try:
            # 1. 获取或创建会话
            async with async_db_session() as db:
                chat_session = await self.get_or_create_session(
                    db,
                    request.user_id,
                    request.roadmap_id,
                    request.concept_id,
                    request.session_id,
                )
                
                # 发送会话ID
                event = ChatStreamEvent(
                    type="session_id",
                    session_id=chat_session.session_id
                )
                yield f"data: {event.model_dump_json()}\n\n"
                
                # 2. 保存用户消息
                await self.save_user_message(db, chat_session.session_id, request.message)
                await db.commit()
            
            # 3. 获取会话历史
            async with async_db_session() as db:
                history = await self.get_recent_messages_for_context(
                    db, chat_session.session_id, limit=10
                )
            
            # 4. 获取上下文信息
            context = await self._get_learning_context(
                request.user_id,
                request.roadmap_id,
                request.concept_id,
            )
            
            # 5. 构建Agent输入
            from app.models.domain import ChatMessage as ChatMessageDomain
            mentor_input = MentorAgentInput(
                user_message=request.message,
                user_id=request.user_id,
                roadmap_id=request.roadmap_id,
                concept_id=request.concept_id,
                session_history=[
                    ChatMessageDomain(
                        message_id=msg.message_id,
                        session_id=msg.session_id,
                        role=msg.role,
                        content=msg.content,
                        intent_type=msg.intent_type,
                        created_at=msg.created_at,
                    )
                    for msg in history
                ],
                **context,
            )
            
            # 6. 流式调用MentorAgent
            mentor_agent = MentorAgent()
            async for chunk in mentor_agent.execute_stream(mentor_input):
                full_response += chunk
                event = ChatStreamEvent(type="content", chunk=chunk)
                yield f"data: {event.model_dump_json()}\n\n"
            
            # 7. 保存AI响应
            async with async_db_session() as db:
                # 获取意图类型
                intent_type = await mentor_agent.get_intent(mentor_input)
                
                ai_msg = await self.save_assistant_message(
                    db,
                    chat_session.session_id,
                    full_response,
                    intent_type,
                )
                
                # 更新会话元数据
                await self.update_session_metadata(
                    db,
                    chat_session.session_id,
                    last_message_preview=full_response,
                )
                
                await db.commit()
            
            # 8. 发送完成标记
            event = ChatStreamEvent(
                type="done",
                message_id=ai_msg.message_id
            )
            yield f"data: {event.model_dump_json()}\n\n"
        
        except Exception as e:
            logger.error("chat_stream_failed", error=str(e), error_type=type(e).__name__)
            event = ChatStreamEvent(type="error", message=str(e))
            yield f"data: {event.model_dump_json()}\n\n"
    
    async def _get_learning_context(
        self,
        user_id: str,
        roadmap_id: str,
        concept_id: Optional[str],
    ) -> dict:
        """
        获取学习上下文信息
        
        Args:
            user_id: 用户ID
            roadmap_id: 路线图ID
            concept_id: 概念ID
            
        Returns:
            上下文信息字典
        """
        context = {}
        
        # 获取路线图元数据
        try:
            from app.tools.mentor.get_roadmap_metadata_tool import (
                GetRoadmapMetadataTool,
                GetRoadmapMetadataInput,
            )
            roadmap_tool = GetRoadmapMetadataTool()
            roadmap_result = await roadmap_tool.execute(
                GetRoadmapMetadataInput(roadmap_id=roadmap_id)
            )
            if roadmap_result.success:
                context["roadmap_title"] = roadmap_result.title
        except Exception as e:
            logger.warning("get_roadmap_metadata_failed", error=str(e))
        
        # 获取概念信息
        if concept_id:
            try:
                roadmap_tool = GetRoadmapMetadataTool()
                concept_info = await roadmap_tool.get_concept_info(roadmap_id, concept_id)
                if concept_info:
                    context["concept_name"] = concept_info.name
                    context["concept_description"] = concept_info.description
            except Exception as e:
                logger.warning("get_concept_info_failed", error=str(e))
            
            # 获取教程摘要
            try:
                from app.tools.mentor.get_concept_tutorial_tool import (
                    GetConceptTutorialTool,
                    GetConceptTutorialInput,
                )
                tutorial_tool = GetConceptTutorialTool()
                tutorial_result = await tutorial_tool.execute(
                    GetConceptTutorialInput(
                        roadmap_id=roadmap_id,
                        concept_id=concept_id,
                    )
                )
                if tutorial_result.success:
                    context["tutorial_summary"] = tutorial_result.summary
            except Exception as e:
                logger.warning("get_tutorial_summary_failed", error=str(e))
        
        # 获取用户画像
        try:
            from app.tools.mentor.get_user_profile_tool import (
                GetUserProfileTool,
                GetUserProfileInput,
            )
            profile_tool = GetUserProfileTool()
            profile_result = await profile_tool.execute(
                GetUserProfileInput(user_id=user_id)
            )
            if profile_result.success:
                context["user_background"] = (
                    f"{profile_result.industry or ''} {profile_result.current_role or ''}".strip()
                    or None
                )
                context["user_level"] = (
                    "intermediate" if profile_result.tech_stack else "beginner"
                )
        except Exception as e:
            logger.warning("get_user_profile_failed", error=str(e))
        
        return context
    
    # ========================================
    # 学习笔记相关
    # ========================================
    
    async def create_note(
        self,
        session: AsyncSession,
        note_data: LearningNoteCreate,
    ) -> LearningNoteResponse:
        """
        创建学习笔记
        
        Args:
            session: 数据库会话
            note_data: 笔记数据
            
        Returns:
            LearningNoteResponse
        """
        note = LearningNote(**note_data.model_dump())
        session.add(note)
        await session.flush()
        
        logger.info(
            "learning_note_created",
            note_id=note.note_id,
            user_id=note.user_id,
            roadmap_id=note.roadmap_id,
            concept_id=note.concept_id,
        )
        
        return LearningNoteResponse.model_validate(note)
    
    async def get_notes_by_concept(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        concept_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[LearningNoteResponse]:
        """
        获取指定概念的笔记
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            concept_id: 概念ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            笔记列表
        """
        notes = await note_crud.get_by_concept(
            session, user_id, roadmap_id, concept_id, limit, offset
        )
        return [LearningNoteResponse.model_validate(n) for n in notes]
    
    async def get_notes_by_roadmap(
        self,
        session: AsyncSession,
        user_id: str,
        roadmap_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[LearningNoteResponse]:
        """
        获取指定路线图的所有笔记
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            roadmap_id: 路线图ID
            limit: 返回数量限制
            offset: 分页偏移
            
        Returns:
            笔记列表
        """
        notes = await note_crud.get_by_roadmap(
            session, user_id, roadmap_id, limit, offset
        )
        return [LearningNoteResponse.model_validate(n) for n in notes]
    
    async def update_note(
        self,
        session: AsyncSession,
        note_id: str,
        user_id: str,
        update_data: LearningNoteUpdate,
    ) -> LearningNoteResponse:
        """
        更新学习笔记
        
        Args:
            session: 数据库会话
            note_id: 笔记ID
            user_id: 用户ID（用于权限验证）
            update_data: 更新数据
            
        Returns:
            LearningNoteResponse
            
        Raises:
            ValueError: 笔记不存在或无权更新
        """
        # 验证笔记所有权
        note = await note_crud.get_by_id(session, note_id)
        if not note:
            raise ValueError(f"笔记 {note_id} 不存在")
        if note.user_id != user_id:
            raise ValueError(f"无权更新笔记 {note_id}")
        
        # 更新笔记
        updated_note = await note_crud.update_note(session, note_id, update_data)
        
        logger.info(
            "learning_note_updated",
            note_id=note_id,
            user_id=user_id,
        )
        
        return LearningNoteResponse.model_validate(updated_note)
    
    async def delete_note(
        self,
        session: AsyncSession,
        note_id: str,
        user_id: str,
    ) -> bool:
        """
        删除学习笔记
        
        Args:
            session: 数据库会话
            note_id: 笔记ID
            user_id: 用户ID（用于权限验证）
            
        Returns:
            是否删除成功
            
        Raises:
            ValueError: 笔记不存在或无权删除
        """
        # 验证笔记所有权
        note = await note_crud.get_by_id(session, note_id)
        if not note:
            raise ValueError(f"笔记 {note_id} 不存在")
        if note.user_id != user_id:
            raise ValueError(f"无权删除笔记 {note_id}")
        
        # 删除笔记
        await session.delete(note)
        await session.flush()
        
        logger.info(
            "learning_note_deleted",
            note_id=note_id,
            user_id=user_id,
        )
        
        return True


# ========================================
# 依赖注入函数
# ========================================

def get_mentor_service() -> MentorService:
    """依赖注入函数"""
    return MentorService()

