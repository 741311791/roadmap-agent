"""
技术栈能力测试服务

功能：
- TechAssessmentService: 封装技术栈测评的CRUD操作
- evaluate_answers: 计算加权分数和判定能力级别

注意：Agent实现请参考：
- app.agents.tech_assessment_generator.TechAssessmentGenerator
- app.agents.tech_capability_analyzer.TechCapabilityAnalyzer
"""
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
import structlog

from app.crud.crud_tech_assessment import get_tech_assessment_crud
from app.models.database import UserProfile, beijing_now

logger = structlog.get_logger()


class TechAssessmentService:
    """
    技术栈能力测试服务类
    
    封装技术栈测评相关的业务逻辑，主要负责：
    - 题库查询与管理
    - 能力分析结果保存到用户画像
    """
    
    def __init__(self):
        """初始化服务"""
        self.crud = get_tech_assessment_crud()
    
    async def get_available_technologies(self, session: AsyncSession) -> List[str]:
        """
        获取所有有测验题目的技术栈列表
        
        Args:
            session: 数据库会话
            
        Returns:
            技术栈名称列表（已排序）
        """
        return await self.crud.get_available_technologies(session)
    
    async def technology_exists(self, session: AsyncSession, technology: str) -> bool:
        """
        检查某个技术栈是否已有题库（至少一个级别）
        
        Args:
            session: 数据库会话
            technology: 技术栈名称
            
        Returns:
            是否存在
        """
        return await self.crud.technology_exists(session, technology)
    
    async def get_assessment(
        self, session: AsyncSession, technology: str, proficiency_level: str
    ):
        """
        获取指定技术栈和级别的题库
        
        Args:
            session: 数据库会话
            technology: 技术栈名称
            proficiency_level: 能力级别
            
        Returns:
            题库对象（TechStackAssessment）
        """
        return await self.crud.get_by_tech_and_level(session, technology, proficiency_level)
    
    async def get_assessments_by_levels(
        self, session: AsyncSession, technology: str
    ) -> Dict[str, Any]:
        """
        获取指定技术栈的所有级别题库（beginner, intermediate, expert）
        
        Args:
            session: 数据库会话
            technology: 技术栈名称
            
        Returns:
            {
                "beginner": TechStackAssessment,
                "intermediate": TechStackAssessment,
                "expert": TechStackAssessment
            }
            
        Raises:
            ValueError: 如果任何级别的题库不存在
        """
        levels = ["beginner", "intermediate", "expert"]
        result = {}
        
        for level in levels:
            assessment = await self.crud.get_by_tech_and_level(session, technology, level)
            if not assessment:
                raise ValueError(
                    f"Assessment for {technology} at {level} level not found. "
                    "Please generate it first."
                )
            result[level] = assessment
        
        return result
    
    async def create_assessment(
        self,
        session: AsyncSession,
        assessment_id: str,
        technology: str,
        proficiency_level: str,
        questions: List[dict],
        total_questions: int,
    ):
        """
        创建新的技术栈测评题库
        
        Args:
            session: 数据库会话
            assessment_id: 题库ID
            technology: 技术栈名称
            proficiency_level: 能力级别
            questions: 题目列表
            total_questions: 总题目数
            
        Returns:
            创建的题库对象
        """
        return await self.crud.create_assessment(
            session=session,
            assessment_id=assessment_id,
            technology=technology,
            proficiency_level=proficiency_level,
            questions=questions,
            total_questions=total_questions,
        )
    
    async def save_capability_analysis_to_profile(
        self,
        session: AsyncSession,
        user_id: str,
        technology: str,
        proficiency: str,
        analysis_result: Dict[str, Any],
    ) -> None:
        """
        将能力分析结果保存到用户画像的tech_stack字段
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            technology: 技术栈名称
            proficiency: 能力级别
            analysis_result: 能力分析结果
        """
        # 构建技术栈能力数据
        tech_capability = {
            "technology": technology,
            "proficiency": proficiency,
            "verified_level": analysis_result.get("proficiency_verification", {}).get("verified_level"),
            "confidence": analysis_result.get("proficiency_verification", {}).get("confidence"),
            "overall_assessment": analysis_result.get("overall_assessment"),
            "strengths": analysis_result.get("strengths", []),
            "weaknesses": analysis_result.get("weaknesses", []),
            "knowledge_gaps": analysis_result.get("knowledge_gaps", []),
            "learning_suggestions": analysis_result.get("learning_suggestions", []),
            "score_breakdown": analysis_result.get("score_breakdown", {}),
            "assessed_at": beijing_now().isoformat(),
        }
        
        # 查询用户画像
        result = await session.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            # 更新已有的tech_stack数据
            tech_stack = profile.tech_stack or []
            
            # 查找是否已有该技术栈的记录
            existing_index = None
            for i, item in enumerate(tech_stack):
                if item.get("technology") == technology:
                    existing_index = i
                    break
            
            # 更新或添加
            if existing_index is not None:
                tech_stack[existing_index] = tech_capability
            else:
                tech_stack.append(tech_capability)
            
            # 执行更新
            await session.execute(
                update(UserProfile)
                .where(UserProfile.user_id == user_id)
                .values(
                    tech_stack=tech_stack,
                    updated_at=beijing_now()
                )
            )
        else:
            # 创建新的用户画像
            stmt = insert(UserProfile).values(
                user_id=user_id,
                tech_stack=[tech_capability],
                created_at=beijing_now(),
                updated_at=beijing_now(),
            )
            await session.execute(stmt)
        # ✅ 不需要手动 commit，由调用方的事务上下文自动处理
        # Service 层不应该包含 commit 逻辑
        
        logger.info(
            "tech_capability_saved_to_profile",
            user_id=user_id,
            technology=technology,
            proficiency=proficiency,
        )


