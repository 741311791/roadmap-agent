"""
重置技术栈能力测试题库

功能：
1. 清空现有题库
2. 使用新的 Plan & Execute 模式重新生成题库
3. 为 6 个技术栈的 3 个级别生成题目

使用方法:
    cd backend
    uv run python scripts/reset_assessment_pool.py
"""
import asyncio
import structlog

from app.db.session import get_db
from app.db.repositories.tech_assessment_repo import TechAssessmentRepository
from app.services.tech_assessment_generator import TechAssessmentGenerator

logger = structlog.get_logger()

# 技术栈列表（缩减后的6个）
TECHNOLOGIES = ['python', 'javascript', 'typescript', 'nodejs', 'sql', 'docker']
PROFICIENCY_LEVELS = ['beginner', 'intermediate', 'expert']


async def reset_and_regenerate():
    """清空题库并重新生成"""
    logger.info("assessment_pool_reset_started")
    
    # 获取数据库会话
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        repo = TechAssessmentRepository(db)
        
        # Step 1: 清空现有题库
        deleted_count = await repo.delete_all_assessments()
        logger.info("existing_assessments_deleted", count=deleted_count)
        
        # Step 2: 重新生成
        generator = TechAssessmentGenerator()
        total = len(TECHNOLOGIES) * len(PROFICIENCY_LEVELS)
        completed = 0
        failed = 0
        
        for tech in TECHNOLOGIES:
            for level in PROFICIENCY_LEVELS:
                try:
                    logger.info(
                        "generating_assessment",
                        technology=tech,
                        level=level,
                        progress=f"{completed}/{total}"
                    )
                    
                    # 使用 Plan & Execute 模式生成
                    assessment_data = await generator.generate_assessment_with_plan(
                        technology=tech,
                        proficiency_level=level,
                    )
                    
                    # 保存到数据库
                    await repo.create_assessment(
                        assessment_id=assessment_data["assessment_id"],
                        technology=tech,
                        proficiency_level=level,
                        questions=assessment_data["questions"],
                        total_questions=assessment_data["total_questions"],
                    )
                    
                    completed += 1
                    logger.info(
                        "assessment_generated",
                        technology=tech,
                        level=level,
                        total_questions=assessment_data["total_questions"],
                    )
                    
                    # 避免API限流
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    failed += 1
                    logger.error(
                        "generation_failed",
                        technology=tech,
                        level=level,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
        
        logger.info(
            "assessment_pool_reset_completed", 
            completed=completed, 
            failed=failed,
            total=total
        )
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(reset_and_regenerate())
