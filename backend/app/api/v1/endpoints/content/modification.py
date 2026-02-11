"""
内容修改相关端点

使用Modifier Agent对现有内容进行增量修改：
- 修改测验内容
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
import structlog

from app.schemas.content import ModifyContentRequest
from app.api.v1.deps import CurrentContentService, CurrentSessionTransaction

router = APIRouter(tags=["modification"])
logger = structlog.get_logger()


@router.post("/{roadmap_id}/concepts/{concept_id}/quiz/modify")
async def modify_quiz(
    roadmap_id: str,
    concept_id: str,
    request: ModifyContentRequest,
    session: CurrentSessionTransaction,
    service: CurrentContentService = None,
):
    """
    修改指定概念的测验内容
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 修改请求
        session: 数据库会话
        service: 内容服务
        
    Returns:
        修改后的测验信息
        
    Raises:
        HTTPException: 404/500 错误
    """
    logger.info(
        "modify_quiz_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        requirements_count=len(request.requirements),
    )
    
    try:
        result = await service.modify_quiz(
            session=session,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            requirements=request.requirements,
            preferences=request.preferences,
        )
        # ✅ 不需要手动 commit，CurrentSessionTransaction 自动处理
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(
            "modify_quiz_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"测验修改失败: {str(e)}")
