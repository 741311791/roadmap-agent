"""
技术栈能力测试服务

负责处理:
- 技术栈题库管理
- 测验题目查询
- 用户画像更新
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.db.redis_client import redis_client
from app.crud.crud_tech_assessment import (
    TechAssessmentCRUD,
    UserProfileCRUD,
    get_tech_assessment_crud,
    get_user_profile_crud,
)
from app.models.database import TechStackAssessment, UserProfile, beijing_now

logger = structlog.get_logger()


class TechAssessmentService:
    """技术栈能力测试业务逻辑"""
    
    def __init__(self):
        self.tech_crud = get_tech_assessment_crud()
        self.profile_crud = get_user_profile_crud()
    
    async def get_available_technologies(self, session: AsyncSession) -> List[str]:
        """
        获取所有可用的技术栈列表
        
        Args:
            session: 数据库会话
            
        Returns:
            技术栈名称列表
        """
        technologies = await self.tech_crud.get_available_technologies(session)
        
        logger.info("available_technologies_fetched", count=len(technologies))
        
        return technologies
    
    async def get_assessment(
        self,
        session: AsyncSession,
        technology: str,
        proficiency: str,
    ) -> Optional[TechStackAssessment]:
        """
        获取指定技术栈和级别的测验
        
        Args:
            session: 数据库会话
            technology: 技术栈名称
            proficiency: 能力级别
            
        Returns:
            测验对象（如果存在）
        """
        assessment = await self.tech_crud.get_assessment(session, technology, proficiency)
        
        if assessment:
            logger.info(
                "assessment_fetched",
                technology=technology,
                proficiency=proficiency,
                questions_count=len(assessment.questions) if assessment.questions else 0,
            )
        
        return assessment
    
    async def get_assessments_by_levels(
        self,
        session: AsyncSession,
        technology: str,
    ) -> Dict[str, TechStackAssessment]:
        """
        获取指定技术栈的所有级别测验
        
        Args:
            session: 数据库会话
            technology: 技术栈名称
            
        Returns:
            {级别: 测验对象} 字典
            
        Raises:
            ValueError: 任一级别的测验缺失
        """
        assessments = {}
        
        for level in ["beginner", "intermediate", "expert"]:
            assessment = await self.tech_crud.get_assessment(session, technology, level)
            if not assessment:
                raise ValueError(f"Missing {level} assessment for {technology}")
            assessments[level] = assessment
        
        logger.info("assessments_by_levels_fetched", technology=technology, levels=3)
        
        return assessments
    
    async def technology_exists(
        self,
        session: AsyncSession,
        technology: str,
    ) -> bool:
        """
        检查指定技术栈是否存在题库
        
        Args:
            session: 数据库会话
            technology: 技术栈名称
            
        Returns:
            是否存在
        """
        exists = await self.tech_crud.technology_exists(session, technology)
        
        logger.info("technology_existence_checked", technology=technology, exists=exists)
        
        return exists
    
    async def create_assessment(
        self,
        session: AsyncSession,
        technology: str,
        proficiency: str,
        questions: List[Dict[str, Any]],
    ) -> TechStackAssessment:
        """
        创建技术栈测验
        
        Args:
            session: 数据库会话
            technology: 技术栈名称
            proficiency: 能力级别
            questions: 题目列表
            
        Returns:
            新创建的测验对象
        """
        import uuid
        assessment_id = str(uuid.uuid4())
        
        assessment = await self.tech_crud.create_assessment(
            session,
            assessment_id=assessment_id,
            technology=technology,
            proficiency_level=proficiency,
            questions=questions,
            total_questions=len(questions),
        )
        
        logger.info(
            "assessment_created",
            technology=technology,
            proficiency=proficiency,
            questions_count=len(questions),
        )
        
        return assessment
    
    async def save_capability_analysis_to_profile(
        self,
        session: AsyncSession,
        user_id: str,
        technology: str,
        proficiency: str,
        analysis_result: dict,
    ) -> None:
        """
        将能力分析结果保存到用户画像
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            technology: 技术栈名称
            proficiency: 能力级别
            analysis_result: 分析结果字典
        """
        # 获取或创建用户画像
        profile = await self.profile_crud.get_by_user_id(session, user_id)
        if not profile:
            profile_data = {
                "industry": "",
                "current_role": "",
                "tech_stack": [],
                "tech_assessments": [],
            }
            profile = await self.profile_crud.upsert_profile(session, user_id, profile_data)
        
        # 更新技术栈测评记录
        tech_assessments = profile.tech_assessments or []
        
        # 查找是否已有该技术栈的记录
        existing_idx = None
        for idx, assessment in enumerate(tech_assessments):
            if assessment.get("technology") == technology:
                existing_idx = idx
                break
        
        # 构建新的测评记录
        new_assessment = {
            "technology": technology,
            "proficiency": proficiency,
            "score": analysis_result.get("score", 0),
            "accuracy": analysis_result.get("accuracy", 0),
            "recommendation": analysis_result.get("recommendation"),
            "strengths": analysis_result.get("strengths", []),
            "weaknesses": analysis_result.get("weaknesses", []),
            "knowledge_gaps": analysis_result.get("knowledge_gaps", []),
            "learning_suggestions": analysis_result.get("learning_suggestions", []),
            "assessed_at": beijing_now().isoformat(),
        }
        
        if existing_idx is not None:
            # 更新现有记录
            tech_assessments[existing_idx] = new_assessment
        else:
            # 添加新记录
            tech_assessments.append(new_assessment)
        
        # 保存到数据库
        profile.tech_assessments = tech_assessments
        profile.updated_at = beijing_now()
        session.add(profile)
        await session.flush()
        
        logger.info(
            "capability_analysis_saved_to_profile",
            user_id=user_id,
            technology=technology,
            proficiency=proficiency,
            score=new_assessment["score"],
        )

