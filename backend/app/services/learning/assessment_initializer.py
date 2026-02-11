"""
启动时检查并初始化技术栈测验数据（非阻塞版本）

在应用启动时触发Celery异步任务，不阻塞应用启动。
先快速检查数据库，如果已全部生成则跳过Celery任务。
"""
from typing import Dict, Any
import structlog

logger = structlog.get_logger()

# 支持的技术栈列表（与任务保持一致）
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


async def initialize_tech_assessments() -> Dict[str, Any]:
    """
    非阻塞启动初始化：先检查是否已全部生成，未完成才触发Celery异步任务
    
    此函数在应用启动时调用，流程：
    1. 快速检查数据库中已存在的测验题数量
    2. 如果已全部生成，跳过Celery任务（避免不必要的任务调度开销）
    3. 如果有缺失，触发异步任务生成
    
    Returns:
        初始化结果摘要
    """
    logger.info("tech_assessments_initialization_check_started")
    
    total_expected = len(TECHNOLOGIES) * len(PROFICIENCY_LEVELS)
    
    try:
        # 快速检查数据库中已存在的测验题
        from app.db.session import async_session_maker
        from app.crud.crud_tech_assessment import get_tech_assessment_crud
        
        async with async_session_maker() as db:
            tech_crud = get_tech_assessment_crud()
            existing_combinations = await tech_crud.get_existing_combinations(db)
            existing_count = len(existing_combinations)
        
        logger.info(
            "tech_assessments_startup_check_completed",
            existing_count=existing_count,
            total_expected=total_expected,
        )
        
        # 如果已全部生成，跳过Celery任务
        if existing_count == total_expected:
            logger.info(
                "tech_assessments_all_exist_skip_celery",
                message="所有测验题已存在，跳过Celery任务生成",
            )
            return {
                "status": "complete",
                "total_expected": total_expected,
                "existing": existing_count,
                "missing": 0,
                "message": "All assessments already exist, skipped Celery task",
                "success": True,
            }
        
        # 有缺失，触发Celery异步任务
        missing_count = total_expected - existing_count
        logger.info(
            "tech_assessments_missing_found_triggering_celery",
            existing_count=existing_count,
            missing_count=missing_count,
        )
        
        # 导入Celery任务（延迟导入避免循环依赖）
        from app.tasks.assessment_initialization_tasks import (
            check_and_trigger_assessment_generation
        )
        
        # 触发异步任务（不等待结果）
        task = check_and_trigger_assessment_generation.apply_async()
        
        logger.info(
            "tech_assessments_initialization_task_triggered",
            task_id=task.id,
            existing_count=existing_count,
            missing_count=missing_count,
            message=f"发现 {missing_count} 个缺失的测验题，已提交Celery任务生成",
        )
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "total_expected": total_expected,
            "existing": existing_count,
            "missing": missing_count,
            "message": f"Triggered Celery task to generate {missing_count} missing assessments",
            "success": True,
        }
    
    except Exception as e:
        logger.error(
            "tech_assessments_initialization_check_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "status": "error",
            "message": f"Failed to check/trigger assessment initialization: {str(e)}",
            "success": False,
            "error": str(e),
        }

