"""
技术栈测验题初始化异步任务

将测验题生成从同步启动流程迁移到Celery异步任务，避免阻塞应用启动。
"""
import asyncio
from typing import Dict, Any
import structlog
from celery import group

from app.core.celery_app import celery_app
from app.tasks.utils import run_async
from app.db.celery_session import get_celery_session
from app.crud.crud_tech_assessment import get_tech_assessment_crud
from app.agents.tech_assessment_generator import TechAssessmentGenerator

logger = structlog.get_logger()

# 支持的技术栈列表（与前端TECHNOLOGIES保持一致）
TECHNOLOGIES = [
    'python',
    'javascript',
    'typescript',
    'nodejs',
    'sql',
    'docker'
]

# 能力级别列表
PROFICIENCY_LEVELS = ['beginner', 'intermediate', 'expert']


@celery_app.task(
    name="assessment_init.check_and_trigger",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
)
def check_and_trigger_assessment_generation(self) -> Dict[str, Any]:
    """
    检查数据库中的测验题，触发缺失题目的生成任务
    
    此任务在应用启动时触发，检查哪些题目缺失，然后并行启动生成任务。
    
    Returns:
        初始化结果摘要
    """
    return run_async(_check_and_trigger_assessment_generation_async())


async def _check_and_trigger_assessment_generation_async() -> Dict[str, Any]:
    """异步实现：检查并触发测验题生成"""
    logger.info("assessment_init_check_started")
    
    total_expected = len(TECHNOLOGIES) * len(PROFICIENCY_LEVELS)
    
    try:
        # 使用上下文管理器获取数据库会话
        async with get_celery_session() as db:
            tech_crud = get_tech_assessment_crud()
            
            # 批量查询已存在的 (technology, level) 组合
            existing_combinations = await tech_crud.get_existing_combinations(db)
            existing_count = len(existing_combinations)
            
            logger.info(
                "assessment_init_existing_check_completed",
                existing_count=existing_count,
                total_expected=total_expected,
            )
            
            # 构建需要生成的组合列表
            missing_combinations = [
                (tech, level)
                for tech in TECHNOLOGIES
                for level in PROFICIENCY_LEVELS
                if (tech, level) not in existing_combinations
            ]
            
            if not missing_combinations:
                logger.info("assessment_init_all_exist_skip_generation")
                return {
                    "total_expected": total_expected,
                    "existing": existing_count,
                    "missing": 0,
                    "tasks_triggered": 0,
                    "success": True,
                }
            
            logger.info(
                "assessment_init_missing_found_triggering_tasks",
                missing_count=len(missing_combinations),
                missing=missing_combinations,
            )
            
            # 并行触发所有缺失题目的生成任务
            # 使用Celery的group原语实现并行执行
            job = group(
                generate_single_assessment.s(tech, level)
                for tech, level in missing_combinations
            )
            result = job.apply_async()
            
            logger.info(
                "assessment_init_tasks_triggered",
                missing_count=len(missing_combinations),
                group_id=result.id,
            )
            
            return {
                "total_expected": total_expected,
                "existing": existing_count,
                "missing": len(missing_combinations),
                "tasks_triggered": len(missing_combinations),
                "group_id": result.id,
                "success": True,
            }
    
    except Exception as e:
        logger.error(
            "assessment_init_check_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "total_expected": total_expected,
            "existing": 0,
            "missing": 0,
            "tasks_triggered": 0,
            "success": False,
            "error": str(e),
        }


@celery_app.task(
    name="assessment_init.generate_single",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    # 单个题目生成可能需要较长时间（多次LLM调用）
    time_limit=1800,  # 30分钟硬超时
    soft_time_limit=1680,  # 28分钟软超时
    # 失败后重试3次
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},  # 重试间隔60秒
)
def generate_single_assessment(
    self,
    technology: str,
    proficiency_level: str
) -> Dict[str, Any]:
    """
    生成单个技术栈测验题目集
    
    Args:
        technology: 技术栈名称
        proficiency_level: 能力级别
        
    Returns:
        生成结果
    """
    return run_async(_generate_single_assessment_async(technology, proficiency_level))


async def _generate_single_assessment_async(
    technology: str,
    proficiency_level: str
) -> Dict[str, Any]:
    """异步实现：生成单个技术栈测验题目集"""
    logger.info(
        "generating_single_tech_assessment",
        technology=technology,
        proficiency_level=proficiency_level,
    )
    
    try:
        # 使用上下文管理器获取数据库会话
        async with get_celery_session() as db:
            tech_crud = get_tech_assessment_crud()
            
            # 再次检查是否已存在（避免并发重复生成）
            existing = await tech_crud.get_assessment(
                db,
                technology=technology,
                proficiency_level=proficiency_level,
            )
            
            if existing:
                logger.info(
                    "assessment_already_exists_skip_generation",
                    technology=technology,
                    proficiency_level=proficiency_level,
                )
                return {
                    "technology": technology,
                    "proficiency_level": proficiency_level,
                    "status": "skipped",
                    "reason": "already_exists",
                }
            
            # 创建生成器并生成题目
            generator = TechAssessmentGenerator()
            assessment_data = await generator.generate_assessment_with_plan(
                technology,
                proficiency_level
            )
            
            # 保存到数据库
            await tech_crud.create_assessment(
                db,
                assessment_id=assessment_data["assessment_id"],
                technology=technology,
                proficiency_level=proficiency_level,
                questions=assessment_data["questions"],
                total_questions=assessment_data["total_questions"],
            )
            
            logger.info(
                "tech_assessment_generated_and_saved",
                technology=technology,
                proficiency_level=proficiency_level,
                total_questions=assessment_data["total_questions"],
            )
            
            return {
                "technology": technology,
                "proficiency_level": proficiency_level,
                "status": "success",
                "total_questions": assessment_data["total_questions"],
                "assessment_id": assessment_data["assessment_id"],
            }
    
    except Exception as e:
        logger.error(
            "tech_assessment_generation_failed",
            technology=technology,
            proficiency_level=proficiency_level,
            error=str(e),
            error_type=type(e).__name__,
        )
        # 异常会被safe_task捕获并记录，同时触发Celery重试机制
        raise


@celery_app.task(
    name="assessment_init.get_progress",
    bind=True,
    ignore_result=False,  # 需要返回结果供API查询
)
def get_initialization_progress(self) -> Dict[str, Any]:
    """
    获取测验题初始化进度
    
    Returns:
        进度信息
    """
    return run_async(_get_initialization_progress_async())


async def _get_initialization_progress_async() -> Dict[str, Any]:
    """异步实现：获取测验题初始化进度"""
    total_expected = len(TECHNOLOGIES) * len(PROFICIENCY_LEVELS)
    
    try:
        # 使用上下文管理器获取数据库会话
        async with get_celery_session() as db:
            tech_crud = get_tech_assessment_crud()
            existing_combinations = await tech_crud.get_existing_combinations(db)
            existing_count = len(existing_combinations)
            
            progress_percentage = (existing_count / total_expected) * 100
            
            return {
                "total_expected": total_expected,
                "completed": existing_count,
                "missing": total_expected - existing_count,
                "progress_percentage": round(progress_percentage, 2),
                "is_complete": existing_count == total_expected,
            }
    
    except Exception as e:
        logger.error(
            "assessment_init_progress_query_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "total_expected": total_expected,
            "completed": 0,
            "missing": total_expected,
            "progress_percentage": 0.0,
            "is_complete": False,
            "error": str(e),
        }

