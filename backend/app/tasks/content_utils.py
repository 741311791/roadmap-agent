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


def parse_failed_concept(failed_item: str) -> tuple[str, str | None]:
    """
    解析失败项格式 (支持双格式向后兼容)
    
    格式 1 (旧): "concept_id" - 代表整个 Concept 失败
    格式 2 (新): "concept_id:content_type" - 代表特定内容类型失败
    
    Args:
        failed_item: 失败项字符串
        
    Returns:
        (concept_id, content_type | None)
        
    Examples:
        >>> parse_failed_concept("abc123")
        ("abc123", None)
        >>> parse_failed_concept("abc123:tutorial")
        ("abc123", "tutorial")
    """
    if ":" in failed_item:
        # 新格式: "concept_id:content_type"
        parts = failed_item.split(":", 1)
        return parts[0], parts[1]
    else:
        # 旧格式: "concept_id" (代表整个 Concept 失败)
        return failed_item, None


def update_framework_with_content_refs(
    framework_data: dict,
    tutorial_refs: dict,
    resource_refs: dict,
    quiz_refs: dict,
    failed_concepts: list,
) -> dict:
    """
    更新 framework 中所有 Concept 的内容引用字段
    
    支持双格式失败记录:
    - 旧格式: ["concept_id_1", "concept_id_2"]
    - 新格式: ["concept_id_1:tutorial", "concept_id_2:resources"]
    
    Args:
        framework_data: 原始 framework 字典数据
        tutorial_refs: 教程引用字典
        resource_refs: 资源引用字典
        quiz_refs: 测验引用字典
        failed_concepts: 失败的概念 ID 列表 (支持双格式)
        
    Returns:
        更新后的 framework 字典
    """
    # 解析失败概念列表，构建查找映射
    # failed_map: {concept_id: set(failed_content_types)}
    # None 表示所有内容类型失败（旧格式）
    failed_map: dict[str, set[str] | None] = {}
    for failed_item in failed_concepts:
        concept_id, content_type = parse_failed_concept(failed_item)
        
        if content_type is None:
            # 旧格式：整个 Concept 失败
            failed_map[concept_id] = None
        else:
            # 新格式：特定内容类型失败
            if concept_id not in failed_map:
                failed_map[concept_id] = set()
            if failed_map[concept_id] is not None:
                failed_map[concept_id].add(content_type)
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                concept_id = concept.get("concept_id")
                
                if not concept_id:
                    continue
                
                # 获取该 Concept 的失败内容类型集合
                failed_types = failed_map.get(concept_id)
                
                # 更新教程相关字段
                if concept_id in tutorial_refs:
                    tutorial_output = tutorial_refs[concept_id]
                    concept["content_status"] = "completed"
                    concept["tutorial_id"] = tutorial_output.tutorial_id
                    concept["content_ref"] = tutorial_output.content_url
                    concept["content_summary"] = tutorial_output.summary
                    concept["content_version"] = f"v{tutorial_output.content_version}"
                elif failed_types is None or "tutorial" in failed_types:
                    # failed_types is None: 旧格式，所有内容失败
                    # "tutorial" in failed_types: 新格式，tutorial 失败
                    if "content_status" not in concept or concept["content_status"] == "pending":
                        concept["content_status"] = "failed"
                
                # 更新资源相关字段
                if concept_id in resource_refs:
                    resource_output = resource_refs[concept_id]
                    concept["resources_status"] = "completed"
                    concept["resources_id"] = resource_output.id
                    concept["resources_count"] = len(resource_output.resources)
                elif failed_types is None or "resources" in failed_types:
                    if "resources_status" not in concept or concept["resources_status"] == "pending":
                        concept["resources_status"] = "failed"
                
                # 更新测验相关字段
                if concept_id in quiz_refs:
                    quiz_output = quiz_refs[concept_id]
                    concept["quiz_status"] = "completed"
                    concept["quiz_id"] = quiz_output.quiz_id
                    concept["quiz_questions_count"] = quiz_output.total_questions
                elif failed_types is None or "quiz" in failed_types:
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
    # 使用 Celery 专用的数据库连接管理，避免 Fork 进程继承问题
    # CeleryRepositoryFactory 已删除，直接使用 CRUD
    from app.crud.crud_roadmap import RoadmapCRUD
    from app.models.database import RoadmapMetadata
    from app.models.domain import RoadmapFramework
    
    roadmap_crud = RoadmapCRUD(RoadmapMetadata)
    
    async with get_celery_session() as session:
        # 获取当前路线图
        metadata = await roadmap_crud.get_by_roadmap_id(session, roadmap_id)
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


