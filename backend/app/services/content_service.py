"""
内容生成服务 - 统一的重试逻辑
"""
from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import uuid

from app.crud.crud_tutorial import TutorialCRUD, get_tutorial_crud
from app.crud.crud_resource import ResourceCRUD, get_resource_crud
from app.crud.crud_quiz import QuizCRUD, get_quiz_crud
from app.crud.crud_task import TaskCRUD, get_task_crud
from app.crud.crud_roadmap import RoadmapCRUD
from app.crud.crud_concept import ConceptCRUD
from app.services.concept_service import ConceptService, get_concept_service
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.agents.resource_recommender import ResourceRecommenderAgent
from app.agents.quiz_generator import QuizGeneratorAgent
from app.schemas.roadmap import ConceptRetryRequest, ConceptRetryResponse
from app.models.domain import (
    Concept, TutorialGenerationInput, ResourceRecommendationInput, QuizGenerationInput,
    S3DownloadRequest, LearningPreferences, TutorialModificationInput,
)
from app.models.database import (
    TutorialMetadata, ResourceRecommendationMetadata, QuizMetadata,
    RoadmapMetadata, ConceptMetadata,
)
from app.core.tool_registry import tool_registry
from urllib.parse import unquote

logger = structlog.get_logger()

ContentType = Literal["tutorial", "resources", "quiz"]

