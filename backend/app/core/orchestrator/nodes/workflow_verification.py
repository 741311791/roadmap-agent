"""
工作流验证节点

在路线图生成完成后验证所有数据库表的完整性，并生成执行摘要。

验证内容：
1. roadmap_tasks 表：status、current_step、user_request、roadmap_id
2. roadmap_metadata 表：framework_data 的 Concept 属性
3. intent_analysis_metadata 表：对应 roadmap_id 的数据
4. structure_validation_records 表：对应 task_id 的数据
5. edit_plan_records 表：对应 task_id 的数据（可选）
6. roadmap_edit_records 表：对应 task_id 的数据（可选）
7. concept_metadata 表：所有 Concept 的内容生成状态
8. execution_logs 表：任务执行日志和经历的阶段
"""
import structlog
from langchain_core.runnables import RunnableConfig
from sqlalchemy import select, func
from datetime import datetime

from app.core.orchestrator.base import RoadmapState
from app.core.orchestrator.runtime_context import RuntimeContext
from app.models.database import (
    RoadmapTask,
    RoadmapMetadata,
    IntentAnalysisMetadata,
    StructureValidationRecord,
    EditPlanRecord,
    RoadmapEditRecord,
    ConceptMetadata,
    ExecutionLog,
)
from app.db.celery_session import get_celery_session

logger = structlog.get_logger()


