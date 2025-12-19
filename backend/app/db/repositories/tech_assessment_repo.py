"""
技术栈能力测试 Repository

负责 TechStackAssessment 表的数据访问操作。
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.database import TechStackAssessment
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class TechAssessmentRepository(BaseRepository[TechStackAssessment]):
    """
    技术栈能力测试数据访问层
    
    管理技术栈测验题目的数据库操作。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TechStackAssessment)
    
    async def get_assessment(
        self,
        technology: str,
        proficiency_level: str,
    ) -> Optional[TechStackAssessment]:
        """
        获取指定技术栈和级别的测验题目
        
        Args:
            technology: 技术栈名称 (python, react等)
            proficiency_level: 能力级别 (beginner, intermediate, expert)
            
        Returns:
            测验记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(TechStackAssessment).where(
                and_(
                    TechStackAssessment.technology == technology,
                    TechStackAssessment.proficiency_level == proficiency_level,
                )
            )
        )
        
        assessment = result.scalar_one_or_none()
        
        if assessment:
            logger.debug(
                "tech_assessment_found",
                technology=technology,
                proficiency_level=proficiency_level,
                total_questions=assessment.total_questions,
            )
        else:
            logger.debug(
                "tech_assessment_not_found",
                technology=technology,
                proficiency_level=proficiency_level,
            )
        
        return assessment
    
    async def assessment_exists(
        self,
        technology: str,
        proficiency_level: str,
    ) -> bool:
        """
        检查测验是否已存在
        
        Args:
            technology: 技术栈名称
            proficiency_level: 能力级别
            
        Returns:
            是否存在
        """
        assessment = await self.get_assessment(technology, proficiency_level)
        return assessment is not None
    
    async def create_assessment(
        self,
        assessment_id: str,
        technology: str,
        proficiency_level: str,
        questions: list,
        total_questions: int,
    ) -> TechStackAssessment:
        """
        创建新的测验记录
        
        Args:
            assessment_id: 测验ID (UUID)
            technology: 技术栈名称
            proficiency_level: 能力级别
            questions: 题目列表
            total_questions: 题目总数
            
        Returns:
            创建的测验记录
        """
        assessment = TechStackAssessment(
            assessment_id=assessment_id,
            technology=technology,
            proficiency_level=proficiency_level,
            questions=questions,
            total_questions=total_questions,
        )
        
        self.session.add(assessment)
        await self.session.commit()
        await self.session.refresh(assessment)
        
        logger.info(
            "tech_assessment_created",
            assessment_id=assessment_id,
            technology=technology,
            proficiency_level=proficiency_level,
            total_questions=total_questions,
        )
        
        return assessment
    
    async def list_all_assessments(self) -> List[TechStackAssessment]:
        """
        列出所有测验记录
        
        Returns:
            所有测验记录列表
        """
        result = await self.session.execute(
            select(TechStackAssessment).order_by(
                TechStackAssessment.technology,
                TechStackAssessment.proficiency_level,
            )
        )
        
        assessments = list(result.scalars().all())
        
        logger.debug(
            "tech_assessments_listed",
            count=len(assessments),
        )
        
        return assessments
    
    async def count_assessments(self) -> int:
        """
        统计测验记录总数
        
        Returns:
            记录总数
        """
        result = await self.session.execute(
            select(TechStackAssessment)
        )
        assessments = result.scalars().all()
        return len(list(assessments))
    
    async def delete_all_assessments(self) -> int:
        """
        清空所有测验记录
        
        Returns:
            删除的记录数
        """
        from sqlalchemy import delete
        
        result = await self.session.execute(select(TechStackAssessment))
        assessments = result.scalars().all()
        count = len(list(assessments))
        
        await self.session.execute(delete(TechStackAssessment))
        await self.session.commit()
        
        logger.info("all_tech_assessments_deleted", count=count)
        return count
    
    async def technology_exists(self, technology: str) -> bool:
        """
        检查某个技术栈是否已有题库（至少一个级别）
        
        Args:
            technology: 技术栈名称
            
        Returns:
            是否存在
        """
        result = await self.session.execute(
            select(TechStackAssessment).where(
                TechStackAssessment.technology == technology
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

