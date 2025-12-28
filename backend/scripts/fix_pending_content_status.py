#!/usr/bin/env python3
"""
修复内容生成完成但状态未同步的数据

问题描述：
- 内容生成阶段（tutorial/resource/quiz）已完成
- 但 roadmap_metadata.framework_data 中的 concept 状态未更新
- 任务状态未更新为 completed

此脚本会：
1. 查询所有已生成的 tutorial/resource/quiz 元数据
2. 按 roadmap_id 分组
3. 更新对应 roadmap_metadata.framework_data 中的 concept 状态
4. 更新任务状态为 completed

使用方法：
    # 方式1: 使用 Poetry（推荐）
    cd backend
    poetry run python scripts/fix_pending_content_status.py [--dry-run] [--roadmap-id ROADMAP_ID]
    
    # 方式2: 使用 uv
    cd backend
    uv run python scripts/fix_pending_content_status.py [--dry-run] [--roadmap-id ROADMAP_ID]
    
    # 方式3: 如果已激活虚拟环境
    cd backend
    python scripts/fix_pending_content_status.py [--dry-run] [--roadmap-id ROADMAP_ID]

参数：
    --dry-run: 只打印将要执行的操作，不实际修改数据库
    --roadmap-id: 只修复指定的 roadmap（可选）
"""
import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.models.database import (
    RoadmapMetadata,
    RoadmapTask,
    TutorialMetadata,
    ResourceRecommendationMetadata,
    QuizMetadata,
)
from app.models.domain import RoadmapFramework
from sqlalchemy.orm.attributes import flag_modified

logger = structlog.get_logger()


async def get_content_refs_by_roadmap(session, roadmap_id: str | None = None) -> dict:
    """
    获取所有内容元数据，按 roadmap_id 分组
    
    Returns:
        {
            roadmap_id: {
                "tutorials": {concept_id: TutorialMetadata, ...},
                "resources": {concept_id: ResourceRecommendationMetadata, ...},
                "quizzes": {concept_id: QuizMetadata, ...},
            },
            ...
        }
    """
    result = {}
    
    # 查询 tutorials
    tutorial_query = select(TutorialMetadata)
    if roadmap_id:
        tutorial_query = tutorial_query.where(TutorialMetadata.roadmap_id == roadmap_id)
    tutorials = (await session.execute(tutorial_query)).scalars().all()
    
    for t in tutorials:
        if t.roadmap_id not in result:
            result[t.roadmap_id] = {"tutorials": {}, "resources": {}, "quizzes": {}}
        result[t.roadmap_id]["tutorials"][t.concept_id] = t
    
    # 查询 resources
    resource_query = select(ResourceRecommendationMetadata)
    if roadmap_id:
        resource_query = resource_query.where(ResourceRecommendationMetadata.roadmap_id == roadmap_id)
    resources = (await session.execute(resource_query)).scalars().all()
    
    for r in resources:
        if r.roadmap_id not in result:
            result[r.roadmap_id] = {"tutorials": {}, "resources": {}, "quizzes": {}}
        result[r.roadmap_id]["resources"][r.concept_id] = r
    
    # 查询 quizzes
    quiz_query = select(QuizMetadata)
    if roadmap_id:
        quiz_query = quiz_query.where(QuizMetadata.roadmap_id == roadmap_id)
    quizzes = (await session.execute(quiz_query)).scalars().all()
    
    for q in quizzes:
        if q.roadmap_id not in result:
            result[q.roadmap_id] = {"tutorials": {}, "resources": {}, "quizzes": {}}
        result[q.roadmap_id]["quizzes"][q.concept_id] = q
    
    return result


def update_framework_concepts(
    framework_data: dict,
    tutorials: dict,
    resources: dict,
    quizzes: dict,
) -> tuple[dict, int]:
    """
    更新 framework_data 中的 concept 状态
    
    Returns:
        (updated_framework_data, updated_count)
    """
    updated_count = 0
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                concept_id = concept.get("concept_id")
                if not concept_id:
                    continue
                
                # 更新 tutorial 状态
                if concept_id in tutorials:
                    tutorial = tutorials[concept_id]
                    if concept.get("content_status") != "completed":
                        concept["content_status"] = "completed"
                        concept["content_ref"] = tutorial.content_url
                        concept["content_summary"] = tutorial.summary
                        updated_count += 1
                
                # 更新 resource 状态
                if concept_id in resources:
                    resource = resources[concept_id]
                    if concept.get("resources_status") != "completed":
                        concept["resources_status"] = "completed"
                        concept["resources_id"] = resource.id
                        # 优先使用 resources_count 字段，否则从 resources 列表计算
                        if hasattr(resource, "resources_count") and resource.resources_count:
                            concept["resources_count"] = resource.resources_count
                        else:
                            resources_list = resource.resources if isinstance(resource.resources, list) else []
                            concept["resources_count"] = len(resources_list)
                        updated_count += 1
                
                # 更新 quiz 状态
                if concept_id in quizzes:
                    quiz = quizzes[concept_id]
                    if concept.get("quiz_status") != "completed":
                        concept["quiz_status"] = "completed"
                        concept["quiz_id"] = quiz.quiz_id
                        # 优先使用 total_questions 字段，否则从 questions 列表计算
                        if hasattr(quiz, "total_questions") and quiz.total_questions:
                            concept["quiz_questions_count"] = quiz.total_questions
                        else:
                            questions_list = quiz.questions if isinstance(quiz.questions, list) else []
                            concept["quiz_questions_count"] = len(questions_list)
                        updated_count += 1
    
    return framework_data, updated_count


