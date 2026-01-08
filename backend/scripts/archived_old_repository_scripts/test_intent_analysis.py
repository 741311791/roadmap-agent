"""
测试 Intent Analysis 数据的保存和查询

用途：验证 Intent Analysis 元数据是否正确保存到数据库并能被查询到
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy import select
from app.db.session import async_session_maker
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.models.db_models import IntentAnalysisMetadata, RoadmapTask

logger = structlog.get_logger()


async def test_intent_analysis_for_task(task_id: str):
    """
    测试指定任务的 Intent Analysis 数据
    
    Args:
        task_id: 任务 ID
    """
    print(f"\n{'='*60}")
    print(f"测试任务: {task_id}")
    print(f"{'='*60}\n")
    
    async with async_session_maker.begin() as session:
        repo = RoadmapRepository(session)
        
        # 1. 获取任务信息
        task = await session.execute(
            select(RoadmapTask).where(RoadmapTask.id == task_id)
        )
        task_obj = task.scalar_one_or_none()
        
        if not task_obj:
            print(f"❌ 任务不存在: {task_id}")
            return
        
        print(f"✅ 任务信息:")
        print(f"   - 状态: {task_obj.status}")
        print(f"   - 当前步骤: {task_obj.current_step}")
        print(f"   - 路线图ID: {task_obj.roadmap_id}")
        print(f"   - 用户ID: {task_obj.user_id}")
        print(f"   - 创建时间: {task_obj.created_at}")
        print(f"   - 更新时间: {task_obj.updated_at}")
        
        # 2. 查询 Intent Analysis 数据
        print(f"\n📊 查询 Intent Analysis 数据...")
        intent_metadata = await repo.get_intent_analysis_metadata(task_id)
        
        if not intent_metadata:
            print(f"❌ Intent Analysis 数据不存在")
            
            # 检查数据库中是否有该记录（直接查询）
            direct_query = await session.execute(
                select(IntentAnalysisMetadata).where(
                    IntentAnalysisMetadata.task_id == task_id
                )
            )
            direct_result = direct_query.scalar_one_or_none()
            
            if direct_result:
                print(f"   ⚠️  但直接查询找到了记录！可能是 Repository 方法有问题。")
            else:
                print(f"   ℹ️  数据库中确实没有该任务的 Intent Analysis 记录")
                print(f"   提示：任务可能还未完成 intent_analysis 步骤")
            return
        
        print(f"✅ Intent Analysis 数据存在:")
        print(f"   - ID: {intent_metadata.id}")
        print(f"   - 路线图ID: {intent_metadata.roadmap_id}")
        print(f"   - 学习目标: {intent_metadata.parsed_goal[:100]}...")
        print(f"   - 关键技术: {', '.join(intent_metadata.key_technologies[:5])}")
        print(f"   - 难度级别: {intent_metadata.difficulty_profile}")
        print(f"   - 时间约束: {intent_metadata.time_constraint}")
        print(f"   - 推荐关注点: {', '.join(intent_metadata.recommended_focus[:3])}")
        
        if intent_metadata.skill_gap_analysis:
            print(f"   - 技能差距: {len(intent_metadata.skill_gap_analysis)} 项")
        
        if intent_metadata.personalized_suggestions:
            print(f"   - 个性化建议: {len(intent_metadata.personalized_suggestions)} 条")
        
        print(f"   - 学习路径类型: {intent_metadata.estimated_learning_path_type}")
        print(f"   - 创建时间: {intent_metadata.created_at}")
        
        print(f"\n✅ Intent Analysis 数据验证通过！")


async def list_recent_tasks(limit: int = 10):
    """
    列出最近的任务
    
    Args:
        limit: 返回的任务数量
    """
    print(f"\n{'='*60}")
    print(f"最近 {limit} 个任务")
    print(f"{'='*60}\n")
    
    async with async_session_maker.begin() as session:
        result = await session.execute(
            select(RoadmapTask)
            .order_by(RoadmapTask.created_at.desc())
            .limit(limit)
        )
        tasks = result.scalars().all()
        
        if not tasks:
            print("没有找到任务")
            return []
        
        print(f"{'序号':<5} {'任务ID':<38} {'状态':<15} {'当前步骤':<20} {'路线图ID':<30}")
        print("-" * 130)
        
        for idx, task in enumerate(tasks, 1):
            roadmap_id_display = (task.roadmap_id[:27] + '...') if task.roadmap_id and len(task.roadmap_id) > 30 else (task.roadmap_id or 'N/A')
            print(f"{idx:<5} {task.id:<38} {task.status:<15} {task.current_step or 'N/A':<20} {roadmap_id_display:<30}")
        
        return [task.id for task in tasks]


async def main():
    """主函数"""
    import sys
    
    if len(sys.argv) > 1:
        # 指定任务ID测试
        task_id = sys.argv[1]
        await test_intent_analysis_for_task(task_id)
    else:
        # 列出最近的任务，让用户选择
        print("\n" + "="*60)
        print("Intent Analysis 数据测试工具")
        print("="*60)
        
        task_ids = await list_recent_tasks(limit=10)
        
        if task_ids:
            print(f"\n提示：使用以下命令测试特定任务：")
            print(f"python scripts/test_intent_analysis.py <task_id>")
            print(f"\n例如：")
            print(f"python scripts/test_intent_analysis.py {task_ids[0]}")


if __name__ == "__main__":
    asyncio.run(main())


