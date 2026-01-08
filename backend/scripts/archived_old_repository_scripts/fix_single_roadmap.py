"""
修复单个路线图的 framework_data 同步问题

用法: python fix_single_roadmap.py <roadmap_id>
"""
import asyncio
import sys
from sqlalchemy import text, update

from app.db.session import async_session_maker
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.models.domain import RoadmapFramework
from app.models.database import RoadmapMetadata


async def fix_roadmap(roadmap_id: str):
    """修复单个路线图的 framework_data"""
    
    print(f"\n{'='*80}")
    print(f"🔧 修复路线图: {roadmap_id}")
    print(f"{'='*80}\n")
    
    async with async_session_maker.begin() as session:
        repo = RoadmapRepository(session)
        
        # 1. 读取 framework_data
        print("📖 Step 1: 读取 roadmap_metadata...")
        metadata = await repo.get_roadmap_metadata(roadmap_id)
        if not metadata:
            print(f"❌ 错误: 路线图 {roadmap_id} 不存在")
            return False
        
        if not metadata.framework_data:
            print("❌ 错误: framework_data 为空")
            return False
        
        print(f"✅ 找到路线图: {metadata.title}")
        framework_data = metadata.framework_data
        
        # 2. 读取独立元数据表
        print("\n📊 Step 2: 读取独立元数据表...")
        
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
        
        print(f"   TutorialMetadata: {len(tutorials)} 条")
        print(f"   ResourceRecommendationMetadata: {len(resources)} 条")
        print(f"   QuizMetadata: {len(quizzes)} 条")
        
        if not (tutorials or resources or quizzes):
            print("\n⚠️  没有内容数据，无需修复")
            return False
        
        # 3. 更新 framework_data
        print("\n🔄 Step 3: 更新 framework_data...")
        updated_count = 0
        total_concepts = 0
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    total_concepts += 1
                    
                    if not concept_id:
                        continue
                    
                    concept_updated = False
                    
                    # 更新教程相关字段
                    if concept_id in tutorials:
                        tutorial = tutorials[concept_id]
                        concept["content_status"] = "completed"
                        concept["content_ref"] = tutorial["content_url"]
                        concept["content_summary"] = tutorial["summary"]
                        concept_updated = True
                    
                    # 更新资源相关字段
                    if concept_id in resources:
                        resource = resources[concept_id]
                        concept["resources_status"] = "completed"
                        concept["resources_id"] = resource["id"]
                        concept["resources_count"] = resource["resources_count"]
                        concept_updated = True
                    
                    # 更新测验相关字段
                    if concept_id in quizzes:
                        quiz = quizzes[concept_id]
                        concept["quiz_status"] = "completed"
                        concept["quiz_id"] = quiz["quiz_id"]
                        concept["quiz_questions_count"] = quiz["total_questions"]
                        concept_updated = True
                    
                    if concept_updated:
                        updated_count += 1
                        print(f"   ✅ 更新: {concept.get('name', 'Unknown')}")
        
        if updated_count == 0:
            print("\n⚠️  没有需要更新的 Concept")
            return False
        
        # 4. 保存回数据库
        print(f"\n💾 Step 4: 保存到数据库...")
        stmt = (
            update(RoadmapMetadata)
            .where(RoadmapMetadata.roadmap_id == roadmap_id)
            .values(framework_data=framework_data)
        )
        await session.execute(stmt)
        await session.commit()
        
        print(f"\n{'='*80}")
        print(f"✅ 修复完成!")
        print(f"   总 Concept 数: {total_concepts}")
        print(f"   成功更新: {updated_count} 个")
        print(f"{'='*80}\n")
        
        return True


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python fix_single_roadmap.py <roadmap_id>")
        print("示例: python fix_single_roadmap.py python-design-patterns-a5b4c3d2")
        sys.exit(1)
    
    roadmap_id = sys.argv[1]
    
    try:
        success = await fix_roadmap(roadmap_id)
        if success:
            print("🎉 修复成功！可以运行 diagnose_framework_data.py 验证结果")
        else:
            print("⚠️  未进行任何修复")
    except Exception as e:
        print(f"\n❌ 修复失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
