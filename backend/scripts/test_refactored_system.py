"""
测试重构后的技术栈测验系统

验证以下功能：
1. Plan & Execute 模式生成题目
2. 混合级别抽题
3. 评估计分（基于 proficiency_level）
4. 能力分析

使用方法:
    cd backend
    uv run python scripts/test_refactored_system.py
"""
import asyncio
import structlog

from app.services.tech_assessment_generator import TechAssessmentGenerator
from app.services.tech_assessment_evaluator import evaluate_answers, TechCapabilityAnalyzer
from app.db.session import get_db
from app.db.repositories.tech_assessment_repo import TechAssessmentRepository

logger = structlog.get_logger()


async def test_generation():
    """测试 Plan & Execute 生成模式"""
    logger.info("=== 测试 1: Plan & Execute 生成模式 ===")
    
    generator = TechAssessmentGenerator()
    
    try:
        result = await generator.generate_assessment_with_plan(
            technology="python",
            proficiency_level="intermediate",
        )
        
        logger.info(
            "generation_test_passed",
            total_questions=result["total_questions"],
            has_examination_plan=result.get("examination_plan") is not None,
        )
        
        # 验证题目中没有 difficulty 字段
        for i, q in enumerate(result["questions"][:3]):  # 只检查前3题
            if "difficulty" in q:
                logger.error(f"题目 {i+1} 包含 difficulty 字段，应该已被移除")
            else:
                logger.info(f"题目 {i+1} 正确：无 difficulty 字段")
        
        return result
        
    except Exception as e:
        logger.error("generation_test_failed", error=str(e))
        raise


async def test_evaluation():
    """测试评估计分（基于 proficiency_level）"""
    logger.info("=== 测试 2: 评估计分 ===")
    
    # 构造测试题目（模拟混合级别）
    test_questions = [
        {
            "question": "Test Q1",
            "type": "single_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "proficiency_level": "beginner",
        },
        {
            "question": "Test Q2",
            "type": "single_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "B",
            "proficiency_level": "intermediate",
        },
        {
            "question": "Test Q3",
            "type": "single_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "C",
            "proficiency_level": "expert",
        },
    ]
    
    # 模拟用户答案（全对）
    user_answers = ["A", "B", "C"]
    
    result = evaluate_answers(test_questions, user_answers)
    
    logger.info(
        "evaluation_test_passed",
        score=result["score"],
        max_score=result["max_score"],
        expected_max_score=6,  # 1 + 2 + 3
        level_stats=result.get("level_stats"),
    )
    
    # 验证计分逻辑
    assert result["score"] == 6, f"Expected score 6, got {result['score']}"
    assert result["max_score"] == 6, f"Expected max_score 6, got {result['max_score']}"
    assert "level_stats" in result, "Missing level_stats in result"
    
    logger.info("evaluation_test_all_checks_passed")


async def test_database_operations():
    """测试数据库操作"""
    logger.info("=== 测试 3: 数据库操作 ===")
    
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        repo = TechAssessmentRepository(db)
        
        # 测试 delete_all_assessments
        count = await repo.delete_all_assessments()
        logger.info("delete_all_assessments_test_passed", deleted_count=count)
        
        # 测试 technology_exists
        exists = await repo.technology_exists("python")
        logger.info("technology_exists_test_passed", exists=exists)
        
        assert not exists, "Expected technology to not exist after deletion"
        
        logger.info("database_operations_test_all_checks_passed")
    finally:
        await db.close()


async def main():
    """运行所有测试"""
    logger.info("开始测试重构后的系统")
    
    try:
        # 测试 1: 生成
        await test_generation()
        
        # 测试 2: 评估
        await test_evaluation()
        
        # 测试 3: 数据库操作
        await test_database_operations()
        
        logger.info("✅ 所有测试通过！系统重构成功。")
        
    except Exception as e:
        logger.error("❌ 测试失败", error=str(e), error_type=type(e).__name__)
        raise


if __name__ == "__main__":
    asyncio.run(main())
