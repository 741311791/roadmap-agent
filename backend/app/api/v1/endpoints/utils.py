"""
API端点辅助工具函数

所有函数已迁移到 app.services.content_retry_service
请直接使用 ContentRetryService
"""
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.domain import Concept
from app.services.content_retry_service import ContentRetryService

logger = structlog.get_logger()


# 直接导出Service实例供外部使用
def get_content_retry_service() -> ContentRetryService:
    """获取ContentRetryService实例"""
    return ContentRetryService()


# 简化的包装函数（仅用于最小化迁移影响）
def get_failed_content_items(framework_data: dict) -> dict:
    """获取失败的内容项目"""
    service = ContentRetryService()
    return service.get_failed_content_items(framework_data)


def extract_concepts_from_framework(framework_data: dict):
    """从framework_data中提取Concepts及其上下文"""
    service = ContentRetryService()
    return service.extract_concepts_with_context(framework_data)


async def get_failed_content_items_v2(roadmap_id: str, session: AsyncSession) -> dict:
    """基于concept_metadata表获取失败的内容项目"""
    service = ContentRetryService()
    return await service.get_failed_content_items_v2(session, roadmap_id)


def find_concept_in_framework(
    framework_data: dict,
    concept_id: str,
    roadmap_id: str,
) -> tuple[dict | None, dict]:
    """在路线图框架中查找概念"""
    context = {"roadmap_id": roadmap_id}
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for c in module.get("concepts", []):
                if c.get("concept_id") == concept_id:
                    context.update({
                        "stage_id": stage.get("stage_id"),
                        "stage_name": stage.get("name"),
                        "module_id": module.get("module_id"),
                        "module_name": module.get("name"),
                    })
                    return c, context
    
    return None, context
