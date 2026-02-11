"""
检查framework_data是否包含content_refs

用法:
    python scripts/check_framework_data.py <roadmap_id>
"""
import asyncio
import sys
import json
from sqlalchemy import select
from app.db.session import async_session_maker
from app.models.database import RoadmapMetadata

async def check_framework_data(roadmap_id: str):
    """检查roadmap_metadata中的framework_data"""
    async with async_session_maker() as session:
        stmt = select(RoadmapMetadata).where(
            RoadmapMetadata.roadmap_id == roadmap_id
        )
        result = await session.execute(stmt)
        roadmap = result.scalar_one_or_none()
        
        if not roadmap:
            print(f"❌ 路线图 {roadmap_id} 不存在")
            return
        
        print(f"✅ 找到路线图: {roadmap.title}")
        print(f"创建时间: {roadmap.created_at}")
        print(f"更新时间: {roadmap.updated_at}")
        print("\n" + "="*80)
        
        framework_data = roadmap.framework_data
        
        if not framework_data:
            print("❌ framework_data 为空")
            return
        
        # 检查结构
        print(f"\n📊 framework_data 基本信息:")
        print(f"  - roadmap_id: {framework_data.get('roadmap_id')}")
        print(f"  - title: {framework_data.get('title')}")
        print(f"  - 阶段数: {len(framework_data.get('stages', []))}")
        
        # 遍历所有Concept,检查content_refs
        total_concepts = 0
        has_tutorial_id = 0
        has_resources_id = 0
        has_quiz_id = 0
        has_tutorial_status = 0
        has_resources_status = 0
        has_quiz_status = 0
        
        print(f"\n📋 Concept 内容引用检查:")
        print("="*80)
        
        for stage in framework_data.get('stages', []):
            for module in stage.get('modules', []):
                for concept in module.get('concepts', []):
                    total_concepts += 1
                    concept_id = concept.get('concept_id', '未知')
                    
                    # 检查ID字段
                    tutorial_id = concept.get('tutorial_id')
                    resources_id = concept.get('resources_id')
                    quiz_id = concept.get('quiz_id')
                    
                    # 检查状态字段
                    tutorial_status = concept.get('tutorial_status')
                    resources_status = concept.get('resources_status')
                    quiz_status = concept.get('quiz_status')
                    
                    if tutorial_id:
                        has_tutorial_id += 1
                    if resources_id:
                        has_resources_id += 1
                    if quiz_id:
                        has_quiz_id += 1
                    if tutorial_status:
                        has_tutorial_status += 1
                    if resources_status:
                        has_resources_status += 1
                    if quiz_status:
                        has_quiz_status += 1
                    
                    # 打印第一个Concept的详细信息
                    if total_concepts == 1:
                        print(f"\n示例 Concept: {concept_id}")
                        print(f"  - tutorial_id: {tutorial_id or '❌ 无'}")
                        print(f"  - tutorial_status: {tutorial_status or '❌ 无'}")
                        print(f"  - resources_id: {resources_id or '❌ 无'}")
                        print(f"  - resources_status: {resources_status or '❌ 无'}")
                        print(f"  - quiz_id: {quiz_id or '❌ 无'}")
                        print(f"  - quiz_status: {quiz_status or '❌ 无'}")
                        print(f"  - quiz_questions_count: {concept.get('quiz_questions_count', '❌ 无')}")
        
        print("\n" + "="*80)
        print(f"\n📈 统计结果:")
        print(f"  - 总Concept数: {total_concepts}")
        print(f"  - 有tutorial_id: {has_tutorial_id} ({has_tutorial_id/total_concepts*100:.1f}%)" if total_concepts > 0 else "")
        print(f"  - 有resources_id: {has_resources_id} ({has_resources_id/total_concepts*100:.1f}%)" if total_concepts > 0 else "")
        print(f"  - 有quiz_id: {has_quiz_id} ({has_quiz_id/total_concepts*100:.1f}%)" if total_concepts > 0 else "")
        print(f"  - 有tutorial_status: {has_tutorial_status} ({has_tutorial_status/total_concepts*100:.1f}%)" if total_concepts > 0 else "")
        print(f"  - 有resources_status: {has_resources_status} ({has_resources_status/total_concepts*100:.1f}%)" if total_concepts > 0 else "")
        print(f"  - 有quiz_status: {has_quiz_status} ({has_quiz_status/total_concepts*100:.1f}%)" if total_concepts > 0 else "")
        
        # 判断
        print("\n" + "="*80)
        if has_tutorial_id > 0 or has_resources_id > 0 or has_quiz_id > 0:
            print("✅ framework_data 包含内容引用 (content_refs)")
        else:
            print("❌ framework_data 不包含内容引用 (content_refs)")
            print("\n可能原因:")
            print("  1. 内容生成未完成")
            print("  2. update_framework_batch 未被调用")
            print("  3. Session 未正确 commit")
            print("  4. concept_id 不匹配")
        
        # 保存到文件
        output_file = f"framework_data_{roadmap_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(framework_data, f, ensure_ascii=False, indent=2)
        print(f"\n💾 完整的framework_data已保存到: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/check_framework_data.py <roadmap_id>")
        sys.exit(1)
    
    roadmap_id = sys.argv[1]
    asyncio.run(check_framework_data(roadmap_id))

