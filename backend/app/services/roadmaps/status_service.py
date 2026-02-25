"""
路线图状态查询服务
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_task import TaskCRUD
from app.models.database import RoadmapMetadata, RoadmapTask

logger = structlog.get_logger()

# 内容生成阶段的步骤列表
CONTENT_GENERATION_STEPS = {
    "content_generation",
    "content_generation_queued",
    "resource_recommendation",
    "quiz_generation",
}

# Celery PENDING 状态的超时阈值（分钟）
# Celery 对"未知任务 ID"也返回 PENDING，超过此时间的 PENDING 任务视为僵尸
CELERY_PENDING_ZOMBIE_THRESHOLD_MINUTES = 15


class StatusService:
    """路线图状态查询业务逻辑"""
    
    def __init__(self):
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.task_crud = TaskCRUD(RoadmapTask)
    
    async def get_roadmap_status(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[dict]:
        """
        获取路线图状态
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            
        Returns:
            路线图状态信息（包含roadmap_id、status、task_id）
        """
        # 获取路线图元数据
        metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        if not metadata:
            return None
        
        # 获取最新的任务
        result = await session.execute(
            select(RoadmapTask.task_id)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .order_by(RoadmapTask.created_at.desc())
            .limit(1)
        )
        task_id = result.scalar_one_or_none()
        
        return {
            "roadmap_id": roadmap_id,
            "status": metadata.status or "draft",
            "task_id": task_id,
        }
    
    async def get_active_task(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> dict:
        """
        获取路线图当前的活跃任务
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            
        Returns:
            活跃任务信息
        """
        # 查询活跃任务
        result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .where(RoadmapTask.status.in_(["processing", "human_review_pending"]))
            .order_by(RoadmapTask.updated_at.desc())
        )
        task = result.scalars().first()
        
        if task:
            return {
                "has_active_task": True,
                "task_id": task.task_id,
                "status": task.status,
                "current_step": task.current_step,
                "task_type": task.task_type,
                "concept_id": task.concept_id,
                "content_type": task.content_type,
                "created_at": task.created_at.isoformat() if task.created_at else None,
                "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            }
        else:
            return {
                "has_active_task": False,
                "task_id": None,
                "status": None,
                "current_step": None,
            }
    
    async def get_active_retry_task(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> dict:
        """
        获取路线图当前正在进行的重试任务
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            
        Returns:
            重试任务信息
        """
        # 检查路线图是否存在
        metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        if not metadata:
            return None
        
        # 获取正在进行的重试任务
        result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .where(RoadmapTask.status.in_(["processing", "human_review_pending"]))
            .where(RoadmapTask.task_type.in_([
                "retry_tutorial", "retry_resources", "retry_quiz", "retry_batch", "content_retry"
            ]))
            .order_by(RoadmapTask.updated_at.desc())
        )
        retry_task = result.scalars().first()
        
        if retry_task:
            user_request = retry_task.user_request or {}
            items_to_retry = user_request.get("items_to_retry", {})
            content_types = user_request.get("content_types", [])
            
            return {
                "has_active_retry_task": True,
                "task_id": retry_task.task_id,
                "status": retry_task.status,
                "current_step": retry_task.current_step,
                "items_to_retry": items_to_retry,
                "content_types": content_types,
                "created_at": retry_task.created_at.isoformat() if retry_task.created_at else None,
                "updated_at": retry_task.updated_at.isoformat() if retry_task.updated_at else None,
            }
        else:
            return {
                "has_active_retry_task": False,
                "task_id": None,
                "status": None,
                "current_step": None,
                "items_to_retry": None,
                "content_types": None,
            }
    
    async def check_status_quick(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> dict:
        """
        快速检查路线图状态，用于检测僵尸状态
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            
        Returns:
            包含活跃任务和僵尸概念信息的字典
        """
        # 获取路线图元数据
        metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        if not metadata:
            return None
        
        # 获取所有活跃任务
        result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.roadmap_id == roadmap_id)
            .where(RoadmapTask.status.in_(["processing", "human_review_pending"]))
            .order_by(RoadmapTask.updated_at.desc())
        )
        active_tasks = list(result.scalars().all())
        
        # 检查 Celery 任务状态
        has_active_task = self._check_active_tasks(active_tasks)
        
        # 如果有活跃任务，说明正在正常生成
        if has_active_task:
            return {
                "roadmap_id": roadmap_id,
                "has_active_task": True,
                "active_tasks": [
                    {
                        "task_id": task.task_id,
                        "task_type": task.task_type,
                        "status": task.status,
                        "current_step": task.current_step,
                        "concept_id": task.concept_id,
                        "content_type": task.content_type,
                    }
                    for task in active_tasks
                ],
                "stale_concepts": [],
            }
        
        # 检查是否有僵尸状态的概念
        stale_concepts = self._find_stale_concepts(metadata.framework_data)
        
        return {
            "roadmap_id": roadmap_id,
            "has_active_task": False,
            "active_tasks": [],
            "stale_concepts": stale_concepts,
        }
    
    def _check_active_tasks(self, active_tasks: List[RoadmapTask]) -> bool:
        """
        检查任务是否真正活跃（包含Celery状态检查）

        对内容生成阶段的任务，额外校验 Celery 任务状态以识别僵尸任务：
        - Celery 状态为 PENDING/STARTED/RETRY → 任务仍活跃
        - Celery 状态为 FAILURE/SUCCESS/REVOKED → 任务已死亡，视为僵尸
        - 无 celery_task_id → 记录警告，视为僵尸（不阻塞僵尸检测）

        非内容生成阶段的任务（如 human_review_pending）直接视为活跃。

        Args:
            active_tasks: 数据库中状态为 processing/human_review_pending 的任务列表

        Returns:
            True 表示存在真正活跃的任务，False 表示全部为僵尸
        """
        for task in active_tasks:
            is_content_generation = task.current_step in CONTENT_GENERATION_STEPS

            # 非内容生成阶段（如人工审核）直接视为活跃
            if not is_content_generation:
                return True

            if task.celery_task_id:
                try:
                    from app.core.celery_app import celery_app
                    celery_result = celery_app.AsyncResult(task.celery_task_id)

                    if celery_result.state in ["STARTED", "RETRY"]:
                        return True

                    if celery_result.state == "PENDING":
                        # Celery 对"未知/已过期的任务 ID"也返回 PENDING，
                        # 因此需要结合 updated_at 判断是否为真正在排队的任务。
                        # 超过阈值时间未更新的 PENDING 任务视为僵尸。
                        threshold = timedelta(minutes=CELERY_PENDING_ZOMBIE_THRESHOLD_MINUTES)
                        if task.updated_at and (datetime.utcnow() - task.updated_at) < threshold:
                            return True
                        logger.info(
                            "celery_task_pending_expired",
                            task_id=task.task_id,
                            celery_task_id=task.celery_task_id,
                            updated_at=task.updated_at,
                        )
                        # PENDING 超过阈值 → 视为僵尸，继续检查其他任务

                    # FAILURE / SUCCESS / REVOKED 或过期 PENDING → 继续检查其他任务
                    logger.info(
                        "celery_task_not_active",
                        task_id=task.task_id,
                        celery_task_id=task.celery_task_id,
                        celery_state=celery_result.state,
                    )
                except Exception as e:
                    # Celery 无法访问时保守地视为活跃，避免误杀正常任务
                    logger.warning(
                        "failed_to_check_celery_task_status",
                        task_id=task.task_id,
                        celery_task_id=task.celery_task_id,
                        error=str(e),
                    )
                    return True
            else:
                # 内容生成阶段任务缺少 celery_task_id，说明 Celery 任务未能正常分发
                logger.warning(
                    "content_generation_task_missing_celery_id",
                    task_id=task.task_id,
                    current_step=task.current_step,
                )
                # 视为僵尸，继续检查其他任务

        return False
    
    def _find_stale_concepts(self, framework_data: dict) -> List[dict]:
        """
        查找僵尸状态的概念
        
        Args:
            framework_data: 路线图框架数据
            
        Returns:
            僵尸概念列表
        """
        stale_concepts = []
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    concept_name = concept.get("name")
                    
                    checks = [
                        ("tutorial", "content_status"),
                        ("resources", "resources_status"),
                        ("quiz", "quiz_status"),
                    ]
                    
                    for content_type, status_key in checks:
                        status = concept.get(status_key)

                        # 检测僵尸/失效状态：
                        # - "pending"/"generating"：任务卡死未完成（传统僵尸）
                        # - "failed"：后端已标记失败但前端状态可能是陈旧的 "generating"，
                        #   需要通过此接口将正确状态同步给前端
                        if status in ["pending", "generating", "failed"]:
                            stale_concepts.append({
                                "concept_id": concept_id,
                                "concept_name": concept_name,
                                "content_type": content_type,
                                "current_status": status,
                            })
        
        return stale_concepts


def get_status_service() -> StatusService:
    """获取StatusService实例"""
    return StatusService()

