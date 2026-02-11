#!/usr/bin/env python3
"""
清空数据库所有表数据

⚠️  警告: 此脚本会删除数据库中所有表的数据，包括checkpoint表
⚠️  仅用于开发/测试环境，禁止在生产环境使用

使用方法：
    python backend/scripts/clear_all_tables.py
    
功能：
    1. 清空所有业务表数据（除排除的表）
    2. 清空所有checkpoint表数据（LangGraph状态）
    3. 使用TRUNCATE CASCADE避免外键约束问题
    4. 提供安全确认提示
    
排除的表（不会被清空）：
    - users: 用户账号
    - user_profiles: 用户画像
    - tavily_api_keys: Tavily API密钥
    - tech_stack_assessments: 技术栈评估
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import async_session_maker, engine
from app.config.settings import settings

logger = structlog.get_logger()

# ============================================================
# 业务表列表（按照database.py中的定义）
# ============================================================
BUSINESS_TABLES = [
    "users",
    "roadmap_tasks",
    "roadmap_metadata",
    "concept_metadata",
    "tutorial_metadata",
    "intent_analysis_metadata",
    "resource_recommendation_metadata",
    "quiz_metadata",
    "tech_stack_assessments",
    "user_profiles",
    "execution_logs",
    "concept_progress",
    "quiz_attempts",
    "structure_validation_records",
    "roadmap_edit_records",
    "human_review_feedbacks",
    "edit_plan_records",
    "chat_sessions",
    "chat_messages",
    "learning_notes",
    "waitlist_emails",
    "roadmap_cover_images",
    "tavily_api_keys",
]

# ============================================================
# LangGraph Checkpoint表列表
# ============================================================
CHECKPOINT_TABLES = [
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
]

# ============================================================
# 排除的表（不会被清空）
# ============================================================
EXCLUDED_TABLES = [
    "users",
    "user_profiles",
    "tavily_api_keys",
    "tech_stack_assessments",
]

# ============================================================
# 获取数据库中所有表
# ============================================================
async def get_all_tables(session: AsyncSession) -> list[str]:
    """
    从数据库中获取所有表名
    
    Args:
        session: 数据库会话
        
    Returns:
        表名列表
    """
    result = await session.execute(
        text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
    )
    tables = [row[0] for row in result.fetchall()]
    return tables


# ============================================================
# 清空单个表
# ============================================================
async def truncate_table(session: AsyncSession, table_name: str) -> bool:
    """
    清空单个表的数据
    
    Args:
        session: 数据库会话
        table_name: 表名
        
    Returns:
        是否成功
    """
    try:
        await session.execute(
            text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE")
        )
        logger.info("table_truncated", table=table_name, status="✅ 成功")
        return True
    except Exception as e:
        logger.error(
            "table_truncate_failed",
            table=table_name,
            error=str(e),
            status="❌ 失败"
        )
        return False


# ============================================================
# 清空所有表
# ============================================================
async def clear_all_tables(
    include_checkpoints: bool = True,
    dry_run: bool = False
) -> dict:
    """
    清空数据库中所有表的数据
    
    Args:
        include_checkpoints: 是否包含checkpoint表
        dry_run: 是否为演习模式（不实际执行）
        
    Returns:
        执行结果统计
    """
    async with async_session_maker.begin() as session:
        # 1. 获取数据库中所有表
        all_tables = await get_all_tables(session)
        logger.info("tables_found", count=len(all_tables), tables=all_tables)
        
        # 2. 确定要清空的表
        tables_to_clear = []
        
        # 添加业务表（排除指定的表）
        for table in BUSINESS_TABLES:
            if table in all_tables and table not in EXCLUDED_TABLES:
                tables_to_clear.append(table)
        
        # 添加checkpoint表（如果指定）
        if include_checkpoints:
            for table in CHECKPOINT_TABLES:
                if table in all_tables:
                    tables_to_clear.append(table)
        
        logger.info(
            "tables_to_clear",
            count=len(tables_to_clear),
            tables=tables_to_clear,
            excluded_count=len(EXCLUDED_TABLES),
            excluded_tables=EXCLUDED_TABLES
        )
        
        if not tables_to_clear:
            logger.warning("no_tables_to_clear", message="没有找到需要清空的表")
            return {"total": 0, "success": 0, "failed": 0}
        
        # 3. 执行清空操作
        success_count = 0
        failed_count = 0
        
        if dry_run:
            logger.info(
                "dry_run_mode",
                message="🔍 演习模式：不会实际删除数据",
                tables=tables_to_clear
            )
            return {
                "total": len(tables_to_clear),
                "success": 0,
                "failed": 0,
                "dry_run": True
            }
        
        logger.info("start_truncating", message="⚙️ 开始清空表数据...")
        
        for table in tables_to_clear:
            if await truncate_table(session, table):
                success_count += 1
            else:
                failed_count += 1
        
        # 4. 提交事务
        await session.commit()
        
        return {
            "total": len(tables_to_clear),
            "success": success_count,
            "failed": failed_count,
        }


# ============================================================
# 安全确认
# ============================================================
def confirm_action() -> bool:
    """
    要求用户确认操作
    
    Returns:
        是否确认
    """
    print("\n" + "="*60)
    print("⚠️  警告：即将清空数据库所有表的数据")
    print("="*60)
    print(f"数据库URL: {settings.DATABASE_URL}")
    print(f"环境: {settings.ENVIRONMENT}")
    print("\n此操作将清空以下表：")
    print(f"  - 业务表 ({len([t for t in BUSINESS_TABLES if t not in EXCLUDED_TABLES])}张)")
    print(f"  - Checkpoint表 ({len(CHECKPOINT_TABLES)}张)")
    print("\n🔒 以下表将被保留（不会清空）：")
    for table in EXCLUDED_TABLES:
        print(f"  - {table}")
    print("\n⚠️  此操作不可逆！")
    print("="*60)
    
    response = input("\n请输入 'YES' 确认继续: ").strip()
    return response == "YES"


# ============================================================
# 主函数
# ============================================================
async def main():
    """主函数"""
    # 1. 检查环境（禁止在生产环境执行）
    if settings.ENVIRONMENT == "production":
        logger.error(
            "production_environment_blocked",
            message="🚫 禁止在生产环境执行清空数据库操作"
        )
        sys.exit(1)
    
    # 2. 安全确认
    if not confirm_action():
        logger.info("operation_cancelled", message="❌ 用户取消操作")
        sys.exit(0)
    
    # 3. 执行清空
    logger.info("operation_started", message="🚀 开始清空数据库...")
    
    try:
        result = await clear_all_tables(
            include_checkpoints=True,
            dry_run=False
        )
        
        logger.info(
            "operation_completed",
            message="✅ 数据库清空完成",
            **result
        )
        
        print("\n" + "="*60)
        print("✅ 数据库清空完成")
        print("="*60)
        print(f"总计: {result['total']} 张表")
        print(f"成功: {result['success']} 张")
        print(f"失败: {result['failed']} 张")
        print("="*60)
        
    except Exception as e:
        logger.error(
            "operation_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        print(f"\n❌ 操作失败: {e}")
        sys.exit(1)
    
    finally:
        # 关闭数据库连接
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

