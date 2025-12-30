"""
内容生成工具函数

提供内容生成任务的通用工具和辅助方法。
"""
import asyncio
import structlog

logger = structlog.get_logger()

# 每个 Worker 进程的事件循环（懒加载）
_worker_loop = None


def get_worker_loop():
    """
    获取或创建 Worker 进程的事件循环
    
    每个 Worker 进程维护一个独立的事件循环，
    不在任务结束时关闭，避免连接清理问题。
    
    Returns:
        asyncio.AbstractEventLoop: Worker 进程的事件循环
    """
    global _worker_loop
    
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
        logger.debug("celery_worker_loop_created", loop_id=id(_worker_loop))
    
    return _worker_loop


def run_async(coro):
    """
    在同步上下文中运行异步协程
    
    使用 Worker 进程级别的事件循环，避免频繁创建/销毁循环。
    
    Args:
        coro: 异步协程对象
        
    Returns:
        协程的返回值
    """
    loop = get_worker_loop()
    return loop.run_until_complete(coro)


def update_framework_with_content_refs(
    framework_data: dict,
    tutorial_refs: dict,
    resource_refs: dict,
    quiz_refs: dict,
    failed_concepts: list,
) -> dict:
    """
    更新 framework 中所有 Concept 的内容引用字段
    
    Args:
        framework_data: 原始 framework 字典数据
        tutorial_refs: 教程引用字典
        resource_refs: 资源引用字典
        quiz_refs: 测验引用字典
        failed_concepts: 失败的概念 ID 列表
        
    Returns:
        更新后的 framework 字典
    """
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                concept_id = concept.get("concept_id")
                
                if not concept_id:
                    continue
                
                # 更新教程相关字段
                if concept_id in tutorial_refs:
                    tutorial_output = tutorial_refs[concept_id]
                    concept["content_status"] = "completed"
                    concept["tutorial_id"] = tutorial_output.tutorial_id
                    concept["content_ref"] = tutorial_output.content_url
                    concept["content_summary"] = tutorial_output.summary
                    concept["content_version"] = f"v{tutorial_output.content_version}"
                elif concept_id in failed_concepts:
                    if "content_status" not in concept or concept["content_status"] == "pending":
                        concept["content_status"] = "failed"
                
                # 更新资源相关字段
                if concept_id in resource_refs:
                    resource_output = resource_refs[concept_id]
                    concept["resources_status"] = "completed"
                    concept["resources_id"] = resource_output.id
                    concept["resources_count"] = len(resource_output.resources)
                elif concept_id in failed_concepts:
                    if "resources_status" not in concept or concept["resources_status"] == "pending":
                        concept["resources_status"] = "failed"
                
                # 更新测验相关字段
                if concept_id in quiz_refs:
                    quiz_output = quiz_refs[concept_id]
                    concept["quiz_status"] = "completed"
                    concept["quiz_id"] = quiz_output.quiz_id
                    concept["quiz_questions_count"] = quiz_output.total_questions
                elif concept_id in failed_concepts:
                    if "quiz_status" not in concept or concept["quiz_status"] == "pending":
                        concept["quiz_status"] = "failed"
    
    return framework_data


async def update_concept_status_in_framework(
    roadmap_id: str,
    concept_id: str,
    content_type: str,
    status: str,
    result: dict | None = None,
):
    """
    更新路线图 framework 中特定概念的内容状态
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        content_type: 内容类型 ('tutorial', 'resources', 'quiz')
        status: 新状态 ('generating', 'completed', 'failed')
        result: 生成结果数据（可选）
    """
    from app.db.repository_factory import RepositoryFactory
    from app.db.repositories.roadmap_repo import RoadmapRepository
    from app.models.domain import RoadmapFramework
    
    async with RepositoryFactory().create_session() as session:
        repo = RoadmapRepository(session)
        
        # 获取当前路线图
        metadata = await repo.get_roadmap_metadata(roadmap_id)
        if not metadata or not metadata.framework_data:
            logger.warning(
                "roadmap_not_found_for_status_update",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            return
        
        framework_data = metadata.framework_data
        
        # 查找并更新概念
        status_field = f"{content_type}_status" if content_type != "tutorial" else "content_status"
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    if concept.get("concept_id") == concept_id:
                        concept[status_field] = status
                        
                        if result and status == "completed":
                            concept.update(result)
                        
                        logger.info(
                            "concept_status_updated",
                            roadmap_id=roadmap_id,
                            concept_id=concept_id,
                            content_type=content_type,
                            status=status,
                        )
                        break
        
        # 保存更新
        framework_obj = RoadmapFramework.model_validate(framework_data)
        await repo.save_roadmap_metadata(
            roadmap_id=roadmap_id,
            user_id=metadata.user_id,
            framework=framework_obj,
        )
        await session.commit()

