"""
Repository Factory 集成测试

测试 RepositoryFactory 的功能和会话管理。
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repository_factory import RepositoryFactory
from app.models.database import RoadmapTask, beijing_now


@pytest.fixture
def repo_factory() -> RepositoryFactory:
    """创建 Repository 工厂"""
    return RepositoryFactory()


@pytest.mark.asyncio
class TestRepositoryFactory:
    """RepositoryFactory 测试套件"""
    
    async def test_create_session(self, repo_factory: RepositoryFactory):
        """测试会话创建"""
        async with repo_factory.create_session() as session:
            assert session is not None
            assert isinstance(session, AsyncSession)
    
    async def test_create_task_repo(self, repo_factory: RepositoryFactory):
        """测试创建任务 Repository"""
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            assert task_repo is not None
    
    async def test_create_all_repos(self, repo_factory: RepositoryFactory):
        """测试批量创建所有 Repository"""
        async with repo_factory.create_session() as session:
            repos = repo_factory.create_all_repos(session)
            
            assert "task" in repos
            assert "roadmap_meta" in repos
            assert "tutorial" in repos
            assert "resource" in repos
            assert "quiz" in repos
            assert "intent_analysis" in repos
            assert "user_profile" in repos
            assert "execution_log" in repos
    
    @pytest.mark.skip(reason="需要真实数据库")
    async def test_task_crud_workflow(self, repo_factory: RepositoryFactory):
        """
        测试完整的 CRUD 工作流（需要真实数据库）
        
        这个测试演示了如何使用 RepositoryFactory 进行完整的数据库操作。
        """
        task_id = f"test-task-{beijing_now().isoformat()}"
        
        # 创建任务
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            
            task = await task_repo.create_task(
                task_id=task_id,
                user_id="test-user",
                user_request={"goal": "Learn Python"},
            )
            
            await session.commit()
            
            assert task.task_id == task_id
            assert task.status == "pending"
        
        # 查询任务
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            
            found = await task_repo.get_by_task_id(task_id)
            
            assert found is not None
            assert found.task_id == task_id
        
        # 更新任务状态
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            
            updated = await task_repo.update_task_status(
                task_id=task_id,
                status="processing",
                current_step="intent_analysis",
            )
            
            await session.commit()
            
            assert updated is True
        
        # 删除任务
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            
            deleted = await task_repo.delete_task(task_id)
            
            await session.commit()
            
            assert deleted is True
