"""
内容修改相关端点

使用Modifier Agent对现有内容进行增量修改：
- 修改教程内容
- 修改资源推荐
- 修改测验内容
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
import structlog

from app.schemas.content import ModifyContentRequest
from app.api.v1.deps import CurrentContentService, CurrentSessionTransaction

router = APIRouter(tags=["modification"])
logger = structlog.get_logger()


@router.post("/{roadmap_id}/concepts/{concept_id}/tutorial/modify")
async def modify_tutorial(
    roadmap_id: str,
    concept_id: str,
    request: ModifyContentRequest,
    session: CurrentSessionTransaction,
    service: CurrentContentService = None,
):
    """
    修改指定概念的教程内容
    
    使用 TutorialModifierAgent 增量修改现有教程
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 修改请求，包含修改要求
        session: 数据库会话
        service: 内容服务
        
    Returns:
        修改后的教程信息
        
    Raises:
        HTTPException:
            - 404: 路线图、概念或教程不存在
            - 500: 修改失败
    """
    logger.info(
        "modify_tutorial_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        requirements_count=len(request.requirements),
    )
    
    try:
        result = await service.modify_tutorial(
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
            "modify_tutorial_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"教程修改失败: {str(e)}")


@router.post("/{roadmap_id}/concepts/{concept_id}/resources/modify")
async def modify_resources(
    roadmap_id: str,
    concept_id: str,
    request: ModifyContentRequest,
    session: CurrentSessionTransaction,
    service: CurrentContentService = None,
):
    """
    修改指定概念的学习资源
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 修改请求
        session: 数据库会话
        service: 内容服务
        
    Returns:
        修改后的资源信息
        
    Raises:
        HTTPException: 404/500 错误
    """
    logger.info(
        "modify_resources_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        requirements_count=len(request.requirements),
    )
    
    try:
        result = await service.modify_resources(
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
            "modify_resources_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"资源修改失败: {str(e)}")


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
