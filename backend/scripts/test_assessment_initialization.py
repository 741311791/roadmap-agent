#!/usr/bin/env python3
"""
测试技术栈测验题异步初始化功能

使用方式：
1. 启动后端服务：make run
2. 启动 Celery Worker：make celery
3. 运行此脚本：python backend/scripts/test_assessment_initialization.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import structlog
from sqlalchemy import select, delete

from app.db.celery_session import get_celery_db_transaction
from app.models.database import TechAssessment
from app.tasks.assessment_initialization_tasks import (
    check_and_trigger_assessment_generation,
    get_initialization_progress,
)

logger = structlog.get_logger()


async def clear_all_assessments():
    """清空所有测验题数据（用于测试）"""
    logger.info("clearing_all_assessments")
    
    db_gen = get_celery_db_transaction()
    db = await db_gen.__anext__()
    
    try:
        # 删除所有测验题
        stmt = delete(TechAssessment)
        result = await db.execute(stmt)
        deleted_count = result.rowcount
        
        await db.commit()
        
        logger.info(
            "assessments_cleared",
            deleted_count=deleted_count,
        )
        
        return deleted_count
    finally:
        await db.close()


async def count_assessments():
    """统计当前数据库中的测验题数量"""
    db_gen = get_celery_db_transaction()
    db = await db_gen.__anext__()
    
    try:
        stmt = select(TechAssessment)
        result = await db.execute(stmt)
        assessments = result.scalars().all()
        
        logger.info(
            "assessments_counted",
            total_count=len(assessments),
        )
        
        return len(assessments)
    finally:
        await db.close()


async def test_initialization_workflow():
    """测试完整的异步初始化工作流"""
    print("\n" + "=" * 60)
    print("测试：技术栈测验题异步初始化工作流")
    print("=" * 60)
    
    # 步骤1：清空现有数据
    print("\n[步骤1] 清空现有测验题数据...")
    deleted_count = await clear_all_assessments()
    print(f"✅ 已删除 {deleted_count} 条记录")
    
    # 步骤2：查询初始状态
    print("\n[步骤2] 查询初始状态...")
    progress = await get_initialization_progress()
    print(f"✅ 当前状态：")
    print(f"   - 总需求：{progress['total_expected']} 组")
    print(f"   - 已完成：{progress['completed']} 组")
    print(f"   - 缺失：{progress['missing']} 组")
    print(f"   - 进度：{progress['progress_percentage']:.2f}%")
    
    if progress['completed'] > 0:
        print(f"⚠️  警告：数据库中仍有 {progress['completed']} 组题目，清空可能未成功")
        return
    
    # 步骤3：触发异步生成任务
    print("\n[步骤3] 触发异步生成任务...")
    try:
        task = check_and_trigger_assessment_generation.apply_async()
        print(f"✅ 任务已触发")
        print(f"   - 任务ID: {task.id}")
        print(f"   - 任务状态: {task.status}")
        
        # 等待任务完成（最多等待60秒）
        print("\n   等待任务完成...")
        result = task.get(timeout=60)
        
        print(f"\n✅ 任务执行完成")
        print(f"   - 总需求：{result['total_expected']} 组")
        print(f"   - 已存在：{result['existing']} 组")
        print(f"   - 缺失：{result['missing']} 组")
        print(f"   - 已触发：{result['tasks_triggered']} 个子任务")
        
        if result.get('group_id'):
            print(f"   - 并行任务组ID: {result['group_id']}")
        
    except Exception as e:
        print(f"❌ 任务触发失败: {e}")
        print(f"   错误类型: {type(e).__name__}")
        return
    
    # 步骤4：等待一段时间，让Celery Worker生成题目
    print("\n[步骤4] 等待 Celery Worker 生成题目（预计60秒）...")
    for i in range(12):  # 每5秒查询一次，共60秒
        await asyncio.sleep(5)
        progress = await get_initialization_progress()
        print(f"   [{(i+1)*5}秒] 进度：{progress['progress_percentage']:.2f}% ({progress['completed']}/{progress['total_expected']})")
        
        if progress['is_complete']:
            print("   ✅ 所有题目生成完成！")
            break
    
    # 步骤5：最终验证
    print("\n[步骤5] 最终验证...")
    final_count = await count_assessments()
    final_progress = await get_initialization_progress()
    
    print(f"✅ 最终状态：")
    print(f"   - 数据库记录数：{final_count} 条")
    print(f"   - 已完成组数：{final_progress['completed']} 组")
    print(f"   - 完成度：{final_progress['progress_percentage']:.2f}%")
    print(f"   - 是否全部完成：{'✅ 是' if final_progress['is_complete'] else '❌ 否'}")
    
    if final_progress['is_complete']:
        print("\n" + "=" * 60)
        print("🎉 测试成功！异步初始化工作流正常运行")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("⚠️  测试部分成功，但未全部完成（可能需要更长时间）")
        print(f"   缺失：{final_progress['missing']} 组")
        print("=" * 60)


async def test_progress_query_only():
    """仅测试进度查询功能（不触发生成）"""
    print("\n" + "=" * 60)
    print("测试：查询当前初始化进度")
    print("=" * 60)
    
    progress = await get_initialization_progress()
    
    print(f"\n当前状态：")
    print(f"   - 总需求：{progress['total_expected']} 组")
    print(f"   - 已完成：{progress['completed']} 组")
    print(f"   - 缺失：{progress['missing']} 组")
    print(f"   - 进度：{progress['progress_percentage']:.2f}%")
    print(f"   - 是否全部完成：{'✅ 是' if progress['is_complete'] else '❌ 否'}")


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试技术栈测验题异步初始化")
    parser.add_argument(
        "--mode",
        choices=["full", "progress"],
        default="progress",
        help="测试模式：full=完整测试（清空+生成），progress=仅查询进度"
    )
    
    args = parser.parse_args()
    
    if args.mode == "full":
        await test_initialization_workflow()
    else:
        await test_progress_query_only()


if __name__ == "__main__":
    asyncio.run(main())

