"""
修复 roadmap_metadata 中的 concept 状态

问题：当单独生成 tutorial_metadata, resource_recommendation_metadata, quiz_metadata 时，
     roadmap_metadata 的 framework_data 中的 concept 状态没有同步更新。

解决方案：读取各个元数据表，同步更新 roadmap_metadata 中的 concept 状态。
"""
import asyncio
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import async_session_maker
from app.models.database import (
    RoadmapMetadata,
    TutorialMetadata,
    ResourceRecommendationMetadata,
    QuizMetadata,
)
from app.models.domain import RoadmapFramework

logger = structlog.get_logger()


async def fix_roadmap_metadata_status(
    roadmap_id: str | None = None,
    dry_run: bool = False
):
    """
    修复 roadmap_metadata 中的 concept 状态
    
    Args:
        roadmap_id: 如果指定，只修复该路线图；否则修复所有路线图
        dry_run: 如果为 True，只显示将要修改的内容，不实际保存
    """
    async with async_session_maker.begin() as session:
        # 查询需要修复的路线图
        query = select(RoadmapMetadata)
        if roadmap_id:
            query = query.where(RoadmapMetadata.roadmap_id == roadmap_id)
        
        result = await session.execute(query)
        roadmaps = result.scalars().all()
        
        if not roadmaps:
            print(f"❌ 没有找到路线图{f' (ID: {roadmap_id})' if roadmap_id else ''}")
            return
        
        print(f"📊 找到 {len(roadmaps)} 个路线图需要检查")
        print()
        
        for roadmap in roadmaps:
            await fix_single_roadmap(session, roadmap, dry_run)
        
        if not dry_run:
            await session.commit()
            print("✅ 所有修复已保存到数据库")
        else:
            print("🔍 这是预览模式，没有实际修改数据库")


