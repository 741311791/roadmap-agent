"""
技术能力分析异步任务

将技术能力分析从同步API迁移到Celery异步任务，避免阻塞请求。
"""
from typing import Dict, Any
import structlog

from app.core.celery_app import celery_app
from app.tasks.utils import run_async
from app.db.celery_session import get_celery_session
from app.agents.tech_capability_analyzer import TechCapabilityAnalyzer
from app.services.learning.assessment_service import TechAssessmentService, evaluate_answers
from app.db.redis_client import redis_client

logger = structlog.get_logger()

# Redis缓存配置
ASSESSMENT_CACHE_PREFIX = "assessment:session:"
ANALYSIS_RESULT_PREFIX = "capability_analysis:result:"
ANALYSIS_RESULT_TTL = 86400  # 24小时过期


@celery_app.task(
    name="capability_analysis.analyze_tech_capability",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    max_retries=3,
)
def analyze_tech_capability_task(
    self,
    technology: str,
    proficiency: str,
    user_id: str,
    assessment_id: str,
    answers: list[str],
    save_to_profile: bool = True,
) -> Dict[str, Any]:
    """
    异步分析用户的技术栈能力
    
    Args:
        technology: 技术栈名称
        proficiency: 能力级别
        user_id: 用户ID
        assessment_id: 测验ID
        answers: 用户答案列表
        save_to_profile: 是否保存到用户画像
        
    Returns:
        分析结果摘要
    """
    logger.info(
        "capability_analysis_task_started",
        task_id=self.request.id,
        technology=technology,
        proficiency=proficiency,
        user_id=user_id,
        assessment_id=assessment_id,
    )
    
    try:
        result = run_async(
            _analyze_tech_capability_async(
                task_id=self.request.id,
                technology=technology,
                proficiency=proficiency,
                user_id=user_id,
                assessment_id=assessment_id,
                answers=answers,
                save_to_profile=save_to_profile,
            )
        )
        
        logger.info(
            "capability_analysis_task_completed",
            task_id=self.request.id,
            technology=technology,
            user_id=user_id,
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "capability_analysis_task_failed",
            task_id=self.request.id,
            technology=technology,
            user_id=user_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def _analyze_tech_capability_async(
    task_id: str,
    technology: str,
    proficiency: str,
    user_id: str,
    assessment_id: str,
    answers: list[str],
    save_to_profile: bool,
) -> Dict[str, Any]:
    """
    异步实现：技术能力分析
    
    流程：
    1. 从Redis获取测验题目
    2. 评估答案
    3. 使用LLM进行能力分析
    4. 保存结果到Redis
    5. （可选）保存到用户画像
    """
    # 从Redis缓存中获取测验题目
    cache_key = f"{ASSESSMENT_CACHE_PREFIX}{assessment_id}"
    questions = await redis_client.get_json(cache_key)
    
    if not questions:
        raise ValueError(f"Assessment session not found or expired: {assessment_id}")
    
    # 验证答案数量
    if len(answers) != len(questions):
        raise ValueError(
            f"Expected {len(questions)} answers, got {len(answers)}"
        )
    
    # 评估答案
    evaluation_result = evaluate_answers(questions, answers)
    
    logger.info(
        "capability_analysis_evaluation_completed",
        task_id=task_id,
        technology=technology,
        user_id=user_id,
        score=evaluation_result["score"],
        percentage=evaluation_result["percentage"],
    )
    
    # 使用LLM进行能力分析
    analyzer = TechCapabilityAnalyzer()
    analysis_result = await analyzer.analyze_capability(
        technology=technology,
        proficiency_level=proficiency,
        questions=questions,
        user_answers=answers,
        evaluation_result=evaluation_result,
    )
    
    logger.info(
        "capability_analysis_llm_completed",
        task_id=task_id,
        technology=technology,
        user_id=user_id,
        verified_level=analysis_result.get("proficiency_verification", {}).get("verified_level"),
    )
    
    # 保存结果到Redis（供前端查询）
    result_cache_key = f"{ANALYSIS_RESULT_PREFIX}{user_id}:{technology}:{proficiency}"
    await redis_client.set_json(
        result_cache_key,
        {
            "task_id": task_id,
            "technology": technology,
            "proficiency": proficiency,
            "user_id": user_id,
            "analysis_result": analysis_result,
            "status": "completed",
        },
        ex=ANALYSIS_RESULT_TTL,
    )
    
    logger.info(
        "capability_analysis_result_cached",
        task_id=task_id,
        cache_key=result_cache_key,
    )
    
    # 如果需要保存到用户画像
    if save_to_profile:
        async with get_celery_session() as db:
            service = TechAssessmentService()
            await service.save_capability_analysis_to_profile(
                session=db,
                user_id=user_id,
                technology=technology,
                proficiency=proficiency,
                analysis_result=analysis_result,
            )
            
            logger.info(
                "capability_analysis_saved_to_profile",
                task_id=task_id,
                user_id=user_id,
                technology=technology,
            )
    
    return {
        "status": "completed",
        "task_id": task_id,
        "technology": technology,
        "proficiency": proficiency,
        "user_id": user_id,
        "verified_level": analysis_result.get("proficiency_verification", {}).get("verified_level"),
    }


async def get_analysis_result(
    user_id: str,
    technology: str,
    proficiency: str,
) -> Dict[str, Any] | None:
    """
    获取能力分析结果（从Redis缓存）
    
    Args:
        user_id: 用户ID
        technology: 技术栈名称
        proficiency: 能力级别
        
    Returns:
        分析结果，如果不存在则返回None
    """
    result_cache_key = f"{ANALYSIS_RESULT_PREFIX}{user_id}:{technology}:{proficiency}"
    result = await redis_client.get_json(result_cache_key)
    
    if result:
        logger.debug(
            "capability_analysis_result_retrieved",
            user_id=user_id,
            technology=technology,
            proficiency=proficiency,
        )
    else:
        logger.debug(
            "capability_analysis_result_not_found",
            user_id=user_id,
            technology=technology,
            proficiency=proficiency,
        )
    
    return result
