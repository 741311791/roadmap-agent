"""
学习进度 API 端点

提供 Concept 完成状态标记和 Quiz 答题记录功能。
"""
from typing import Annotated, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_session, get_current_user_id_flexible
from app.services.progress_service import ProgressService, get_progress_service
from app.models.domain import (
    ConceptProgressUpdate,
    ConceptProgressResponse,
    QuizAttemptCreate,
    QuizAttemptResponse
)

router = APIRouter(prefix="/progress", tags=["Progress"])

# 依赖注入
CurrentProgressService = Annotated[ProgressService, Depends(get_progress_service)]


@router.put(
    "/roadmaps/{roadmap_id}/concepts/{concept_id}",
    response_model=ConceptProgressResponse
)
async def update_concept_progress(
    roadmap_id: str,
    concept_id: str,
    payload: ConceptProgressUpdate,
    user_id: str = Depends(get_current_user_id_flexible),
    session: AsyncSession = Depends(get_current_session),
    service: CurrentProgressService = None,
):
    """
    标记/取消 Concept 完成状态
    
    - **is_completed=true**: 标记完成
    - **is_completed=false**: 取消完成
    """
    # 调用Service层
    progress = await service.update_concept_progress(
        session=session,
        user_id=user_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        is_completed=payload.is_completed,
    )
    await session.commit()
    
    return ConceptProgressResponse(
        concept_id=progress.concept_id,
        is_completed=progress.is_completed,
        completed_at=progress.completed_at
    )


@router.get(
    "/roadmaps/{roadmap_id}/concepts",
    response_model=List[ConceptProgressResponse]
)
async def get_roadmap_progress(
    roadmap_id: str,
    user_id: str = Depends(get_current_user_id_flexible),
    session: AsyncSession = Depends(get_current_session),
    service: CurrentProgressService = None,
):
    """获取某个路线图的所有Concept进度"""
    # 调用Service层
    progress_list = await service.get_roadmap_progress(
        session=session,
        user_id=user_id,
        roadmap_id=roadmap_id,
    )
    
    return [
        ConceptProgressResponse(
            concept_id=p.concept_id,
            is_completed=p.is_completed,
            completed_at=p.completed_at
        )
        for p in progress_list
    ]


@router.post(
    "/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz",
    response_model=QuizAttemptResponse
)
async def submit_quiz_attempt(
    roadmap_id: str,
    concept_id: str,
    payload: QuizAttemptCreate,
    user_id: str = Depends(get_current_user_id_flexible),
    session: AsyncSession = Depends(get_current_session),
    service: CurrentProgressService = None,
):
    """提交Quiz答题记录"""
    # 调用Service层
    attempt = await service.submit_quiz_attempt(
        session=session,
        user_id=user_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        quiz_id=payload.quiz_id,
        total_questions=payload.total_questions,
        correct_answers=payload.correct_answers,
        score_percentage=payload.score_percentage,
        incorrect_question_indices=payload.incorrect_question_indices,
    )
    await session.commit()
    
    return QuizAttemptResponse(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        concept_id=attempt.concept_id,
        total_questions=attempt.total_questions,
        correct_answers=attempt.correct_answers,
        score_percentage=attempt.score_percentage,
        incorrect_question_indices=attempt.incorrect_question_indices,
        attempted_at=attempt.attempted_at
    )
