"""
验证 framework_data 同步情况

检查 framework_data 中是否正确设置了所有引用字段
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.repository_factory import RepositoryFactory


async def verify_sync(task_id: str):
    """验证同步情况"""
    repo_factory = RepositoryFactory()
    
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
        
        # 获取任务
        task = await task_repo.get_by_task_id(task_id)
        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            return
        
        # 获取路线图
        roadmap = await roadmap_repo.get_by_roadmap_id(task.roadmap_id)
        if not roadmap:
            print(f"❌ 路线图 {task.roadmap_id} 不存在")
            return
        
        framework_data = roadmap.framework_data or {}
        
        print("=" * 80)
        print("🔍 验证 framework_data 同步情况")
        print("=" * 80)
        print()
        
        total_concepts = 0
        completed_count = 0
        failed_count = 0
        concepts_with_refs = 0
        
        for stage_idx, stage in enumerate(framework_data.get("stages", []), 1):
            print(f"📚 Stage {stage_idx}: {stage.get('title', 'N/A')}")
            
            for module_idx, module in enumerate(stage.get("modules", []), 1):
                print(f"  📖 Module {module_idx}: {module.get('title', 'N/A')}")
                
                for concept_idx, concept in enumerate(module.get("concepts", []), 1):
                    total_concepts += 1
                    concept_id = concept.get("concept_id", "N/A")
                    title = concept.get("title", "N/A")
                    
                    # 状态
                    content_status = concept.get("content_status", "pending")
                    resources_status = concept.get("resources_status", "pending")
                    quiz_status = concept.get("quiz_status", "pending")
                    
                    # 引用字段
                    tutorial_id = concept.get("tutorial_id")
                    resources_id = concept.get("resources_id")
                    quiz_id = concept.get("quiz_id")
                    content_ref = concept.get("content_ref")
                    
                    # 统计
                    if content_status == "completed":
                        completed_count += 1
                    if content_status == "failed":
                        failed_count += 1
                    
                    # 检查引用完整性
                    has_all_refs = tutorial_id and resources_id and quiz_id
                    if has_all_refs:
                        concepts_with_refs += 1
                    
                    # 显示信息
                    status_emoji = "✅" if content_status == "completed" else "❌"
                    refs_emoji = "🔗" if has_all_refs else "⚠️ "
                    
                    print(f"    {status_emoji} {refs_emoji} Concept {concept_idx}: {title[:40]}")
                    print(f"       ID: {concept_id}")
                    print(f"       状态: T:{content_status} / R:{resources_status} / Q:{quiz_status}")
                    
                    if content_status == "completed":
                        print(f"       引用: tutorial_id={'✓' if tutorial_id else '✗'} | "
                              f"resources_id={'✓' if resources_id else '✗'} | "
                              f"quiz_id={'✓' if quiz_id else '✗'}")
                        if content_ref:
                            print(f"       内容: {content_ref[:60]}...")
                    
                    print()
        
        print("=" * 80)
        print("📊 统计摘要")
        print("=" * 80)
        print(f"总概念数: {total_concepts}")
        print(f"已完成: {completed_count} ({completed_count/total_concepts*100:.1f}%)")
        print(f"失败: {failed_count}")
        print(f"包含完整引用: {concepts_with_refs}/{completed_count}")
        print()
        
        if concepts_with_refs == completed_count:
            print("✅ 所有已完成的概念都包含完整的引用字段！")
        else:
            missing = completed_count - concepts_with_refs
            print(f"⚠️  有 {missing} 个已完成的概念缺少引用字段")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="验证 framework_data 同步情况")
    parser.add_argument("task_id", help="任务 ID")
    
    args = parser.parse_args()
    
    await verify_sync(args.task_id)


if __name__ == "__main__":
    asyncio.run(main())

