"""
伴学Agent API端点

提供伴学模式的聊天和会话管理功能：
- POST /mentor/chat/stream: 流式对话
- GET /mentor/sessions/{roadmap_id}: 获取会话列表
- GET /mentor/messages/{session_id}: 获取会话消息
- GET /mentor/notes/{roadmap_id}: 获取学习笔记
"""
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import structlog

from app.models.domain import (
    ChatMessageRequest,
    ChatSession,
    ChatMessage,
    LearningNote,
    MentorAgentInput,
)
from app.agents.mentor_agent import MentorAgent
from app.db.repository_factory import get_repo_factory, RepositoryFactory
from app.tools.mentor.get_roadmap_metadata_tool import GetRoadmapMetadataTool
from app.tools.mentor.get_concept_tutorial_tool import GetConceptTutorialTool
from app.tools.mentor.get_user_profile_tool import GetUserProfileTool

logger = structlog.get_logger()

router = APIRouter(prefix="/mentor", tags=["mentor"])


# ============================================================
# 响应模型
# ============================================================

class ChatSessionResponse(BaseModel):
    """会话响应"""
    session_id: str
    user_id: str
    roadmap_id: str
    concept_id: Optional[str] = None
    title: Optional[str] = None
    message_count: int
    last_message_preview: Optional[str] = None
    created_at: str
    updated_at: str


class ChatMessageResponse(BaseModel):
    """消息响应"""
    message_id: str
    session_id: str
    role: str
    content: str
    intent_type: Optional[str] = None
    created_at: str


class LearningNoteResponse(BaseModel):
    """笔记响应"""
    note_id: str
    user_id: str
    roadmap_id: str
    concept_id: str
    title: Optional[str] = None
    content: str
    source: str
    tags: List[str]
    created_at: str
    updated_at: str


# ============================================================
# 流式对话端点
# ============================================================

