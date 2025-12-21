"""
启动时检查并初始化技术栈测验数据

在应用启动时调用，检查数据库是否已有60组题目（20技术×3级别）
如果缺失，则通过LLM生成并保存
"""
import asyncio
from typing import List, Dict, Any
import structlog

from app.db.session import get_db
from app.db.repositories.tech_assessment_repo import TechAssessmentRepository
from app.services.tech_assessment_generator import TechAssessmentGenerator

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


async def initialize_tech_assessments() -> Dict[str, Any]:
    """
    检查并生成缺失的测验题目
    
    Returns:
        初始化结果摘要
    """
    logger.info("tech_assessments_initialization_started")
    
    total_expected = len(TECHNOLOGIES) * len(PROFICIENCY_LEVELS)
    generated_count = 0
    existing_count = 0
    failed_count = 0
    failed_items = []
    
    try:
        # 获取数据库会话
        db_gen = get_db()
        db = await db_gen.__anext__()
        
        try:
            repo = TechAssessmentRepository(db)
            generator = TechAssessmentGenerator()
            
            # 检查每个技术栈的每个级别
            for tech in TECHNOLOGIES:
                for level in PROFICIENCY_LEVELS:
                    try:
                        # 检查是否已存在
                        exists = await repo.assessment_exists(tech, level)
                        
                        if exists:
                            logger.debug(
                                "tech_assessment_exists",
                                technology=tech,
                                proficiency_level=level,
                            )
                            existing_count += 1
                        else:
                            logger.info(
                                "generating_tech_assessment",
                                technology=tech,
                                proficiency_level=level,
                            )
                            
                            # 使用新的 Plan & Execute 模式生成题目
                            assessment_data = await generator.generate_assessment_with_plan(tech, level)
                            
                            # 保存到数据库（已移除 easy_count, medium_count, hard_count）
                            await repo.create_assessment(
                                assessment_id=assessment_data["assessment_id"],
                                technology=tech,
                                proficiency_level=level,
                                questions=assessment_data["questions"],
                                total_questions=assessment_data["total_questions"],
                            )
                            
                            generated_count += 1
                            
                            logger.info(
                                "tech_assessment_generated_and_saved",
                                technology=tech,
                                proficiency_level=level,
                                total_questions=assessment_data["total_questions"],
                            )
                            
                            # 避免API限流，每生成一个休息1秒
                            await asyncio.sleep(1)
                    
                    except Exception as e:
                        # 回滚当前事务，避免影响后续操作
                        await db.rollback()
                        
                        logger.error(
                            "tech_assessment_generation_failed",
                            technology=tech,
                            proficiency_level=level,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        failed_count += 1
                        failed_items.append(f"{tech}-{level}")
                        # 继续处理下一个
                        continue
            
            result = {
                "total_expected": total_expected,
                "existing": existing_count,
                "generated": generated_count,
                "failed": failed_count,
                "failed_items": failed_items,
                "success": failed_count == 0,
            }
            
            logger.info(
                "tech_assessments_initialization_completed",
                total_expected=total_expected,
                existing=existing_count,
                generated=generated_count,
                failed=failed_count,
            )
            
            return result
            
        finally:
            # 关闭数据库会话
            await db.close()
    
    except Exception as e:
        logger.error(
            "tech_assessments_initialization_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return {
            "total_expected": total_expected,
            "existing": 0,
            "generated": 0,
            "failed": total_expected,
            "failed_items": ["initialization_error"],
            "success": False,
            "error": str(e),
        }

