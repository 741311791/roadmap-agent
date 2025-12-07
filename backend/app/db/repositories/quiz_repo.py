"""
测验 Repository

负责 QuizMetadata 表的数据访问操作。

职责范围：
- 测验元数据的 CRUD 操作
- 测验查询（根据路线图、概念等）

不包含：
- 测验题目的生成逻辑（在 Agent 层）
- 测验评分和统计（在 Service 层）
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models.database import QuizMetadata
from app.models.domain import QuizGenerationOutput
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class QuizRepository(BaseRepository[QuizMetadata]):
    """
    测验数据访问层
    
    管理学习测验元数据。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, QuizMetadata)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_by_quiz_id(self, quiz_id: str) -> Optional[QuizMetadata]:
        """
        根据 quiz_id 查询测验元数据
        
        Args:
            quiz_id: 测验 ID
            
        Returns:
            测验元数据，如果不存在则返回 None
        """
        return await self.get_by_id(quiz_id)
    
    async def get_by_concept(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[QuizMetadata]:
        """
        获取指定概念的测验
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            测验元数据，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(QuizMetadata)
            .where(
                QuizMetadata.roadmap_id == roadmap_id,
                QuizMetadata.concept_id == concept_id,
            )
        )
        
        quiz = result.scalar_one_or_none()
        
        if quiz:
            logger.debug(
                "quiz_found",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                quiz_id=quiz.quiz_id,
                total_questions=quiz.total_questions,
            )
        
        return quiz
    
    async def list_by_roadmap(
        self,
        roadmap_id: str,
    ) -> List[QuizMetadata]:
        """
        获取路线图的所有测验
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            测验元数据列表
        """
        result = await self.session.execute(
            select(QuizMetadata)
            .where(QuizMetadata.roadmap_id == roadmap_id)
        )
        
        quizzes = list(result.scalars().all())
        
        logger.debug(
            "quizzes_listed_by_roadmap",
            roadmap_id=roadmap_id,
            count=len(quizzes),
        )
        
        return quizzes
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def save_quiz(
        self,
        quiz_output: QuizGenerationOutput,
        roadmap_id: str,
    ) -> QuizMetadata:
        """
        保存测验元数据（如果已存在则替换）
        
        Args:
            quiz_output: 测验生成输出
            roadmap_id: 路线图 ID
            
        Returns:
            保存的元数据记录
        """
        # 删除旧的测验记录（如果存在）
        await self.session.execute(
            delete(QuizMetadata)
            .where(
                QuizMetadata.roadmap_id == roadmap_id,
                QuizMetadata.concept_id == quiz_output.concept_id,
            )
        )
        
        # 统计难度分布
        easy_count = sum(1 for q in quiz_output.questions if q.difficulty == "easy")
        medium_count = sum(1 for q in quiz_output.questions if q.difficulty == "medium")
        hard_count = sum(1 for q in quiz_output.questions if q.difficulty == "hard")
        
        # 创建新记录
        metadata = QuizMetadata(
            quiz_id=quiz_output.quiz_id,
            concept_id=quiz_output.concept_id,
            roadmap_id=roadmap_id,
            questions=[q.model_dump() for q in quiz_output.questions],
            total_questions=quiz_output.total_questions,
            easy_count=easy_count,
            medium_count=medium_count,
            hard_count=hard_count,
            generated_at=quiz_output.generated_at,
        )
        
        await self.create(metadata, flush=True)
        
        logger.info(
            "quiz_metadata_saved",
            quiz_id=quiz_output.quiz_id,
            concept_id=quiz_output.concept_id,
            roadmap_id=roadmap_id,
            total_questions=quiz_output.total_questions,
        )
        
        return metadata
    
    async def save_quizzes_batch(
        self,
        quiz_refs: dict[str, QuizGenerationOutput],
        roadmap_id: str,
    ) -> List[QuizMetadata]:
        """
        批量保存测验元数据
        
        Args:
            quiz_refs: 测验字典（concept_id -> QuizGenerationOutput）
            roadmap_id: 路线图 ID
            
        Returns:
            保存的元数据记录列表
        """
        metadata_list = []
        
        for concept_id, quiz_output in quiz_refs.items():
            metadata = await self.save_quiz(quiz_output, roadmap_id)
            metadata_list.append(metadata)
        
        logger.info(
            "quizzes_metadata_saved_batch",
            roadmap_id=roadmap_id,
            count=len(metadata_list),
        )
        
        return metadata_list
    
    # ============================================================
    # 删除方法
    # ============================================================
    
    async def delete_quiz(self, quiz_id: str) -> bool:
        """
        删除测验元数据
        
        Args:
            quiz_id: 测验 ID
            
        Returns:
            True 如果删除成功，False 如果测验不存在
        """
        deleted = await self.delete_by_id(quiz_id)
        
        if deleted:
            logger.info("quiz_metadata_deleted", quiz_id=quiz_id)
        
        return deleted
    
    async def delete_quizzes_by_roadmap(self, roadmap_id: str) -> int:
        """
        删除路线图的所有测验
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            删除的记录数
        """
        result = await self.session.execute(
            delete(QuizMetadata)
            .where(QuizMetadata.roadmap_id == roadmap_id)
        )
        
        deleted_count = result.rowcount
        
        logger.info(
            "quizzes_deleted_by_roadmap",
            roadmap_id=roadmap_id,
            deleted_count=deleted_count,
        )
        
        return deleted_count
    
    async def delete_quiz_by_concept(
        self,
        roadmap_id: str,
        concept_id: str,
    ) -> bool:
        """
        删除指定概念的测验
        
        Args:
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            True 如果删除成功，False 如果测验不存在
        """
        result = await self.session.execute(
            delete(QuizMetadata)
            .where(
                QuizMetadata.roadmap_id == roadmap_id,
                QuizMetadata.concept_id == concept_id,
            )
        )
        
        deleted = result.rowcount > 0
        
        if deleted:
            logger.info(
                "quiz_deleted_by_concept",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
        
        return deleted
