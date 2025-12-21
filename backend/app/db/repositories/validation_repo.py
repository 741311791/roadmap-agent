"""
结构验证记录 Repository

负责 StructureValidationRecord 表的数据访问操作。

职责范围：
- 验证记录的 CRUD 操作
- 根据 task_id 查询验证记录
- 获取最新验证结果
- 查询验证历史
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import StructureValidationRecord
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class ValidationRepository(BaseRepository[StructureValidationRecord]):
    """
    结构验证记录数据访问层
    
    管理路线图结构验证的历史记录。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, StructureValidationRecord)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_latest_by_task(
        self, 
        task_id: str
    ) -> Optional[StructureValidationRecord]:
        """
        获取任务的最新验证记录
        
        Args:
            task_id: 任务 ID
            
        Returns:
            最新的验证记录，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(StructureValidationRecord)
            .where(StructureValidationRecord.task_id == task_id)
            .order_by(StructureValidationRecord.validation_round.desc())
            .limit(1)
        )
        
        record = result.scalar_one_or_none()
        
        if record:
            logger.debug(
                "latest_validation_record_found",
                task_id=task_id,
                validation_round=record.validation_round,
                is_valid=record.is_valid,
            )
        else:
            logger.debug(
                "no_validation_record_found",
                task_id=task_id,
            )
        
        return record
    
    async def get_all_by_task(
        self, 
        task_id: str
    ) -> List[StructureValidationRecord]:
        """
        获取任务的所有验证记录（按轮次排序）
        
        Args:
            task_id: 任务 ID
            
        Returns:
            验证记录列表（按轮次降序）
        """
        result = await self.session.execute(
            select(StructureValidationRecord)
            .where(StructureValidationRecord.task_id == task_id)
            .order_by(StructureValidationRecord.validation_round.desc())
        )
        
        records = list(result.scalars().all())
        
        logger.debug(
            "validation_records_listed",
            task_id=task_id,
            count=len(records),
        )
        
        return records
    
    async def get_by_roadmap(
        self, 
        roadmap_id: str,
        limit: int = 10
    ) -> List[StructureValidationRecord]:
        """
        获取路线图的所有验证记录
        
        Args:
            roadmap_id: 路线图 ID
            limit: 返回数量限制
            
        Returns:
            验证记录列表（按时间降序）
        """
        result = await self.session.execute(
            select(StructureValidationRecord)
            .where(StructureValidationRecord.roadmap_id == roadmap_id)
            .order_by(StructureValidationRecord.created_at.desc())
            .limit(limit)
        )
        
        records = list(result.scalars().all())
        
        logger.debug(
            "roadmap_validation_records_listed",
            roadmap_id=roadmap_id,
            count=len(records),
        )
        
        return records
    
    # ============================================================
    # 创建方法
    # ============================================================
    
    async def create_validation_record(
        self,
        task_id: str,
        roadmap_id: str,
        is_valid: bool,
        overall_score: float,
        issues: list,
        dimension_scores: list,
        improvement_suggestions: list,
        validation_summary: str,
        validation_round: int = 1,
        critical_count: int = 0,
        warning_count: int = 0,
        suggestion_count: int = 0,
    ) -> StructureValidationRecord:
        """
        创建验证记录
        
        Args:
            task_id: 任务 ID
            roadmap_id: 路线图 ID
            is_valid: 是否通过验证
            overall_score: 总体评分 (0-100)
            issues: 问题列表（只包含 critical 和 warning）
            dimension_scores: 维度评分列表
            improvement_suggestions: 改进建议列表（结构化）
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
            issues={"issues": issues} if isinstance(issues, list) else issues,
            dimension_scores={"scores": dimension_scores} if isinstance(dimension_scores, list) else dimension_scores,
            improvement_suggestions={"suggestions": improvement_suggestions} if isinstance(improvement_suggestions, list) else improvement_suggestions,
            validation_summary=validation_summary,
            validation_round=validation_round,
            critical_count=critical_count,
            warning_count=warning_count,
            suggestion_count=suggestion_count,
        )
        
        await self.create(record, flush=True)
        
        logger.info(
            "validation_record_created",
            task_id=task_id,
            roadmap_id=roadmap_id,
            validation_round=validation_round,
            is_valid=is_valid,
            overall_score=overall_score,
            suggestion_count=suggestion_count,
        )
        
        return record





