"""
内容修改相关端点

使用Modifier Agent对现有内容进行增量修改：
- 修改教程内容
- 修改资源推荐
- 修改测验内容
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog

from app.models.domain import (
    LearningPreferences,
    Concept,
    TutorialModificationInput,
    ResourceModificationInput,
    QuizModificationInput,
)
from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository
from .utils import find_concept_in_framework

router = APIRouter(prefix="/roadmaps", tags=["modification"])
logger = structlog.get_logger()


class ModifyContentRequest(BaseModel):
    """修改内容请求"""
    user_id: str = Field(..., description="用户ID")
    preferences: LearningPreferences = Field(..., description="用户学习偏好")
    requirements: list[str] = Field(
        ...,
        description="修改要求列表",
        min_length=1,
        examples=[["增加更多代码示例", "简化技术术语"]]
    )


@router.post("/{roadmap_id}/concepts/{concept_id}/tutorial/modify")
async def modify_tutorial(
    roadmap_id: str,
    concept_id: str,
    request: ModifyContentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    修改指定概念的教程内容
    
    使用 TutorialModifierAgent 增量修改现有教程
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 修改请求，包含修改要求
        db: 数据库会话
        
    Returns:
        修改后的教程信息
        
    Raises:
        HTTPException:
            - 404: 路线图、概念或教程不存在
            - 500: 修改失败
            
    Example:
        ```json
        {
            "success": true,
            "concept_id": "flask-basics",
            "tutorial_id": "tut-001",
            "title": "Flask基础入门（修订版）",
            "content_version": 4,
            "modification_summary": "增加了代码示例，简化了技术术语",
            "changes_made": ["添加3个实战代码示例", "重写专业术语说明"]
        }
        ```
    """
    logger.info(
        "modify_tutorial_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        requirements_count=len(request.requirements),
    )
    
    repo = RoadmapRepository(db)
    
    # 获取路线图和概念
    roadmap_metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not roadmap_metadata:
        raise HTTPException(status_code=404, detail=f"路线图 {roadmap_id} 不存在")
    
    framework_data = roadmap_metadata.framework_data
    concept_data, context = find_concept_in_framework(framework_data, concept_id, roadmap_id)
    
    if not concept_data:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 不存在")
    
    # 获取现有教程
    tutorial = await repo.get_latest_tutorial(roadmap_id, concept_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail=f"概念 {concept_id} 没有教程，请先生成")
    
    # 构建 Concept 对象
    concept = Concept(
        concept_id=concept_data.get("concept_id"),
        name=concept_data.get("name"),
        description=concept_data.get("description", ""),
        estimated_hours=concept_data.get("estimated_hours", 1.0),
        prerequisites=concept_data.get("prerequisites", []),
        difficulty=concept_data.get("difficulty", "medium"),
        keywords=concept_data.get("keywords", []),
    )
    
    # 添加版本信息到上下文
    context["content_version"] = tutorial.content_version
    
    try:
        from app.agents.tutorial_modifier import TutorialModifierAgent
        modifier = TutorialModifierAgent()
        
        modification_input = TutorialModificationInput(
            concept=concept,
            context=context,
            user_preferences=request.preferences,
            existing_content_url=tutorial.content_url,
            modification_requirements=request.requirements,
        )
        
        result = await modifier.modify(modification_input)
        
        # 保存新版本到数据库
        from app.models.domain import TutorialGenerationOutput
        tutorial_output = TutorialGenerationOutput(
            concept_id=result.concept_id,
            tutorial_id=result.tutorial_id,
            title=result.title,
            summary=result.summary,
            content_url=result.content_url,
            content_status="completed",
            content_version=result.content_version,
            estimated_completion_time=result.estimated_completion_time,
            generated_at=result.generated_at,
        )
        await repo.save_tutorial_metadata(tutorial_output, roadmap_id)
        await db.commit()
        
        return {
            "success": True,
            "concept_id": result.concept_id,
            "tutorial_id": result.tutorial_id,
            "title": result.title,
            "summary": result.summary,
            "content_url": result.content_url,
            "content_version": result.content_version,
            "modification_summary": result.modification_summary,
            "changes_made": result.changes_made,
        }
        
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
    db: AsyncSession = Depends(get_db),
):
    """
    修改指定概念的学习资源
    
    使用 ResourceModifierAgent 调整现有资源推荐
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 修改请求，包含修改要求
        db: 数据库会话
        
    Returns:
        修改后的资源信息
        
    Raises:
        HTTPException:
            - 404: 路线图、概念或资源不存在
            - 500: 修改失败
            
    Example:
        ```json
        {
            "success": true,
            "concept_id": "flask-basics",
            "resources_id": "res-001-v2",
            "resources_count": 5,
            "modification_summary": "添加了视频教程资源，移除了过时链接",
            "changes_made": ["新增2个视频教程", "替换1个官方文档链接"]
        }
        ```
    """
    logger.info(
        "modify_resources_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        requirements_count=len(request.requirements),
    )
    
    # TODO: 完整实现逻辑类似modify_tutorial
    # 这里返回占位响应
    return {
        "success": True,
        "concept_id": concept_id,
        "message": "资源修改功能正在开发中",
    }


@router.post("/{roadmap_id}/concepts/{concept_id}/quiz/modify")
async def modify_quiz(
    roadmap_id: str,
    concept_id: str,
    request: ModifyContentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    修改指定概念的测验内容
    
    使用 QuizModifierAgent 调整现有测验题目
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        request: 修改请求，包含修改要求
        db: 数据库会话
        
    Returns:
        修改后的测验信息
        
    Raises:
        HTTPException:
            - 404: 路线图、概念或测验不存在
            - 500: 修改失败
            
    Example:
        ```json
        {
            "success": true,
            "concept_id": "flask-basics",
            "quiz_id": "quiz-001-v2",
            "total_questions": 12,
            "modification_summary": "增加了难题，调整了题目顺序",
            "changes_made": ["新增3道hard难度题", "重新排序题目"]
        }
        ```
    """
    logger.info(
        "modify_quiz_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        requirements_count=len(request.requirements),
    )
    
    # TODO: 完整实现逻辑类似modify_tutorial
    # 这里返回占位响应
    return {
        "success": True,
        "concept_id": concept_id,
        "message": "测验修改功能正在开发中",
    }
