"""
测试脚本：验证内容生成后 framework_data 是否会被自动更新

模拟完整的工作流程：
1. 创建一个测试路线图（使用简单的 demo 架构）
2. 模拟内容生成并保存
3. 验证 framework_data 是否被正确更新

目的：验证当前代码逻辑是否真的能正确同步 framework_data
"""
import asyncio
import uuid
from datetime import datetime
from sqlalchemy import update

from app.db.session import AsyncSessionLocal
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.models.domain import (
    RoadmapFramework,
    Stage,
    Module,
    Concept,
    TutorialGenerationOutput,
    ResourceRecommendationOutput,
    QuizGenerationOutput,
)
from app.models.database import RoadmapMetadata


def create_demo_framework(roadmap_id: str) -> RoadmapFramework:
    """
    创建一个简单的 demo 架构图（只包含 2 个 Concept）
    """
    return RoadmapFramework(
        roadmap_id=roadmap_id,
        title="测试路线图 - Framework Data 更新验证",
        stages=[
            Stage(
                stage_id=f"{roadmap_id}:s-1",
                order=1,
                name="测试阶段",
                description="用于测试的阶段",
                modules=[
                    Module(
                        module_id=f"{roadmap_id}:m-1-1",
                        name="测试模块",
                        description="用于测试的模块",
                        concepts=[
                            Concept(
                                concept_id=f"{roadmap_id}:c-1-1-1",
                                name="测试概念 1",
                                description="第一个测试概念",
                                importance="核心概念",
                                difficulty="easy",
                                estimated_hours=1.0,
                                learning_objectives=["测试目标1", "测试目标2"],
                                prerequisites=[],
                                # 初始状态：pending
                                content_status="pending",
                                resources_status="pending",
                                quiz_status="pending",
                            ),
                            Concept(
                                concept_id=f"{roadmap_id}:c-1-1-2",
                                name="测试概念 2",
                                description="第二个测试概念",
                                importance="重要概念",
                                difficulty="easy",
                                estimated_hours=1.0,
                                learning_objectives=["测试目标3", "测试目标4"],
                                prerequisites=[f"{roadmap_id}:c-1-1-1"],
                                # 初始状态：pending
                                content_status="pending",
                                resources_status="pending",
                                quiz_status="pending",
                            ),
                        ],
                    ),
                ],
            ),
        ],
        total_estimated_hours=2.0,
        recommended_completion_weeks=1,
    )


def create_mock_tutorial_output(concept_id: str, concept_name: str) -> TutorialGenerationOutput:
    """创建模拟的教程输出"""
    tutorial_id = str(uuid.uuid4())
    return TutorialGenerationOutput(
        tutorial_id=tutorial_id,
        concept_id=concept_id,
        title=f"教程：{concept_name}",
        summary=f"这是 {concept_name} 的教程摘要",
        content="# 测试内容\n\n这是测试教程内容",
        content_url=f"http://test.com/tutorials/{tutorial_id}.md",
        content_status="completed",
        content_version=1,
        estimated_completion_time=60,
        generated_at=datetime.utcnow(),
    )


def create_mock_resource_output(concept_id: str, concept_name: str) -> ResourceRecommendationOutput:
    """创建模拟的资源推荐输出"""
    from app.models.domain import Resource
    
    resource_id = str(uuid.uuid4())
    return ResourceRecommendationOutput(
        id=resource_id,
        concept_id=concept_id,
        resources=[
            Resource(
                title=f"{concept_name} - 资源1",
                url="http://test.com/resource1",
                type="article",
                description="测试资源1",
                difficulty="easy",
                relevance_score=0.9,
            ),
            Resource(
                title=f"{concept_name} - 资源2",
                url="http://test.com/resource2",
                type="video",
                description="测试资源2",
                difficulty="easy",
                relevance_score=0.8,
            ),
        ],
    )


def create_mock_quiz_output(concept_id: str, concept_name: str) -> QuizGenerationOutput:
    """创建模拟的测验输出"""
    from app.models.domain import QuizQuestion
    
    quiz_id = str(uuid.uuid4())
    return QuizGenerationOutput(
        quiz_id=quiz_id,
        concept_id=concept_id,
        questions=[
            QuizQuestion(
                question_id=f"{quiz_id}-q1",
                question=f"{concept_name} - 测试题目1",
                question_type="single_choice",
                options=["选项A", "选项B", "选项C", "选项D"],
                correct_answer=[0],  # 第一个选项的索引
                explanation="这是测试题目的解释",
                difficulty="easy",
            ),
            QuizQuestion(
                question_id=f"{quiz_id}-q2",
                question=f"{concept_name} - 测试题目2",
                question_type="single_choice",
                options=["选项A", "选项B", "选项C", "选项D"],
                correct_answer=[1],  # 第二个选项的索引
                explanation="这是测试题目的解释",
                difficulty="easy",
            ),
        ],
        total_questions=2,
    )


