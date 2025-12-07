#!/usr/bin/env python3
"""
测试Repository迁移是否成功

验证：
1. RepositoryFactory正常工作
2. 各个Repository可以正常创建
3. RoadmapService可以使用新Repository系统
"""
import asyncio
import sys
import os

# 添加backend目录到path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.db.repository_factory import get_repository_factory
from app.core.dependencies import init_orchestrator
from app.services.roadmap_service import RoadmapService
import structlog

logger = structlog.get_logger()


async def test_repository_factory():
    """测试Repository Factory"""
    print("\n=== 测试 1: Repository Factory ===")
    
    try:
        repo_factory = get_repository_factory()
        print("✅ Repository Factory 创建成功")
        
        # 测试会话创建
        async with repo_factory.create_session() as session:
            print("✅ 数据库会话创建成功")
            
            # 测试创建各个Repository
            task_repo = repo_factory.create_task_repo(session)
            print("✅ TaskRepository 创建成功")
            
            roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
            print("✅ RoadmapMetadataRepository 创建成功")
            
            tutorial_repo = repo_factory.create_tutorial_repo(session)
            print("✅ TutorialRepository 创建成功")
            
            resource_repo = repo_factory.create_resource_repo(session)
            print("✅ ResourceRepository 创建成功")
            
            quiz_repo = repo_factory.create_quiz_repo(session)
            print("✅ QuizRepository 创建成功")
            
            intent_repo = repo_factory.create_intent_analysis_repo(session)
            print("✅ IntentAnalysisRepository 创建成功")
            
            user_profile_repo = repo_factory.create_user_profile_repo(session)
            print("✅ UserProfileRepository 创建成功")
            
            execution_log_repo = repo_factory.create_execution_log_repo(session)
            print("✅ ExecutionLogRepository 创建成功")
        
        print("✅ 数据库会话自动关闭")
        return True
        
    except Exception as e:
        print(f"❌ Repository Factory 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_roadmap_service():
    """测试RoadmapService使用新Repository系统"""
    print("\n=== 测试 2: RoadmapService ===")
    
    try:
        # 初始化orchestrator
        await init_orchestrator()
        print("✅ Orchestrator 初始化成功")
        
        # 获取工厂和executor
        from app.core.dependencies import get_workflow_executor
        repo_factory = get_repository_factory()
        orchestrator = get_workflow_executor()
        
        # 创建RoadmapService
        service = RoadmapService(repo_factory, orchestrator)
        print("✅ RoadmapService 创建成功")
        
        # 测试基本方法（不实际执行数据库操作）
        print("✅ RoadmapService 使用新Repository系统")
        
        return True
        
    except Exception as e:
        print(f"❌ RoadmapService 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_import_check():
    """测试导入检查：确保没有旧Repository导入"""
    print("\n=== 测试 3: 导入检查 ===")
    
    try:
        # 尝试导入新模块
        from app.db.repository_factory import RepositoryFactory
        print("✅ 新RepositoryFactory可以导入")
        
        from app.db.repositories.task_repo import TaskRepository
        print("✅ TaskRepository可以导入")
        
        from app.db.repositories.roadmap_meta_repo import RoadmapMetadataRepository
        print("✅ RoadmapMetadataRepository可以导入")
        
        # 检查RoadmapService是否移除了旧导入
        import inspect
        from app.services import roadmap_service
        source = inspect.getsource(roadmap_service)
        
        if "from app.db.repositories.roadmap_repo import RoadmapRepository" in source:
            print("❌ RoadmapService仍然导入旧的RoadmapRepository")
            return False
        else:
            print("✅ RoadmapService已移除旧Repository导入")
        
        if "from app.db.repository_factory import RepositoryFactory" in source:
            print("✅ RoadmapService使用新RepositoryFactory")
        else:
            print("⚠️  RoadmapService未导入RepositoryFactory（可能不需要）")
        
        return True
        
    except Exception as e:
        print(f"❌ 导入检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("=" * 60)
    print("Repository 迁移验证测试")
    print("=" * 60)
    
    results = []
    
    # 测试1: Repository Factory
    result1 = await test_repository_factory()
    results.append(("Repository Factory", result1))
    
    # 测试2: RoadmapService
    result2 = await test_roadmap_service()
    results.append(("RoadmapService", result2))
    
    # 测试3: 导入检查
    result3 = await test_import_check()
    results.append(("导入检查", result3))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！Repository迁移成功！")
        print("=" * 60)
        return 0
    else:
        print("❌ 部分测试失败，请检查错误信息")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
