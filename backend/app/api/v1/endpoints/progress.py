"""
学习进度 API 端点

提供 Concept 完成状态标记和 Quiz 答题记录功能。

重构说明：
- ✅ 使用CurrentSessionTransaction自动管理事务
- ✅ 删除手动commit调用
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Annotated, List
from fastapi import APIRouter, Depends

from app.api.v1.deps import CurrentSessionTransaction, get_current_user_id_flexible
from app.services.progress_service import ProgressService, get_progress_service
from app.models.domain import (
    ConceptProgressUpdate,
    ConceptProgressResponse,
    QuizAttemptCreate,
    QuizAttemptResponse
)
from app.core.response_schema import ResponseSchemaModel, response_base

router = APIRouter(prefix="/progress", tags=["Progress"])

# 依赖注入
CurrentProgressService = Annotated[ProgressService, Depends(get_progress_service)]


@router.put(
    "/roadmaps/{roadmap_id}/concepts/{concept_id}",
    response_model=ResponseSchemaModel[ConceptProgressResponse]
)
async def update_concept_progress(
    roadmap_id: str,
    concept_id: str,
    payload: ConceptProgressUpdate,
    db: CurrentSessionTransaction,  # ✅ 写操作使用CurrentSessionTransaction
    user_id: str = Depends(get_current_user_id_flexible),
    service: CurrentProgressService = None,
) -> ResponseSchemaModel[ConceptProgressResponse]:
    """
    标记/取消 Concept 完成状态
    
    - **is_completed=true**: 标记完成
    - **is_completed=false**: 取消完成
    
    Args:
        roadmap_id: 路线图ID
        concept_id: 概念ID
        payload: 进度更新请求
        db: 数据库会话（自动commit/rollback）
        user_id: 用户ID
        service: 进度服务
        
    Returns:
        更新后的进度信息
    """
    # 调用Service层
    progress = await service.update_concept_progress(
        session=db,
        user_id=user_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        is_completed=payload.is_completed,
    )
    
    # ✅ 自动 commit，无需手动调用
    
    return response_base.success(data=ConceptProgressResponse(
        concept_id=progress.concept_id,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at
    ))


@router.get(
    "/roadmaps/{roadmap_id}/concepts",
    response_model=ResponseSchemaModel[List[ConceptProgressResponse]]
)
async def get_roadmap_progress(
    roadmap_id: str,
    db: CurrentSessionTransaction,  # ✅ 使用CurrentSessionTransaction
    user_id: str = Depends(get_current_user_id_flexible),
    service: CurrentProgressService = None,
) -> ResponseSchemaModel[List[ConceptProgressResponse]]:
    """
    获取某个路线图的所有Concept进度
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        user_id: 用户ID
        service: 进度服务
        
    Returns:
        概念进度列表
    """
    # 调用Service层
    progress_list = await service.get_roadmap_progress(
        session=db,
        user_id=user_id,
        roadmap_id=roadmap_id,
    )
    
    return response_base.success(data=[
        ConceptProgressResponse(
            concept_id=p.concept_id,
            is_completed=p.is_completed,
            completed_at=p.completed_at
        )
        for p in progress_list
    ])


@router.post(
    "/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz",
    response_model=ResponseSchemaModel[QuizAttemptResponse]
)
async def submit_quiz_attempt(
    roadmap_id: str,
    concept_id: str,
    payload: QuizAttemptCreate,
    db: CurrentSessionTransaction,  # ✅ 写操作使用CurrentSessionTransaction
    user_id: str = Depends(get_current_user_id_flexible),
    service: CurrentProgressService = None,
) -> ResponseSchemaModel[QuizAttemptResponse]:
    """
    提交Quiz答题记录
    
    Args:
        roadmap_id: 路线图ID
        concept_id: 概念ID
        payload: 答题记录
        db: 数据库会话（自动commit/rollback）
        user_id: 用户ID
        service: 进度服务
        
    Returns:
        答题记录详情
    """
    # 调用Service层
    attempt = await service.submit_quiz_attempt(
        session=db,
        user_id=user_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        quiz_id=payload.quiz_id,
        total_questions=payload.total_questions,
        correct_answers=payload.correct_answers,
        score_percentage=payload.score_percentage,
        incorrect_question_indices=payload.incorrect_question_indices,
    )
    
    # ✅ 自动 commit
    
    return response_base.success(data=QuizAttemptResponse(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        concept_id=attempt.concept_id,
        total_questions=attempt.total_questions,
        correct_answers=attempt.correct_answers,
        score_percentage=attempt.score_percentage,
        incorrect_question_indices=attempt.incorrect_question_indices,
        attempted_at=attempt.attempted_at
    ))
