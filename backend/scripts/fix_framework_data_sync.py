"""
修复脚本：同步独立元数据表到 roadmap_metadata.framework_data

问题：
- 独立元数据表（TutorialMetadata、ResourceRecommendationMetadata、QuizMetadata）有数据
- 但 framework_data 中的 Concept 没有对应的引用字段（content_ref、resources_id、quiz_id）

解决方案：
1. 读取所有路线图的 framework_data
2. 读取对应的独立元数据表
3. 更新 framework_data 中的 Concept 字段
4. 保存回数据库
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.models.domain import RoadmapFramework


async def fix_single_roadmap(roadmap_id: str):
    """修复单个路线图的 framework_data（独立事务）"""
    
    print(f"\n{'='*80}")
    print(f"🔧 修复路线图: {roadmap_id}")
    print(f"{'='*80}")
    
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        
        # 1. 读取 framework_data
        metadata = await repo.get_roadmap_metadata(roadmap_id)
        if not metadata or not metadata.framework_data:
            print("❌ 没有 framework_data，跳过")
            return False
        
        framework_data = metadata.framework_data
        framework = RoadmapFramework.model_validate(framework_data)
        
        # 2. 读取独立元数据表
        # 2.1 TutorialMetadata
        result = await session.execute(
            text("""
                SELECT concept_id, tutorial_id, content_url, summary
                FROM tutorial_metadata
                WHERE roadmap_id = :roadmap_id AND is_latest = true
            """),
            {"roadmap_id": roadmap_id}
        )
        tutorials = {row[0]: {"tutorial_id": row[1], "content_url": row[2], "summary": row[3]} 
                    for row in result.fetchall()}
        
        # 2.2 ResourceRecommendationMetadata
        result = await session.execute(
            text("""
                SELECT concept_id, id, resources_count
                FROM resource_recommendation_metadata
                WHERE roadmap_id = :roadmap_id
            """),
            {"roadmap_id": roadmap_id}
        )
        resources = {row[0]: {"id": row[1], "resources_count": row[2]} 
                    for row in result.fetchall()}
        
        # 2.3 QuizMetadata
        result = await session.execute(
            text("""
                SELECT concept_id, quiz_id, total_questions
                FROM quiz_metadata
                WHERE roadmap_id = :roadmap_id
            """),
            {"roadmap_id": roadmap_id}
        )
        quizzes = {row[0]: {"quiz_id": row[1], "total_questions": row[2]} 
                  for row in result.fetchall()}
    
        print(f"📊 独立表数据:")
        print(f"   TutorialMetadata: {len(tutorials)} 条")
        print(f"   ResourceRecommendationMetadata: {len(resources)} 条")
        print(f"   QuizMetadata: {len(quizzes)} 条")
        
        # 调试：打印前几个 concept_id
        if tutorials:
            print(f"   示例 tutorial concept_ids: {list(tutorials.keys())[:5]}")
        if resources:
            print(f"   示例 resource concept_ids: {list(resources.keys())[:5]}")
        if quizzes:
            print(f"   示例 quiz concept_ids: {list(quizzes.keys())[:5]}")
        
        if not (tutorials or resources or quizzes):
            print("⚠️  没有内容数据，跳过")
            return False
        
        # 3. 更新 framework_data
        updated_count = 0
        total_concepts = 0
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    total_concepts += 1
                    
                    if not concept_id:
                        continue
                    
                    # 更新教程相关字段
                    if concept_id in tutorials:
                        tutorial = tutorials[concept_id]
                        concept["content_status"] = "completed"
                        concept["content_ref"] = tutorial["content_url"]
                        concept["content_summary"] = tutorial["summary"]
                        updated_count += 1
                        print(f"   ✅ 更新 {concept['name']} 的 tutorial")
                    
                    # 更新资源相关字段
                    if concept_id in resources:
                        resource = resources[concept_id]
                        concept["resources_status"] = "completed"
                        concept["resources_id"] = resource["id"]
                        concept["resources_count"] = resource["resources_count"]
                        updated_count += 1
                        print(f"   ✅ 更新 {concept['name']} 的 resources")
                    
                    # 更新测验相关字段
                    if concept_id in quizzes:
                        quiz = quizzes[concept_id]
                        concept["quiz_status"] = "completed"
                        concept["quiz_id"] = quiz["quiz_id"]
                        concept["quiz_questions_count"] = quiz["total_questions"]
                        updated_count += 1
                        print(f"   ✅ 更新 {concept['name']} 的 quiz")
        
        # 判断是否有更新（所有 Stage 遍历完成后才判断）
        if updated_count == 0:
            print("⚠️  没有需要更新的 Concept")
            return False
        
        # 4. 保存回数据库（使用 UPDATE 语句直接更新）
        from sqlalchemy import update
        from app.models.database import RoadmapMetadata
        
        stmt = (
            update(RoadmapMetadata)
            .where(RoadmapMetadata.roadmap_id == roadmap_id)
            .values(framework_data=framework_data)
        )
        await session.execute(stmt)
        await session.commit()
        
        print(f"\n✅ 修复完成:")
        print(f"   总 Concept 数: {total_concepts}")
        print(f"   更新项数: {updated_count}")
        
        return True


async def fix_all_roadmaps():
    """修复所有路线图的 framework_data"""
    
    print("=" * 80)
    print("🔧 修复所有路线图的 framework_data")
    print("=" * 80)
    print()
    
    # 1. 查询所有路线图（独立事务）
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT roadmap_id, title
                FROM roadmap_metadata 
                WHERE deleted_at IS NULL
                ORDER BY created_at DESC
            """)
        )
        roadmaps = result.fetchall()
    
    print(f"📊 找到 {len(roadmaps)} 个路线图\n")
    
    fixed_count = 0
    skipped_count = 0
    
    # 2. 逐个修复（每个路线图使用独立事务）
    for roadmap in roadmaps:
        roadmap_id, title = roadmap
        print(f"\n处理: {title}")
        
        try:
            if await fix_single_roadmap(roadmap_id):
                fixed_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            print(f"❌ 修复失败: {str(e)}")
            import traceback
            traceback.print_exc()
            skipped_count += 1
    
    print(f"\n" + "=" * 80)
    print(f"🎉 修复完成!")
    print(f"   修复成功: {fixed_count} 个")
    print(f"   跳过: {skipped_count} 个")
    print(f"=" * 80)


async def main():
    """主函数"""
    try:
        await fix_all_roadmaps()
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
