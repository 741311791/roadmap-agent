"""
测试TutorialGeneratorAgent的场景识别功能

验证开发场景和非开发场景的识别逻辑
"""
import asyncio
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.models.domain import Concept


async def test_scenario_detection():
    """测试场景识别"""
    
    # 创建Agent实例
    agent = TutorialGeneratorAgent()
    
    # 测试用例
    test_cases = [
        # 开发场景
        Concept(
            concept_id="c1",
            name="React Hooks",
            description="Learn React Hooks for state management",
            difficulty="medium",
            estimated_hours=4.0,
        ),
        Concept(
            concept_id="c2",
            name="FastAPI 异步路由",
            description="使用FastAPI构建异步API端点",
            difficulty="medium",
            estimated_hours=3.0,
        ),
        Concept(
            concept_id="c3",
            name="Python 装饰器",
            description="深入理解Python装饰器的原理和应用",
            difficulty="medium",
            estimated_hours=2.0,
        ),
        Concept(
            concept_id="c4",
            name="LangGraph 状态图",
            description="使用LangGraph构建复杂的Agent工作流",
            difficulty="hard",
            estimated_hours=5.0,
        ),
        # 非开发场景
        Concept(
            concept_id="c5",
            name="烹饪基础",
            description="学习基本的烹饪技巧和食材处理方法",
            difficulty="easy",
            estimated_hours=2.0,
        ),
        Concept(
            concept_id="c6",
            name="健身入门",
            description="了解健身的基本原理和训练方法",
            difficulty="easy",
            estimated_hours=3.0,
        ),
        Concept(
            concept_id="c7",
            name="英语口语练习",
            description="提升英语口语表达能力的实用技巧",
            difficulty="medium",
            estimated_hours=4.0,
        ),
    ]
    
    print("\n" + "="*80)
    print("场景识别测试（使用LLM智能判断）")
    print("="*80 + "\n")
    
    for concept in test_cases:
        is_dev = await agent._is_development_scenario(concept)
        scenario_type = "开发场景" if is_dev else "非开发场景"
        
        print(f"概念: {concept.name}")
        print(f"描述: {concept.description}")
        print(f"识别结果: {scenario_type}")
        print(f"预期工具: {'Context7 (resolve-library-id + query-docs)' if is_dev else '无 (使用LLM知识库)'}")
        print("-" * 80)
    
    print("\n✅ 场景识别测试完成\n")


if __name__ == "__main__":
    asyncio.run(test_scenario_detection())
