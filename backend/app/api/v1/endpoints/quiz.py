"""
测验管理相关端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository

router = APIRouter(prefix="/roadmaps", tags=["quiz"])
logger = structlog.get_logger()


@router.get("/{roadmap_id}/concepts/{concept_id}/quiz")
async def get_concept_quiz(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的测验
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        db: 数据库会话
        
    Returns:
        测验数据，包含题目列表
        
    Raises:
        HTTPException: 404 - 概念没有测验
        
    Example:
        ```json
        {
            "roadmap_id": "python-web-dev-2024",
            "concept_id": "flask-basics",
            "quiz_id": "quiz-001",
            "questions": [
                {
                    "question": "Flask是什么类型的框架？",
                    "options": ["Web框架", "数据分析框架", "游戏框架", "GUI框架"],
                    "correct_answer": 0,
                    "explanation": "Flask是一个轻量级的Python Web框架",
                    "difficulty": "easy"
                },
                ...
            ],
            "total_questions": 10,
            "easy_count": 3,
            "medium_count": 5,
            "hard_count": 2,
            "generated_at": "2024-01-01T00:00:00Z"
        }
        ```
    """
    repo = RoadmapRepository(db)
    
    quiz = await repo.get_quiz_by_concept(concept_id, roadmap_id)
    
    if not quiz:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有测验"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "quiz_id": quiz.quiz_id,
        "questions": quiz.questions,
        "total_questions": quiz.total_questions,
        "easy_count": quiz.easy_count,
        "medium_count": quiz.medium_count,
        "hard_count": quiz.hard_count,
        "generated_at": quiz.generated_at.isoformat() if quiz.generated_at else None,
    }
