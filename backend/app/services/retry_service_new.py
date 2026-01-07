"""
重试服务（符合架构规范的版本）

处理失败内容的重试逻辑：
- 批量重试失败内容
- 重新生成概念内容
- 智能重试任务（checkpoint/content）
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid

from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_task import TaskCRUD
from app.crud.crud_concept import ConceptCRUD
from app.models.database import RoadmapMetadata, RoadmapTask, ConceptMetadata
from app.models.domain import LearningPreferences

logger = structlog.get_logger()


class RetryService:
    """
    重试服务
    
    职责：
    - 识别失败的内容项
    - 创建重试任务
    - 调度后台任务执行
    """
    
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.task_crud = TaskCRUD(RoadmapTask)
        self.concept_crud = ConceptCRUD(ConceptMetadata)
    
    async def prepare_retry_failed_content(
        self,
        session: AsyncSession,
        roadmap_id: str,
        content_types: list[str],
    ) -> dict:
        """
        准备重试失败内容的数据
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            content_types: 要重试的内容类型列表
            
        Returns:
            包含失败项目和任务ID的字典
            
        Raises:
            ValueError: 路线图不存在
        """
        # 检查路线图是否存在
        roadmap_metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        if not roadmap_metadata:
            raise ValueError(f"路线图 {roadmap_id} 不存在")
        
        # 获取失败的内容项目（使用细粒度检测）
        failed_items = await self._get_failed_content_items_v2(session, roadmap_id)
        
        # 如果返回为空，降级到旧逻辑
        if not any(failed_items.values()):
            logger.info(
                "fallback_to_old_failed_detection",
                roadmap_id=roadmap_id,
                message="concept_metadata 为空,使用 framework_data 作为降级方案"
            )
            failed_items = self._get_failed_content_items_from_framework(
                roadmap_metadata.framework_data
            )
        
        # 根据请求筛选要重试的类型
        items_to_retry = {}
        total_items = 0
        for content_type in content_types:
            if content_type in failed_items and failed_items[content_type]:
                items_to_retry[content_type] = failed_items[content_type]
                total_items += len(failed_items[content_type])
        
        # 创建重试任务ID
        retry_task_id = str(uuid.uuid4())
        
        return {
            "retry_task_id": retry_task_id,
            "roadmap_id": roadmap_id,
            "items_to_retry": items_to_retry,
            "total_items": total_items,
            "failed_counts": {
                "tutorial": len(failed_items.get("tutorial", [])),
                "resources": len(failed_items.get("resources", [])),
                "quiz": len(failed_items.get("quiz", [])),
            }
        }
    
    async def prepare_regenerate_content(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> dict:
        """
        准备重新生成概念内容的数据
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            
        Returns:
            包含路线图和概念信息的字典
            
        Raises:
            ValueError: 路线图或概念不存在
        """
        # 检查路线图是否存在
        roadmap_metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        if not roadmap_metadata:
            raise ValueError(f"路线图 {roadmap_id} 不存在")
        
        # TODO: 实现完整的重新生成逻辑
        return {
            "roadmap_id": roadmap_id,
            "concept_id": concept_id,
        }
    
    async def prepare_retry_task(
        self,
        session: AsyncSession,
        task_id: str,
        force_checkpoint: bool = False,
    ) -> dict:
        """
        准备基于任务ID的重试
        
        判断使用checkpoint恢复还是内容重试
        
        Args:
            session: 数据库会话
            task_id: 任务 ID
            force_checkpoint: 强制使用checkpoint恢复
            
        Returns:
            重试策略和相关数据
            
        Raises:
            ValueError: 任务不存在或无法重试
        """
        # 查询任务记录
        task = await self.task_crud.get_by_task_id(session, task_id)
        
        if not task:
            raise ValueError(f"任务 {task_id} 不存在")
        
        # 检查 checkpoint 是否存在
        checkpoint_exists = await self._check_checkpoint_exists(task_id)
        checkpoint_step = None
        
        if checkpoint_exists:
            checkpoint_step = await self._get_checkpoint_step(task_id)
        
        # 判断重试策略
        EARLY_STAGE_STEPS = [
            "init", "queued", "intent_analysis", "curriculum_design",
            "structure_validation", "roadmap_edit", "human_review"
        ]
        
        CONTENT_GENERATION_STEPS = ["content_generation_queued"]
        
        is_early_stage = (
            task.current_step in EARLY_STAGE_STEPS or
            (checkpoint_step and checkpoint_step in EARLY_STAGE_STEPS)
        )
        
        is_content_generation = (
            task.current_step in CONTENT_GENERATION_STEPS or
            (checkpoint_step and checkpoint_step in CONTENT_GENERATION_STEPS)
        )
        
        is_cancelled = task.status == "cancelled"
        
        # 策略决策
        use_checkpoint_recovery = (
            checkpoint_exists and (
                force_checkpoint or
                (is_early_stage and not is_content_generation) or
                (is_cancelled and not is_content_generation)
            )
        )
        
        if use_checkpoint_recovery:
            return {
                "strategy": "checkpoint",
                "task": task,
                "checkpoint_step": checkpoint_step,
            }
        else:
            # 检查是否有 roadmap_id
            if not task.roadmap_id:
                raise ValueError("任务尚未生成路线图，无法进行内容重试")
            
            # 获取失败的内容项目
            failed_items = await self._get_failed_content_items_v2(session, task.roadmap_id)
            
            # 降级方案
            if not any(failed_items.values()):
                roadmap_metadata = await self.roadmap_crud.get_by_roadmap_id(session, task.roadmap_id)
                if roadmap_metadata:
                    failed_items = self._get_failed_content_items_from_framework(
                        roadmap_metadata.framework_data
                    )
            
            return {
                "strategy": "content_retry",
                "task": task,
                "failed_items": failed_items,
            }
    
    async def _get_checkpoint_step(self, task_id: str) -> Optional[str]:
        """获取checkpoint的当前步骤"""
        try:
            from app.core.orchestrator_factory import OrchestratorFactory
            
            checkpointer = OrchestratorFactory.get_checkpointer()
            config = {"configurable": {"thread_id": task_id}}
            checkpoint_tuple = await checkpointer.aget_tuple(config)
            
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
                return channel_values.get("current_step")
        except Exception as e:
            logger.warning("get_checkpoint_step_failed", task_id=task_id, error=str(e))
        
        return None
    
    async def _get_failed_content_items_v2(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> dict:
        """
        从 concept_metadata 表中获取失败的内容项（细粒度检测）
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            
        Returns:
            失败项目字典 {"tutorial": [...], "resources": [...], "quiz": [...]}
        """
        concept_metas = await self.concept_crud.get_by_roadmap(session, roadmap_id)
        
        failed_items = {
            "tutorial": [],
            "resources": [],
            "quiz": [],
        }
        
        for meta in concept_metas:
            if meta.tutorial_status == "failed":
                failed_items["tutorial"].append({
                    "concept_id": meta.concept_id,
                    "concept_data": {},  # 需要从framework_data获取
                    "context": {},
                })
            
            if meta.resources_status == "failed":
                failed_items["resources"].append({
                    "concept_id": meta.concept_id,
                    "concept_data": {},
                    "context": {},
                })
            
            if meta.quiz_status == "failed":
                failed_items["quiz"].append({
                    "concept_id": meta.concept_id,
                    "concept_data": {},
                    "context": {},
                })
        
        return failed_items
    
    def _get_failed_content_items_from_framework(self, framework_data: dict) -> dict:
        """
        从 framework_data 中获取失败的内容项（降级方案）
        
        Args:
            framework_data: 路线图框架数据
            
        Returns:
            失败项目字典
        """
        failed_items = {
            "tutorial": [],
            "resources": [],
            "quiz": [],
        }
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    
                    if concept.get("content_status") == "failed":
                        failed_items["tutorial"].append({
                            "concept_id": concept_id,
                            "concept_data": concept,
                            "context": {"stage": stage, "module": module},
                        })
                    
                    if concept.get("resources_status") == "failed":
                        failed_items["resources"].append({
                            "concept_id": concept_id,
                            "concept_data": concept,
                            "context": {"stage": stage, "module": module},
                        })
                    
                    if concept.get("quiz_status") == "failed":
                        failed_items["quiz"].append({
                            "concept_id": concept_id,
                            "concept_data": concept,
                            "context": {"stage": stage, "module": module},
                        })
        
        return failed_items
    
    async def _check_checkpoint_exists(self, task_id: str) -> bool:
        """
        检查 LangGraph checkpoint 是否存在
        
        Args:
            task_id: 任务 ID
            
        Returns:
            checkpoint是否存在
        """
        try:
            from app.core.orchestrator_factory import OrchestratorFactory
            
            checkpointer = OrchestratorFactory.get_checkpointer()
            config = {"configurable": {"thread_id": task_id}}
            checkpoint_tuple = await checkpointer.aget_tuple(config)
            
            return checkpoint_tuple is not None and checkpoint_tuple.checkpoint is not None
        except Exception as e:
            logger.warning(
                "checkpoint_check_failed",
                task_id=task_id,
                error=str(e),
            )
            return False


def get_retry_service() -> RetryService:
    """获取RetryService实例"""
    return RetryService()

