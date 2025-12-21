"""
路线图编辑记录相关端点

提供查询编辑历史记录的 API。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import structlog

from app.db.session import get_db
from app.db.repositories.edit_repo import EditRepository
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.models.domain import RoadmapFramework
from app.services.roadmap_comparison_service import RoadmapComparisonService

router = APIRouter(prefix="/tasks", tags=["edit"])
logger = structlog.get_logger()


@router.get("/{task_id}/edit/latest")
async def get_latest_edit(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务的最新编辑记录（包含 modified_node_ids）
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        
    Returns:
        最新的编辑记录，包含修改的节点 ID 列表
        
    Raises:
        HTTPException: 404 - 编辑记录不存在
        
    Example:
        ```json
        {
            "id": "uuid",
            "task_id": "task-123",
            "roadmap_id": "roadmap-456",
            "modification_summary": "AI 根据第 1 轮验证结果优化了路线图结构",
            "modified_node_ids": ["concept-1", "concept-5", "concept-12"],
            "edit_round": 1,
            "created_at": "2024-01-01T00:00:00"
        }
        ```
    """
    repo = EditRepository(db)
    record = await repo.get_latest_by_task(task_id)
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No edit record found for task {task_id}"
        )
    
    # 转换为字典并返回（不包含完整的 framework_data，减少响应大小）
    result = {
        "id": record.id,
        "task_id": record.task_id,
        "roadmap_id": record.roadmap_id,
        "modification_summary": record.modification_summary,
        "modified_node_ids": record.modified_node_ids,
        "edit_round": record.edit_round,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
    
    logger.info(
        "edit_record_retrieved",
        task_id=task_id,
        edit_round=record.edit_round,
        modified_nodes_count=len(record.modified_node_ids) if record.modified_node_ids else 0,
    )
    
    return result


@router.get("/{task_id}/edit/history")
async def get_edit_history(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务的所有编辑历史记录
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        
    Returns:
        编辑记录列表（按轮次降序排列）
        
    Example:
        ```json
        [
            {
                "id": "uuid-1",
                "task_id": "task-123",
                "edit_round": 2,
                "modification_summary": "AI 根据第 2 轮验证结果优化了路线图结构",
                "modified_nodes_count": 3,
                "created_at": "2024-01-01T01:00:00"
            },
            {
                "id": "uuid-2",
                "task_id": "task-123",
                "edit_round": 1,
                "modification_summary": "AI 根据第 1 轮验证结果优化了路线图结构",
                "modified_nodes_count": 5,
                "created_at": "2024-01-01T00:00:00"
            }
        ]
        ```
    """
    repo = EditRepository(db)
    records = await repo.get_all_by_task(task_id)
    
    # 转换为字典列表（简化版，不包含 framework_data）
    result = []
    for record in records:
        result.append({
            "id": record.id,
            "task_id": record.task_id,
            "roadmap_id": record.roadmap_id,
            "modification_summary": record.modification_summary,
            "modified_nodes_count": len(record.modified_node_ids) if record.modified_node_ids else 0,
            "edit_round": record.edit_round,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        })
    
    logger.info(
        "edit_history_retrieved",
        task_id=task_id,
        records_count=len(records),
    )
    
    return result


@router.get("/{task_id}/edit/{edit_round}/diff")
async def get_edit_diff(
    task_id: str,
    edit_round: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取特定编辑轮次的前后对比数据
    
    返回完整的 origin_framework_data 和 modified_framework_data，
    用于前端展示详细的变更对比。
    
    Args:
        task_id: 任务 ID
        edit_round: 编辑轮次
        db: 数据库会话
        
    Returns:
        包含原始框架和修改后框架的完整数据
        
    Raises:
        HTTPException: 404 - 编辑记录不存在
    """
    repo = EditRepository(db)
    records = await repo.get_all_by_task(task_id)
    
    # 查找指定轮次的记录
    target_record = None
    for record in records:
        if record.edit_round == edit_round:
            target_record = record
            break
    
    if not target_record:
        raise HTTPException(
            status_code=404,
            detail=f"No edit record found for task {task_id} round {edit_round}"
        )
    
    result = {
        "id": target_record.id,
        "task_id": target_record.task_id,
        "roadmap_id": target_record.roadmap_id,
        "edit_round": target_record.edit_round,
        "origin_framework_data": target_record.origin_framework_data,
        "modified_framework_data": target_record.modified_framework_data,
        "modified_node_ids": target_record.modified_node_ids,
        "modification_summary": target_record.modification_summary,
        "created_at": target_record.created_at.isoformat() if target_record.created_at else None,
    }
    
    logger.info(
        "edit_diff_retrieved",
        task_id=task_id,
        edit_round=edit_round,
    )
    
    return result


@router.get("/{task_id}/edit/history-full")
async def get_full_edit_history(
    task_id: str,
    roadmap_id: str = Query(..., description="路线图 ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务的完整编辑历史版本链
    
    将编辑记录按时间顺序串联成完整的版本链，
    每个版本包含完整的框架数据和相对于上一版本的修改节点列表。
    
    Args:
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        db: 数据库会话
        
    Returns:
        完整的版本链数据
        
    Example:
        ```json
        {
            "versions": [
                {
                    "version": 1,
                    "framework_data": {...},
                    "created_at": "2024-12-20T10:00:00",
                    "edit_round": 0,
                    "modification_summary": "Initial version",
                    "modified_node_ids": []
                },
                {
                    "version": 2,
                    "framework_data": {...},
                    "created_at": "2024-12-20T10:05:00",
                    "edit_round": 1,
                    "modification_summary": "AI 根据第 1 轮验证结果优化了路线图结构",
                    "modified_node_ids": ["concept-1", "concept-5"]
                }
            ],
            "current_version": 2
        }
        ```
    """
    edit_repo = EditRepository(db)
    roadmap_repo = RoadmapRepository(db)
    comparison_service = RoadmapComparisonService()
    
    # 1. 获取所有编辑记录（按创建时间升序排列）
    edit_records = await edit_repo.get_all_by_task(task_id)
    
    # 按创建时间升序排序
    edit_records = sorted(edit_records, key=lambda r: r.created_at)
    
    # 2. 获取当前最新的路线图框架数据
    roadmap = await roadmap_repo.get_roadmap_metadata(roadmap_id)
    if not roadmap:
        raise HTTPException(
            status_code=404,
            detail=f"Roadmap {roadmap_id} not found"
        )
    
    # 3. 构建版本链
    versions = []
    
    if not edit_records:
        # 没有编辑记录，只有当前版本
        current_framework = RoadmapFramework(**roadmap.framework_data)
        versions.append({
            "version": 1,
            "framework_data": current_framework.model_dump(),
            "created_at": roadmap.created_at.isoformat() if roadmap.created_at else None,
            "edit_round": 0,
            "modification_summary": "Initial version",
            "modified_node_ids": []
        })
        current_version = 1
    else:
        # 有编辑记录，构建完整版本链
        # V1 = 第一条记录的 origin_framework_data
        first_record = edit_records[0]
        origin_framework = RoadmapFramework(**first_record.origin_framework_data)
        
        versions.append({
            "version": 1,
            "framework_data": first_record.origin_framework_data,
            "created_at": first_record.created_at.isoformat() if first_record.created_at else None,
            "edit_round": 0,
            "modification_summary": "Initial version",
            "modified_node_ids": []
        })
        
        # V2, V3, ... = 每条记录的 modified_framework_data
        prev_framework = origin_framework
        for idx, record in enumerate(edit_records, start=2):
            modified_framework = RoadmapFramework(**record.modified_framework_data)
            
            # 计算相对于上一版本的修改节点
            modified_ids = comparison_service.get_modified_node_ids_simple(
                prev_framework,
                modified_framework
            )
            
            versions.append({
                "version": idx,
                "framework_data": record.modified_framework_data,
                "created_at": record.created_at.isoformat() if record.created_at else None,
                "edit_round": record.edit_round,
                "modification_summary": record.modification_summary,
                "modified_node_ids": modified_ids
            })
            
            prev_framework = modified_framework
        
        current_version = len(versions)
    
    result = {
        "versions": versions,
        "current_version": current_version
    }
    
    logger.info(
        "full_edit_history_retrieved",
        task_id=task_id,
        roadmap_id=roadmap_id,
        total_versions=len(versions),
        edit_rounds=len(edit_records),
    )
    
    return result