# ============================================================
# 单 Concept 重试任务（LangGraph 1.0 子图模式）
# ============================================================

from app.core.celery_app import celery_app
from app.models.domain import Concept, LearningPreferences
from app.db.celery_session import get_celery_session


@celery_app.task(
    name="content.retry_single_content",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=600,  # 10 分钟硬超时
    soft_time_limit=540,  # 9 分钟软超时
)
def retry_single_content(
    self,
    task_id: str,
    roadmap_id: str,
    concept_dict: dict,
    context: dict,
    preferences_dict: dict,
) -> dict:
    """
    单个 Concept 内容重试任务（调用子图）
    
    执行流程：
    1. 初始化 OrchestratorFactory
    2. 创建 WorkflowBrain 和 AgentFactory
    3. 构建内容生成子图
    4. 执行子图生成内容
    5. 批量保存数据库
    6. 更新 ConceptMetadata 状态
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        concept_dict: Concept 数据（字典格式）
        context: 上下文信息
        preferences_dict: 用户偏好（字典格式）
        
    Returns:
        dict: 执行结果
    """
    logger.info(
        "retry_single_content_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_id=concept_dict.get("concept_id"),
    )
    
    try:
        result = run_async(
            _retry_single_content_async(
                task_id, roadmap_id, concept_dict, context, preferences_dict
            )
        )
        
        logger.info(
            "retry_single_content_completed",
            task_id=task_id,
            success=result.get("success"),
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "retry_single_content_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        
        return {
            "success": False,
            "error": str(e),
        }


async def _retry_single_content_async(
    task_id: str,
    roadmap_id: str,
    concept_dict: dict,
    context: dict,
    preferences_dict: dict,
) -> dict:
    """
    异步执行单个 Concept 重试
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        concept_dict: Concept 数据
        context: 上下文信息
        preferences_dict: 用户偏好
        
    Returns:
        dict: 执行结果
    """
    from app.core.orchestrator_factory import OrchestratorFactory
    from app.core.orchestrator.workflow_brain import WorkflowBrain
    from app.core.orchestrator.subgraphs.content_generation import build_content_generation_subgraph
    from app.services.notification_service import notification_service
    from app.services.execution_logger import execution_logger
    
    # 初始化 Orchestrator
    factory = OrchestratorFactory()
    await factory.initialize()
    
    try:
        # 获取共享组件
        state_manager = factory.get_state_manager()
        agent_factory = factory._agent_factory
        
        # 创建 WorkflowBrain
        brain = WorkflowBrain(
            state_manager=state_manager,
            notification_service=notification_service,
            execution_logger=execution_logger,
            agent_factory=agent_factory,
        )
        
        # 构建子图
        subgraph = build_content_generation_subgraph()
        
        # 构造 Concept 对象
        concept = Concept(**concept_dict)
        preferences = LearningPreferences(**preferences_dict)
        
        # 准备子图输入状态
        sub_state = {
            "roadmap_id": roadmap_id,
            "concepts": [concept],  # 仅重试单个 Concept
            "user_preferences": preferences,
            "task_id": task_id,
            "brain": brain,
            "agent_factory": agent_factory,
            "concept": None,  # 用于 Send API
            "context": None,  # 用于 Send API
            "tutorials": [],
            "resources": [],
            "quizzes": [],
            "errors": [],
        }
        
        # 执行子图
        result = await subgraph.ainvoke(sub_state)
        
        # 批量保存数据库（重用 ContentRunner 的逻辑）
        from app.core.orchestrator.node_runners.content_runner import ContentRunner
        runner = ContentRunner(brain)
        await runner._save_all_content_metadata(roadmap_id, result)
        await runner._update_concept_metadata(roadmap_id, result)
        
        logger.info(
            "retry_single_content_db_saved",
            task_id=task_id,
            roadmap_id=roadmap_id,
            tutorial_count=len(result["tutorials"]),
            resource_count=len(result["resources"]),
            quiz_count=len(result["quizzes"]),
            error_count=len(result["errors"]),
        )
        
        return {
            "success": True,
            "tutorial_count": len(result["tutorials"]),
            "resource_count": len(result["resources"]),
            "quiz_count": len(result["quizzes"]),
            "error_count": len(result["errors"]),
        }
        
    finally:
        # 清理 Orchestrator Factory
        await factory.cleanup()