async def workflow_verification_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    工作流验证节点
    
    验证所有相关表的数据完整性，生成执行摘要并更新到 roadmap_tasks 表。
    
    Args:
        state: 工作流状态
        config: 运行时配置
        
    Returns:
        状态更新字典
    """
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    task_id = state["task_id"]
    roadmap_id = state["roadmap_id"]
    
    logger.info(
        "workflow_verification_started",
        task_id=task_id,
        roadmap_id=roadmap_id,
    )
    
    async with get_celery_session() as session:
        # 执行验证
        verification_results = await _verify_all_tables(
            session=session,
            task_id=task_id,
            roadmap_id=roadmap_id,
        )
        
        # 生成执行摘要
        execution_summary = _generate_execution_summary(verification_results)
        
        # 更新 roadmap_tasks 表的 execution_summary 字段
        from app.crud.crud_task import get_task_crud
        task_crud = get_task_crud()
        await task_crud.update_execution_summary(
            session=session,
            task_id=task_id,
            execution_summary=execution_summary,
        )
    
    logger.info(
        "workflow_verification_completed",
        task_id=task_id,
        execution_summary=execution_summary,
    )
    
    return {
        "current_step": "workflow_verification",
    }


async def _verify_all_tables(
    session,
    task_id: str,
    roadmap_id: str,
) -> dict:
    """
    验证所有相关表的数据完整性
    
    Args:
        session: 数据库会话
        task_id: 任务 ID
        roadmap_id: 路线图 ID
        
    Returns:
        验证结果字典
    """
    results = {
        "task_id": task_id,
        "roadmap_id": roadmap_id,
        "timestamp": datetime.utcnow().isoformat(),
        "tables": {},
    }
    
    # 1. 验证 roadmap_tasks 表
    results["tables"]["roadmap_tasks"] = await _verify_roadmap_tasks(
        session, task_id, roadmap_id
    )
    
    # 2. 验证 roadmap_metadata 表
    results["tables"]["roadmap_metadata"] = await _verify_roadmap_metadata(
        session, roadmap_id
    )
    
    # 3. 验证 intent_analysis_metadata 表
    results["tables"]["intent_analysis_metadata"] = await _verify_intent_analysis(
        session, roadmap_id
    )
    
    # 4. 验证 structure_validation_records 表
    results["tables"]["structure_validation_records"] = await _verify_validation_records(
        session, task_id
    )
    
    # 5. 验证 edit_plan_records 表（可选）
    results["tables"]["edit_plan_records"] = await _verify_edit_plan_records(
        session, task_id
    )
    
    # 6. 验证 roadmap_edit_records 表（可选）
    results["tables"]["roadmap_edit_records"] = await _verify_roadmap_edit_records(
        session, task_id
    )
    
    # 7. 验证 concept_metadata 表
    results["tables"]["concept_metadata"] = await _verify_concept_metadata(
        session, roadmap_id
    )
    
    # 8. 验证 execution_logs 表
    results["tables"]["execution_logs"] = await _verify_execution_logs(
        session, task_id
    )
    
    return results


async def _verify_roadmap_tasks(session, task_id: str, roadmap_id: str) -> dict:
    """验证 roadmap_tasks 表"""
    stmt = select(RoadmapTask).where(RoadmapTask.task_id == task_id)
    result = await session.execute(stmt)
    task = result.scalar_one_or_none()
    
    if not task:
        return {
            "status": "failed",
            "error": f"Task {task_id} not found",
        }
    
    checks = {
        "exists": True,
        "has_status": bool(task.status),
        "status_value": task.status,
        "has_current_step": bool(task.current_step),
        "current_step_value": task.current_step,
        "has_user_request": bool(task.user_request),
        "has_roadmap_id": bool(task.roadmap_id),
        "roadmap_id_match": task.roadmap_id == roadmap_id,
    }
    
    all_passed = all([
        checks["exists"],
        checks["has_status"],
        checks["has_current_step"],
        checks["has_user_request"],
        checks["has_roadmap_id"],
        checks["roadmap_id_match"],
    ])
    
    return {
        "status": "passed" if all_passed else "failed",
        "checks": checks,
    }


async def _verify_roadmap_metadata(session, roadmap_id: str) -> dict:
    """验证 roadmap_metadata 表"""
    stmt = select(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == roadmap_id)
    result = await session.execute(stmt)
    metadata_list = result.scalars().all()
    
    if not metadata_list:
        return {
            "status": "failed",
            "error": f"Roadmap metadata for {roadmap_id} not found",
        }
    
    if len(metadata_list) > 1:
        return {
            "status": "failed",
            "error": f"Multiple roadmap metadata records found for {roadmap_id}",
            "count": len(metadata_list),
        }
    
    metadata = metadata_list[0]
    framework_data = metadata.framework_data
    
    # 检查 framework_data 中的 Concept 属性
    concept_stats = _analyze_framework_concepts(framework_data)
    
    checks = {
        "unique_record": len(metadata_list) == 1,
        "has_framework_data": bool(framework_data),
        "concept_stats": concept_stats,
    }
    
    all_passed = all([
        checks["unique_record"],
        checks["has_framework_data"],
        concept_stats["total_concepts"] > 0,
    ])
    
    return {
        "status": "passed" if all_passed else "failed",
        "checks": checks,
    }


def _analyze_framework_concepts(framework_data: dict) -> dict:
    """分析 framework_data 中的 Concept 属性"""
    if not framework_data:
        return {
            "total_concepts": 0,
            "concepts_with_tutorial_id": 0,
            "concepts_with_content_status": 0,
            "concepts_with_resources_id": 0,
            "concepts_with_quiz_id": 0,
        }
    
    total = 0
    with_tutorial = 0
    with_content_status = 0
    with_resources = 0
    with_quiz = 0
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                total += 1
                if concept.get("tutorial_id"):
                    with_tutorial += 1
                if concept.get("content_status"):
                    with_content_status += 1
                if concept.get("resources_id"):
                    with_resources += 1
                if concept.get("quiz_id"):
                    with_quiz += 1
    
    return {
        "total_concepts": total,
        "concepts_with_tutorial_id": with_tutorial,
        "concepts_with_content_status": with_content_status,
        "concepts_with_resources_id": with_resources,
        "concepts_with_quiz_id": with_quiz,
        "tutorial_completion_rate": f"{with_tutorial/total*100:.1f}%" if total > 0 else "0%",
        "resources_completion_rate": f"{with_resources/total*100:.1f}%" if total > 0 else "0%",
        "quiz_completion_rate": f"{with_quiz/total*100:.1f}%" if total > 0 else "0%",
    }


async def _verify_intent_analysis(session, roadmap_id: str) -> dict:
    """验证 intent_analysis_metadata 表"""
    stmt = select(IntentAnalysisMetadata).where(
        IntentAnalysisMetadata.roadmap_id == roadmap_id
    )
    result = await session.execute(stmt)
    records = result.scalars().all()
    
    if not records:
        return {
            "status": "failed",
            "error": f"Intent analysis for {roadmap_id} not found",
        }
    
    if len(records) > 1:
        return {
            "status": "warning",
            "message": f"Multiple intent analysis records found for {roadmap_id}",
            "count": len(records),
        }
    
    return {
        "status": "passed",
        "count": len(records),
    }


async def _verify_validation_records(session, task_id: str) -> dict:
    """验证 structure_validation_records 表"""
    stmt = select(StructureValidationRecord).where(
        StructureValidationRecord.task_id == task_id
    )
    result = await session.execute(stmt)
    records = result.scalars().all()
    
    if not records:
        return {
            "status": "warning",
            "message": "No validation records found (may be skipped in test mode)",
            "count": 0,
        }
    
    passed_count = sum(1 for r in records if r.is_valid)
    
    return {
        "status": "passed",
        "count": len(records),
        "passed_count": passed_count,
        "failed_count": len(records) - passed_count,
    }


async def _verify_edit_plan_records(session, task_id: str) -> dict:
    """验证 edit_plan_records 表（可选）"""
    stmt = select(EditPlanRecord).where(EditPlanRecord.task_id == task_id)
    result = await session.execute(stmt)
    records = result.scalars().all()
    
    return {
        "status": "optional",
        "count": len(records),
        "message": "Edit plan records are optional",
    }


async def _verify_roadmap_edit_records(session, task_id: str) -> dict:
    """验证 roadmap_edit_records 表（可选）"""
    stmt = select(RoadmapEditRecord).where(RoadmapEditRecord.task_id == task_id)
    result = await session.execute(stmt)
    records = result.scalars().all()
    
    return {
        "status": "optional",
        "count": len(records),
        "message": "Edit records are optional",
    }


async def _verify_concept_metadata(session, roadmap_id: str) -> dict:
    """验证 concept_metadata 表"""
    stmt = select(ConceptMetadata).where(ConceptMetadata.roadmap_id == roadmap_id)
    result = await session.execute(stmt)
    concepts = result.scalars().all()
    
    if not concepts:
        return {
            "status": "warning",
            "message": "No concept metadata found",
            "count": 0,
        }
    
    # 统计各类内容的生成状态
    tutorial_count = sum(1 for c in concepts if c.tutorial_id)
    resource_count = sum(1 for c in concepts if c.resources_id)  # ✅ 修正：使用正确的字段名
    quiz_count = sum(1 for c in concepts if c.quiz_id)
    
    return {
        "status": "passed",
        "total_concepts": len(concepts),
        "with_tutorial": tutorial_count,
        "with_resource": resource_count,
        "with_quiz": quiz_count,
    }


async def _verify_execution_logs(session, task_id: str) -> dict:
    """验证 execution_logs 表"""
    stmt = select(ExecutionLog).where(ExecutionLog.task_id == task_id).order_by(
        ExecutionLog.created_at
    )
    result = await session.execute(stmt)
    logs = result.scalars().all()
    
    if not logs:
        return {
            "status": "failed",
            "error": "No execution logs found",
            "count": 0,
        }
    
    # 提取经历的阶段
    stages = list(set(log.step for log in logs if log.step))
    stages_timeline = [log.step for log in logs if log.step]
    
    # 统计日志类型
    log_levels = {}
    for log in logs:
        level = getattr(log, "level", "info")
        log_levels[level] = log_levels.get(level, 0) + 1
    
    return {
        "status": "passed",
        "total_logs": len(logs),
        "unique_stages": len(stages),
        "stages": stages,
        "stages_timeline": stages_timeline,
        "log_levels": log_levels,
    }


def _generate_execution_summary(verification_results: dict) -> dict:
    """
    生成执行摘要
    
    Args:
        verification_results: 验证结果
        
    Returns:
        执行摘要字典
    """
    tables = verification_results["tables"]
    
    # 统计验证结果
    passed_count = sum(
        1 for t in tables.values() if t.get("status") == "passed"
    )
    failed_count = sum(
        1 for t in tables.values() if t.get("status") == "failed"
    )
    warning_count = sum(
        1 for t in tables.values() if t.get("status") == "warning"
    )
    optional_count = sum(
        1 for t in tables.values() if t.get("status") == "optional"
    )
    
    total_tables = len(tables)
    
    # 提取关键指标
    concept_stats = tables.get("roadmap_metadata", {}).get("checks", {}).get("concept_stats", {})
    execution_logs = tables.get("execution_logs", {})
    
    summary = {
        "verification_time": verification_results["timestamp"],
        "task_id": verification_results["task_id"],
        "roadmap_id": verification_results["roadmap_id"],
        
        # 验证统计
        "verification": {
            "total_tables": total_tables,
            "passed": passed_count,
            "failed": failed_count,
            "warning": warning_count,
            "optional": optional_count,
            "all_critical_passed": failed_count == 0,
        },
        
        # Concept 统计
        "concepts": {
            "total": concept_stats.get("total_concepts", 0),
            "with_tutorial": concept_stats.get("concepts_with_tutorial_id", 0),
            "with_resources": concept_stats.get("concepts_with_resources_id", 0),
            "with_quiz": concept_stats.get("concepts_with_quiz_id", 0),
            "tutorial_rate": concept_stats.get("tutorial_completion_rate", "0%"),
            "resources_rate": concept_stats.get("resources_completion_rate", "0%"),
            "quiz_rate": concept_stats.get("quiz_completion_rate", "0%"),
        },
        
        # 执行日志
        "execution": {
            "total_logs": execution_logs.get("total_logs", 0),
            "stages": execution_logs.get("stages", []),
            "stages_count": execution_logs.get("unique_stages", 0),
        },
        
        # 详细结果（供调试）
        "details": tables,
    }
    
    return summary

