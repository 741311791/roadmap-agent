"""测试单个教程生成"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.domain import Concept, TutorialGenerationInput, LearningPreferences
from app.agents.tutorial_generator import TutorialGeneratorAgent
import structlog

logger = structlog.get_logger()


async def test_single_tutorial():
    """测试生成单个教程"""
    # 创建一个测试概念
    concept = Concept(
        concept_id="test-concept-1",
        name="Python 基础语法",
        description="学习 Python 的基本语法规则",
        estimated_hours=2.0,
        prerequisites=[],
        difficulty="easy",
        keywords=["Python", "语法", "基础"],
    )
    
    # 创建上下文
    context = {
        "roadmap_id": "test-roadmap-001",
        "stage_id": "stage-1",
        "stage_name": "基础阶段",
        "module_id": "module-1",
        "module_name": "Python 入门",
    }
    
    # 创建用户偏好
    preferences = LearningPreferences(
        learning_goal="学习 Python 编程",
        available_hours_per_week=10,
        motivation="兴趣",
        current_level="beginner",
        career_background="学生",
        content_preference=["text", "interactive"],
    )
    
    # 创建生成输入
    generation_input = TutorialGenerationInput(
        concept=concept,
        context=context,
        user_preferences=preferences,
    )
    
    print("=== 测试单个教程生成 ===")
    print(f"概念: {concept.name}")
    print(f"路线图 ID: {context['roadmap_id']}")
    print()
    
    try:
        # 创建 generator 并执行
        generator = TutorialGeneratorAgent()
        result = await generator.execute(generation_input)
        
        print("✓ 教程生成成功！")
        print(f"  Tutorial ID: {result.tutorial_id}")
        print(f"  Title: {result.title}")
        print(f"  Summary: {result.summary[:100]}...")
        print(f"  Content URL: {result.content_url}")
        print(f"  Status: {result.content_status}")
        print(f"  Estimated Time: {result.estimated_completion_time} 分钟")
        
    except Exception as e:
        logger.error("test_failed", error=str(e), error_type=type(e).__name__)
        print(f"✗ 测试失败: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(test_single_tutorial())