@router.post("/chat/stream")
async def chat_stream(
    request: ChatMessageRequest,
    repo_factory: RepositoryFactory = Depends(get_repo_factory),
):
    """
    伴学Agent流式对话
    
    使用SSE实时推送AI响应，支持打字机效果。
    
    SSE事件格式：
    - {type: 'session_id', session_id: string}: 会话ID
    - {type: 'content', chunk: string}: 内容片段
    - {type: 'done', message_id: string}: 完成标记
    - {type: 'error', message: string}: 错误信息
    
    Args:
        request: 聊天请求，包含user_id, roadmap_id, concept_id, message, session_id
        
    Returns:
        SSE流
    """
    async def generate():
        try:
            # 1. 获取或创建会话
            async with repo_factory.create_session() as session:
                chat_repo = repo_factory.create_chat_repo(session)
                
                if request.session_id:
                    chat_session = await chat_repo.get_session(request.session_id)
                    if not chat_session:
                        yield f"data: {json.dumps({'type': 'error', 'message': '会话不存在'})}\n\n"
                        return
                else:
                    # 创建新会话
                    chat_session = await chat_repo.create_session(
                        user_id=request.user_id,
                        roadmap_id=request.roadmap_id,
                        concept_id=request.concept_id,
                    )
                    await session.commit()
                
                # 发送会话ID
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': chat_session.session_id})}\n\n"
                
                # 2. 保存用户消息
                user_msg = await chat_repo.create_message(
                    session_id=chat_session.session_id,
                    role="user",
                    content=request.message,
                )
                await session.commit()
            
            # 3. 获取会话历史
            async with repo_factory.create_session() as session:
                chat_repo = repo_factory.create_chat_repo(session)
                history = await chat_repo.get_recent_messages(
                    chat_session.session_id,
                    limit=10,
                )
            
            # 4. 获取上下文信息
            context = await _get_learning_context(
                request.user_id,
                request.roadmap_id,
                request.concept_id,
            )
            
            # 5. 构建Agent输入
            mentor_input = MentorAgentInput(
                user_message=request.message,
                user_id=request.user_id,
                roadmap_id=request.roadmap_id,
                concept_id=request.concept_id,
                session_history=[
                    ChatMessage(
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
            full_response = ""
            
            async for chunk in mentor_agent.execute_stream(mentor_input):
                full_response += chunk
                # SSE格式
                yield f"data: {json.dumps({'type': 'content', 'chunk': chunk})}\n\n"
            
            # 7. 保存AI响应
            async with repo_factory.create_session() as session:
                chat_repo = repo_factory.create_chat_repo(session)
                
                # 获取意图类型
                intent_type = await mentor_agent.get_intent(mentor_input)
                
                ai_msg = await chat_repo.create_message(
                    session_id=chat_session.session_id,
                    role="assistant",
                    content=full_response,
                    intent_type=intent_type,
                )
                
                # 更新会话元数据
                message_count = await chat_repo.count_messages(chat_session.session_id)
                await chat_repo.update_session_metadata(
                    session_id=chat_session.session_id,
                    message_count=message_count,
                    last_message_preview=full_response[:100] if full_response else None,
                )
                
                await session.commit()
            
            # 8. 发送完成标记
            yield f"data: {json.dumps({'type': 'done', 'message_id': ai_msg.message_id})}\n\n"
        
        except Exception as e:
            logger.error("chat_stream_failed", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _get_learning_context(
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
        from app.tools.mentor.get_roadmap_metadata_tool import GetRoadmapMetadataInput
        roadmap_tool = GetRoadmapMetadataTool()
        roadmap_result = await roadmap_tool.execute(GetRoadmapMetadataInput(roadmap_id=roadmap_id))
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
            from app.tools.mentor.get_concept_tutorial_tool import GetConceptTutorialInput
            tutorial_tool = GetConceptTutorialTool()
            tutorial_result = await tutorial_tool.execute(GetConceptTutorialInput(
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            ))
            if tutorial_result.success:
                context["tutorial_summary"] = tutorial_result.summary
        except Exception as e:
            logger.warning("get_tutorial_summary_failed", error=str(e))
    
    # 获取用户画像
    try:
        from app.tools.mentor.get_user_profile_tool import GetUserProfileInput
        profile_tool = GetUserProfileTool()
        profile_result = await profile_tool.execute(GetUserProfileInput(user_id=user_id))
        if profile_result.success:
            context["user_background"] = f"{profile_result.industry or ''} {profile_result.current_role or ''}".strip() or None
            context["user_level"] = "intermediate" if profile_result.tech_stack else "beginner"
    except Exception as e:
        logger.warning("get_user_profile_failed", error=str(e))
    
    return context


# ============================================================
# 会话管理端点
# ============================================================

@router.get("/sessions/{roadmap_id}")
async def get_sessions(
    roadmap_id: str,
    user_id: str = Query(..., description="用户ID"),
    limit: int = Query(50, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    repo_factory: RepositoryFactory = Depends(get_repo_factory),
) -> dict:
    """
    获取用户在指定路线图下的所有聊天会话
    
    Args:
        roadmap_id: 路线图ID
        user_id: 用户ID
        limit: 返回数量限制
        offset: 分页偏移
        
    Returns:
        会话列表
    """
    async with repo_factory.create_session() as session:
        chat_repo = repo_factory.create_chat_repo(session)
        sessions = await chat_repo.get_user_sessions(
            user_id=user_id,
            roadmap_id=roadmap_id,
            limit=limit,
            offset=offset,
        )
    
    return {
        "sessions": [
            ChatSessionResponse(
                session_id=s.session_id,
                user_id=s.user_id,
                roadmap_id=s.roadmap_id,
                concept_id=s.concept_id,
                title=s.title,
                message_count=s.message_count,
                last_message_preview=s.last_message_preview,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            )
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get("/messages/{session_id}")
async def get_messages(
    session_id: str,
    limit: int = Query(50, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    repo_factory: RepositoryFactory = Depends(get_repo_factory),
) -> dict:
    """
    获取会话的历史消息
    
    Args:
        session_id: 会话ID
        limit: 返回数量限制
        offset: 分页偏移
        
    Returns:
        消息列表
    """
    async with repo_factory.create_session() as session:
        chat_repo = repo_factory.create_chat_repo(session)
        
        # 验证会话是否存在
        chat_session = await chat_repo.get_session(session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        messages = await chat_repo.get_messages(
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
    
    return {
        "messages": [
            ChatMessageResponse(
                message_id=m.message_id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                intent_type=m.intent_type,
                created_at=m.created_at.isoformat(),
            )
            for m in messages
        ],
        "total": len(messages),
    }


# ============================================================
# 笔记管理端点
# ============================================================

@router.get("/notes/{roadmap_id}")
async def get_notes(
    roadmap_id: str,
    user_id: str = Query(..., description="用户ID"),
    concept_id: Optional[str] = Query(None, description="概念ID（可选，用于过滤）"),
    limit: int = Query(50, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    repo_factory: RepositoryFactory = Depends(get_repo_factory),
) -> dict:
    """
    获取用户的学习笔记
    
    Args:
        roadmap_id: 路线图ID
        user_id: 用户ID
        concept_id: 概念ID（可选）
        limit: 返回数量限制
        offset: 分页偏移
        
    Returns:
        笔记列表
    """
    async with repo_factory.create_session() as session:
        note_repo = repo_factory.create_note_repo(session)
        
        if concept_id:
            notes = await note_repo.get_notes_by_concept(
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                limit=limit,
                offset=offset,
            )
        else:
            notes = await note_repo.get_notes_by_roadmap(
                user_id=user_id,
                roadmap_id=roadmap_id,
                limit=limit,
                offset=offset,
            )
    
    return {
        "notes": [
            LearningNoteResponse(
                note_id=n.note_id,
                user_id=n.user_id,
                roadmap_id=n.roadmap_id,
                concept_id=n.concept_id,
                title=n.title,
                content=n.content,
                source=n.source,
                tags=n.tags or [],
                created_at=n.created_at.isoformat(),
                updated_at=n.updated_at.isoformat(),
            )
            for n in notes
        ],
        "total": len(notes),
    }


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    user_id: str = Query(..., description="用户ID"),
    repo_factory: RepositoryFactory = Depends(get_repo_factory),
) -> dict:
    """
    删除学习笔记
    
    Args:
        note_id: 笔记ID
        user_id: 用户ID（用于权限验证）
        
    Returns:
        删除结果
    """
    async with repo_factory.create_session() as session:
        note_repo = repo_factory.create_note_repo(session)
        
        # 验证笔记是否属于该用户
        note = await note_repo.get_note(note_id)
        if not note:
            raise HTTPException(status_code=404, detail="笔记不存在")
        if note.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权删除该笔记")
        
        success = await note_repo.delete_note(note_id)
        await session.commit()
    
    return {"success": success, "message": "笔记已删除" if success else "删除失败"}
