"""
将数据库中教程的 content_url 从预签名 URL 迁移为 S3 Key

**背景**：
- 旧代码：content_url 存储预签名 URL（7天有效期）
- 新代码：content_url 存储 S3 Key（永久有效）

**迁移逻辑**：
- 识别预签名 URL（包含 `://`）
- 提取 S3 Key（去除 domain、bucket、签名参数）
- 更新数据库记录

**使用方法**：
```bash
cd backend
python scripts/migrate_tutorial_urls_to_keys.py
```
"""
import asyncio
import sys
from pathlib import Path
from urllib.parse import unquote

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import structlog

from app.config.settings import settings
from app.models.database import Tutorial

logger = structlog.get_logger()


def extract_s3_key_from_url(url: str, default_bucket: str) -> str:
    """
    从预签名 URL 提取 S3 Key
    
    Args:
        url: 预签名 URL 或 S3 Key
        default_bucket: 默认 bucket 名称
        
    Returns:
        S3 Key（格式：roadmap_id/concepts/concept_id/vN.md）
    """
    # 如果不是 URL，直接返回（已经是 S3 Key）
    if "://" not in url:
        return url
    
    # 解析 URL
    # 示例：https://xxx.r2.cloudflarestorage.com/roadmap-content/abc123/concepts/python-basics/v1.md?X-Amz-...
    
    parts = url.split("/")
    
    # 尝试识别 bucket
    s3_key = None
    
    if len(parts) >= 4:
        potential_bucket = parts[3]
        
        # 如果是已知的 bucket，key 从 bucket 后开始
        if potential_bucket == default_bucket:
            s3_key = "/".join(parts[4:])
        elif "%" not in potential_bucket and ":" not in potential_bucket:
            # 可能是 bucket
            s3_key = "/".join(parts[4:])
        else:
            # 无法识别，保守提取
            s3_key = "/".join(parts[3:])
    
    # 移除签名参数
    if s3_key and "?" in s3_key:
        s3_key = s3_key.split("?")[0]
    
    # URL 解码
    if s3_key:
        s3_key = unquote(s3_key)
    
    return s3_key or url


async def migrate_tutorial_urls():
    """迁移教程 URL 到 S3 Key"""
    # 创建数据库引擎
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )
    
    # 创建会话工厂
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    default_bucket = settings.S3_BUCKET_NAME
    
    logger.info(
        "migration_started",
        database=settings.DATABASE_URL.split("@")[-1].split("/")[0],
        default_bucket=default_bucket,
    )
    
    async with async_session() as session:
        # 1. 查询所有教程
        result = await session.execute(
            select(Tutorial).where(Tutorial.content_url.isnot(None))
        )
        tutorials = result.scalars().all()
        
        total = len(tutorials)
        logger.info("tutorials_found", total=total)
        
        if total == 0:
            logger.info("no_tutorials_to_migrate")
            return
        
        # 2. 统计需要迁移的数量
        to_migrate = []
        already_migrated = []
        
        for tutorial in tutorials:
            if "://" in tutorial.content_url:
                to_migrate.append(tutorial)
            else:
                already_migrated.append(tutorial)
        
        logger.info(
            "migration_stats",
            total=total,
            to_migrate=len(to_migrate),
            already_migrated=len(already_migrated),
        )
        
        if len(to_migrate) == 0:
            logger.info("all_tutorials_already_migrated")
            return
        
        # 3. 执行迁移
        migrated_count = 0
        failed_count = 0
        
        for tutorial in to_migrate:
            try:
                old_url = tutorial.content_url
                new_key = extract_s3_key_from_url(old_url, default_bucket)
                
                # 更新数据库
                await session.execute(
                    update(Tutorial)
                    .where(Tutorial.id == tutorial.id)
                    .values(content_url=new_key)
                )
                
                migrated_count += 1
                
                logger.info(
                    "tutorial_migrated",
                    tutorial_id=tutorial.tutorial_id,
                    concept_id=tutorial.concept_id,
                    old_url=old_url[:80] + "..." if len(old_url) > 80 else old_url,
                    new_key=new_key,
                )
            
            except Exception as e:
                failed_count += 1
                logger.error(
                    "tutorial_migration_failed",
                    tutorial_id=tutorial.tutorial_id,
                    concept_id=tutorial.concept_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
        
        # 4. 提交事务
        await session.commit()
        
        logger.info(
            "migration_completed",
            total=total,
            migrated=migrated_count,
            already_migrated=len(already_migrated),
            failed=failed_count,
        )
        
        # 5. 验证迁移结果
        result = await session.execute(
            select(Tutorial).where(Tutorial.content_url.contains("://"))
        )
        remaining_urls = result.scalars().all()
        
        if remaining_urls:
            logger.warning(
                "migration_incomplete",
                remaining_urls=len(remaining_urls),
                message="仍有教程包含完整 URL，请检查",
            )
        else:
            logger.info("migration_verified", message="所有教程已成功迁移为 S3 Key")
    
    await engine.dispose()


async def main():
    """主函数"""
    print("=" * 60)
    print("教程 URL 迁移脚本")
    print("=" * 60)
    print(f"数据库: {settings.DATABASE_URL.split('@')[-1]}")
    print(f"S3 Bucket: {settings.S3_BUCKET_NAME}")
    print()
    
    # 确认提示
    confirm = input("确认开始迁移？(yes/no): ").strip().lower()
    
    if confirm != "yes":
        print("迁移已取消")
        return
    
    print()
    print("开始迁移...")
    print()
    
    try:
        await migrate_tutorial_urls()
        print()
        print("✅ 迁移完成！")
    except Exception as e:
        print()
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

