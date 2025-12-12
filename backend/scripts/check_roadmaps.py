"""检查数据库中的路线图"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

async def main():
    # 数据库连接
    DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/roadmap_db"
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session_maker() as session:
        # 查询路线图
        result = await session.execute(
            text("SELECT roadmap_id, title, created_at FROM roadmap_metadata ORDER BY created_at DESC LIMIT 3")
        )
        roadmaps = result.fetchall()
        
        if roadmaps:
            print("\n=== 现有路线图 ===")
            for rm in roadmaps:
                print(f"ID: {rm[0]}")
                print(f"标题: {rm[1]}")
                print(f"创建时间: {rm[2]}")
                print()
        else:
            print("数据库中没有路线图")
        
        # 检查 roadmap_tasks 表结构
        result = await session.execute(
            text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'roadmap_tasks' ORDER BY ordinal_position")
        )
        columns = result.fetchall()
        print("\n=== roadmap_tasks 表结构 ===")
        for col in columns:
            print(f"{col[0]}: {col[1]}")
        
        # 检查 roadmap_metadata 表结构
        result = await session.execute(
            text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'roadmap_metadata' ORDER BY ordinal_position")
        )
        columns = result.fetchall()
        print("\n=== roadmap_metadata 表结构 ===")
        for col in columns:
            print(f"{col[0]}: {col[1]}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())