async def fix_roadmap_metadata(session, roadmap_id: str, content_refs: dict, dry_run: bool) -> bool:
    """
    修复单个 roadmap 的 framework_data
    
    Returns:
        True if fixed, False if skipped
    """
    # 获取 roadmap_metadata
    query = select(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == roadmap_id)
    metadata = (await session.execute(query)).scalar_one_or_none()
    
    if not metadata:
        print(f"  ⚠️ RoadmapMetadata not found for {roadmap_id}")
        return False
    
    if not metadata.framework_data:
        print(f"  ⚠️ No framework_data for {roadmap_id}")
        return False
    
    tutorials = content_refs.get("tutorials", {})
    resources = content_refs.get("resources", {})
    quizzes = content_refs.get("quizzes", {})
    
    print(f"  📊 Content counts: {len(tutorials)} tutorials, {len(resources)} resources, {len(quizzes)} quizzes")
    
    # 更新 framework_data
    updated_framework, updated_count = update_framework_concepts(
        metadata.framework_data,
        tutorials,
        resources,
        quizzes,
    )
    
    if updated_count == 0:
        print(f"  ✅ All concepts already up-to-date")
        return False
    
    print(f"  🔄 {updated_count} concept status(es) need updating")
    
    if not dry_run:
        # 更新数据库
        metadata.framework_data = updated_framework
        flag_modified(metadata, "framework_data")
        await session.commit()
        print(f"  ✅ framework_data updated")
    else:
        print(f"  [DRY RUN] Would update framework_data")
    
    return True


async def fix_task_status(session, roadmap_id: str, dry_run: bool) -> bool:
    """
    修复任务状态
    
    Returns:
        True if fixed, False if skipped
    """
    # 查询关联的任务
    query = select(RoadmapTask).where(RoadmapTask.roadmap_id == roadmap_id)
    task = (await session.execute(query)).scalar_one_or_none()
    
    if not task:
        print(f"  ⚠️ No task found for roadmap {roadmap_id}")
        return False
    
    print(f"  📋 Task {task.task_id}: status={task.status}, step={task.current_step}")
    
    if task.status == "completed" and task.current_step == "completed":
        print(f"  ✅ Task already completed")
        return False
    
    if not dry_run:
        task.status = "completed"
        task.current_step = "completed"
        await session.commit()
        print(f"  ✅ Task status updated to completed")
    else:
        print(f"  [DRY RUN] Would update task status to completed")
    
    return True


async def main(dry_run: bool, roadmap_id: str | None = None):
    """主函数"""
    print("=" * 60)
    print("🔧 修复内容生成状态同步问题")
    print("=" * 60)
    
    if dry_run:
        print("⚠️  DRY RUN MODE - 不会实际修改数据库")
    
    print()
    
    async with AsyncSessionLocal() as session:
        # 获取所有内容元数据
        print("📥 Fetching content metadata...")
        content_refs = await get_content_refs_by_roadmap(session, roadmap_id)
        
        if not content_refs:
            print("❌ No content metadata found")
            return
        
        print(f"📊 Found {len(content_refs)} roadmap(s) with content")
        print()
        
        fixed_frameworks = 0
        fixed_tasks = 0
        
        for rid, refs in content_refs.items():
            print(f"🗺️ Processing roadmap: {rid}")
            
            # 修复 framework_data
            if await fix_roadmap_metadata(session, rid, refs, dry_run):
                fixed_frameworks += 1
            
            # 修复任务状态
            if await fix_task_status(session, rid, dry_run):
                fixed_tasks += 1
            
            print()
        
        print("=" * 60)
        print("📊 Summary:")
        print(f"   - Roadmaps processed: {len(content_refs)}")
        print(f"   - Frameworks {'would be ' if dry_run else ''}updated: {fixed_frameworks}")
        print(f"   - Tasks {'would be ' if dry_run else ''}updated: {fixed_tasks}")
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="修复内容生成状态同步问题")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印将要执行的操作，不实际修改数据库",
    )
    parser.add_argument(
        "--roadmap-id",
        type=str,
        default=None,
        help="只修复指定的 roadmap（可选）",
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run, roadmap_id=args.roadmap_id))

