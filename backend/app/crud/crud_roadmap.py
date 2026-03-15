"""
路线图CRUD操作

扩展了以下Repository方法：
- 路线图元数据查询（get_roadmap_metadata_by_task等）
- Intent分析元数据（get_intent_analysis_metadata等）
- 执行日志查询（get_execution_logs_by_trace等）
- 批量查询优化（get_roadmaps_by_user等）
"""
from typing import Optional, List, Dict
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from app.crud.base import BaseCRUD
from app.models.database import (
    RoadmapMetadata,
    RoadmapTask,
    IntentAnalysisMetadata,
    ExecutionLog,
)
from app.schemas.roadmap import RoadmapCreate, RoadmapUpdate

logger = structlog.get_logger()

class RoadmapCRUD(BaseCRUD[RoadmapMetadata, RoadmapCreate, RoadmapUpdate]):
    """
    路线图CRUD操作
    
    继承BaseCRUD，自动获得：
    - get(id)
    - get_multi(skip, limit)
    - create(obj_in)
    - update(db_obj, obj_in)
    - remove(id)
    - soft_delete(id)
    """
    
    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[RoadmapMetadata]:
        """
        根据roadmap_id获取路线图
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            路线图元数据或None
        """
        result = await session.execute(
            select(RoadmapMetadata).where(
                RoadmapMetadata.roadmap_id == roadmap_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_by_user(
        self,
        session: AsyncSession,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[RoadmapMetadata]:
        """
        获取用户的路线图列表
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            路线图列表
        """
        result = await session.execute(
            select(RoadmapMetadata)
            .where(RoadmapMetadata.user_id == user_id)
            .where(RoadmapMetadata.deleted_at.is_(None))  # 排除软删除
            .order_by(RoadmapMetadata.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_user(
        self,
        session: AsyncSession,
        user_id: str,
        *,
        deleted: bool = False,
    ) -> int:
        """
        统计用户路线图数量。

        Args:
            session: 数据库会话
            user_id: 用户ID
            deleted: 是否统计已删除路线图

        Returns:
            路线图数量
        """
        query = select(func.count()).select_from(RoadmapMetadata).where(
            RoadmapMetadata.user_id == user_id
        )

        if deleted:
            query = query.where(RoadmapMetadata.deleted_at.is_not(None))
        else:
            query = query.where(RoadmapMetadata.deleted_at.is_(None))

        result = await session.execute(query)
        return int(result.scalar() or 0)
    
    async def get_with_concepts(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[RoadmapMetadata]:
        """
        获取路线图及其所有概念元数据（避免N+1查询）
        
        使用selectinload预加载关联数据，消除N+1查询问题。
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            路线图元数据（包含关联的concepts）
        """
        result = await session.execute(
            select(RoadmapMetadata)
            .options(selectinload(RoadmapMetadata.concept_metas))
            .where(RoadmapMetadata.roadmap_id == roadmap_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_all_relations(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[RoadmapMetadata]:
        """
        获取路线图及其所有关联数据（避免N+1查询）
        
        使用多级selectinload预加载：
        - concept_metas（概念元数据）
        - concept_metas.tutorial_metas（教程元数据）
        - concept_metas.resource_metas（资源元数据）
        - concept_metas.quiz_metas（测验元数据）
        
        性能优势：100个概念时，从101次查询降低到4次查询（约25倍提升）
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            路线图元数据（包含所有关联数据）
        """
        from app.models.database import ConceptMetadata
        
        result = await session.execute(
            select(RoadmapMetadata)
            .options(
                # ✅ 预加载concepts
                selectinload(RoadmapMetadata.concept_metas).selectinload(
                    # ✅ 预加载tutorial_metas
                    ConceptMetadata.tutorial_metas
                ),
                selectinload(RoadmapMetadata.concept_metas).selectinload(
                    # ✅ 预加载resource_metas
                    ConceptMetadata.resource_metas
                ),
                selectinload(RoadmapMetadata.concept_metas).selectinload(
                    # ✅ 预加载quiz_metas
                    ConceptMetadata.quiz_metas
                ),
            )
            .where(RoadmapMetadata.roadmap_id == roadmap_id)
        )
        return result.scalar_one_or_none()
    
    # ========== Week 4扩展方法 ==========
    
    async def get_roadmap_metadata_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[RoadmapMetadata]:
        """
        通过task_id获取路线图元数据
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            路线图元数据或None
        """
        # 先获取task
        task_result = await session.execute(
            select(RoadmapTask).where(RoadmapTask.task_id == task_id)
        )
        task = task_result.scalar_one_or_none()
        
        if not task or not task.roadmap_id:
            return None
        
        # 通过roadmap_id获取元数据
        return await self.get_by_roadmap_id(session, task.roadmap_id)
    
    async def get_roadmap_with_framework(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[dict]:
        """
        获取路线图及其framework_data
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            包含framework_data的字典或None
        """
        metadata = await self.get_by_roadmap_id(session, roadmap_id)
        if not metadata:
            return None
        
        return {
            "roadmap_id": metadata.roadmap_id,
            "title": metadata.title,
            "description": metadata.description,
            "framework_data": metadata.framework_data,
            "created_at": metadata.created_at,
            "updated_at": metadata.updated_at,
        }
    
    async def get_roadmaps_by_user(
        self,
        session: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        with_concepts: bool = False,
    ) -> List[RoadmapMetadata]:
        """
        获取用户的所有路线图列表（排除已删除的）
        
        Args:
            session: 数据库会话
            user_id: 用户ID
            skip: 跳过的记录数
            limit: 返回数量限制
            with_concepts: 是否预加载概念元数据（避免N+1查询）
            
        Returns:
            路线图元数据列表（按创建时间降序）
        """
        query = select(RoadmapMetadata).where(
            RoadmapMetadata.user_id == user_id,
            RoadmapMetadata.deleted_at.is_(None)
        )
        
        # ✅ 可选：预加载概念元数据（避免N+1查询）
        if with_concepts:
            query = query.options(selectinload(RoadmapMetadata.concept_metas))
        
        result = await session.execute(
            query
            .order_by(RoadmapMetadata.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def roadmap_id_exists(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> bool:
        """
        检查roadmap_id是否存在
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            存在返回True，否则False
        """
        result = await session.execute(
            select(RoadmapMetadata.roadmap_id).where(
                RoadmapMetadata.roadmap_id == roadmap_id
            )
        )
        return result.scalar_one_or_none() is not None
    
    # ========== Intent分析相关 ==========
    
    async def get_intent_analysis_metadata(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[IntentAnalysisMetadata]:
        """
        获取需求分析元数据
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            需求分析元数据或None
        """
        result = await session.execute(
            select(IntentAnalysisMetadata).where(
                IntentAnalysisMetadata.roadmap_id == roadmap_id
            )
        )
        return result.scalar_one_or_none()

    def _apply_execution_log_filters(
        self,
        query,
        *,
        task_id: str,
        level: Optional[str] = None,
        category: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ):
        """
        统一应用执行日志过滤条件。

        Args:
            query: 原始 SQLAlchemy 查询对象
            task_id: 任务ID
            level: 单个日志级别过滤
            category: 单个日志分类过滤（兼容旧参数）
            categories: 多个日志分类过滤（新参数，优先级高于 category）

        Returns:
            应用过滤条件后的查询对象
        """
        filtered_query = query.where(ExecutionLog.task_id == task_id)

        if level:
            filtered_query = filtered_query.where(ExecutionLog.level == level)

        normalized_categories = [item for item in (categories or []) if item]
        if normalized_categories:
            filtered_query = filtered_query.where(ExecutionLog.category.in_(normalized_categories))
        elif category:
            filtered_query = filtered_query.where(ExecutionLog.category == category)

        return filtered_query
    
    # ========== 执行日志相关 ==========
    
    async def get_execution_logs_by_trace(
        self,
        session: AsyncSession,
        task_id: str,
        level: Optional[str] = None,
        category: Optional[str] = None,
        categories: Optional[List[str]] = None,
        offset: int = 0,
        limit: int = 100,
        limit_per_category: Optional[int] = None,
    ) -> List[ExecutionLog]:
        """
        获取指定task_id的执行日志
        
        Args:
            session: 数据库会话
            task_id: 追踪ID
            level: 过滤日志级别（可选）
            category: 过滤日志分类（可选，兼容旧参数）
            categories: 过滤多个日志分类（可选）
            offset: 分页偏移
            limit: 返回数量限制
            limit_per_category: 每个 category 的返回上限（仅多 category 查询时生效）
            
        Returns:
            执行日志列表（按时间倒序，最新优先）
        """
        normalized_categories = [item for item in (categories or []) if item]
        should_apply_category_window = limit_per_category is not None and len(normalized_categories) > 1

        if should_apply_category_window:
            ranked_log_ids = self._apply_execution_log_filters(
                select(
                    ExecutionLog.id.label("log_id"),
                    func.row_number().over(
                        partition_by=ExecutionLog.category,
                        order_by=ExecutionLog.created_at.desc(),
                    ).label("category_rank"),
                ),
                task_id=task_id,
                level=level,
                categories=normalized_categories,
            ).subquery()

            query = (
                select(ExecutionLog)
                .join(ranked_log_ids, ExecutionLog.id == ranked_log_ids.c.log_id)
                .where(ranked_log_ids.c.category_rank <= limit_per_category)
                .order_by(ExecutionLog.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
        else:
            query = self._apply_execution_log_filters(
                select(ExecutionLog),
                task_id=task_id,
                level=level,
                category=category,
                categories=normalized_categories,
            ).order_by(ExecutionLog.created_at.desc()).offset(offset).limit(limit)

        result = await session.execute(query)
        return list(result.scalars().all())
    
    async def count_execution_logs_by_trace(
        self,
        session: AsyncSession,
        task_id: str,
        level: Optional[str] = None,
        category: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> int:
        """
        统计指定task_id的执行日志总数
        
        Args:
            session: 数据库会话
            task_id: 追踪ID
            level: 过滤日志级别（可选）
            category: 过滤日志分类（可选，兼容旧参数）
            categories: 过滤多个日志分类（可选）
            
        Returns:
            满足条件的日志总数
        """
        query = self._apply_execution_log_filters(
            select(func.count(ExecutionLog.id)),
            task_id=task_id,
            level=level,
            category=category,
            categories=categories,
        )

        result = await session.execute(query)
        return result.scalar_one()
    
    async def get_execution_logs_summary(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Dict:
        """
        获取执行日志摘要统计
        
        Args:
            session: 数据库会话
            task_id: 追踪ID
            
        Returns:
            包含统计信息的字典
        """
        # 统计各级别日志数量
        level_counts_result = await session.execute(
            select(
                ExecutionLog.level,
                func.count(ExecutionLog.id).label('count')
            )
            .where(ExecutionLog.task_id == task_id)
            .group_by(ExecutionLog.level)
        )
        level_counts = {row.level: row.count for row in level_counts_result}
        
        # 统计各步骤日志数量
        step_counts_result = await session.execute(
            select(
                ExecutionLog.step,  # ✅ 修复：使用正确的字段名 step
                func.count(ExecutionLog.id).label('count')
            )
            .where(ExecutionLog.task_id == task_id)
            .group_by(ExecutionLog.step)  # ✅ 修复：使用正确的字段名 step
        )
        step_counts = {row.step: row.count for row in step_counts_result}  # ✅ 修复：使用正确的字段名 step
        
        # 获取最新日志时间
        latest_log_result = await session.execute(
            select(ExecutionLog.created_at)
            .where(ExecutionLog.task_id == task_id)
            .order_by(desc(ExecutionLog.created_at))
            .limit(1)
        )
        latest_log = latest_log_result.scalar_one_or_none()
        
        # 总数
        total = sum(level_counts.values())
        
        return {
            "total": total,
            "by_level": level_counts,
            "by_step": step_counts,
            "latest_log_time": latest_log.isoformat() if latest_log else None,
        }
    
    async def get_error_logs_by_trace(
        self,
        session: AsyncSession,
        task_id: str,
        limit: int = 50,
    ) -> List[ExecutionLog]:
        """
        获取指定task_id的错误日志
        
        Args:
            session: 数据库会话
            task_id: 追踪ID
            limit: 返回数量限制
            
        Returns:
            错误日志列表（按时间降序）
        """
        result = await session.execute(
            select(ExecutionLog)
            .where(
                ExecutionLog.task_id == task_id,
                ExecutionLog.level == "error"
            )
            .order_by(desc(ExecutionLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def save_roadmap_metadata(
        self,
        session: AsyncSession,
        roadmap_id: str,
        user_id: str,
        framework: "RoadmapFramework",
    ) -> RoadmapMetadata:
        """
        保存路线图元数据和框架
        
        如果路线图已存在则更新，否则创建新记录。
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            user_id: 用户ID
            framework: 路线图框架对象
            
        Returns:
            保存的路线图元数据
        """
        from app.models.domain import RoadmapFramework
        
        # 检查是否已存在
        existing = await self.get_by_roadmap_id(session, roadmap_id)
        
        # 准备框架数据（转换为字典）
        framework_dict = framework.model_dump() if framework else {}
        
        if existing:
            # 更新现有记录
            existing.title = framework.title
            existing.total_estimated_hours = framework.total_estimated_hours
            existing.recommended_completion_weeks = framework.recommended_completion_weeks
            existing.framework_data = framework_dict
            
            # ✅ 修复：标记 JSON 字段已修改（SQLAlchemy 需要显式通知）
            from sqlalchemy.orm import attributes
            attributes.flag_modified(existing, "framework_data")
            
            session.add(existing)
            await session.flush()
            
            logger.info(
                "roadmap_metadata_updated",
                roadmap_id=roadmap_id,
                user_id=user_id,
                stages_count=len(framework.stages) if framework else 0,
            )
            
            return existing
        else:
            # 创建新记录
            roadmap_metadata = RoadmapMetadata(
                roadmap_id=roadmap_id,
                user_id=user_id,
                title=framework.title,
                total_estimated_hours=framework.total_estimated_hours,
                recommended_completion_weeks=framework.recommended_completion_weeks,
                framework_data=framework_dict,
            )
            
            session.add(roadmap_metadata)
            await session.flush()
            
            logger.info(
                "roadmap_metadata_created",
                roadmap_id=roadmap_id,
                user_id=user_id,
                stages_count=len(framework.stages) if framework else 0,
            )
            
            return roadmap_metadata
    
    async def delete_roadmap(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> bool:
        """
        软删除路线图
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            是否成功删除
        """
        from app.models.database import beijing_now
        
        roadmap = await self.get_by_roadmap_id(session, roadmap_id)
        if not roadmap:
            logger.warning("roadmap_not_found_for_deletion", roadmap_id=roadmap_id)
            return False
        
        # 软删除
        roadmap.deleted_at = beijing_now()
        session.add(roadmap)
        await session.flush()
        
        logger.info("roadmap_soft_deleted", roadmap_id=roadmap_id)
        return True


# 创建单例（工厂函数）
def get_roadmap_crud() -> RoadmapCRUD:
    """获取RoadmapCRUD实例"""
    return RoadmapCRUD(RoadmapMetadata)

