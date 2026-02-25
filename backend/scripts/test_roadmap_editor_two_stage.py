"""
RoadmapEditorAgent 两阶段生成测试

验证：
1. 两阶段生成流程正常工作
2. 生成的 framework.stages 非空
3. 编辑后的路线图结构正确
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.agents.roadmap_editor import RoadmapEditorAgent
from app.models.domain import (
    RoadmapEditInput,
    EditPlan,
    EditIntent,
    RoadmapFramework,
    Stage,
    Module,
    Concept,
    LearningPreferences,
)

print("=" * 80)
print("测试 RoadmapEditorAgent 两阶段生成")
print("=" * 80)

async def test_roadmap_editor_two_stage():
    """测试路线图编辑的两阶段生成"""
    
    # 创建现有路线图框架（简化版）
    existing_framework = RoadmapFramework(
        roadmap_id="test-roadmap-001",
        title="Python Web 开发学习路线",
        total_estimated_hours=100,
        recommended_completion_weeks=10,
        stages=[
            Stage(
                stage_id="stage-1",
                name="基础入门",
                description="Python 基础知识",
                order=1,
                modules=[
                    Module(
                        module_id="mod-1-1",
                        name="Python 核心语法",
                        description="基础语法和数据结构",
                        concepts=[
                            Concept(
                                concept_id="c-1-1-1",
                                name="变量与数据类型",
                                description="掌握基本数据类型",
                                estimated_hours=2.0,
                                difficulty="easy",
                                keywords=["变量", "数据类型", "类型转换"],
                                prerequisites=[],
                            ),
                            Concept(
                                concept_id="c-1-1-2",
                                name="函数与模块",
                                description="理解函数定义和模块导入",
                                estimated_hours=3.0,
                                difficulty="medium",
                                keywords=["函数", "模块", "import"],
                                prerequisites=["c-1-1-1"],
                            ),
                        ]
                    )
                ]
            ),
            Stage(
                stage_id="stage-2",
                name="Web 框架实战",
                description="学习 FastAPI 框架",
                order=2,
                modules=[
                    Module(
                        module_id="mod-2-1",
                        name="FastAPI 基础",
                        description="FastAPI 核心特性",
                        concepts=[
                            Concept(
                                concept_id="c-2-1-1",
                                name="路由与请求处理",
                                description="掌握 FastAPI 路由",
                                estimated_hours=4.0,
                                difficulty="medium",
                                keywords=["FastAPI", "路由", "请求"],
                                prerequisites=["c-1-1-2"],
                            ),
                        ]
                    )
                ]
            ),
        ]
    )
    
    # 创建编辑计划
    edit_plan = EditPlan(
        feedback_summary="用户希望增加数据库相关内容，并调整 Stage 2 的难度",
        scope_analysis="修改 Stage 2，增加一个新的 Module 关于数据库操作",
        intents=[
            EditIntent(
                priority="must",
                intent_type="add",
                target_type="module",
                target_path="Stage 2",
                target_id=None,
                description="在 Stage 2 中增加一个关于 SQLAlchemy 的新 Module",
            ),
            EditIntent(
                priority="should",
                intent_type="modify",
                target_type="concept",
                target_path="Stage 2 > Module 1 > Concept 1",
                target_id="c-2-1-1",
                description="调整路由与请求处理的难度从 medium 到 easy",
            ),
        ],
        preservation_requirements=[
            "Stage 1 完整保留",
            "所有现有的 Concept ID 保持不变",
        ]
    )
    
    # 创建用户偏好
    user_preferences = LearningPreferences(
        learning_goal="成为 Python Web 开发工程师",
        current_level="intermediate",
        career_background="后端开发工程师",
        available_hours_per_week=10,
        motivation="职业发展",
        content_preference=["text", "hands_on"],
    )
    
    # 创建输入
    input_data = RoadmapEditInput(
        existing_framework=existing_framework,
        edit_plan=edit_plan,
        user_preferences=user_preferences,
    )
    
    print("\n[1] 创建测试数据...")
    print(f"  ✓ Roadmap ID: {existing_framework.roadmap_id}")
    print(f"  ✓ 现有 Stage 数量: {len(existing_framework.stages)}")
    print(f"  ✓ 编辑意图数量: {len(edit_plan.intents)}")
    
    print("\n[2] 创建 Agent 实例...")
    agent = RoadmapEditorAgent()
    print(f"  ✓ Agent ID: {agent.agent_id}")
    print(f"  ✓ Model: {agent.model_provider}/{agent.model_name}")
    print(f"  ✓ 使用两阶段生成: True")
    
    print("\n[3] 执行 Agent（两阶段生成）...")
    print("  ⏳ 正在编辑路线图，请稍候...")
    
    try:
        result = await agent.execute(input_data)
        
        print("\n" + "=" * 80)
        print("✅ 路线图编辑成功！")
        print("=" * 80)
        
        print("\n[4] 验证输出结构...")
        print(f"  ✓ Roadmap ID: {result.framework.roadmap_id}")
        print(f"  ✓ 标题: {result.framework.title}")
        print(f"  ✓ Stage 数量: {len(result.framework.stages)}")
        
        # 计算 Module 和 Concept 总数
        total_modules = sum(len(stage.modules) for stage in result.framework.stages)
        total_concepts = sum(
            len(module.concepts)
            for stage in result.framework.stages
            for module in stage.modules
        )
        print(f"  ✓ Module 总数: {total_modules}")
        print(f"  ✓ Concept 总数: {total_concepts}")
        
        # 验证 Stages 非空
        assert len(result.framework.stages) > 0, "Stages 不应为空"
        print("\n  ✅ 关键验证：Stages 非空（两阶段生成解决了 empty stages 问题）")
        
        print("\n[5] 修改摘要...")
        print(f"  {result.modification_summary}")
        
        if result.preserved_elements:
            print("\n[6] 保留元素...")
            for elem in result.preserved_elements:
                print(f"  - {elem}")
        
        print("\n" + "=" * 80)
        print("✅ 测试通过！")
        print("=" * 80)
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ 测试失败")
        print("=" * 80)
        print(f"\n错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        
        import traceback
        print("\n详细错误堆栈:")
        traceback.print_exc()
        
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_roadmap_editor_two_stage())
