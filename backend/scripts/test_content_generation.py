#!/usr/bin/env python3
"""
内容生成流程测试脚本

功能：
1. 准备已通过 human_review 的路线图（包含完整的 framework）
2. 直接触发内容生成流程（跳过前期的意图分析、课程设计等步骤）
3. 监控内容生成进度
4. 验证生成结果

使用方法：
    cd backend
    # 使用 Mock 路线图数据测试（快速）
    uv run python scripts/test_content_generation.py --mock
    
    # 使用现有路线图测试
    uv run python scripts/test_content_generation.py --roadmap-id <roadmap_id>
    
    # 使用现有路线图并限制生成的 Concept 数量
    uv run python scripts/test_content_generation.py --roadmap-id <roadmap_id> --max-concepts 2

注意：
    - Mock 模式会创建一个简化的路线图框架（3个Concepts）
    - 使用现有路线图时，需要确保该路线图包含完整的 framework 数据
    - 可以通过 --max-concepts 参数限制生成的 Concept 数量，加快测试速度
"""
import argparse
import asyncio
import sys
import uuid
from datetime import datetime
from pathlib import Path

import structlog

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import async_session_maker
from app.crud.crud_roadmap import get_roadmap_crud
from app.crud.crud_task import get_task_crud
from app.models.domain import (
    Concept,
    Module,
    Stage,
    RoadmapFramework,
    LearningPreferences,
)
from app.core.orchestrator.subgraphs.content_generation import (
    build_content_generation_subgraph,
    ContentGenState,
)
from app.core.orchestrator.runtime_context import RuntimeContext
from app.core.orchestrator_factory import OrchestratorFactory
from app.services.shared.notification_service import NotificationService
from app.services.shared.execution_logger import ExecutionLogger
from app.config.settings import settings

logger = structlog.get_logger()


# ============================================================
# Mock 路线图数据
# ============================================================

def create_mock_framework(roadmap_id: str) -> RoadmapFramework:
    """
    创建 Mock 路线图框架
    
    包含 2 个 Stage、2 个 Module、3 个 Concept，用于快速测试
    
    Args:
        roadmap_id: 路线图 ID
    """
    return RoadmapFramework(
        roadmap_id=roadmap_id,
        title="Mock 路线图 - Python 学习路径",
        stages=[
            Stage(
                stage_id="S-1",
                name="基础阶段",
                description="学习核心基础知识",
                order=1,
                estimated_hours=5.0,
                modules=[
                    Module(
                        module_id="M-1-1",
                        name="入门模块",
                        description="基础概念学习",
                        order=1,
                        estimated_hours=3.0,
                        concepts=[
                            Concept(
                                concept_id="C-1-1-1",
                                name="Python 基本语法",
                                description="学习 Python 的基本语法规则",
                                order=1,
                                estimated_hours=1.5,
                                difficulty="easy",
                                learning_objectives=[
                                    "理解变量和数据类型",
                                    "掌握控制流语句",
                                    "学会使用函数",
                                ],
                                prerequisites=[],
                            ),
                            Concept(
                                concept_id="C-1-1-2",
                                name="数据结构基础",
                                description="掌握基本数据结构",
                                order=2,
                                estimated_hours=1.5,
                                difficulty="easy",
                                learning_objectives=[
                                    "理解列表和元组",
                                    "掌握字典的使用",
                                    "了解集合的特性",
                                ],
                                prerequisites=["C-1-1-1"],
                            ),
                        ],
                    ),
                ],
            ),
            Stage(
                stage_id="S-2",
                name="进阶阶段",
                description="深入学习高级特性",
                order=2,
                estimated_hours=2.0,
                modules=[
                    Module(
                        module_id="M-2-1",
                        name="进阶模块",
                        description="高级概念学习",
                        order=1,
                        estimated_hours=2.0,
                        concepts=[
                            Concept(
                                concept_id="C-2-1-1",
                                name="面向对象编程",
                                description="理解 OOP 核心概念",
                                order=1,
                                estimated_hours=2.0,
                                difficulty="medium",
                                learning_objectives=[
                                    "理解类和对象",
                                    "掌握继承和多态",
                                    "学会使用装饰器",
                                ],
                                prerequisites=["C-1-1-1", "C-1-1-2"],
                            ),
                        ],
                    ),
                ],
            ),
        ],
        total_estimated_hours=7.0,
        recommended_completion_weeks=2,
    )