async def fix_single_roadmap(
    session: AsyncSession,
    roadmap: RoadmapMetadata,
    dry_run: bool
):
    """修复单个路线图的 concept 状态"""
    roadmap_id = roadmap.roadmap_id
    print(f"🔧 正在处理路线图: {roadmap_id}")
    
    try:
        # 解析 framework_data
        framework = RoadmapFramework.model_validate(roadmap.framework_data)
        
        # 统计
        total_concepts = 0
        updated_concepts = 0
        changes = {
            "tutorial": {"pending_to_completed": 0, "already_completed": 0},
            "resources": {"pending_to_completed": 0, "already_completed": 0},
            "quiz": {"pending_to_completed": 0, "already_completed": 0},
        }
        
        # 查询该路线图的所有元数据
        tutorials_query = select(TutorialMetadata).where(
            TutorialMetadata.roadmap_id == roadmap_id
        )
        resources_query = select(ResourceRecommendationMetadata).where(
            ResourceRecommendationMetadata.roadmap_id == roadmap_id
        )
        quizzes_query = select(QuizMetadata).where(
            QuizMetadata.roadmap_id == roadmap_id
        )
        
        tutorials_result = await session.execute(tutorials_query)
        resources_result = await session.execute(resources_query)
        quizzes_result = await session.execute(quizzes_query)
        
        tutorials = {t.concept_id: t for t in tutorials_result.scalars().all()}
        resources = {r.concept_id: r for r in resources_result.scalars().all()}
        quizzes = {q.concept_id: q for q in quizzes_result.scalars().all()}
        
        print(f"   📝 找到元数据: {len(tutorials)} 个教程, {len(resources)} 个资源推荐, {len(quizzes)} 个测验")
        
        # 遍历 framework 中的所有 concept
        for stage in framework.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    total_concepts += 1
                    concept_id = concept.concept_id
                    concept_updated = False
                    
                    # 检查并更新教程状态
                    if concept_id in tutorials:
                        if concept.content_status == "pending":
                            tutorial = tutorials[concept_id]
                            concept.content_status = "completed"
                            # 更新引用信息
                            if tutorial.tutorial_id:
                                concept.content_ref = tutorial.tutorial_id
                            if hasattr(tutorial, 'summary') and tutorial.summary:
                                concept.content_summary = tutorial.summary
                            changes["tutorial"]["pending_to_completed"] += 1
                            concept_updated = True
                            print(f"   ✓ 更新概念 {concept_id} 的教程状态: pending → completed")
                        else:
                            changes["tutorial"]["already_completed"] += 1
                    
                    # 检查并更新资源推荐状态
                    if concept_id in resources:
                        if concept.resources_status == "pending":
                            resource = resources[concept_id]
                            concept.resources_status = "completed"
                            # 更新引用信息
                            if hasattr(resource, 'id') and resource.id:
                                concept.resources_id = resource.id
                            if hasattr(resource, 'resources') and resource.resources:
                                concept.resources_count = len(resource.resources)
                            elif hasattr(resource, 'resources_count') and resource.resources_count:
                                concept.resources_count = resource.resources_count
                            changes["resources"]["pending_to_completed"] += 1
                            concept_updated = True
                            print(f"   ✓ 更新概念 {concept_id} 的资源推荐状态: pending → completed")
                        else:
                            changes["resources"]["already_completed"] += 1
                    
                    # 检查并更新测验状态
                    if concept_id in quizzes:
                        if concept.quiz_status == "pending":
                            quiz = quizzes[concept_id]
                            concept.quiz_status = "completed"
                            # 更新引用信息
                            if hasattr(quiz, 'quiz_id') and quiz.quiz_id:
                                concept.quiz_id = quiz.quiz_id
                            if hasattr(quiz, 'total_questions') and quiz.total_questions:
                                concept.quiz_questions_count = quiz.total_questions
                            elif hasattr(quiz, 'questions') and quiz.questions:
                                concept.quiz_questions_count = len(quiz.questions)
                            changes["quiz"]["pending_to_completed"] += 1
                            concept_updated = True
                            print(f"   ✓ 更新概念 {concept_id} 的测验状态: pending → completed")
                        else:
                            changes["quiz"]["already_completed"] += 1
                    
                    if concept_updated:
                        updated_concepts += 1
        
        # 打印统计信息
        print()
        print(f"   📊 统计信息:")
        print(f"      - 总概念数: {total_concepts}")
        print(f"      - 更新概念数: {updated_concepts}")
        print(f"      - 教程: {changes['tutorial']['pending_to_completed']} 个更新, {changes['tutorial']['already_completed']} 个已完成")
        print(f"      - 资源: {changes['resources']['pending_to_completed']} 个更新, {changes['resources']['already_completed']} 个已完成")
        print(f"      - 测验: {changes['quiz']['pending_to_completed']} 个更新, {changes['quiz']['already_completed']} 个已完成")
        
        # 如果有更新，保存到数据库
        if updated_concepts > 0 and not dry_run:
            roadmap.framework_data = framework.model_dump(mode='json')
            await session.flush()
            print(f"   ✅ 已保存更新到数据库")
        elif updated_concepts > 0:
            print(f"   🔍 预览模式：将会更新 {updated_concepts} 个概念")
        else:
            print(f"   ℹ️  没有需要更新的概念")
        
        print()
        
    except Exception as e:
        print(f"   ❌ 处理路线图 {roadmap_id} 时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        print()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="修复 roadmap_metadata 中的 concept 状态"
    )
    parser.add_argument(
        "--roadmap-id",
        type=str,
        help="要修复的路线图 ID（如果不指定，将修复所有路线图）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际修改数据库"
    )
    
    args = parser.parse_args()
    
    print("🚀 开始修复 roadmap_metadata 状态同步问题")
    print()
    
    if args.dry_run:
        print("🔍 运行在预览模式（--dry-run）")
    if args.roadmap_id:
        print(f"🎯 目标路线图: {args.roadmap_id}")
    else:
        print("🌐 将检查所有路线图")
    print()
    
    await fix_roadmap_metadata_status(
        roadmap_id=args.roadmap_id,
        dry_run=args.dry_run
    )
    
    print()
    print("🎉 完成！")


if __name__ == "__main__":
    asyncio.run(main())