class ContentService:
    """
    内容生成服务
    
    职责：
    - 统一的重试逻辑（消除tutorial/resources/quiz三个重复函数）
    - Agent调用管理
    - 内容元数据保存
    
    设计模式：策略模式 + 模板方法
    """
    
    def __init__(
        self,
        concept_service: Optional[ConceptService] = None,
        tutorial_crud: Optional[TutorialCRUD] = None,
        resource_crud: Optional[ResourceCRUD] = None,
        quiz_crud: Optional[QuizCRUD] = None,
        task_crud: Optional[TaskCRUD] = None,
    ):
        """
        初始化内容服务
        
        Args:
            concept_service: 概念服务实例
            tutorial_crud: 教程CRUD实例
            resource_crud: 资源CRUD实例
            quiz_crud: 测验CRUD实例
            task_crud: 任务CRUD实例
        """
        self.concept_service = concept_service or get_concept_service()
        self.tutorial_crud = tutorial_crud or get_tutorial_crud()
        self.resource_crud = resource_crud or get_resource_crud()
        self.quiz_crud = quiz_crud or get_quiz_crud()
        self.task_crud = task_crud or get_task_crud()
        self.roadmap_crud = RoadmapCRUD(RoadmapMetadata)
        self.concept_crud = ConceptCRUD(ConceptMetadata)
        
        # Agent实例（延迟初始化以避免循环依赖）
        self._tutorial_agent: Optional[TutorialGeneratorAgent] = None
        self._resource_agent: Optional[ResourceRecommenderAgent] = None
        self._quiz_agent: Optional[QuizGeneratorAgent] = None
    
    @property
    def tutorial_agent(self) -> TutorialGeneratorAgent:
        """延迟初始化教程生成Agent"""
        if self._tutorial_agent is None:
            self._tutorial_agent = TutorialGeneratorAgent()
        return self._tutorial_agent
    
    @property
    def resource_agent(self) -> ResourceRecommenderAgent:
        """延迟初始化资源推荐Agent"""
        if self._resource_agent is None:
            self._resource_agent = ResourceRecommenderAgent()
        return self._resource_agent
    
    @property
    def quiz_agent(self) -> QuizGeneratorAgent:
        """延迟初始化测验生成Agent"""
        if self._quiz_agent is None:
            self._quiz_agent = QuizGeneratorAgent()
        return self._quiz_agent
    
    async def retry_content(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
        content_type: ContentType,
        request: ConceptRetryRequest,
    ) -> ConceptRetryResponse:
        """
        统一的内容重试逻辑（模板方法）
        
        这个方法消除了generation.py中的90%重复代码：
        - retry_tutorial (200行) 
        - retry_resources (180行)
        - retry_quiz (180行)
        
        统一为一个60行的函数
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            content_type: 内容类型 (tutorial/resources/quiz)
            request: 重试请求
            
        Returns:
            重试响应
        """
        logger.info(
            "content_retry_started",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type=content_type,
        )
        
        # ===== 步骤1: 获取概念 =====
        concept, context, roadmap_metadata = await self.concept_service.get_concept_from_roadmap(
            session, roadmap_id, concept_id
        )
        
        if not concept:
            logger.error(
                "concept_not_found_for_retry",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            return ConceptRetryResponse(
                success=False,
                concept_id=concept_id,
                content_type=content_type,
                message=f"Concept {concept_id} not found",
            )
        
        # ===== 步骤2: 更新状态为generating =====
        await self.concept_service.update_concept_status(
            session,
            roadmap_id,
            concept_id,
            content_type,
            "generating",
        )
        
        try:
            # ===== 步骤3: 调用Agent生成内容 =====
            if content_type == "tutorial":
                result = await self._generate_tutorial(concept, context, request)
            elif content_type == "resources":
                result = await self._generate_resources(concept, context, request)
            elif content_type == "quiz":
                result = await self._generate_quiz(concept, context, request)
            else:
                raise ValueError(f"Unknown content type: {content_type}")
            
            # ===== 步骤4: 保存元数据 =====
            await self._save_content_metadata(
                session, roadmap_id, concept_id, content_type, result
            )
            
            # ===== 步骤5: 更新状态为completed =====
            await self.concept_service.update_concept_status(
                session,
                roadmap_id,
                concept_id,
                content_type,
                "completed",
                result,
            )
            
            logger.info(
                "content_retry_success",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                content_type=content_type,
            )
            
            return ConceptRetryResponse(
                success=True,
                concept_id=concept_id,
                content_type=content_type,
                message=f"{content_type.capitalize()} regenerated successfully",
                data=result,
            )
            
        except Exception as e:
            # ===== 步骤6: 错误处理 =====
            logger.error(
                "content_retry_failed",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                content_type=content_type,
                error=str(e),
                exc_info=True,
            )
            
            await self.concept_service.update_concept_status(
                session,
                roadmap_id,
                concept_id,
                content_type,
                "failed",
                {"error": str(e)},
            )
            
            return ConceptRetryResponse(
                success=False,
                concept_id=concept_id,
                content_type=content_type,
                message=f"Failed to regenerate {content_type}: {str(e)}",
            )
    
    # ===== 私有方法：Agent调用（策略实现）=====
    
    async def _generate_tutorial(
        self, 
        concept: dict, 
        context: dict,
        request: ConceptRetryRequest
    ) -> dict:
        """
        生成教程
        
        Args:
            concept: 概念字典
            context: 上下文信息
            request: 重试请求
            
        Returns:
            教程生成结果
        """
        # 构造Agent输入
        concept_obj = Concept.model_validate(concept)
        input_data = TutorialGenerationInput(
            concept=concept_obj,
            context=context,
            user_preferences=request.preferences,
        )
        
        # 调用Agent
        result = await self.tutorial_agent.execute(input_data.model_dump(mode='json'))
        
        return result
    
    async def _generate_resources(
        self, 
        concept: dict, 
        context: dict,
        request: ConceptRetryRequest
    ) -> dict:
        """
        生成资源推荐
        
        Args:
            concept: 概念字典
            context: 上下文信息
            request: 重试请求
            
        Returns:
            资源推荐结果
        """
        # 构造Agent输入
        concept_obj = Concept.model_validate(concept)
        input_data = ResourceRecommendationInput(
            concept=concept_obj,
            context=context,
            user_preferences=request.preferences,
        )
        
        # 调用Agent
        result = await self.resource_agent.execute(input_data.model_dump(mode='json'))
        
        return result
    
    async def _generate_quiz(
        self, 
        concept: dict, 
        context: dict,
        request: ConceptRetryRequest
    ) -> dict:
        """
        生成测验
        
        Args:
            concept: 概念字典
            context: 上下文信息
            request: 重试请求
            
        Returns:
            测验生成结果
        """
        # 构造Agent输入
        concept_obj = Concept.model_validate(concept)
        input_data = QuizGenerationInput(
            concept=concept_obj,
            context=context,
            user_preferences=request.preferences,
        )
        
        # 调用Agent
        result = await self.quiz_agent.execute(input_data.model_dump(mode='json'))
        
        return result
    
    # ===== 私有方法：保存元数据 =====
    
    async def _save_content_metadata(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
        content_type: ContentType,
        result: dict,
    ):
        """
        保存内容元数据到相应的表
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            content_type: 内容类型
            result: 生成结果
        """
        if content_type == "tutorial":
            await self.tutorial_crud.create(session, obj_in={
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "tutorial_id": result.get("tutorial_id"),
                "content": result,
                "version": result.get("content_version", 1),
            })
        elif content_type == "resources":
            await self.resource_crud.create(session, obj_in={
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "resource_id": result.get("id"),
                "content": result,
                "version": 1,
            })
        elif content_type == "quiz":
            await self.quiz_crud.create(session, obj_in={
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "quiz_id": result.get("quiz_id"),
                "content": result,
                "version": 1,
            })
        
        logger.info(
            "content_metadata_saved",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type=content_type,
        )
    
    # ===== 异步任务调度（Celery）=====
    
    async def retry_content_async(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
        content_type: ContentType,
        request: ConceptRetryRequest,
        user_id: str,
    ) -> dict:
        """
        异步重试内容（Celery任务）
        
        激进重构：将Celery任务创建和调度也封装在Service层
        API层只负责HTTP适配
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图ID
            concept_id: 概念ID
            content_type: 内容类型
            request: 重试请求
            user_id: 用户ID
            
        Returns:
            包含task_id的字典
        """
        # 1. 获取概念（验证存在性）
        concept, context, roadmap_metadata = await self.concept_service.get_concept_from_roadmap(
            session, roadmap_id, concept_id
        )
        
        if not concept:
            logger.error(
                "concept_not_found_for_async_retry",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            raise ValueError(f"Concept {concept_id} not found in roadmap {roadmap_id}")
        
        # 2. 生成任务ID
        task_id = self._generate_retry_task_id(roadmap_id, concept_id, content_type)
        
        # 3. 创建任务记录
        await self.task_crud.create(session, obj_in={
            "task_id": task_id,
            "user_id": user_id,
            "user_request": {
                "type": f"retry_{content_type}",
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "preferences": request.preferences.model_dump(mode='json'),
            },
            "task_type": f"retry_{content_type}",
            "status": "processing",
            "current_step": f"{content_type}_generation",
            "roadmap_id": roadmap_id,
            "concept_id": concept_id,
            "content_type": content_type,
        })
        await session.flush()
        
        # 4. 提交Celery任务
        from app.tasks.content_retry_tasks import (
            retry_tutorial_task,
            retry_resources_task,
            retry_quiz_task,
        )
        
        # 准备Celery任务参数
        concept_obj = Concept.model_validate(concept)
        celery_args = [
            task_id,
            roadmap_id,
            concept_id,
            concept_obj.model_dump(mode='json'),
            context,
            request.preferences.model_dump(mode='json'),
        ]
        
        # 根据类型调度不同的任务
        if content_type == "tutorial":
            retry_tutorial_task.apply_async(args=celery_args, task_id=task_id)
        elif content_type == "resources":
            retry_resources_task.apply_async(args=celery_args, task_id=task_id)
        elif content_type == "quiz":
            retry_quiz_task.apply_async(args=celery_args, task_id=task_id)
        else:
            raise ValueError(f"Unknown content type: {content_type}")
        
        logger.info(
            "content_retry_task_submitted",
            task_id=task_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_type=content_type,
        )
        
        return {
            "task_id": task_id,
            "status": "processing",
            "message": f"{content_type.capitalize()} regeneration task submitted",
        }
    
    @staticmethod
    def _generate_retry_task_id(roadmap_id: str, concept_id: str, content_type: str) -> str:
        """
        生成重试任务ID
        
        格式: retry-{content_type}-{concept_id[:8]}-{random}
        """
        short_concept_id = concept_id[:8] if len(concept_id) >= 8 else concept_id
        random_suffix = str(uuid.uuid4())[:8]
        return f"retry-{content_type}-{short_concept_id}-{random_suffix}"
    
    # ===== 查询方法（用于content.py API） =====
    
    async def get_tutorial_versions(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> list[TutorialMetadata]:
        """获取指定概念的所有教程版本历史"""
        from sqlalchemy import select
        
        result = await session.execute(
            select(TutorialMetadata)
            .where(TutorialMetadata.roadmap_id == roadmap_id)
            .where(TutorialMetadata.concept_id == concept_id)
            .order_by(TutorialMetadata.content_version.desc())
        )
        return list(result.scalars().all())
    
    async def get_latest_tutorial(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[TutorialMetadata]:
        """获取最新版本教程"""
        return await self.tutorial_crud.get_latest_by_concept(session, roadmap_id, concept_id)
    
    async def get_tutorial_by_version(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
        version: int,
    ) -> Optional[TutorialMetadata]:
        """获取指定版本教程"""
        from sqlalchemy import select
        
        result = await session.execute(
            select(TutorialMetadata)
            .where(TutorialMetadata.roadmap_id == roadmap_id)
            .where(TutorialMetadata.concept_id == concept_id)
            .where(TutorialMetadata.content_version == version)
        )
        return result.scalars().first()
    
    async def download_tutorial_content(self, tutorial: TutorialMetadata) -> str:
        """下载教程Markdown内容"""
        content_url = tutorial.content_url
        s3_key = content_url
        s3_bucket = None
        
        if "://" in content_url:
            parts = content_url.split("/")
            if len(parts) >= 4:
                potential_bucket = parts[3]
                if "%" not in potential_bucket and ":" not in potential_bucket:
                    s3_bucket = potential_bucket
                    s3_key = "/".join(parts[4:])
                else:
                    from app.config.settings import settings
                    s3_bucket = settings.S3_BUCKET_NAME
                    s3_key = "/".join(parts[4:])
        
        if not s3_bucket:
            from app.config.settings import settings
            s3_bucket = settings.S3_BUCKET_NAME
        
        if "?" in s3_key:
            s3_key = s3_key.split("?")[0]
        
        s3_key = unquote(s3_key)
        
        s3_tool = tool_registry.get("s3_storage_v1")
        if not s3_tool:
            raise ValueError("S3 Storage Tool not available")
        
        download_request = S3DownloadRequest(key=s3_key, bucket=s3_bucket)
        download_result = await s3_tool.download(download_request)
        
        if not download_result.success or not download_result.content:
            raise ValueError("Failed to download tutorial content from storage")
        
        return download_result.content
    
    async def get_concept_resources(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[ResourceRecommendationMetadata]:
        """获取概念的学习资源"""
        return await self.resource_crud.get_by_concept(session, roadmap_id, concept_id)
    
    async def get_concept_quiz(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
    ) -> Optional[QuizMetadata]:
        """获取概念的测验"""
        return await self.quiz_crud.get_by_concept(session, roadmap_id, concept_id)
    
    # ===== 修改方法（用于modification.py API） =====
    
    async def modify_tutorial(
        self,
        session: AsyncSession,
        roadmap_id: str,
        concept_id: str,
        requirements: list[str],
        preferences: LearningPreferences,
    ) -> dict:
        """
        修改教程内容
        
        Args:
            session: 数据库会话
            roadmap_id: 路线图 ID
            concept_id: 概念 ID
            requirements: 修改要求列表
            preferences: 用户学习偏好
            
        Returns:
            修改结果
        """
        # 获取路线图和概念
        roadmap_metadata = await self.roadmap_crud.get_by_roadmap_id(session, roadmap_id)
        if not roadmap_metadata:
            raise ValueError(f"路线图 {roadmap_id} 不存在")
        
        # 获取概念数据
        concept_result = await self.concept_crud.get_concept_from_roadmap(
            session, roadmap_id, concept_id
        )
        if not concept_result:
            raise ValueError(f"概念 {concept_id} 不存在")
        
        concept_data, context, _ = concept_result
        
        # 获取现有教程
        tutorial = await self.tutorial_crud.get_latest_by_concept(session, roadmap_id, concept_id)
        if not tutorial:
            raise ValueError(f"概念 {concept_id} 没有教程，请先生成")
        
        # 构建 Concept 对象
        from app.models.domain import Concept, TutorialModificationInput
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
        
        # 调用修改Agent
        from app.agents.tutorial_modifier import TutorialModifierAgent
        modifier = TutorialModifierAgent()
        
        modification_input = TutorialModificationInput(
            concept=concept,
            context=context,
            user_preferences=preferences,
            existing_content_url=tutorial.content_url,
            modification_requirements=requirements,
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
        
        # 使用concept_service保存
        await self.concept_service.save_tutorial_metadata(
            session, tutorial_output, roadmap_id
        )
        
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


# 全局单例（可选）
_content_service_instance: Optional[ContentService] = None

def get_content_service() -> ContentService:
    """获取内容服务实例（单例模式）"""
    global _content_service_instance
    if _content_service_instance is None:
        _content_service_instance = ContentService()
    return _content_service_instance

