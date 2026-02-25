#!/usr/bin/env python3
"""
封面图生成服务测试脚本

功能：
1. 测试封面图生成（直接调用服务和通过 Celery）
2. 查询封面图状态
3. 测试批量生成
4. 验证数据库记录

使用方法：
    cd backend
    
    # 测试单个路线图的封面图生成（直接调用服务）
    uv run python scripts/test_cover_image_generation.py --roadmap-id fastapi-99c921a9
    
    # 测试单个路线图的封面图生成（通过 Celery 异步任务）
    uv run python scripts/test_cover_image_generation.py --roadmap-id fastapi-99c921a9 --async
    
    # 测试批量生成（需要提供多个 roadmap_id）
    uv run python scripts/test_cover_image_generation.py --batch --roadmap-ids id1 id2 id3
    
    # 只查询状态，不生成
    uv run python scripts/test_cover_image_generation.py --roadmap-id fastapi-99c921a9 --status-only

注意：
    - 需要确保 Celery Worker 已启动（如果使用 --async 模式）
    - 封面图生成 API 地址: http://47.111.115.130:5678/webhook/text-to-image
    - 生成时间约 10-30 秒
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import structlog

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import async_session_maker
from app.crud.crud_roadmap import get_roadmap_crud
from app.services.roadmaps.cover_image_service import CoverImageService
from app.tasks.cover_image_tasks import generate_cover_image_task

logger = structlog.get_logger()


# ============================================================
# 测试函数
# ============================================================

async def check_roadmap_exists(roadmap_id: str) -> dict:
    """
    检查路线图是否存在
    
    Args:
        roadmap_id: 路线图ID
    
    Returns:
        路线图信息字典
    """
    print(f"\n{'='*70}")
    print(f"🔍 检查路线图")
    print(f"{'='*70}")
    print(f"   Roadmap ID: {roadmap_id}")
    
    try:
        async with async_session_maker() as session:
            roadmap_crud = get_roadmap_crud()
            roadmap = await roadmap_crud.get_by_roadmap_id(session, roadmap_id)
            
            if not roadmap:
                print(f"   ❌ 路线图不存在")
                sys.exit(1)
            
            print(f"   ✅ 路线图存在")
            print(f"      标题: {roadmap.title or 'N/A'}")
            print(f"      用户: {roadmap.user_id}")
            print(f"      创建时间: {roadmap.created_at}")
            
            return {
                "roadmap_id": roadmap_id,
                "title": roadmap.title,
                "user_id": roadmap.user_id,
            }
    
    except Exception as e:
        print(f"   ❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def get_cover_image_status(roadmap_id: str) -> dict:
    """
    查询封面图状态
    
    Args:
        roadmap_id: 路线图ID
    
    Returns:
        封面图状态信息
    """
    print(f"\n{'='*70}")
    print(f"📊 查询封面图状态")
    print(f"{'='*70}")
    
    try:
        async with async_session_maker() as session:
            service = CoverImageService(session)
            status = await service.get_cover_image_status(roadmap_id)
            
            print(f"   状态: {status.status}")
            print(f"   URL: {status.url or 'N/A'}")
            print(f"   重试次数: {status.retry_count}")
            
            if status.error:
                print(f"   错误信息: {status.error}")
            
            return {
                "status": status.status,
                "url": status.url,
                "retry_count": status.retry_count,
                "error": status.error,
            }
    
    except Exception as e:
        print(f"   ❌ 查询失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def generate_cover_image_sync(roadmap_id: str, prompt: str | None = None) -> dict:
    """
    生成封面图（同步方式，直接调用服务）
    
    Args:
        roadmap_id: 路线图ID
        prompt: 可选的提示词
    
    Returns:
        生成结果
    """
    print(f"\n{'='*70}")
    print(f"🎨 生成封面图（同步方式）")
    print(f"{'='*70}")
    print(f"   Roadmap ID: {roadmap_id}")
    print(f"   Prompt: {prompt or '使用路线图标题'}")
    
    start_time = datetime.now()
    
    try:
        async with async_session_maker.begin() as session:
            service = CoverImageService(session)
            
            print(f"\n   ⏳ 开始生成...")
            result_url = await service.generate_cover_image(roadmap_id, prompt)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            if result_url:
                print(f"\n   ✅ 生成成功")
                print(f"   耗时: {elapsed:.1f}秒")
                print(f"   URL: {result_url}")
                return {
                    "success": True,
                    "url": result_url,
                    "elapsed": elapsed,
                }
            else:
                print(f"\n   ⚠️ 生成失败或跳过")
                print(f"   耗时: {elapsed:.1f}秒")
                
                # 查询状态获取更多信息
                status = await service.get_cover_image_status(roadmap_id)
                print(f"   当前状态: {status.status}")
                if status.error:
                    print(f"   错误: {status.error}")
                
                return {
                    "success": False,
                    "url": None,
                    "elapsed": elapsed,
                    "status": status.status,
                    "error": status.error,
                }
    
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n   ❌ 生成失败")
        print(f"   耗时: {elapsed:.1f}秒")
        print(f"   错误: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "url": None,
            "elapsed": elapsed,
            "error": str(e),
        }


def generate_cover_image_async(roadmap_id: str, prompt: str | None = None) -> dict:
    """
    生成封面图（异步方式，通过 Celery）
    
    Args:
        roadmap_id: 路线图ID
        prompt: 可选的提示词
    
    Returns:
        Celery 任务信息
    """
    print(f"\n{'='*70}")
    print(f"🎨 生成封面图（异步方式 - Celery）")
    print(f"{'='*70}")
    print(f"   Roadmap ID: {roadmap_id}")
    print(f"   Prompt: {prompt or '使用路线图标题'}")
    
    try:
        # 分发 Celery 任务
        celery_task = generate_cover_image_task.delay(
            roadmap_id=roadmap_id,
            prompt=prompt or "Generate a modern learning roadmap cover",
        )
        
        print(f"\n   ✅ Celery 任务已分发")
        print(f"   Task ID: {celery_task.id}")
        print(f"   状态: {celery_task.state}")
        
        print(f"\n   💡 提示:")
        print(f"      - 任务将在后台执行")
        print(f"      - 可以使用 --status-only 参数查询进度")
        print(f"      - 生成时间约 10-30 秒")
        
        return {
            "success": True,
            "task_id": celery_task.id,
            "state": celery_task.state,
        }
    
    except Exception as e:
        print(f"\n   ❌ 任务分发失败")
        print(f"   错误: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
        }


async def batch_get_cover_images(roadmap_ids: list[str]) -> dict:
    """
    批量查询封面图状态
    
    Args:
        roadmap_ids: 路线图ID列表
    
    Returns:
        批量查询结果
    """
    print(f"\n{'='*70}")
    print(f"📊 批量查询封面图状态")
    print(f"{'='*70}")
    print(f"   Roadmap IDs 数量: {len(roadmap_ids)}")
    
    try:
        async with async_session_maker() as session:
            service = CoverImageService(session)
            results = await service.batch_get_cover_images(roadmap_ids)
            
            print(f"\n   查询结果:")
            
            # 统计各状态数量
            status_counts = {
                "not_started": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
            }
            
            for roadmap_id, status_info in results.items():
                status_counts[status_info.status] = status_counts.get(status_info.status, 0) + 1
                
                print(f"\n      [{roadmap_id}]")
                print(f"         状态: {status_info.status}")
                print(f"         URL: {status_info.url or 'N/A'}")
                print(f"         重试次数: {status_info.retry_count}")
                if status_info.error:
                    print(f"         错误: {status_info.error}")
            
            print(f"\n   统计:")
            print(f"      - 未开始: {status_counts['not_started']}")
            print(f"      - 生成中: {status_counts['processing']}")
            print(f"      - 已完成: {status_counts['completed']}")
            print(f"      - 失败: {status_counts['failed']}")
            
            return {
                "total": len(roadmap_ids),
                "results": results,
                "stats": status_counts,
            }
    
    except Exception as e:
        print(f"   ❌ 批量查询失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def verify_database_record(roadmap_id: str):
    """
    验证数据库记录
    
    Args:
        roadmap_id: 路线图ID
    """
    print(f"\n{'='*70}")
    print(f"🔍 验证数据库记录")
    print(f"{'='*70}")
    
    try:
        from sqlalchemy import select
        from app.models.database import RoadmapCoverImage
        
        async with async_session_maker() as session:
            result = await session.execute(
                select(RoadmapCoverImage).where(
                    RoadmapCoverImage.roadmap_id == roadmap_id
                )
            )
            cover_image = result.scalars().first()
            
            if not cover_image:
                print(f"   ⚠️ 数据库中无记录")
                return
            
            print(f"   ✅ 找到数据库记录")
            print(f"      Roadmap ID: {cover_image.roadmap_id} (主键)")
            print(f"      状态: {cover_image.generation_status}")
            print(f"      URL: {cover_image.cover_image_url or 'N/A'}")
            print(f"      重试次数: {cover_image.retry_count}")
            print(f"      创建时间: {cover_image.created_at}")
            print(f"      更新时间: {cover_image.updated_at}")
            
            if cover_image.error_message:
                print(f"      错误信息: {cover_image.error_message}")
    
    except Exception as e:
        print(f"   ⚠️ 验证过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


# ============================================================
# 主函数
# ============================================================

async def main():
    """主测试流程"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="封面图生成服务测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 测试单个路线图（同步方式）
  uv run python scripts/test_cover_image_generation.py --roadmap-id fastapi-99c921a9
  
  # 测试单个路线图（异步方式 - Celery）
  uv run python scripts/test_cover_image_generation.py --roadmap-id fastapi-99c921a9 --async
  
  # 只查询状态
  uv run python scripts/test_cover_image_generation.py --roadmap-id fastapi-99c921a9 --status-only
  
  # 自定义提示词
  uv run python scripts/test_cover_image_generation.py --roadmap-id fastapi-99c921a9 --prompt "Modern tech roadmap design"
  
  # 批量查询
  uv run python scripts/test_cover_image_generation.py --batch --roadmap-ids id1 id2 id3
        """
    )
    
    parser.add_argument(
        "--roadmap-id",
        type=str,
        help="路线图ID"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="自定义生成提示词（可选）"
    )
    parser.add_argument(
        "--async",
        action="store_true",
        dest="use_async",
        help="使用异步方式（Celery）"
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="只查询状态，不生成"
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量模式"
    )
    parser.add_argument(
        "--roadmap-ids",
        nargs="+",
        help="批量模式下的路线图ID列表"
    )
    
    args = parser.parse_args()
    
    # 验证参数
    if not args.batch and not args.roadmap_id:
        parser.error("必须提供 --roadmap-id 或使用 --batch 模式")
    
    if args.batch and not args.roadmap_ids:
        parser.error("批量模式需要提供 --roadmap-ids")
    
    print(f"\n{'#'*70}")
    print(f"# 封面图生成服务测试脚本")
    print(f"# 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if args.batch:
        print(f"# 模式: 批量查询")
        print(f"# Roadmap IDs: {len(args.roadmap_ids)} 个")
    else:
        print(f"# 模式: {'只查询状态' if args.status_only else '生成封面图'}")
        if not args.status_only:
            print(f"# 生成方式: {'异步 (Celery)' if args.use_async else '同步 (直接调用)'}")
        print(f"# Roadmap ID: {args.roadmap_id}")
    
    print(f"{'#'*70}")
    
    try:
        if args.batch:
            # 批量查询模式
            await batch_get_cover_images(args.roadmap_ids)
        
        else:
            # 单个路线图模式
            roadmap_id = args.roadmap_id
            
            # 步骤1: 检查路线图是否存在
            roadmap_info = await check_roadmap_exists(roadmap_id)
            
            # 步骤2: 查询当前状态
            current_status = await get_cover_image_status(roadmap_id)
            
            if args.status_only:
                # 只查询状态
                print(f"\n   💡 提示: 如需生成封面图，请移除 --status-only 参数")
            
            else:
                # 生成封面图
                if args.use_async:
                    # 异步方式（Celery）
                    result = generate_cover_image_async(
                        roadmap_id,
                        prompt=args.prompt,
                    )
                else:
                    # 同步方式（直接调用服务）
                    result = await generate_cover_image_sync(
                        roadmap_id,
                        prompt=args.prompt,
                    )
                
                # 生成后再次查询状态
                if result.get("success"):
                    print(f"\n   ⏳ 等待3秒后查询最新状态...")
                    await asyncio.sleep(3)
                    await get_cover_image_status(roadmap_id)
            
            # 步骤3: 验证数据库记录
            await verify_database_record(roadmap_id)
        
        print(f"\n{'#'*70}")
        print(f"# ✅ 测试完成")
        print(f"{'#'*70}\n")
    
    except KeyboardInterrupt:
        print(f"\n\n{'='*70}")
        print(f"🛑 测试被用户中断")
        print(f"{'='*70}\n")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n\n{'='*70}")
        print(f"❌ 测试过程中发生未预期的错误")
        print(f"错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print(f"{'='*70}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
