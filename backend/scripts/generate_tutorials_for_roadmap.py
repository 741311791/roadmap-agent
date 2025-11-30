"""为现有路线图生成教程（不依赖 checkpointer）"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.database import RoadmapMetadata, RoadmapTask
from app.models.domain import RoadmapFramework, TutorialGenerationInput, Concept
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.core.tool_registry import tool_registry
import structlog

logger = structlog.get_logger()

# 确保工具注册表已初始化（通过导入 minio_init 模块）
from app.db import minio_init  # 触发工具注册


async def generate_tutorials_for_roadmap(roadmap_id: str):
    """为指定的路线图生成教程"""
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        
        # 获取路线图元数据
        metadata = await repo.get_roadmap_metadata(roadmap_id)
        if not metadata:
            print(f"路线图 {roadmap_id} 不存在")
            return
        
        # 从 JSON 数据重建 RoadmapFramework
        framework = RoadmapFramework.model_validate(metadata.framework_data)
        
        print(f"\n=== 为路线图生成教程 ===")
        print(f"Roadmap ID: {roadmap_id}")
        print(f"Title: {framework.title}")
        print(f"Task ID: {metadata.task_id}\n")
        
        # 提取所有 Concepts
        concepts_with_context = []
        for stage in framework.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    context = {
                        "roadmap_id": framework.roadmap_id,
                        "stage_id": stage.stage_id,
                        "stage_name": stage.name,
                        "module_id": module.module_id,
                        "module_name": module.name,
                    }
                    concepts_with_context.append((concept, context))
        
        print(f"共 {len(concepts_with_context)} 个概念需要生成教程\n")
        
        # 获取任务信息（用于用户偏好）
        task = await repo.get_task(metadata.task_id)
        if not task:
            print(f"任务 {metadata.task_id} 不存在")
            return
        
        # 从 user_request 中提取学习偏好
        user_request_dict = task.user_request
        from app.models.domain import LearningPreferences
        preferences = LearningPreferences.model_validate(user_request_dict.get("preferences", {}))
        
        # 创建 Tutorial Generator Agent
        generator = TutorialGeneratorAgent()
        
        # 逐个生成教程
        tutorial_refs = {}
        failed_concepts = []
        
        for i, (concept, context) in enumerate(concepts_with_context, 1):
            print(f"[{i}/{len(concepts_with_context)}] 正在生成教程: {concept.name} ({concept.concept_id})")
            
            try:
                generation_input = TutorialGenerationInput(
                    concept=concept,
                    context=context,
                    user_preferences=preferences,
                )
                tutorial_output = await generator.execute(generation_input)
                
                # 保存教程元数据到数据库
                await repo.save_tutorial_metadata(tutorial_output, roadmap_id)
                
                tutorial_refs[concept.concept_id] = tutorial_output
                print(f"  ✓ 成功生成并保存教程")
                print(f"    Content URL: {tutorial_output.content_url}\n")
                
            except Exception as e:
                logger.error(
                    "tutorial_generation_failed",
                    concept_id=concept.concept_id,
                    error=str(e),
                )
                failed_concepts.append(concept.concept_id)
                print(f"  ✗ 生成失败: {str(e)}\n")
        
        # 更新路线图框架中的 Concept 状态
        print("\n=== 更新路线图框架 ===")
        updated_framework = _update_concept_statuses(framework, tutorial_refs)
        
        # 保存更新后的框架
        await repo.save_roadmap_metadata(
            roadmap_id=roadmap_id,
            user_id=metadata.user_id,
            task_id=metadata.task_id,
            framework=updated_framework,
        )
        print(f"✓ 路线图框架已更新\n")
        
        await session.commit()
        
        # 更新任务状态
        if task.status != "completed":
            await repo.update_task_status(
                task_id=metadata.task_id,
                status="completed",
                current_step="completed",
                roadmap_id=roadmap_id,
            )
            await session.commit()
            print("✓ 任务状态已更新为 completed\n")
        
        print(f"\n=== 生成完成 ===")
        print(f"成功: {len(tutorial_refs)} 个")
        print(f"失败: {len(failed_concepts)} 个")
        if failed_concepts:
            print(f"失败的概念 ID: {', '.join(failed_concepts)}")


def _update_concept_statuses(
    framework: RoadmapFramework,
    tutorial_refs: dict,
) -> RoadmapFramework:
    """更新路线图框架中所有 Concept 的 content_status 和 content_ref"""
    from app.models.domain import Stage, Module
    
    updated_stages = []
    
    for stage in framework.stages:
        updated_modules = []
        for module in stage.modules:
            updated_concepts = []
            for concept in module.concepts:
                if concept.concept_id in tutorial_refs:
                    tutorial_output = tutorial_refs[concept.concept_id]
                    # 先获取字典，然后更新字段（避免重复参数）
                    concept_dict = concept.model_dump()
                    concept_dict.update({
                        "content_status": "completed",
                        "content_ref": tutorial_output.content_url,
                        "content_summary": tutorial_output.summary,
                    })
                    updated_concept = Concept(**concept_dict)
                    updated_concepts.append(updated_concept)
                else:
                    # 保持原状态
                    updated_concepts.append(concept)
            
            # 先获取字典，然后更新字段（避免重复参数）
            module_dict = module.model_dump()
            module_dict["concepts"] = updated_concepts
            updated_module = Module(**module_dict)
            updated_modules.append(updated_module)
        
        # 先获取字典，然后更新字段（避免重复参数）
        stage_dict = stage.model_dump()
        stage_dict["modules"] = updated_modules
        updated_stage = Stage(**stage_dict)
        updated_stages.append(updated_stage)
    
    # 先获取字典，然后更新字段（避免重复参数）
    framework_dict = framework.model_dump()
    framework_dict["stages"] = updated_stages
    return RoadmapFramework(**framework_dict)


async def generate_tutorials_for_all_pending():
    """为所有等待审核或没有教程的路线图生成教程"""
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        
        # 查询所有路线图元数据
        result = await session.execute(
            select(RoadmapMetadata).order_by(RoadmapMetadata.created_at.desc())
        )
        all_roadmaps = result.scalars().all()
        
        print(f"\n=== 找到 {len(all_roadmaps)} 个路线图 ===\n")
        
        for i, metadata in enumerate(all_roadmaps, 1):
            # 检查是否已有教程
            from app.models.database import TutorialMetadata
            result_tutorials = await session.execute(
                select(TutorialMetadata)
                .where(TutorialMetadata.roadmap_id == metadata.roadmap_id)
            )
            tutorials = result_tutorials.scalars().all()
            
            if len(tutorials) > 0:
                print(f"[{i}/{len(all_roadmaps)}] {metadata.roadmap_id}: 已有 {len(tutorials)} 个教程，跳过")
                continue
            
            print(f"[{i}/{len(all_roadmaps)}] {metadata.roadmap_id}: 没有教程，开始生成...\n")
            
            try:
                await generate_tutorials_for_roadmap(metadata.roadmap_id)
                print(f"✓ 完成\n")
            except Exception as e:
                logger.error(
                    "generate_tutorials_failed",
                    roadmap_id=metadata.roadmap_id,
                    error=str(e),
                )
                print(f"✗ 失败: {str(e)}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 为单个路线图生成教程
        roadmap_id = sys.argv[1]
        asyncio.run(generate_tutorials_for_roadmap(roadmap_id))
    else:
        # 为所有需要的路线图生成教程
        asyncio.run(generate_tutorials_for_all_pending())

