"""
基础 Repository 单元测试

测试 BaseRepository 的通用 CRUD 操作。
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Field

from app.db.repositories.base import BaseRepository


# 测试用的简单模型
class TestModel(SQLModel, table=True):
    """测试模型"""
    __tablename__ = "test_models"
    
    id: str = Field(primary_key=True)
    name: str
    value: int


class TestModelRepository(BaseRepository[TestModel]):
    """测试 Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TestModel)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
async def db_session():
    """创建内存数据库会话"""
    # 使用 SQLite 内存数据库进行测试
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    
    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # 创建会话
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session
    
    # 清理
    await engine.dispose()


@pytest.fixture
def test_repo(db_session: AsyncSession) -> TestModelRepository:
    """创建测试 Repository"""
    return TestModelRepository(db_session)


# ============================================================
# 测试用例
# ============================================================

@pytest.mark.asyncio
class TestBaseRepository:
    """BaseRepository 测试套件"""
    
    async def test_create(self, test_repo: TestModelRepository, db_session: AsyncSession):
        """测试创建实体"""
        # 创建实体
        entity = TestModel(id="test-1", name="Test Entity", value=100)
        created = await test_repo.create(entity, flush=True)
        await db_session.commit()
        
        # 验证
        assert created.id == "test-1"
        assert created.name == "Test Entity"
        assert created.value == 100
    
    async def test_get_by_id(self, test_repo: TestModelRepository, db_session: AsyncSession):
        """测试根据 ID 查询"""
        # 准备数据
        entity = TestModel(id="test-2", name="Get Test", value=200)
        await test_repo.create(entity, flush=True)
        await db_session.commit()
        
        # 查询
        found = await test_repo.get_by_id("test-2")
        
        # 验证
        assert found is not None
        assert found.id == "test-2"
        assert found.name == "Get Test"
        assert found.value == 200
    
    async def test_get_by_id_not_found(self, test_repo: TestModelRepository):
        """测试查询不存在的实体"""
        found = await test_repo.get_by_id("non-existent")
        assert found is None
    
    async def test_update_by_id(self, test_repo: TestModelRepository, db_session: AsyncSession):
        """测试更新实体"""
        # 准备数据
        entity = TestModel(id="test-3", name="Original", value=300)
        await test_repo.create(entity, flush=True)
        await db_session.commit()
        
        # 更新
        updated = await test_repo.update_by_id("test-3", name="Updated", value=999)
        await db_session.commit()
        
        # 验证
        assert updated is True
        
        # 重新查询验证
        found = await test_repo.get_by_id("test-3")
        assert found.name == "Updated"
        assert found.value == 999
    
    async def test_delete_by_id(self, test_repo: TestModelRepository, db_session: AsyncSession):
        """测试删除实体"""
        # 准备数据
        entity = TestModel(id="test-4", name="To Delete", value=400)
        await test_repo.create(entity, flush=True)
        await db_session.commit()
        
        # 删除
        deleted = await test_repo.delete_by_id("test-4")
        await db_session.commit()
        
        # 验证
        assert deleted is True
        
        # 确认已删除
        found = await test_repo.get_by_id("test-4")
        assert found is None
    
    async def test_list_all(self, test_repo: TestModelRepository, db_session: AsyncSession):
        """测试列表查询"""
        # 准备数据
        entities = [
            TestModel(id=f"test-{i}", name=f"Entity {i}", value=i * 100)
            for i in range(1, 6)
        ]
        await test_repo.create_batch(entities, flush=True)
        await db_session.commit()
        
        # 查询
        results = await test_repo.list_all(limit=10)
        
        # 验证
        assert len(results) == 5
    
    async def test_count(self, test_repo: TestModelRepository, db_session: AsyncSession):
        """测试计数"""
        # 准备数据
        entities = [
            TestModel(id=f"test-{i}", name=f"Entity {i}", value=i * 100)
            for i in range(1, 4)
        ]
        await test_repo.create_batch(entities, flush=True)
        await db_session.commit()
        
        # 计数
        count = await test_repo.count()
        
        # 验证
        assert count == 3
    
    async def test_exists(self, test_repo: TestModelRepository, db_session: AsyncSession):
        """测试存在性检查"""
        # 准备数据
        entity = TestModel(id="test-5", name="Exists Test", value=500)
        await test_repo.create(entity, flush=True)
        await db_session.commit()
        
        # 检查存在
        exists = await test_repo.exists(id="test-5")
        assert exists is True
        
        # 检查不存在
        not_exists = await test_repo.exists(id="non-existent")
        assert not_exists is False
    
    async def test_create_batch(self, test_repo: TestModelRepository, db_session: AsyncSession):
        """测试批量创建"""
        # 批量创建
        entities = [
            TestModel(id=f"batch-{i}", name=f"Batch {i}", value=i)
            for i in range(1, 6)
        ]
        created = await test_repo.create_batch(entities, flush=True)
        await db_session.commit()
        
        # 验证
        assert len(created) == 5
        
        # 验证所有实体都已创建
        count = await test_repo.count()
        assert count == 5
    
    async def test_get_by_ids(self, test_repo: TestModelRepository, db_session: AsyncSession):
        """测试批量 ID 查询"""
        # 准备数据
        entities = [
            TestModel(id=f"multi-{i}", name=f"Multi {i}", value=i)
            for i in range(1, 4)
        ]
        await test_repo.create_batch(entities, flush=True)
        await db_session.commit()
        
        # 批量查询
        ids = ["multi-1", "multi-2", "multi-3"]
        results = await test_repo.get_by_ids(ids)
        
        # 验证
        assert len(results) == 3
        result_ids = {r.id for r in results}
        assert result_ids == set(ids)