async def create_mock_roadmap(user_id: str) -> tuple[str, str]:
    """
    创建 Mock 路线图和任务
    
    Returns:
        (roadmap_id, task_id)
    """
    print(f"\n{'='*70}")
    print(f"🔧 创建 Mock 路线图")
    print(f"{'='*70}")
    
    roadmap_id = f"roadmap_{uuid.uuid4().hex[:12]}"
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    
    # 创建 Mock Framework
    framework = create_mock_framework(roadmap_id)
    
    print(f"   Roadmap ID: {roadmap_id}")
    print(f"   Task ID: {task_id}")
    print(f"   Framework 结构:")
    print(f"      - Stages: {len(framework.stages)}")
    print(f"      - Modules: {sum(len(s.modules) for s in framework.stages)}")
    print(f"      - Concepts: {sum(len(m.concepts) for s in framework.stages for m in s.modules)}")
    print(f"      - 总学时: {framework.total_estimated_hours}小时")
    
    try:
        async with async_session_maker() as session:
            async with session.begin():
                roadmap_crud = get_roadmap_crud()
                task_crud = get_task_crud()
                
                # 1. 保存路线图元数据
                await roadmap_crud.save_roadmap_metadata(
                    session=session,
                    roadmap_id=roadmap_id,
                    user_id=user_id,
                    framework=framework,
                )
                
                # 2. 创建任务记录
                await task_crud.create(
                    session=session,
                    obj_in={
                        "task_id": task_id,
                        "user_id": user_id,
                        "roadmap_id": roadmap_id,
                        "status": "in_progress",
                        "task_type": "content_generation",
                        "current_step": "content_generation",
                        "user_request": {},  # 空字典作为占位符
                    },
                )
        
        print(f"   ✅ Mock 路线图创建成功")
        return roadmap_id, task_id
        
    except Exception as e:
        print(f"   ❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def load_existing_roadmap(roadmap_id: str) -> tuple[str, RoadmapFramework]:
    """
    加载现有路线图
    
    Returns:
        (user_id, framework)
    """
    print(f"\n{'='*70}")
    print(f"📚 加载现有路线图")
    print(f"{'='*70}")
    print(f"   Roadmap ID: {roadmap_id}")
    
    try:
        async with async_session_maker() as session:
            roadmap_crud = get_roadmap_crud()
            roadmap_metadata = await roadmap_crud.get_by_roadmap_id(
                session,
                roadmap_id,
            )
            
            if not roadmap_metadata:
                print(f"   ❌ 路线图不存在")
                sys.exit(1)
            
            if not roadmap_metadata.framework_data:
                print(f"   ❌ 路线图缺少 framework 数据")
                sys.exit(1)
            
            # 解析 framework_data
            framework = RoadmapFramework.model_validate(
                roadmap_metadata.framework_data
            )
            
            print(f"   ✅ 路线图加载成功")
            print(f"   Title: {roadmap_metadata.title}")
            print(f"   User ID: {roadmap_metadata.user_id}")
            print(f"   Framework 结构:")
            print(f"      - Stages: {len(framework.stages)}")
            print(f"      - Modules: {sum(len(s.modules) for s in framework.stages)}")
            print(f"      - Concepts: {sum(len(m.concepts) for s in framework.stages for m in s.modules)}")
            print(f"      - 总学时: {framework.total_estimated_hours}小时")
            
            return roadmap_metadata.user_id, framework
            
    except Exception as e:
        print(f"   ❌ 加载失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def create_task_for_roadmap(roadmap_id: str, user_id: str) -> str:
    """
    为现有路线图创建任务
    
    Returns:
        task_id
    """
    print(f"\n{'='*70}")
    print(f"📝 创建任务记录")
    print(f"{'='*70}")
    
    task_id = f"task_{uuid.uuid4().hex[:12]}"
    print(f"   Task ID: {task_id}")
    
    try:
        async with async_session_maker() as session:
            async with session.begin():
                task_crud = get_task_crud()
                await task_crud.create(
                    session=session,
                    obj_in={
                        "task_id": task_id,
                        "user_id": user_id,
                        "roadmap_id": roadmap_id,
                        "status": "in_progress",
                        "task_type": "content_generation",
                        "current_step": "content_generation",
                        "user_request": {},  # 空字典作为占位符
                    },
                )
        
        print(f"   ✅ 任务创建成功")
        return task_id
        
    except Exception as e:
        print(f"   ❌ 创建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def extract_concepts_from_framework(
    framework: RoadmapFramework,
    max_concepts: int | None = None,
) -> list[dict]:
    """
    从 Framework 中提取所有 Concepts（包含上下文信息）
    
    Args:
        framework: 路线图框架
        max_concepts: 最大提取数量（用于加快测试）
    
    Returns:
        包含 Concept 和上下文信息的字典列表
        每个字典包含: concept, stage_name, module_name
    """
    concepts = []
    
    for stage in framework.stages:
        for module in stage.modules:
            for concept in module.concepts:
                # 创建包含上下文信息的字典
                concept_with_context = {
                    "concept": concept,
                    "stage_name": stage.name,
                    "module_name": module.name,
                }
                concepts.append(concept_with_context)
                
                if max_concepts and len(concepts) >= max_concepts:
                    return concepts
    
    return concepts


async def run_content_generation(
    roadmap_id: str,
    task_id: str,
    concepts_with_context: list[dict],
    user_preferences: LearningPreferences | None = None,
) -> dict:
    """
    执行内容生成流程
    
    Args:
        roadmap_id: 路线图 ID
        task_id: 任务 ID
        concepts_with_context: 包含 Concept 和上下文信息的字典列表
        user_preferences: 用户学习偏好（可选）
    
    Returns:
        执行结果
    """
    print(f"\n{'='*70}")
    print(f"🚀 执行内容生成流程")
    print(f"{'='*70}")
    print(f"   Roadmap ID: {roadmap_id}")
    print(f"   Task ID: {task_id}")
    print(f"   Concepts 数量: {len(concepts_with_context)}")
    
    # 提取 Concept 对象
    concepts = [item["concept"] for item in concepts_with_context]
    
    # 显示待生成的 Concepts
    print(f"\n   待生成的 Concepts:")
    for i, item in enumerate(concepts_with_context, 1):
        concept = item["concept"]
        print(f"      {i}. [{concept.concept_id}] {concept.name}")
        print(f"         Stage: {item['stage_name']}")
        print(f"         Module: {item['module_name']}")
        print(f"         难度: {concept.difficulty}")
    
    # 准备用户偏好（如果未提供，使用默认值）
    if not user_preferences:
        user_preferences = LearningPreferences(
            learning_goal="测试内容生成",
            available_hours_per_week=10,
            current_level="beginner",
            content_preference=["text", "hands_on"],
            motivation="测试",
        )
    
    # 构建初始状态
    initial_state: ContentGenState = {
        "roadmap_id": roadmap_id,
        "concepts": concepts,
        "user_preferences": user_preferences,
        "task_id": task_id,
        "concept": None,
        "concept_results": [],
    }
    
    print(f"\n   ⏳ 开始生成...")
    start_time = datetime.now()
    
    try:
        # 创建 OrchestratorFactory 并获取组件
        orchestrator_factory = OrchestratorFactory(settings=settings)
        state_manager = orchestrator_factory.state_manager
        
        # 创建 RuntimeContext
        notification_service = NotificationService()
        execution_logger = ExecutionLogger()
        
        runtime_context = RuntimeContext(
            state_manager=state_manager,
            notification_service=notification_service,
            execution_logger=execution_logger,
        )
        
        # 构建内容生成子图
        # ✅ 传入子图专用的 checkpointer（双 Checkpointer 架构）
        child_checkpointer = orchestrator_factory.build_child_checkpointer()
        subgraph = build_content_generation_subgraph(checkpointer=child_checkpointer)
        
        # 执行子图
        config = {
            "configurable": {
                "thread_id": task_id,  # ✅ 与父图共享 thread_id
                "checkpoint_ns": "child_graph",  # ✅ 子图命名空间
                "runtime_context": runtime_context,
            }
        }
        
        result = await subgraph.ainvoke(initial_state, config)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        print(f"\n   ✅ 内容生成完成")
        print(f"   总耗时: {elapsed:.1f}秒 ({elapsed/60:.1f}分钟)")
        
        return result
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n   ❌ 内容生成失败")
        print(f"   耗时: {elapsed:.1f}秒")
        print(f"   错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def display_generation_results(result: dict):
    """
    显示生成结果统计
    
    Args:
        result: 执行结果
    """
    print(f"\n{'='*70}")
    print(f"📊 生成结果统计")
    print(f"{'='*70}")
    
    concept_results = result.get("concept_results", [])
    
    if not concept_results:
        print(f"   ⚠️ 未找到生成结果")
        return
    
    print(f"   总 Concepts 数量: {len(concept_results)}")
    
    # 统计成功/失败数量
    tutorial_success = sum(
        1 for r in concept_results
        if r.get("save_status", {}).get("tutorial") == "success"
    )
    resource_success = sum(
        1 for r in concept_results
        if r.get("save_status", {}).get("resource") == "success"
    )
    quiz_success = sum(
        1 for r in concept_results
        if r.get("save_status", {}).get("quiz") == "success"
    )
    metadata_success = sum(
        1 for r in concept_results
        if r.get("save_status", {}).get("metadata_saved", False)
    )
    
    print(f"\n   生成成功统计:")
    print(f"      - Tutorial: {tutorial_success}/{len(concept_results)}")
    print(f"      - Resource: {resource_success}/{len(concept_results)}")
    print(f"      - Quiz: {quiz_success}/{len(concept_results)}")
    print(f"      - 元数据已保存: {metadata_success}/{len(concept_results)}")
    
    # 显示每个 Concept 的详细结果
    print(f"\n   详细结果:")
    for i, concept_result in enumerate(concept_results, 1):
        concept_id = concept_result.get("concept_id", "Unknown")
        concept_name = concept_result.get("concept_name", "Unknown")
        save_status = concept_result.get("save_status", {})
        
        print(f"\n      [{i}] {concept_name} ({concept_id})")
        print(f"         Tutorial: {save_status.get('tutorial', 'N/A')}")
        print(f"         Resource: {save_status.get('resource', 'N/A')}")
        print(f"         Quiz: {save_status.get('quiz', 'N/A')}")
        print(f"         元数据: {'✅ 已保存' if save_status.get('metadata_saved') else '❌ 未保存'}")
        
        # 显示错误信息（如果有）
        if not save_status.get("metadata_saved"):
            error_msg = save_status.get("error_message")
            if error_msg:
                print(f"         错误: {error_msg}")


async def verify_database_records(roadmap_id: str, concepts_with_context: list[dict]):
    """
    验证数据库中的记录
    
    Args:
        roadmap_id: 路线图 ID
        concepts_with_context: 包含 Concept 和上下文信息的字典列表
    """
    # 提取 Concept 对象
    concepts = [item["concept"] for item in concepts_with_context]
    print(f"\n{'='*70}")
    print(f"🔍 验证数据库记录")
    print(f"{'='*70}")
    
    try:
        from app.crud.crud_tutorial import get_tutorial_crud
        from app.crud.crud_resource import get_resource_crud
        from app.crud.crud_quiz import get_quiz_crud
        
        async with async_session_maker() as session:
            tutorial_crud = get_tutorial_crud()
            resource_crud = get_resource_crud()
            quiz_crud = get_quiz_crud()
            
            print(f"   检查 {len(concepts)} 个 Concepts 的数据库记录...")
            
            tutorial_count = 0
            resource_count = 0
            quiz_count = 0
            
            for concept in concepts:
                # 检查 Tutorial
                tutorial = await tutorial_crud.get_by_concept_id(
                    session,
                    concept.concept_id,
                )
                if tutorial:
                    tutorial_count += 1
                
                # 检查 Resource
                resource = await resource_crud.get_by_concept_id(
                    session,
                    concept.concept_id,
                )
                if resource:
                    resource_count += 1
                
                # 检查 Quiz
                quiz = await quiz_crud.get_by_concept_id(
                    session,
                    concept.concept_id,
                )
                if quiz:
                    quiz_count += 1
            
            print(f"\n   数据库记录统计:")
            print(f"      - Tutorial 记录: {tutorial_count}/{len(concepts)}")
            print(f"      - Resource 记录: {resource_count}/{len(concepts)}")
            print(f"      - Quiz 记录: {quiz_count}/{len(concepts)}")
            
            # 检查 Framework 更新
            roadmap_crud = get_roadmap_crud()
            roadmap_metadata = await roadmap_crud.get_by_roadmap_id(
                session,
                roadmap_id,
            )
            
            if roadmap_metadata and roadmap_metadata.framework_data:
                framework = RoadmapFramework.model_validate(
                    roadmap_metadata.framework_data
                )
                
                # 检查有多少个 Concept 的 content_status 为 completed
                completed_count = 0
                for stage in framework.stages:
                    for module in stage.modules:
                        for concept in module.concepts:
                            if concept.content_status == "completed":
                                completed_count += 1
                
                print(f"      - Framework 已更新: {completed_count} 个 Concept 标记为 completed")
            
            print(f"\n   ✅ 数据库验证完成")
            
    except Exception as e:
        print(f"\n   ⚠️ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


async def cleanup_test_data(roadmap_id: str, task_id: str, skip_cleanup: bool = False):
    """
    清理测试数据
    
    Args:
        roadmap_id: 路线图 ID
        task_id: 任务 ID
        skip_cleanup: 是否跳过清理
    """
    print(f"\n{'='*70}")
    print(f"🧹 清理测试数据")
    print(f"{'='*70}")
    
    if skip_cleanup:
        print(f"   ⏭️  已跳过清理，测试数据保留")
        print(f"   Roadmap ID: {roadmap_id}")
        print(f"   Task ID: {task_id}")
        return
    
    print(f"   提示: 如需保留测试数据供查看，请按 Ctrl+C 取消")
    print(f"   将在5秒后开始清理...")
    
    try:
        await asyncio.sleep(5)
        
        async with async_session_maker() as session:
            async with session.begin():
                from sqlalchemy import delete
                
                roadmap_crud = get_roadmap_crud()
                
                # 删除路线图（级联删除相关内容）
                await roadmap_crud.delete_roadmap(session, roadmap_id)
                
                # 删除任务（直接使用 SQL）
                from app.models.database import RoadmapTask
                await session.execute(
                    delete(RoadmapTask).where(RoadmapTask.task_id == task_id)
                )
        
        print(f"   ✅ 测试数据已清理")
        
    except KeyboardInterrupt:
        print(f"\n   🛑 清理已取消，测试数据保留")
    except Exception as e:
        print(f"   ⚠️ 清理失败: {e}")


# ============================================================
# 主函数
# ============================================================

async def main():
    """主测试流程"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="内容生成流程测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # Mock 模式（快速测试）
  uv run python scripts/test_content_generation.py --mock
  
  # 使用现有路线图
  uv run python scripts/test_content_generation.py --roadmap-id roadmap_abc123
  
  # 限制生成数量（加快测试）
  uv run python scripts/test_content_generation.py --roadmap-id roadmap_abc123 --max-concepts 2
  
  # 不清理测试数据
  uv run python scripts/test_content_generation.py --mock --no-cleanup
        """
    )
    
    parser.add_argument(
        "--mock",
        action="store_true",
        help="使用 Mock 路线图数据（快速测试）"
    )
    parser.add_argument(
        "--roadmap-id",
        type=str,
        help="使用现有路线图的 ID"
    )
    parser.add_argument(
        "--max-concepts",
        type=int,
        help="最多生成的 Concept 数量（用于加快测试）"
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="测试完成后不清理数据"
    )
    
    args = parser.parse_args()
    
    # 验证参数
    if not args.mock and not args.roadmap_id:
        parser.error("必须提供 --mock 或 --roadmap-id")
    
    if args.mock and args.roadmap_id:
        parser.error("--mock 和 --roadmap-id 不能同时使用")
    
    print(f"\n{'#'*70}")
    print(f"# 内容生成流程测试脚本")
    print(f"# 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.mock:
        print(f"# 模式: Mock 路线图（快速测试）")
    else:
        print(f"# 模式: 使用现有路线图")
        print(f"# Roadmap ID: {args.roadmap_id}")
    if args.max_concepts:
        print(f"# 最大 Concepts 数量: {args.max_concepts}")
    if args.no_cleanup:
        print(f"# 清理测试数据: ❌ 已禁用")
    print(f"{'#'*70}")
    
    try:
        # 步骤1: 准备路线图和任务
        if args.mock:
            # Mock 模式：创建新路线图
            user_id = "test_user_" + uuid.uuid4().hex[:8]
            roadmap_id, task_id = await create_mock_roadmap(user_id)
            
            # 加载 Framework
            _, framework = await load_existing_roadmap(roadmap_id)
        else:
            # 使用现有路线图
            user_id, framework = await load_existing_roadmap(args.roadmap_id)
            roadmap_id = args.roadmap_id
            
            # 创建任务
            task_id = await create_task_for_roadmap(roadmap_id, user_id)
        
        # 步骤2: 提取 Concepts（包含上下文信息）
        concepts_with_context = extract_concepts_from_framework(
            framework,
            max_concepts=args.max_concepts,
        )
        
        if not concepts_with_context:
            print(f"\n   ❌ Framework 中没有可用的 Concepts")
            sys.exit(1)
        
        # 步骤3: 执行内容生成
        result = await run_content_generation(
            roadmap_id=roadmap_id,
            task_id=task_id,
            concepts_with_context=concepts_with_context,
        )
        
        # 步骤4: 显示结果
        display_generation_results(result)
        
        # 步骤5: 验证数据库
        await verify_database_records(roadmap_id, concepts_with_context)
        
        # 步骤6: 清理测试数据（可选）
        if args.mock:
            await cleanup_test_data(
                roadmap_id,
                task_id,
                skip_cleanup=args.no_cleanup,
            )
        
        print(f"\n{'#'*70}")
        print(f"# ✅ 测试完成")
        print(f"{'#'*70}\n")
        
    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print(f"🛑 测试被用户中断")
        print(f"{'='*70}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n{'='*70}")
        print(f"❌ 测试过程中发生未预期的错误")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print(f"{'='*70}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
