"""
检查任务恢复状态

检查任务的教程、资源、Quiz 是否已生成，以及 framework_data 和任务状态
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.repository_factory import RepositoryFactory


async def check_task_status(task_id: str):
    """检查任务状态"""
    repo_factory = RepositoryFactory()
    
    async with repo_factory.create_session() as session:
        # 1. 查询任务
        task_repo = repo_factory.create_task_repo(session)
        task = await task_repo.get_by_task_id(task_id)
        
        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            return
        
        print("=" * 80)
        print("📋 任务状态")
        print("=" * 80)
        print(f"任务 ID: {task.task_id}")
        print(f"路线图 ID: {task.roadmap_id}")
        print(f"状态: {task.status}")
        print(f"当前步骤: {task.current_step}")
        print(f"创建时间: {task.created_at}")
        print(f"更新时间: {task.updated_at}")
        if task.completed_at:
            print(f"完成时间: {task.completed_at}")
        if task.error_message:
            print(f"错误信息: {task.error_message}")
        print()
        
        # 2. 查询 roadmap_metadata
        roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
        roadmap = await roadmap_repo.get_by_roadmap_id(task.roadmap_id)
        
        if not roadmap:
            print(f"❌ 路线图 {task.roadmap_id} 不存在")
            return
        
        print("=" * 80)
        print("🗺️  路线图元数据")
        print("=" * 80)
        print(f"路线图 ID: {roadmap.roadmap_id}")
        print(f"标题: {roadmap.title}")
        
        framework_data = roadmap.framework_data or {}
        stages = framework_data.get("stages", [])
        
        total_concepts = 0
        completed_tutorials = 0
        completed_resources = 0
        completed_quizzes = 0
        
        for stage in stages:
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    total_concepts += 1
                    if concept.get("content_status") == "completed":
                        completed_tutorials += 1
                    if concept.get("resources_status") == "completed":
                        completed_resources += 1
                    if concept.get("quiz_status") == "completed":
                        completed_quizzes += 1
        
        print(f"\n📊 内容生成统计（从 framework_data）:")
        print(f"  总概念数: {total_concepts}")
        print(f"  教程已完成: {completed_tutorials}/{total_concepts}")
        print(f"  资源已完成: {completed_resources}/{total_concepts}")
        print(f"  测验已完成: {completed_quizzes}/{total_concepts}")
        print()
        
        # 3. 查询实际的教程、资源、Quiz 数据
        from sqlalchemy import select, func
        from app.models.database import TutorialMetadata, ResourceRecommendationMetadata, QuizMetadata
        
        # 教程
        tutorial_count = await session.scalar(
            select(func.count())
            .select_from(TutorialMetadata)
            .where(TutorialMetadata.roadmap_id == task.roadmap_id)
        ) or 0
        
        # 资源
        resource_count = await session.scalar(
            select(func.count())
            .select_from(ResourceRecommendationMetadata)
            .where(ResourceRecommendationMetadata.roadmap_id == task.roadmap_id)
        ) or 0
        
        # 测验
        quiz_count = await session.scalar(
            select(func.count())
            .select_from(QuizMetadata)
            .where(QuizMetadata.roadmap_id == task.roadmap_id)
        ) or 0
        
        print("=" * 80)
        print("📚 实际数据表统计")
        print("=" * 80)
        print(f"教程元数据记录数: {tutorial_count}")
        print(f"资源推荐元数据记录数: {resource_count}")
        print(f"测验元数据记录数: {quiz_count}")
        print()
        
        # 4. 对比分析
        print("=" * 80)
        print("🔍 问题分析")
        print("=" * 80)
        
        if tutorial_count > 0 and completed_tutorials < total_concepts:
            print(f"⚠️  教程已落表 ({tutorial_count} 条)，但 framework_data 未更新完全")
            print(f"   framework_data 中只有 {completed_tutorials}/{total_concepts} 个概念的 content_status 为 completed")
        
        if resource_count > 0 and completed_resources < total_concepts:
            print(f"⚠️  资源已落表 ({resource_count} 条)，但 framework_data 未更新完全")
            print(f"   framework_data 中只有 {completed_resources}/{total_concepts} 个概念的 resources_status 为 completed")
        
        if quiz_count > 0 and completed_quizzes < total_concepts:
            print(f"⚠️  测验已落表 ({quiz_count} 条)，但 framework_data 未更新完全")
            print(f"   framework_data 中只有 {completed_quizzes}/{total_concepts} 个概念的 quiz_status 为 completed")
        
        if task.status == "processing":
            print(f"⚠️  任务状态仍为 processing，应该更新为 completed 或 partial_failure")
        
        print()


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="检查任务恢复状态")
    parser.add_argument("task_id", help="任务 ID")
    
    args = parser.parse_args()
    
    await check_task_status(args.task_id)


if __name__ == "__main__":
    asyncio.run(main())

