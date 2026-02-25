"""
调试脚本：输出 CurriculumArchitectAgent 的完整 prompt
"""
import asyncio
from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.models.domain import (
    CurriculumDesignInput,
    IntentAnalysisOutput,
    LearningPreferences,
)


async def debug_prompt():
    """输出完整的 prompt 内容"""
    
    # 1. 构造测试数据
    intent_analysis = IntentAnalysisOutput(
        roadmap_id="python-advanced-2024-abc123",
        parsed_goal="面向资深开发者的Python高级能力进阶",
        key_technologies=[
            "Python内存模型与GC机制",
            "Cython/FFI性能优化",
            "asyncio与异步IO生态",
            "multiprocessing/threading/concurrent.futures深度应用",
            "装饰器/描述符/元类/AST元编程"
        ],
        difficulty_profile="intermediate",
        time_constraint="每周10小时，12-14周",
        learning_path_type="skill_upgrade",
        skill_gaps=["CPython实现细节", "异步编程深度", "类型系统"],
        recommended_focus=["GIL", "asyncio", "类型驱动开发"],
        personalized_suggestions=["结合工程经验", "阅读源码", "构建类型安全测试"],
        full_analysis_data={
            "生成语言约束": "请使用简体中文生成响应内容",
            "用户目标约束": "用户学习目标：面向资深开发者的Python高级能力进阶",
            "用户画像约束": "用户画像：科技行业资深开发工程师",
            "难度约束": "用户难度画像：intermediate水平",
            "时间约束": "时间约束：每周10小时，12-14周",
            "学习路径类型约束": "学习路径类型：skill_upgrade",
            "技能差距约束": "用户技能差距：对CPython实现细节缺乏实操级理解",
            "推荐重点约束": "推荐学习重点：Python运行时与GIL真实影响",
        }
    )
    
    user_preferences = LearningPreferences(
        learning_goal="面向资深开发者的Python高级能力进阶",
        available_hours_per_week=10,
        motivation="技能提升",
        current_level="intermediate",
        career_background="科技行业资深开发工程师，5年以上工程经验",
        content_preference=["hands_on", "text"],
        industry="科技",
        current_role="资深开发工程师",
    )
    
    input_data = CurriculumDesignInput(
        intent_analysis=intent_analysis,
        user_preferences=user_preferences,
    )
    
    # 2. 创建 Agent
    agent = CurriculumArchitectAgent()
    
    # 3. 加载约束
    user_constraints = await agent._load_user_constraints(
        intent_analysis=intent_analysis
    )
    
    # 4. 加载 System Prompt
    system_prompt = agent._load_system_prompt(
        "curriculum_architect.j2",
        user_constraints=user_constraints,
        roadmap_id=intent_analysis.roadmap_id,
    )
    
    # 5. 构建用户消息
    user_message = "请设计一个科学的三层学习路线图框架(Stage→Module→Concept)"
    
    # 6. 输出
    print("=" * 100)
    print("SYSTEM PROMPT")
    print("=" * 100)
    print(system_prompt)
    print("\n\n")
    print("=" * 100)
    print("USER MESSAGE")
    print("=" * 100)
    print(user_message)
    print("\n\n")
    print("=" * 100)
    print("STATISTICS")
    print("=" * 100)
    print(f"System Prompt 长度: {len(system_prompt)} 字符")
    print(f"User Message 长度: {len(user_message)} 字符")
    print(f"总长度: {len(system_prompt) + len(user_message)} 字符")
    print(f"约束数量: {len(user_constraints)}")
    print(f"Roadmap ID: {intent_analysis.roadmap_id}")
    print("=" * 100)


if __name__ == "__main__":
    asyncio.run(debug_prompt())
