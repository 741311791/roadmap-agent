"""
验证记录CRUD操作

提供路线图结构验证记录的数据库操作。
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import structlog

from app.crud.base import BaseCRUD
from app.models.database import StructureValidationRecord

logger = structlog.get_logger()


class ValidationCRUD(BaseCRUD[StructureValidationRecord, dict, dict]):
    """
    验证记录CRUD
    
    职责：
    - 验证记录的增删改查
    - 根据路线图ID/任务ID查询验证记录
    """
    
    async def get_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> List[StructureValidationRecord]:
        """
        根据路线图ID获取所有验证记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            验证记录列表（按时间倒序）
        """
        stmt = (
            select(StructureValidationRecord)
            .where(StructureValidationRecord.roadmap_id == roadmap_id)
            .order_by(desc(StructureValidationRecord.created_at))
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_latest_by_roadmap_id(
        self,
        session: AsyncSession,
        roadmap_id: str,
    ) -> Optional[StructureValidationRecord]:
        """
        获取路线图的最新验证记录
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            
        Returns:
            最新验证记录或None
        """
        stmt = (
            select(StructureValidationRecord)
            .where(StructureValidationRecord.roadmap_id == roadmap_id)
            .order_by(desc(StructureValidationRecord.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_latest_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> Optional[StructureValidationRecord]:
        """
        根据任务ID获取最新验证记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            最新验证记录或None
        """
        stmt = (
            select(StructureValidationRecord)
            .where(StructureValidationRecord.task_id == task_id)
            .order_by(desc(StructureValidationRecord.created_at))
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all_by_task(
        self,
        session: AsyncSession,
        task_id: str,
    ) -> List[StructureValidationRecord]:
        """
        根据任务ID获取所有验证记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            
        Returns:
            验证记录列表（按时间倒序）
        """
        stmt = (
            select(StructureValidationRecord)
            .where(StructureValidationRecord.task_id == task_id)
            .order_by(desc(StructureValidationRecord.created_at))
        )
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def create_validation_record(
        self,
        session: AsyncSession,
        task_id: str,
        roadmap_id: str,
        is_valid: bool,
        overall_score: float,
        issues: list[dict],
        dimension_scores: list[dict],
        improvement_suggestions: list[dict],
        validation_summary: str,
        validation_round: int = 1,
        critical_count: int = 0,
        warning_count: int = 0,
        suggestion_count: int = 0,
    ) -> StructureValidationRecord:
        """
        创建验证记录
        
        Args:
            session: 数据库会话
            task_id: 任务ID
            roadmap_id: 路线图ID
            is_valid: 验证是否通过
            overall_score: 总体评分(0-100)
            issues: 问题列表(字典列表)
            dimension_scores: 维度评分列表(字典列表)
            improvement_suggestions: 改进建议列表(字典列表)
            validation_summary: 验证摘要
            validation_round: 验证轮次
            critical_count: 严重问题数量
            warning_count: 警告问题数量
            suggestion_count: 改进建议数量
            
        Returns:
            创建的验证记录
        """
        record = StructureValidationRecord(
            task_id=task_id,
            roadmap_id=roadmap_id,
            is_valid=is_valid,
            overall_score=overall_score,
            issues={"items": issues},  # 包装成字典以符合JSON字段要求
            dimension_scores={"scores": dimension_scores},
            improvement_suggestions={"suggestions": improvement_suggestions},
            validation_summary=validation_summary,
            validation_round=validation_round,
            critical_count=critical_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
        )
        
        session.add(record)
        await session.flush()
        
        logger.info(
            "validation_record_created",
            task_id=task_id,
            roadmap_id=roadmap_id,
            is_valid=is_valid,
            overall_score=overall_score,
            validation_round=validation_round,
            critical_count=critical_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
        )
        
        return record


# 单例模式
_validation_crud_instance: Optional[ValidationCRUD] = None


def get_validation_crud() -> ValidationCRUD:
    """获取ValidationCRUD单例"""
    global _validation_crud_instance
    if _validation_crud_instance is None:
        _validation_crud_instance = ValidationCRUD(StructureValidationRecord)
    return _validation_crud_instance

