"""
诊断脚本：检查 roadmap_metadata 中的 framework_data 是否包含内容引用

检查项：
1. framework_data 中的 Concept 是否有 content_ref、resources_id、quiz_id
2. 对比 framework_data 和独立元数据表中的数据是否一致
3. 找出缺失内容引用的路线图
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_maker
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.models.domain import RoadmapFramework


async def diagnose_framework_data():
    """诊断 framework_data 中的内容引用"""
    
    async with async_session_maker.begin() as session:
        repo = RoadmapRepository(session)
        
        print("=" * 80)
        print("🔍 诊断 roadmap_metadata.framework_data 中的内容引用")
        print("=" * 80)
        print()
        
        # 1. 查询所有路线图
        result = await session.execute(
            text("""
                SELECT roadmap_id, title, created_at 
                FROM roadmap_metadata 
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC 
                LIMIT 5
            """)
        )
        roadmaps = result.fetchall()
        
        print(f"📊 找到 {len(roadmaps)} 个最近的路线图\n")
        
        for roadmap in roadmaps:
            roadmap_id, title, created_at = roadmap
            
            print(f"\n{'=' * 80}")
            print(f"🗺️  路线图: {title}")
            print(f"   ID: {roadmap_id}")
            print(f"   创建时间: {created_at}")
            print(f"{'=' * 80}\n")
            
            # 2. 读取 framework_data
            metadata = await repo.get_roadmap_metadata(roadmap_id)
            if not metadata or not metadata.framework_data:
                print("❌ 没有 framework_data")
                continue
            
            framework = RoadmapFramework.model_validate(metadata.framework_data)
            
            # 3. 统计 Concept
            total_concepts = 0
            concepts_with_content_ref = 0
            concepts_with_resources_id = 0
            concepts_with_quiz_id = 0
            concepts_without_any_content = []
            
            for stage in framework.stages:
                for module in stage.modules:
                    for concept in module.concepts:
                        total_concepts += 1
                        
                        # 检查是否有内容引用
                        has_content_ref = bool(concept.content_ref)
                        has_resources_id = bool(concept.resources_id)
                        has_quiz_id = bool(concept.quiz_id)
                        
                        if has_content_ref:
                            concepts_with_content_ref += 1
                        if has_resources_id:
                            concepts_with_resources_id += 1
                        if has_quiz_id:
                            concepts_with_quiz_id += 1
                        
                        # 如果三个都没有，记录下来
                        if not (has_content_ref or has_resources_id or has_quiz_id):
                            concepts_without_any_content.append({
                                "concept_id": concept.concept_id,
                                "concept_name": concept.name,
                                "content_status": concept.content_status,
                                "resources_status": concept.resources_status,
                                "quiz_status": concept.quiz_status,
                            })
            
            # 4. 显示统计结果
            print(f"📈 统计信息:")
            print(f"   总 Concept 数: {total_concepts}")
            print(f"   包含 content_ref 的: {concepts_with_content_ref} ({concepts_with_content_ref/total_concepts*100:.1f}%)")
            print(f"   包含 resources_id 的: {concepts_with_resources_id} ({concepts_with_resources_id/total_concepts*100:.1f}%)")
            print(f"   包含 quiz_id 的: {concepts_with_quiz_id} ({concepts_with_quiz_id/total_concepts*100:.1f}%)")
            print()
            
            # 5. 检查独立元数据表
            result = await session.execute(
                text("SELECT COUNT(*) FROM tutorial_metadata WHERE roadmap_id = :roadmap_id"),
                {"roadmap_id": roadmap_id}
            )
            tutorial_count = result.scalar()
            
            result = await session.execute(
                text("SELECT COUNT(*) FROM resource_recommendation_metadata WHERE roadmap_id = :roadmap_id"),
                {"roadmap_id": roadmap_id}
            )
            resource_count = result.scalar()
            
            result = await session.execute(
                text("SELECT COUNT(*) FROM quiz_metadata WHERE roadmap_id = :roadmap_id"),
                {"roadmap_id": roadmap_id}
            )
            quiz_count = result.scalar()
            
            print(f"📊 独立元数据表:")
            print(f"   TutorialMetadata: {tutorial_count} 条记录")
            print(f"   ResourceRecommendationMetadata: {resource_count} 条记录")
            print(f"   QuizMetadata: {quiz_count} 条记录")
            print()
            
            # 6. 判断是否存在数据不一致
            if tutorial_count > 0 and concepts_with_content_ref == 0:
                print("⚠️  警告: 独立表中有教程数据，但 framework_data 中没有 content_ref!")
            if resource_count > 0 and concepts_with_resources_id == 0:
                print("⚠️  警告: 独立表中有资源数据，但 framework_data 中没有 resources_id!")
            if quiz_count > 0 and concepts_with_quiz_id == 0:
                print("⚠️  警告: 独立表中有测验数据，但 framework_data 中没有 quiz_id!")
            
            # 7. 显示缺失内容的 Concept
            if concepts_without_any_content:
                print(f"\n❌ 缺失所有内容引用的 Concept ({len(concepts_without_any_content)} 个):")
                for item in concepts_without_any_content[:5]:  # 只显示前5个
                    print(f"   - {item['concept_name']} ({item['concept_id']})")
                    print(f"     状态: content={item['content_status']}, resources={item['resources_status']}, quiz={item['quiz_status']}")
                if len(concepts_without_any_content) > 5:
                    print(f"   ... 还有 {len(concepts_without_any_content) - 5} 个")
            
            # 8. 详细检查第一个 Concept
            if total_concepts > 0:
                first_concept = framework.stages[0].modules[0].concepts[0]
                print(f"\n🔬 详细检查第一个 Concept:")
                print(f"   concept_id: {first_concept.concept_id}")
                print(f"   name: {first_concept.name}")
                print(f"   content_status: {first_concept.content_status}")
                print(f"   content_ref: {first_concept.content_ref or 'None'}")
                print(f"   content_summary: {first_concept.content_summary or 'None'}")
                print(f"   resources_status: {first_concept.resources_status}")
                print(f"   resources_id: {first_concept.resources_id or 'None'}")
                print(f"   resources_count: {first_concept.resources_count or 0}")
                print(f"   quiz_status: {first_concept.quiz_status}")
                print(f"   quiz_id: {first_concept.quiz_id or 'None'}")
                print(f"   quiz_questions_count: {first_concept.quiz_questions_count or 0}")
                
                # 检查独立表中是否有对应数据
                result = await session.execute(
                    text("""
                        SELECT tutorial_id, content_url, summary 
                        FROM tutorial_metadata 
                        WHERE roadmap_id = :roadmap_id AND concept_id = :concept_id AND is_latest = true
                    """),
                    {"roadmap_id": roadmap_id, "concept_id": first_concept.concept_id}
                )
                tutorial_row = result.fetchone()
                
                if tutorial_row:
                    print(f"\n   📚 对应的 TutorialMetadata:")
                    print(f"      tutorial_id: {tutorial_row[0]}")
                    print(f"      content_url: {tutorial_row[1]}")
                    print(f"      summary: {tutorial_row[2][:100] if tutorial_row[2] else 'None'}...")
                    
                    if not first_concept.content_ref:
                        print(f"\n      ⚠️  数据不一致: TutorialMetadata 存在，但 framework_data 中没有 content_ref!")
                else:
                    print(f"\n   ❌ 独立表中没有对应的 TutorialMetadata")


async def main():
    """主函数"""
    try:
        await diagnose_framework_data()
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
