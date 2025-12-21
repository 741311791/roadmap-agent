"""
批量生成封面图脚本

为指定用户的所有路线图生成封面图。
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlmodel import select
from app.db.session import AsyncSessionLocal
from app.models.database import RoadmapMetadata
from app.services.cover_image_service import CoverImageService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_cover_images_for_user(user_id: str):
    """
    为指定用户的所有路线图生成封面图
    
    Args:
        user_id: 用户ID
    """
    logger.info(f"开始为用户 {user_id} 生成封面图")
    
    async with AsyncSessionLocal() as db:
        # 查询用户的所有路线图（未软删除）
        result = await db.execute(
            select(RoadmapMetadata).where(
                RoadmapMetadata.user_id == user_id,
                RoadmapMetadata.deleted_at.is_(None)
            )
        )
        roadmaps = result.scalars().all()
        
        if not roadmaps:
            logger.warning(f"用户 {user_id} 没有路线图")
            return
        
        logger.info(f"找到 {len(roadmaps)} 个路线图")
        
        service = CoverImageService(db)
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        for roadmap in roadmaps:
            roadmap_id = roadmap.roadmap_id
            title = roadmap.title
            
            logger.info(f"处理路线图: {roadmap_id} - {title}")
            
            # 检查是否已有封面图
            status = await service.get_cover_image_status(roadmap_id)
            if status["status"] == "success":
                logger.info(f"  ✓ 已存在封面图: {status['url']}")
                skipped_count += 1
                continue
            
            # 生成封面图
            try:
                cover_url = await service.generate_cover_image(
                    roadmap_id=roadmap_id,
                    prompt=title
                )
                
                if cover_url:
                    logger.info(f"  ✓ 生成成功: {cover_url}")
                    success_count += 1
                else:
                    logger.error(f"  ✗ 生成失败")
                    failed_count += 1
                
                # 避免请求过快
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.exception(f"  ✗ 生成异常: {str(e)}")
                failed_count += 1
        
        logger.info(f"\n生成完成:")
        logger.info(f"  - 成功: {success_count}")
        logger.info(f"  - 失败: {failed_count}")
        logger.info(f"  - 跳过: {skipped_count}")
        logger.info(f"  - 总计: {len(roadmaps)}")


async def main():
    """主函数"""
    # 目标用户ID
    target_user_id = "04005faa-fb45-47dd-a83c-969a25a77046"
    
    logger.info("=" * 60)
    logger.info("批量生成路线图封面图")
    logger.info("=" * 60)
    
    await generate_cover_images_for_user(target_user_id)
    
    logger.info("\n脚本执行完成")


if __name__ == "__main__":
    asyncio.run(main())

