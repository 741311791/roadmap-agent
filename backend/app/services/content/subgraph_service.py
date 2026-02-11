"""
子图内容生成服务

负责单 Concept 子图的业务逻辑

架构说明：
- ✅ Service 层处理业务逻辑和验证
- ✅ 返回 Pydantic Schema（不是 dict）
- ✅ 抛出业务异常，由 API 层转换为 HTTP 响应
- ✅ 遵循分层架构设计规范
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.models.domain import Concept, LearningPreferences
from app.crud.crud_roadmap import get_roadmap_crud
from app.core.orchestrator.subgraphs.single_concept_content_generation import (
    build_single_concept_subgraph,
)
from app.schemas.content import SubgraphGenerationResponse, ContentSaveStatus

logger = structlog.get_logger()


class SubgraphServiceError(Exception):
    """子图服务业务异常基类"""
    pass


class ResourceNotFoundError(SubgraphServiceError):
    """资源不存在异常"""
    pass


class PermissionDeniedError(SubgraphServiceError):
    """权限不足异常"""
    pass


class InvalidDataError(SubgraphServiceError):
    """数据无效异常"""
    pass


class SubgraphService:
    """子图内容生成服务"""
    
    @staticmethod
    async def generate_single_concept_content(
        db: AsyncSession,
        roadmap_id: str,
        concept_id: str,
        user_id: str,
        runtime_context,
        force_regenerate: bool = False,
    ) -> SubgraphGenerationResponse:
        """
        生成单个 Concept 的内容
        
        Args:
            db: 数据库会话
            roadmap_id: 路线图 ID
            concept_id: Concept ID
            user_id: 用户 ID
            runtime_context: RuntimeContext 实例
            force_regenerate: 是否强制重新生成（忽略已有内容）
            
        Returns:
            SubgraphGenerationResponse: 生成结果 Schema
            
        Raises:
            ResourceNotFoundError: Roadmap 或 Concept 不存在
            PermissionDeniedError: 权限不足
            InvalidDataError: Framework 数据无效
        """
        logger.info(
            "subgraph_service_generate_start",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            user_id=user_id,
        )
        
        # 1. 获取 Roadmap 数据
        roadmap_crud = get_roadmap_crud()
        roadmap_metadata = await roadmap_crud.get_by_roadmap_id(db, roadmap_id)
        
        if not roadmap_metadata:
            raise ResourceNotFoundError(f"Roadmap {roadmap_id} not found")
        
        # 2. 权限检查
        if roadmap_metadata.user_id != user_id:
            raise PermissionDeniedError(
                "You don't have permission to access this roadmap"
            )
        
        # 3. 验证 Framework 数据
        if not roadmap_metadata.framework_data:
            raise InvalidDataError("Roadmap framework data not found")
    
        # 4. 提取 Concept
        concept = SubgraphService._extract_concept_from_framework(
            roadmap_metadata.framework_data,
            concept_id,
        )
        
        if not concept:
            raise ResourceNotFoundError(
                f"Concept {concept_id} not found in roadmap {roadmap_id}"
            )
        
        # 5. 获取 UserPreferences
        user_preferences = SubgraphService._build_user_preferences(
            roadmap_metadata.framework_data
        )
        
        # 6. 构建子图并执行
        subgraph = build_single_concept_subgraph()
        
        # 准备子图输入状态
        state = {
            "concept": concept,
            "roadmap_id": roadmap_id,
            "user_preferences": user_preferences,
            "task_id": f"manual_{concept_id}_{user_id}",
            "tutorial": None,
            "resource": None,
            "quiz": None,
            "errors": [],
            "save_status": {},
        }
        
        # 构建 config
        config = {
            "configurable": {
                "runtime_context": runtime_context,
            }
        }
        
        # 执行子图
        result = await subgraph.ainvoke(state, config)
        
        logger.info(
            "subgraph_service_generate_completed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            save_status=result.get("save_status", {}),
        )
        
        # 构建保存状态 Schema
        save_status_dict = result.get("save_status", {})
        save_status = ContentSaveStatus(
            concept_id=save_status_dict.get("concept_id", concept_id),
            tutorial=save_status_dict.get("tutorial", "skipped"),
            resource=save_status_dict.get("resource", "skipped"),
            quiz=save_status_dict.get("quiz", "skipped"),
            metadata_saved=save_status_dict.get("metadata_saved", False),
        )
        
        # 返回 Pydantic Schema
        return SubgraphGenerationResponse(
            concept_id=concept_id,
            roadmap_id=roadmap_id,
            save_status=save_status,
            tutorial_generated=result.get("tutorial") is not None,
            resource_generated=result.get("resource") is not None,
            quiz_generated=result.get("quiz") is not None,
            errors=result.get("errors", []),
        )
    
    @staticmethod
    def _extract_concept_from_framework(
        framework_data: dict,
        concept_id: str,
    ) -> Concept | None:
        """
        从 Framework 中提取指定的 Concept
        
        Args:
            framework_data: Framework 数据字典
            concept_id: Concept ID
            
        Returns:
            Concept 对象或 None
        """
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for c in module.get("concepts", []):
                    if c.get("concept_id") == concept_id:
                        return Concept.model_validate(c)
        return None
    
    @staticmethod
    def _build_user_preferences(framework_data: dict) -> LearningPreferences:
        """
        从 Framework 数据构建 UserPreferences
        
        Args:
            framework_data: Framework 数据字典
            
        Returns:
            LearningPreferences 对象
        """
        return LearningPreferences(
            learning_goal=framework_data.get("learning_goal", ""),
            available_hours_per_week=framework_data.get(
                "available_hours_per_week", 10
            ),
            motivation="Manual regeneration",
            current_level="intermediate",
            career_background="",
        )

