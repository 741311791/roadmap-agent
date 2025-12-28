"""
封面图生成服务

负责调用外部图片生成 API 为路线图生成封面图。
"""
import httpx
import logging
from typing import Optional, Union
from sqlmodel import Session, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import RoadmapCoverImage, RoadmapMetadata, beijing_now

logger = logging.getLogger(__name__)

# 图片生成 API 配置
COVER_IMAGE_API_URL = "http://47.111.115.130:5678/webhook/text-to-image"
COVER_IMAGE_TIMEOUT = 30.0  # 超时时间（秒）
MAX_RETRY_COUNT = 3  # 最大重试次数


class CoverImageService:
    """封面图生成服务"""
    
    def __init__(self, db: Union[Session, AsyncSession]):
        """
        初始化服务
        
        Args:
            db: 数据库会话（支持同步和异步）
        """
        self.db = db
        self.is_async = isinstance(db, AsyncSession)
    
    async def generate_cover_image(
        self, 
        roadmap_id: str,
        prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        为路线图生成封面图
        
        Args:
            roadmap_id: 路线图ID
            prompt: 可选的图片生成提示词，如果不提供则使用路线图标题
        
        Returns:
            生成的封面图URL，失败返回 None
        """
        try:
            # 检查是否已有记录
            if self.is_async:
                result = await self.db.execute(
                    select(RoadmapCoverImage).where(
                        RoadmapCoverImage.roadmap_id == roadmap_id
                    )
                )
                cover_image = result.scalars().first()
            else:
                cover_image = self.db.exec(
                    select(RoadmapCoverImage).where(
                        RoadmapCoverImage.roadmap_id == roadmap_id
                    )
                ).first()
            
            # 如果已经成功生成过，直接返回
            if cover_image and cover_image.generation_status == "success":
                logger.info(f"封面图已存在: roadmap_id={roadmap_id}, url={cover_image.cover_image_url}")
                return cover_image.cover_image_url
            
            # 如果重试次数超过限制，不再重试
            if cover_image and cover_image.retry_count >= MAX_RETRY_COUNT:
                logger.warning(f"封面图生成重试次数已达上限: roadmap_id={roadmap_id}")
                return None
            
            # 获取路线图信息用于生成提示词
            if not prompt:
                if self.is_async:
                    result = await self.db.execute(
                        select(RoadmapMetadata).where(
                            RoadmapMetadata.roadmap_id == roadmap_id
                        )
                    )
                    roadmap = result.scalars().first()
                else:
                    roadmap = self.db.exec(
                        select(RoadmapMetadata).where(
                            RoadmapMetadata.roadmap_id == roadmap_id
                        )
                    ).first()
                
                if roadmap:
                    prompt = roadmap.title
                else:
                    logger.error(f"路线图不存在: roadmap_id={roadmap_id}")
                    return None
            
            # 创建或更新记录状态为 generating
            if not cover_image:
                cover_image = RoadmapCoverImage(
                    roadmap_id=roadmap_id,
                    generation_status="generating",
                    retry_count=0
                )
                self.db.add(cover_image)
            else:
                cover_image.generation_status = "generating"
                cover_image.retry_count += 1
                cover_image.updated_at = beijing_now()
            
            if self.is_async:
                await self.db.commit()
            else:
                self.db.commit()
            
            # 调用外部 API 生成图片
            logger.info(f"开始生成封面图: roadmap_id={roadmap_id}, prompt={prompt}")
            
            async with httpx.AsyncClient(timeout=COVER_IMAGE_TIMEOUT) as client:
                response = await client.post(
                    COVER_IMAGE_API_URL,
                    json={"prompt": prompt}
                )
                response.raise_for_status()
                
                result = response.json()
                
                # 检查返回状态
                if result.get("status") == "success" and result.get("url"):
                    cover_image_url = result["url"]
                    
                    # 更新数据库记录
                    cover_image.cover_image_url = cover_image_url
                    cover_image.generation_status = "success"
                    cover_image.error_message = None
                    cover_image.updated_at = beijing_now()
                    if self.is_async:
                        await self.db.commit()
                    else:
                        self.db.commit()
                    
                    logger.info(f"封面图生成成功: roadmap_id={roadmap_id}, url={cover_image_url}")
                    return cover_image_url
                else:
                    error_msg = f"API 返回状态异常: {result}"
                    logger.error(f"封面图生成失败: roadmap_id={roadmap_id}, {error_msg}")
                    
                    cover_image.generation_status = "failed"
                    cover_image.error_message = error_msg
                    cover_image.updated_at = beijing_now()
                    if self.is_async:
                        await self.db.commit()
                    else:
                        self.db.commit()
                    
                    return None
        
        except httpx.TimeoutException as e:
            error_msg = f"请求超时: {str(e)}"
            logger.error(f"封面图生成失败: roadmap_id={roadmap_id}, {error_msg}")
            
            if cover_image:
                cover_image.generation_status = "failed"
                cover_image.error_message = error_msg
                cover_image.updated_at = beijing_now()
                if self.is_async:
                    await self.db.commit()
                else:
                    self.db.commit()
            
            return None
        
        except httpx.HTTPError as e:
            error_msg = f"HTTP 错误: {str(e)}"
            logger.error(f"封面图生成失败: roadmap_id={roadmap_id}, {error_msg}")
            
            if cover_image:
                cover_image.generation_status = "failed"
                cover_image.error_message = error_msg
                cover_image.updated_at = beijing_now()
                if self.is_async:
                    await self.db.commit()
                else:
                    self.db.commit()
            
            return None
        
        except Exception as e:
            error_msg = f"未知错误: {str(e)}"
            logger.exception(f"封面图生成失败: roadmap_id={roadmap_id}, {error_msg}")
            
            if cover_image:
                cover_image.generation_status = "failed"
                cover_image.error_message = error_msg
                cover_image.updated_at = beijing_now()
                if self.is_async:
                    await self.db.commit()
                else:
                    self.db.commit()
            
            return None
    
    async def get_cover_image_url(self, roadmap_id: str) -> Optional[str]:
        """
        获取路线图的封面图URL
        
        Args:
            roadmap_id: 路线图ID
        
        Returns:
            封面图URL，如果不存在或生成失败返回 None
        """
        if self.is_async:
            result = await self.db.execute(
                select(RoadmapCoverImage).where(
                    RoadmapCoverImage.roadmap_id == roadmap_id
                )
            )
            cover_image = result.scalars().first()
        else:
            cover_image = self.db.exec(
                select(RoadmapCoverImage).where(
                    RoadmapCoverImage.roadmap_id == roadmap_id
                )
            ).first()
        
        if cover_image and cover_image.generation_status == "success":
            return cover_image.cover_image_url
        
        return None
    
    async def get_cover_image_status(self, roadmap_id: str) -> dict:
        """
        获取封面图生成状态
        
        Args:
            roadmap_id: 路线图ID
        
        Returns:
            包含状态信息的字典
        """
        if self.is_async:
            result = await self.db.execute(
                select(RoadmapCoverImage).where(
                    RoadmapCoverImage.roadmap_id == roadmap_id
                )
            )
            cover_image = result.scalars().first()
        else:
            cover_image = self.db.exec(
                select(RoadmapCoverImage).where(
                    RoadmapCoverImage.roadmap_id == roadmap_id
                )
            ).first()
        
        if not cover_image:
            return {
                "status": "not_started",
                "url": None,
                "error": None
            }
        
        return {
            "status": cover_image.generation_status,
            "url": cover_image.cover_image_url,
            "error": cover_image.error_message,
            "retry_count": cover_image.retry_count
        }
    
    async def batch_get_cover_images(self, roadmap_ids: list[str]) -> dict[str, dict]:
        """
        批量获取多个路线图的封面图状态
        
        Args:
            roadmap_ids: 路线图ID列表
        
        Returns:
            字典，key为roadmap_id，value为状态信息字典
        """
        if not roadmap_ids:
            return {}
        
        if self.is_async:
            result = await self.db.execute(
                select(RoadmapCoverImage).where(
                    RoadmapCoverImage.roadmap_id.in_(roadmap_ids)
                )
            )
            cover_images = result.scalars().all()
        else:
            cover_images = self.db.exec(
                select(RoadmapCoverImage).where(
                    RoadmapCoverImage.roadmap_id.in_(roadmap_ids)
                )
            ).all()
        
        # 构建结果字典
        result_dict: dict[str, dict] = {}
        
        # 先处理有记录的路线图
        for cover_image in cover_images:
            result_dict[cover_image.roadmap_id] = {
                "status": cover_image.generation_status,
                "url": cover_image.cover_image_url,
                "error": cover_image.error_message,
                "retry_count": cover_image.retry_count
            }
        
        # 处理没有记录的路线图（返回not_started状态）
        for roadmap_id in roadmap_ids:
            if roadmap_id not in result_dict:
                result_dict[roadmap_id] = {
                    "status": "not_started",
                    "url": None,
                    "error": None,
                    "retry_count": None
                }
        
        return result_dict

