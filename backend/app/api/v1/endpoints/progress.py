"""
学习进度 API 端点

提供 Concept 完成状态标记和 Quiz 答题记录功能。
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_db
from app.db.repositories.progress_repo import ProgressRepository
from app.models.domain import (
    ConceptProgressUpdate,
    ConceptProgressResponse,
    QuizAttemptCreate,
    QuizAttemptResponse
)

router = APIRouter(prefix="/progress", tags=["Progress"])


def get_user_id_from_header(x_user_id: str = Header(...)) -> str:
    """从请求头获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing user ID")
    return x_user_id


@router.put(
    "/roadmaps/{roadmap_id}/concepts/{concept_id}",
    response_model=ConceptProgressResponse
)
async def update_concept_progress(
    roadmap_id: str,
    concept_id: str,
    payload: ConceptProgressUpdate,
    user_id: str = Depends(get_user_id_from_header),
    db: AsyncSession = Depends(get_db)
):
    """
    标记/取消 Concept 完成状态
    
    - **is_completed=true**: 标记完成
    - **is_completed=false**: 取消完成
    """
    repo = ProgressRepository(db)
    progress = await repo.upsert_concept_progress(
        user_id=user_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        is_completed=payload.is_completed
    )
    
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
    user_id: str = Depends(get_user_id_from_header),
    db: AsyncSession = Depends(get_db)
):
    """获取某个路线图的所有Concept进度"""
    repo = ProgressRepository(db)
    progress_list = await repo.get_roadmap_progress(user_id, roadmap_id)
    
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
    user_id: str = Depends(get_user_id_from_header),
    db: AsyncSession = Depends(get_db)
):
    """提交Quiz答题记录"""
    repo = ProgressRepository(db)
    attempt = await repo.create_quiz_attempt(
        user_id=user_id,
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        quiz_id=payload.quiz_id,
        total_questions=payload.total_questions,
        correct_answers=payload.correct_answers,
        score_percentage=payload.score_percentage,
        incorrect_question_indices=payload.incorrect_question_indices
    )
    
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




