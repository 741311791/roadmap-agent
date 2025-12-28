"""
同步任务结果到 framework_data

将已生成的教程、资源、Quiz 数据同步到 roadmap_metadata 的 framework_data 中，
并更新任务状态。

适用场景：
- 任务恢复后，数据已生成但 framework_data 未更新
- 数据库中有教程/资源/Quiz 记录，但路线图状态未同步
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from sqlalchemy import select
from app.db.repository_factory import RepositoryFactory
from app.models.database import TutorialMetadata, ResourceRecommendationMetadata, QuizMetadata
from app.models.domain import RoadmapFramework

logger = structlog.get_logger()


async def sync_task_results(task_id: str):
    """
    同步任务结果到 framework_data
    
    Args:
        task_id: 任务 ID
    """
    repo_factory = RepositoryFactory()
    
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
        
        # 1. 获取任务信息
        task = await task_repo.get_by_task_id(task_id)
        if not task:
            print(f"❌ 任务 {task_id} 不存在")
            return
        
        roadmap_id = task.roadmap_id
        
        print(f"📋 任务信息:")
        print(f"   任务 ID: {task_id}")
        print(f"   路线图 ID: {roadmap_id}")
        print(f"   当前状态: {task.status}")
        print(f"   当前步骤: {task.current_step}")
        print()
        
        # 2. 获取路线图元数据
        roadmap = await roadmap_repo.get_by_roadmap_id(roadmap_id)
        if not roadmap:
            print(f"❌ 路线图 {roadmap_id} 不存在")
            return
        
        framework_data = roadmap.framework_data or {}
        
        # 3. 查询已生成的教程
        tutorials_result = await session.execute(
            select(TutorialMetadata)
            .where(TutorialMetadata.roadmap_id == roadmap_id)
        )
        tutorials = {t.concept_id: t for t in tutorials_result.scalars().all()}
        
        # 4. 查询已生成的资源
        resources_result = await session.execute(
            select(ResourceRecommendationMetadata)
            .where(ResourceRecommendationMetadata.roadmap_id == roadmap_id)
        )
        resources = {r.concept_id: r for r in resources_result.scalars().all()}
        
        # 5. 查询已生成的测验
        quizzes_result = await session.execute(
            select(QuizMetadata)
            .where(QuizMetadata.roadmap_id == roadmap_id)
        )
        quizzes = {q.concept_id: q for q in quizzes_result.scalars().all()}
        
        print(f"📊 已生成的内容:")
        print(f"   教程: {len(tutorials)} 条")
        print(f"   资源: {len(resources)} 条")
        print(f"   测验: {len(quizzes)} 条")
        print()
        
        # 6. 更新 framework_data 中的概念状态
        updated_count = 0
        failed_concepts = []
        total_concepts = 0
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    total_concepts += 1
                    concept_id = concept.get("concept_id")
                    
                    # 更新教程状态
                    if concept_id in tutorials:
                        tutorial = tutorials[concept_id]
                        concept["content_status"] = "completed"
                        concept["content_ref"] = tutorial.content_url  # S3 URL 或 Key
                        concept["tutorial_id"] = tutorial.tutorial_id
                        updated_count += 1
                    else:
                        concept["content_status"] = "failed"
                        failed_concepts.append(concept_id)
                    
                    # 更新资源状态
                    if concept_id in resources:
                        resource = resources[concept_id]
                        concept["resources_status"] = "completed"
                        concept["resources_id"] = resource.id  # 使用 id 字段
                        concept["resources_count"] = resource.resources_count or 0
                        updated_count += 1
                    else:
                        concept["resources_status"] = "failed"
                        if concept_id not in failed_concepts:
                            failed_concepts.append(concept_id)
                    
                    # 更新测验状态
                    if concept_id in quizzes:
                        quiz = quizzes[concept_id]
                        concept["quiz_status"] = "completed"
                        concept["quiz_id"] = quiz.quiz_id
                        concept["quiz_questions_count"] = quiz.total_questions or 0
                        updated_count += 1
                    else:
                        concept["quiz_status"] = "failed"
                        if concept_id not in failed_concepts:
                            failed_concepts.append(concept_id)
        
        print(f"🔄 更新 framework_data:")
        print(f"   总概念数: {total_concepts}")
        print(f"   更新状态数: {updated_count}")
        print(f"   失败概念数: {len(failed_concepts)}")
        if failed_concepts:
            print(f"   失败概念 ID: {failed_concepts[:5]}{'...' if len(failed_concepts) > 5 else ''}")
        print()
        
        # 7. 保存更新后的 framework_data
        updated_framework = RoadmapFramework.model_validate(framework_data)
        await roadmap_repo.update_framework_data(
            roadmap_id=roadmap_id,
            framework=updated_framework,
        )
        
        print("✅ framework_data 已更新")
        print()
        
        # 8. 更新任务状态
        final_status = "partial_failure" if failed_concepts else "completed"
        final_step = "content_generation" if failed_concepts else "completed"
        
        await task_repo.update_task_status(
            task_id=task_id,
            status=final_status,
            current_step=final_step,
            failed_concepts={
                "count": len(failed_concepts),
                "concept_ids": failed_concepts,
            } if failed_concepts else None,
            execution_summary={
                "tutorial_count": len(tutorials),
                "resource_count": len(resources),
                "quiz_count": len(quizzes),
                "failed_count": len(failed_concepts),
            },
        )
        
        await session.commit()
        
        print(f"✅ 任务状态已更新:")
        print(f"   状态: {final_status}")
        print(f"   步骤: {final_step}")
        print()
        
        # 9. 发送完成通知
        try:
            from app.services.notification_service import notification_service
            
            if failed_concepts:
                await notification_service.notify_task_partial_failure(
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                    failed_count=len(failed_concepts),
                    total_count=total_concepts,
                )
            else:
                await notification_service.notify_task_completed(
                    task_id=task_id,
                    roadmap_id=roadmap_id,
                )
            
            print("✅ WebSocket 通知已发送")
        except Exception as e:
            logger.warning(
                "notification_failed",
                error=str(e),
            )
            print(f"⚠️  WebSocket 通知发送失败: {str(e)}")
        
        print()
        print("🎉 同步完成！")


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="同步任务结果到 framework_data")
    parser.add_argument("task_id", help="任务 ID")
    
    args = parser.parse_args()
    
    await sync_task_results(args.task_id)


if __name__ == "__main__":
    asyncio.run(main())

