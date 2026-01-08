"""
测试脚本：验证 framework_data 更新和 concept_metadata overall_status 读取

功能：
1. 检查指定路线图的 framework_data 是否包含内容引用
2. 检查 concept_metadata 表中的 overall_status 是否正确
3. 验证 API 返回的数据是否合并了 concept_metadata 状态
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from sqlalchemy import select
from app.db.session import get_async_session_context
from app.db.repositories.roadmap_meta_repo import RoadmapMetadataRepository
from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
from app.db.repository_factory import RepositoryFactory
from app.services.roadmap_service import RoadmapService
from app.core.orchestrator.executor import WorkflowExecutor
from app.core.orchestrator_factory import OrchestratorFactory

logger = structlog.get_logger()


async def test_roadmap_framework_data(roadmap_id: str):
    """
    测试路线图的 framework_data 是否包含内容引用
    
    Args:
        roadmap_id: 路线图 ID
    """
    print(f"\n{'='*80}")
    print(f"测试路线图: {roadmap_id}")
    print(f"{'='*80}\n")
    
    async with get_async_session_context() as session:
        # 1. 检查 roadmap_metadata 表
        roadmap_repo = RoadmapMetadataRepository(session)
        metadata = await roadmap_repo.get_by_roadmap_id(roadmap_id)
        
        if not metadata:
            print(f"❌ 路线图不存在: {roadmap_id}")
            return False
        
        print(f"✅ 找到路线图元数据")
        print(f"   - 标题: {metadata.title}")
        print(f"   - 用户ID: {metadata.user_id}")
        print(f"   - 创建时间: {metadata.created_at}")
        
        # 2. 检查 framework_data
        framework_data = metadata.framework_data
        if not framework_data:
            print(f"❌ framework_data 为空")
            return False
        
        print(f"\n✅ framework_data 存在")
        
        # 3. 统计概念和内容引用
        total_concepts = 0
        concepts_with_tutorial = 0
        concepts_with_resources = 0
        concepts_with_quiz = 0
        concepts_with_all_content = 0
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    total_concepts += 1
                    
                    has_tutorial = concept.get("tutorial_id") or concept.get("content_ref")
                    has_resources = concept.get("resources_id")
                    has_quiz = concept.get("quiz_id")
                    
                    if has_tutorial:
                        concepts_with_tutorial += 1
                    if has_resources:
                        concepts_with_resources += 1
                    if has_quiz:
                        concepts_with_quiz += 1
                    if has_tutorial and has_resources and has_quiz:
                        concepts_with_all_content += 1
        
        print(f"\n📊 framework_data 统计:")
        print(f"   - 总概念数: {total_concepts}")
        print(f"   - 包含 tutorial 引用: {concepts_with_tutorial}/{total_concepts}")
        print(f"   - 包含 resources 引用: {concepts_with_resources}/{total_concepts}")
        print(f"   - 包含 quiz 引用: {concepts_with_quiz}/{total_concepts}")
        print(f"   - 三项全部完成: {concepts_with_all_content}/{total_concepts}")
        
        # 4. 检查 concept_metadata 表
        concept_meta_repo = ConceptMetadataRepository(session)
        concept_metas = await concept_meta_repo.get_by_roadmap_id(roadmap_id)
        
        print(f"\n📊 concept_metadata 统计:")
        print(f"   - 记录数: {len(concept_metas)}")
        
        if concept_metas:
            status_counts = {}
            for cm in concept_metas:
                status = cm.overall_status
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"   - 状态分布:")
            for status, count in sorted(status_counts.items()):
                print(f"     * {status}: {count}")
            
            # 检查状态一致性
            print(f"\n🔍 检查前 5 个概念的状态一致性:")
            for i, cm in enumerate(concept_metas[:5]):
                print(f"\n   概念 {i+1}: {cm.concept_id}")
                print(f"   - tutorial_status: {cm.tutorial_status}")
                print(f"   - resources_status: {cm.resources_status}")
                print(f"   - quiz_status: {cm.quiz_status}")
                print(f"   - overall_status: {cm.overall_status}")
                
                # 查找对应的 framework_data 中的概念
                for stage in framework_data.get("stages", []):
                    for module in stage.get("modules", []):
                        for concept in module.get("concepts", []):
                            if concept.get("concept_id") == cm.concept_id:
                                print(f"   - framework_data.content_status: {concept.get('content_status')}")
                                print(f"   - framework_data.resources_status: {concept.get('resources_status')}")
                                print(f"   - framework_data.quiz_status: {concept.get('quiz_status')}")
                                
                                # 检查一致性
                                if (concept.get('content_status') != cm.tutorial_status or
                                    concept.get('resources_status') != cm.resources_status or
                                    concept.get('quiz_status') != cm.quiz_status):
                                    print(f"   ⚠️  状态不一致！")
                                else:
                                    print(f"   ✅ 状态一致")
                                break
        else:
            print(f"   ⚠️  没有找到 concept_metadata 记录")
        
        # 5. 测试 API 返回的数据
        print(f"\n{'='*80}")
        print(f"测试 API 数据合并")
        print(f"{'='*80}\n")
        
        factory = OrchestratorFactory()
        await factory.initialize()
        
        repo_factory = RepositoryFactory()
        executor = factory.create_workflow_executor()
        service = RoadmapService(repo_factory, executor)
        
        api_data = await service.get_roadmap(roadmap_id)
        
        if not api_data:
            print(f"❌ API 返回数据为空")
            return False
        
        print(f"✅ API 返回数据")
        
        # 检查是否包含 overall_status
        api_concepts_with_overall_status = 0
        api_total_concepts = 0
        
        for stage in api_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    api_total_concepts += 1
                    if concept.get("overall_status"):
                        api_concepts_with_overall_status += 1
        
        print(f"\n📊 API 数据统计:")
        print(f"   - 总概念数: {api_total_concepts}")
        print(f"   - 包含 overall_status: {api_concepts_with_overall_status}/{api_total_concepts}")
        
        if api_concepts_with_overall_status > 0:
            print(f"   ✅ API 数据已合并 concept_metadata 状态")
        else:
            print(f"   ⚠️  API 数据未包含 overall_status")
        
        # 显示前 3 个概念的详细信息
        print(f"\n🔍 前 3 个概念的 API 数据:")
        concept_count = 0
        for stage in api_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_count += 1
                    if concept_count <= 3:
                        print(f"\n   概念 {concept_count}: {concept.get('name')}")
                        print(f"   - concept_id: {concept.get('concept_id')}")
                        print(f"   - content_status: {concept.get('content_status')}")
                        print(f"   - resources_status: {concept.get('resources_status')}")
                        print(f"   - quiz_status: {concept.get('quiz_status')}")
                        print(f"   - overall_status: {concept.get('overall_status', 'N/A')}")
                        print(f"   - tutorial_id: {concept.get('tutorial_id', 'N/A')}")
                        print(f"   - resources_id: {concept.get('resources_id', 'N/A')}")
                        print(f"   - quiz_id: {concept.get('quiz_id', 'N/A')}")
                    else:
                        break
                if concept_count >= 3:
                    break
            if concept_count >= 3:
                break
        
        print(f"\n{'='*80}")
        print(f"测试完成")
        print(f"{'='*80}\n")
        
        return True


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python test_framework_data_and_concept_status.py <roadmap_id>")
        print("\n示例:")
        print("  python test_framework_data_and_concept_status.py prompt-engineering-abc123")
        sys.exit(1)
    
    roadmap_id = sys.argv[1]
    
    try:
        success = await test_roadmap_framework_data(roadmap_id)
        
        if success:
            print("✅ 所有测试通过")
            sys.exit(0)
        else:
            print("❌ 测试失败")
            sys.exit(1)
    except Exception as e:
        logger.error("test_failed", error=str(e), roadmap_id=roadmap_id)
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

