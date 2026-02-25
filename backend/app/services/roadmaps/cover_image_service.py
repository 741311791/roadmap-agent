"""
封面图生成服务

负责调用外部图片生成 API 为路线图生成封面图。

架构规范：
- 服务层不直接操作数据库，通过 CRUD 层执行
- 服务层不负责事务管理（不调用 commit）
- 由调用方（Celery 任务）通过 get_celery_session 上下文自动提交
"""
import httpx
import structlog
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_cover_image import get_cover_image_crud
from app.crud.crud_roadmap import get_roadmap_crud
from app.schemas.cover_image import CoverImageStatusResponse

logger = structlog.get_logger()

# 图片生成 API 配置
COVER_IMAGE_API_URL = "http://47.111.115.130:5678/webhook/text-to-image"
# API 生成时间最长约 2 分钟，设置 150 秒留有余量
COVER_IMAGE_TIMEOUT = 150.0


class CoverImageService:
    """封面图生成服务"""

    def __init__(self, db: AsyncSession):
        """
        初始化服务
        
        Args:
            db: 异步数据库会话
        """
        self.db = db
        self._cover_image_crud = get_cover_image_crud()
        self._roadmap_crud = get_roadmap_crud()

    async def generate_cover_image(
        self,
        roadmap_id: str,
        prompt: Optional[str] = None,
    ) -> Optional[str]:
        """
        为路线图生成封面图，每次调用均重新生成，结果写入数据库
        
        Args:
            roadmap_id: 路线图 ID
            prompt: 图片生成提示词，不提供时使用路线图标题
            
        Returns:
            生成成功的封面图 URL，失败返回 None
        """
        # 获取提示词（未提供时取路线图标题）
        if not prompt:
            roadmap = await self._roadmap_crud.get_by_roadmap_id(self.db, roadmap_id)
            if not roadmap:
                logger.error("roadmap_not_found", roadmap_id=roadmap_id)
                return None
            prompt = roadmap.title

        # 标记数据库记录为「生成中」
        await self._cover_image_crud.upsert_generating(self.db, roadmap_id)

        logger.info("cover_image_generation_started", roadmap_id=roadmap_id, prompt=prompt)

        try:
            async with httpx.AsyncClient(timeout=COVER_IMAGE_TIMEOUT) as client:
                response = await client.post(
                    COVER_IMAGE_API_URL,
                    json={"prompt": prompt},
                )
                response.raise_for_status()
                result = response.json()

            if result.get("status") == "success" and result.get("url"):
                cover_image_url = result["url"]
                await self._cover_image_crud.mark_success(self.db, roadmap_id, cover_image_url)
                logger.info("cover_image_generation_success", roadmap_id=roadmap_id, url=cover_image_url)
                return cover_image_url

            error_msg = f"API 返回状态异常: {result}"
            await self._cover_image_crud.mark_failed(self.db, roadmap_id, error_msg)
            logger.error("cover_image_generation_failed", roadmap_id=roadmap_id, error=error_msg)
            return None

        except httpx.TimeoutException as e:
            error_msg = f"请求超时: {e}"
            await self._cover_image_crud.mark_failed(self.db, roadmap_id, error_msg)
            logger.error("cover_image_generation_timeout", roadmap_id=roadmap_id, error=error_msg)
            return None

        except httpx.HTTPError as e:
            error_msg = f"HTTP 错误: {e}"
            await self._cover_image_crud.mark_failed(self.db, roadmap_id, error_msg)
            logger.error("cover_image_generation_http_error", roadmap_id=roadmap_id, error=error_msg)
            return None

        except Exception as e:
            error_msg = f"未知错误: {e}"
            await self._cover_image_crud.mark_failed(self.db, roadmap_id, error_msg)
            logger.exception("cover_image_generation_unknown_error", roadmap_id=roadmap_id, error=error_msg)
            return None

    async def get_cover_image_status(self, roadmap_id: str) -> CoverImageStatusResponse:
        """
        获取封面图生成状态
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            封面图状态 Schema
        """
        record = await self._cover_image_crud.get_by_roadmap_id(self.db, roadmap_id)

        if not record:
            return CoverImageStatusResponse(
                status="not_started",
                url=None,
                error=None,
                retry_count=0,
            )

        status_mapping = {
            "pending": "not_started",
            "generating": "processing",
            "success": "completed",
            "failed": "failed",
        }
        return CoverImageStatusResponse(
            status=status_mapping.get(record.generation_status, "not_started"),
            url=record.cover_image_url,
            error=record.error_message,
            retry_count=record.retry_count,
        )

    async def batch_get_cover_images(
        self,
        roadmap_ids: list[str],
    ) -> dict[str, CoverImageStatusResponse]:
        """
        批量获取多个路线图的封面图状态
        
        Args:
            roadmap_ids: 路线图 ID 列表
            
        Returns:
            字典，key 为 roadmap_id，value 为封面图状态 Schema
        """
        if not roadmap_ids:
            return {}

        records = await self._cover_image_crud.batch_get_by_roadmap_ids(self.db, roadmap_ids)

        status_mapping = {
            "pending": "not_started",
            "generating": "processing",
            "success": "completed",
            "failed": "failed",
        }

        result: dict[str, CoverImageStatusResponse] = {
            record.roadmap_id: CoverImageStatusResponse(
                status=status_mapping.get(record.generation_status, "not_started"),
                url=record.cover_image_url,
                error=record.error_message,
                retry_count=record.retry_count,
            )
            for record in records
        }

        # 没有记录的路线图返回 not_started
        for roadmap_id in roadmap_ids:
            if roadmap_id not in result:
                result[roadmap_id] = CoverImageStatusResponse(
                    status="not_started",
                    url=None,
                    error=None,
                    retry_count=0,
                )

        return result