def evaluate_answers(questions: List[dict], answers: List[str]) -> Dict[str, Any]:
    """
    计算加权分数并给出评估建议（基于 proficiency_level）

    评分标准：
    - Beginner题: 1分
    - Intermediate题: 2分
    - Expert题: 3分
    - 总分根据题目分布动态计算

    判定逻辑：
    - ≥80%: confirmed - 确认当前级别
    - 60-79%: adjust - 建议保持当前级别，加强学习
    - <60%: downgrade - 建议降低级别

    Args:
        questions: 题目列表（每个题目包含 proficiency_level 和 correct_answer）
        answers: 用户的答案列表

    Returns:
        {
            "score": 31,
            "max_score": 40,
            "percentage": 77.5,
            "correct_count": 15,
            "total_questions": 20,
            "recommendation": "adjust",
            "message": "建议保持当前级别，加强薄弱环节的学习",
            "level_stats": {
                "beginner": {"correct": 3, "total": 4},
                "intermediate": {"correct": 10, "total": 12},
                "expert": {"correct": 2, "total": 4}
            }
        }
    """
    if len(questions) != len(answers):
        raise ValueError(f"Questions count ({len(questions)}) != Answers count ({len(answers)})")

    score = 0
    correct_count = 0
    
    # 统计各级别的答题情况
    level_stats = {
        "beginner": {"correct": 0, "total": 0},
        "intermediate": {"correct": 0, "total": 0},
        "expert": {"correct": 0, "total": 0},
    }

    # 计算分数
    for question, answer in zip(questions, answers):
        correct_answer = question.get("correct_answer")
        level = question.get("proficiency_level", "intermediate")
        
        # 统计该级别题目总数
        if level in level_stats:
            level_stats[level]["total"] += 1

        # 判断答案是否正确
        is_correct = False
        if isinstance(correct_answer, list):
            # 多选题：答案必须完全匹配
            if isinstance(answer, list):
                is_correct = set(answer) == set(correct_answer)
            else:
                is_correct = False
        else:
            # 单选题或判断题
            is_correct = str(answer) == str(correct_answer)

        if is_correct:
            correct_count += 1
            
            # 统计该级别答对数
            if level in level_stats:
                level_stats[level]["correct"] += 1
            
            # 根据级别加分
            if level == "beginner":
                score += 1
            elif level == "intermediate":
                score += 2
            else:  # expert
                score += 3

    # 计算最大分数（根据题目分布）
    max_score = sum(
        stats["total"] * (1 if level == "beginner" else 2 if level == "intermediate" else 3)
        for level, stats in level_stats.items()
    )
    
    # 计算百分比
    percentage = (score / max_score) * 100 if max_score > 0 else 0

    # 判定建议
    if percentage >= 80:
        recommendation = "confirmed"
        message = "Your ability matches the current level, continue to maintain!"
    elif percentage >= 60:
        recommendation = "adjust"
        message = "It is recommended to keep the current level and strengthen the learning of薄弱环节"
    else:
        recommendation = "downgrade"
        message = "It is recommended to choose a more basic level and gradually improve your ability"

    result = {
        "score": score,
        "max_score": max_score,
        "percentage": round(percentage, 1),
        "correct_count": correct_count,
        "total_questions": len(questions),
        "recommendation": recommendation,
        "message": message,
        "level_stats": level_stats,
    }
    
    logger.info(
        "tech_assessment_evaluated",
        score=score,
        max_score=max_score,
        percentage=result["percentage"],
        correct_count=correct_count,
        total_questions=len(questions),
        recommendation=recommendation,
        level_stats=level_stats,
    )
    
    return result