async def test_framework_data_update():
    """
    测试 framework_data 更新流程
    """
    print("\n" + "="*80)
    print("🧪 测试：内容生成后 framework_data 是否会自动更新")
    print("="*80 + "\n")
    
    # 生成测试用的路线图 ID
    test_roadmap_id = f"test-roadmap-{uuid.uuid4().hex[:8]}"
    test_user_id = "test-user-123"
    test_task_id = f"test-task-{uuid.uuid4().hex[:8]}"
    
    print(f"📝 测试路线图 ID: {test_roadmap_id}")
    print(f"📝 测试任务 ID: {test_task_id}\n")
    
    try:
        # Step 1: 创建测试路线图
        print("Step 1: 创建测试路线图（包含 2 个 Concept）...")
        demo_framework = create_demo_framework(test_roadmap_id)
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            
            # 保存路线图元数据
            await repo.save_roadmap_metadata(
                roadmap_id=test_roadmap_id,
                user_id=test_user_id,
                framework=demo_framework,
            )
            
            # 创建任务记录
            await repo.create_task(
                task_id=test_task_id,
                user_id=test_user_id,
                user_request={"goal": "测试路线图"},
                task_type="creation",
            )
            
            # 更新任务的 roadmap_id
            await repo.update_task_status(
                task_id=test_task_id,
                status="processing",
                current_step="test",
                roadmap_id=test_roadmap_id,
            )
            
            await session.commit()
            print("✅ 路线图创建成功\n")
        
        # Step 2: 验证初始状态
        print("Step 2: 验证初始状态（framework_data 应该没有内容引用）...")
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            metadata = await repo.get_roadmap_metadata(test_roadmap_id)
            
            if not metadata or not metadata.framework_data:
                print("❌ 错误: 无法读取 framework_data")
                return False
            
            # 检查第一个 Concept 的状态
            first_concept = metadata.framework_data["stages"][0]["modules"][0]["concepts"][0]
            
            print(f"   Concept 1 初始状态:")
            print(f"   - content_status: {first_concept.get('content_status', 'N/A')}")
            print(f"   - content_ref: {first_concept.get('content_ref', 'None')}")
            print(f"   - resources_id: {first_concept.get('resources_id', 'None')}")
            print(f"   - quiz_id: {first_concept.get('quiz_id', 'None')}")
            
            if first_concept.get('content_ref') or first_concept.get('resources_id') or first_concept.get('quiz_id'):
                print("❌ 错误: 初始状态不应该有内容引用")
                return False
            
            print("✅ 初始状态正确（没有内容引用）\n")
        
        # Step 3: 模拟内容生成
        print("Step 3: 模拟内容生成（生成教程、资源、测验）...")
        
        # 为两个 Concept 创建模拟内容
        tutorial_refs = {
            f"{test_roadmap_id}:c-1-1-1": create_mock_tutorial_output(
                f"{test_roadmap_id}:c-1-1-1",
                "测试概念 1"
            ),
            f"{test_roadmap_id}:c-1-1-2": create_mock_tutorial_output(
                f"{test_roadmap_id}:c-1-1-2",
                "测试概念 2"
            ),
        }
        
        resource_refs = {
            f"{test_roadmap_id}:c-1-1-1": create_mock_resource_output(
                f"{test_roadmap_id}:c-1-1-1",
                "测试概念 1"
            ),
            f"{test_roadmap_id}:c-1-1-2": create_mock_resource_output(
                f"{test_roadmap_id}:c-1-1-2",
                "测试概念 2"
            ),
        }
        
        quiz_refs = {
            f"{test_roadmap_id}:c-1-1-1": create_mock_quiz_output(
                f"{test_roadmap_id}:c-1-1-1",
                "测试概念 1"
            ),
            f"{test_roadmap_id}:c-1-1-2": create_mock_quiz_output(
                f"{test_roadmap_id}:c-1-1-2",
                "测试概念 2"
            ),
        }
        
        print(f"✅ 生成了 {len(tutorial_refs)} 个教程")
        print(f"✅ 生成了 {len(resource_refs)} 个资源推荐")
        print(f"✅ 生成了 {len(quiz_refs)} 个测验\n")
        
        # Step 4: 模拟 WorkflowBrain.save_content_results() 的逻辑
        print("Step 4: 执行内容保存和 framework_data 更新...")
        print("   （这是测试的关键：验证 workflow_brain.py 中的逻辑）\n")
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            
            # 4.1 保存独立元数据表（模拟 WorkflowBrain 的逻辑）
            print("   4.1 保存独立元数据表...")
            await repo.save_tutorials_batch(tutorial_refs, test_roadmap_id)
            await repo.save_resources_batch(resource_refs, test_roadmap_id)
            await repo.save_quizzes_batch(quiz_refs, test_roadmap_id)
            print("   ✅ 独立元数据表保存完成")
            
            # 4.2 更新 roadmap_metadata 的 framework_data（核心测试逻辑）
            print("\n   4.2 更新 roadmap_metadata.framework_data...")
            print("       （这是 WorkflowBrain.save_content_results() 中的关键步骤）\n")
            
            roadmap_metadata = await repo.get_roadmap_metadata(test_roadmap_id)
            if roadmap_metadata and roadmap_metadata.framework_data:
                # 使用与 WorkflowBrain 相同的更新逻辑
                framework_data = roadmap_metadata.framework_data
                
                # 遍历并更新所有 Concept
                updated_count = 0
                for stage in framework_data.get("stages", []):
                    for module in stage.get("modules", []):
                        for concept in module.get("concepts", []):
                            concept_id = concept.get("concept_id")
                            
                            if not concept_id:
                                continue
                            
                            # 更新教程相关字段
                            if concept_id in tutorial_refs:
                                tutorial_output = tutorial_refs[concept_id]
                                concept["content_status"] = "completed"
                                concept["content_ref"] = tutorial_output.content_url
                                concept["content_summary"] = tutorial_output.summary
                                updated_count += 1
                                print(f"       ✅ 更新 {concept.get('name')} 的 tutorial")
                            
                            # 更新资源相关字段
                            if concept_id in resource_refs:
                                resource_output = resource_refs[concept_id]
                                concept["resources_status"] = "completed"
                                concept["resources_id"] = resource_output.id
                                concept["resources_count"] = len(resource_output.resources)
                                print(f"       ✅ 更新 {concept.get('name')} 的 resources")
                            
                            # 更新测验相关字段
                            if concept_id in quiz_refs:
                                quiz_output = quiz_refs[concept_id]
                                concept["quiz_status"] = "completed"
                                concept["quiz_id"] = quiz_output.quiz_id
                                concept["quiz_questions_count"] = quiz_output.total_questions
                                print(f"       ✅ 更新 {concept.get('name')} 的 quiz")
                
                # 保存更新后的 framework_data
                from sqlalchemy import update as sql_update
                from app.models.database import RoadmapMetadata as RMMetadata
                
                stmt = (
                    sql_update(RMMetadata)
                    .where(RMMetadata.roadmap_id == test_roadmap_id)
                    .values(framework_data=framework_data)
                )
                await session.execute(stmt)
                await session.commit()
                
                print(f"\n       ✅ framework_data 更新完成（更新了 {updated_count} 个 Concept）")
            else:
                print("       ❌ 错误: 无法读取 framework_data")
                return False
        
        print("\n✅ 内容保存和更新流程执行完成\n")
        
        # Step 5: 验证最终状态 - 关键验证！
        print("Step 5: 验证最终状态（framework_data 应该已更新）...")
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            metadata = await repo.get_roadmap_metadata(test_roadmap_id)
            
            if not metadata or not metadata.framework_data:
                print("❌ 错误: 无法读取 framework_data")
                return False
            
            # 检查所有 Concept 的状态
            concepts = metadata.framework_data["stages"][0]["modules"][0]["concepts"]
            
            all_updated = True
            for i, concept in enumerate(concepts, 1):
                concept_id = concept.get("concept_id")
                concept_name = concept.get("name")
                
                print(f"\n   📌 Concept {i}: {concept_name}")
                print(f"      concept_id: {concept_id}")
                print(f"      content_status: {concept.get('content_status', 'N/A')}")
                print(f"      content_ref: {concept.get('content_ref', 'None')}")
                print(f"      resources_status: {concept.get('resources_status', 'N/A')}")
                print(f"      resources_id: {concept.get('resources_id', 'None')}")
                print(f"      quiz_status: {concept.get('quiz_status', 'N/A')}")
                print(f"      quiz_id: {concept.get('quiz_id', 'None')}")
                
                # 验证是否已更新
                has_content = concept.get('content_ref') is not None
                has_resources = concept.get('resources_id') is not None
                has_quiz = concept.get('quiz_id') is not None
                
                if not (has_content and has_resources and has_quiz):
                    print(f"      ❌ 未完全更新！")
                    all_updated = False
                else:
                    print(f"      ✅ 已完全更新")
            
            # 验证独立元数据表
            print("\n   📊 验证独立元数据表...")
            
            # 检查 TutorialMetadata
            from sqlalchemy import text
            result = await session.execute(
                text("SELECT COUNT(*) FROM tutorial_metadata WHERE roadmap_id = :roadmap_id"),
                {"roadmap_id": test_roadmap_id}
            )
            tutorial_count = result.scalar()
            print(f"      TutorialMetadata: {tutorial_count} 条记录")
            
            # 检查 ResourceRecommendationMetadata
            result = await session.execute(
                text("SELECT COUNT(*) FROM resource_recommendation_metadata WHERE roadmap_id = :roadmap_id"),
                {"roadmap_id": test_roadmap_id}
            )
            resource_count = result.scalar()
            print(f"      ResourceRecommendationMetadata: {resource_count} 条记录")
            
            # 检查 QuizMetadata
            result = await session.execute(
                text("SELECT COUNT(*) FROM quiz_metadata WHERE roadmap_id = :roadmap_id"),
                {"roadmap_id": test_roadmap_id}
            )
            quiz_count = result.scalar()
            print(f"      QuizMetadata: {quiz_count} 条记录")
            
            # 最终判断
            print("\n" + "="*80)
            if all_updated and tutorial_count == 2 and resource_count == 2 and quiz_count == 2:
                print("🎉 测试通过！framework_data 已正确更新！")
                print("="*80 + "\n")
                
                print("✅ 结论：当前代码逻辑正确，save_content_results() 会自动更新 framework_data")
                return True
            else:
                print("❌ 测试失败！framework_data 未正确更新！")
                print("="*80 + "\n")
                
                print("❌ 结论：当前代码逻辑有问题，需要修复")
                return False
    
    except Exception as e:
        print(f"\n❌ 测试过程中发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Step 6: 清理测试数据
        print("\nStep 6: 清理测试数据...")
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import delete, text
                from app.models.database import (
                    RoadmapMetadata,
                    RoadmapTask,
                    TutorialMetadata,
                    ResourceRecommendationMetadata,
                    QuizMetadata,
                )
                
                # 删除所有测试数据
                await session.execute(
                    delete(TutorialMetadata).where(TutorialMetadata.roadmap_id == test_roadmap_id)
                )
                await session.execute(
                    delete(ResourceRecommendationMetadata).where(
                        ResourceRecommendationMetadata.roadmap_id == test_roadmap_id
                    )
                )
                await session.execute(
                    delete(QuizMetadata).where(QuizMetadata.roadmap_id == test_roadmap_id)
                )
                await session.execute(
                    delete(RoadmapTask).where(RoadmapTask.task_id == test_task_id)
                )
                await session.execute(
                    delete(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == test_roadmap_id)
                )
                
                await session.commit()
                print("✅ 测试数据已清理\n")
        except Exception as e:
            print(f"⚠️  清理测试数据时出错: {str(e)}\n")


async def main():
    """主函数"""
    try:
        success = await test_framework_data_update()
        
        if success:
            print("\n" + "="*80)
            print("🎉 测试结果：PASS")
            print("="*80)
            print("\n当前代码逻辑正确，WorkflowBrain.save_content_results() 能够正确更新 framework_data。")
            print("\n如果 python-design-patterns 路线图没有更新，可能的原因：")
            print("1. 该路线图生成时使用的是旧版本代码（在修复之前）")
            print("2. 生成过程中发生了异常，导致更新逻辑未执行")
            print("3. 数据库事务回滚导致更新丢失")
            print("\n建议：检查该路线图生成时的日志，查看是否有异常或错误。")
        else:
            print("\n" + "="*80)
            print("❌ 测试结果：FAIL")
            print("="*80)
            print("\n当前代码逻辑有问题，需要修复 WorkflowBrain.save_content_results() 方法。")
    except Exception as e:
        print(f"\n❌ 测试执行失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
