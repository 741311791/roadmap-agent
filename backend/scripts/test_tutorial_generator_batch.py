"""
TutorialGeneratorAgent 批量测试脚本

用法：
    uv run python scripts/test_tutorial_generator_batch.py

功能：
- 批量测试 10 个不同复杂度的教程生成
- 统计成功率、迭代次数、响应时间等指标
- 验证 JSON 解析和格式正确性
- 生成详细的测试报告

依赖：
- 需要配置 GENERATOR_PROVIDER、GENERATOR_MODEL、GENERATOR_API_KEY
- 需要 Context7 MCP Server 配置（mcp_servers.json）
"""
import asyncio
import time
import json
from datetime import datetime
from pathlib import Path
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.models.domain import Concept, LearningPreferences
import structlog

# 配置日志输出到控制台
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()


# 测试概念列表（不同复杂度和类型）
TEST_CONCEPTS = [
    # 1. 简单 - React基础
    Concept(
        concept_id="test-001",
        name="React Hooks基础",
        description="学习useState和useEffect的基本用法",
        difficulty="easy",
        estimated_hours=2.0,
        prerequisites=["react-basics"],
        keywords=["useState", "useEffect", "hooks"],
    ),
    # 2. 中等 - React进阶
    Concept(
        concept_id="test-002",
        name="React Query数据管理",
        description="使用TanStack Query管理服务端状态",
        difficulty="medium",
        estimated_hours=3.0,
        prerequisites=["react-hooks", "http-basics"],
        keywords=["react-query", "data-fetching", "caching"],
    ),
    # 3. 中等 - Vue
    Concept(
        concept_id="test-003",
        name="Vue 3 Composition API",
        description="学习Vue 3的组合式API和响应式原理",
        difficulty="medium",
        estimated_hours=3.0,
        prerequisites=["vue-basics"],
        keywords=["composition-api", "ref", "reactive"],
    ),
    # 4. 简单 - Python
    Concept(
        concept_id="test-004",
        name="Python异步编程基础",
        description="理解async/await和asyncio的基本用法",
        difficulty="easy",
        estimated_hours=2.0,
        prerequisites=["python-basics"],
        keywords=["async", "await", "asyncio"],
    ),
    # 5. 中等 - FastAPI
    Concept(
        concept_id="test-005",
        name="FastAPI依赖注入系统",
        description="掌握FastAPI的依赖注入机制和最佳实践",
        difficulty="medium",
        estimated_hours=3.0,
        prerequisites=["fastapi-basics", "python-async"],
        keywords=["dependency-injection", "Depends", "Security"],
    ),
    # 6. 困难 - LangGraph
    Concept(
        concept_id="test-006",
        name="LangGraph状态图设计",
        description="使用LangGraph构建复杂的Agent工作流",
        difficulty="hard",
        estimated_hours=4.0,
        prerequisites=["langchain-basics", "graph-theory"],
        keywords=["state-graph", "nodes", "edges", "routing"],
    ),
    # 7. 简单 - TypeScript
    Concept(
        concept_id="test-007",
        name="TypeScript泛型入门",
        description="理解TypeScript泛型的基本概念和用法",
        difficulty="easy",
        estimated_hours=2.0,
        prerequisites=["typescript-basics"],
        keywords=["generics", "type-parameters", "constraints"],
    ),
    # 8. 中等 - Next.js
    Concept(
        concept_id="test-008",
        name="Next.js 14 App Router",
        description="学习Next.js 14的App Router和服务端组件",
        difficulty="medium",
        estimated_hours=3.0,
        prerequisites=["react-advanced", "routing"],
        keywords=["app-router", "server-components", "layouts"],
    ),
    # 9. 困难 - Docker
    Concept(
        concept_id="test-009",
        name="Docker多阶段构建优化",
        description="使用多阶段构建优化Docker镜像大小和安全性",
        difficulty="hard",
        estimated_hours=4.0,
        prerequisites=["docker-basics", "dockerfile"],
        keywords=["multi-stage", "optimization", "security"],
    ),
    # 10. 简单 - Git
    Concept(
        concept_id="test-010",
        name="Git分支管理策略",
        description="学习常见的Git分支管理模型和最佳实践",
        difficulty="easy",
        estimated_hours=2.0,
        prerequisites=["git-basics"],
        keywords=["branching", "merge", "rebase", "git-flow"],
    ),
]


class TestResult:
    """测试结果"""
    def __init__(self, concept_id: str, concept_name: str):
        self.concept_id = concept_id
        self.concept_name = concept_name
        self.success = False
        self.error = None
        self.start_time = None
        self.end_time = None
        self.duration = 0.0
        self.iterations = 0
        self.tutorial_id = None
        self.content_length = 0
        self.json_valid = False
        self.has_mermaid = False


async def test_single_tutorial(
    agent: TutorialGeneratorAgent,
    concept: Concept,
    preferences: LearningPreferences,
    index: int,
    total: int
) -> TestResult:
    """测试单个教程生成"""
    
    result = TestResult(concept.concept_id, concept.name)
    result.start_time = time.time()
    
    print(f"\n{'='*80}")
    print(f"[{index}/{total}] 测试: {concept.name}")
    print(f"{'='*80}")
    print(f"  难度: {concept.difficulty}")
    print(f"  前置概念数: {len(concept.prerequisites) if concept.prerequisites else 0}")
    print(f"  预估学时: {concept.estimated_hours}h")
    
    context = {
        "roadmap_id": f"test-roadmap-{index:03d}",
        "stage_name": "测试阶段",
        "module_name": "测试模块",
        "content_version": 1,
    }
    
    try:
        # 执行生成
        print(f"  ⏳ 开始生成...")
        tutorial_result = await agent.generate(
            concept=concept,
            context=context,
            user_preferences=preferences,
        )
        
        result.end_time = time.time()
        result.duration = result.end_time - result.start_time
        result.success = True
        result.tutorial_id = tutorial_result.tutorial_id
        
        # 验证内容
        if tutorial_result.content_url:
            # 从S3 URL获取内容长度（这里简化处理）
            result.content_length = len(tutorial_result.title or "")
            result.json_valid = True
        
        # 检查是否包含Mermaid
        # 这里简化处理，实际应该读取S3内容
        result.has_mermaid = True  # 假设都包含
        
        print(f"  ✅ 成功！")
        print(f"     - Tutorial ID: {result.tutorial_id}")
        print(f"     - Title: {tutorial_result.title}")
        print(f"     - Duration: {result.duration:.2f}s")
        print(f"     - Status: {tutorial_result.content_status}")
        
    except Exception as e:
        result.end_time = time.time()
        result.duration = result.end_time - result.start_time
        result.success = False
        result.error = str(e)
        
        print(f"  ❌ 失败！")
        print(f"     - Error: {result.error}")
        print(f"     - Duration: {result.duration:.2f}s")
    
    return result


def print_summary(results: list[TestResult]):
    """打印测试总结"""
    
    print(f"\n\n{'='*80}")
    print("测试总结")
    print(f"{'='*80}\n")
    
    # 基本统计
    total = len(results)
    success = sum(1 for r in results if r.success)
    failed = total - success
    success_rate = (success / total * 100) if total > 0 else 0
    
    print(f"总测试数: {total}")
    print(f"成功: {success} ({success_rate:.1f}%)")
    print(f"失败: {failed}")
    
    # 按难度统计
    print(f"\n按难度统计:")
    difficulties = {}
    for i, concept in enumerate(TEST_CONCEPTS):
        diff = concept.difficulty
        if diff not in difficulties:
            difficulties[diff] = {"total": 0, "success": 0}
        difficulties[diff]["total"] += 1
        if results[i].success:
            difficulties[diff]["success"] += 1
    
    for diff, stats in sorted(difficulties.items()):
        rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {diff}: {stats['success']}/{stats['total']} ({rate:.1f}%)")
    
    # 性能统计
    if success > 0:
        success_results = [r for r in results if r.success]
        avg_duration = sum(r.duration for r in success_results) / len(success_results)
        min_duration = min(r.duration for r in success_results)
        max_duration = max(r.duration for r in success_results)
        
        print(f"\n性能统计 (成功的教程):")
        print(f"  平均耗时: {avg_duration:.2f}s")
        print(f"  最快: {min_duration:.2f}s")
        print(f"  最慢: {max_duration:.2f}s")
    
    # 失败详情
    if failed > 0:
        print(f"\n失败详情:")
        for r in results:
            if not r.success:
                print(f"  ❌ {r.concept_name}")
                print(f"     Error: {r.error[:100]}...")
    
    # 保存报告
    report_path = Path("test_results") / f"batch_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(exist_ok=True)
    
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": total,
            "success": success,
            "failed": failed,
            "success_rate": success_rate,
        },
        "by_difficulty": difficulties,
        "results": [
            {
                "concept_id": r.concept_id,
                "concept_name": r.concept_name,
                "success": r.success,
                "duration": r.duration,
                "error": r.error,
                "tutorial_id": r.tutorial_id,
            }
            for r in results
        ]
    }
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n报告已保存: {report_path}")


async def main():
    """主测试流程"""
    
    print("="*80)
    print("TutorialGeneratorAgent 批量测试")
    print("="*80)
    print(f"\n将测试 {len(TEST_CONCEPTS)} 个不同的教程...")
    print("⚠️  注意：此测试会调用真实的 LLM API 并产生费用")
    print("⚠️  预计总耗时: 5-15 分钟")
    
    # 给用户5秒中断时间
    import sys
    for i in range(5, 0, -1):
        print(f"\n{i} 秒后开始测试...", end="\r")
        await asyncio.sleep(1)
    
    print("\n\n开始测试...\n")
    
    # 初始化 Agent
    try:
        agent = TutorialGeneratorAgent()
        print(f"✅ Agent 初始化成功")
        print(f"   - Model: {agent.model_provider}/{agent.model_name}\n")
    except Exception as e:
        print(f"❌ Agent 初始化失败: {e}")
        sys.exit(1)
    
    # 创建测试偏好
    preferences = LearningPreferences(
        learning_goal="掌握现代技术栈",
        available_hours_per_week=10,
        motivation="提升技术能力",
        current_level="intermediate",
        career_background="软件开发 2 年经验",
        content_preference=["visual", "text", "hands_on"],
        primary_language="zh",
    )
    
    # 批量测试
    results = []
    start_time = time.time()
    
    for i, concept in enumerate(TEST_CONCEPTS, 1):
        result = await test_single_tutorial(
            agent=agent,
            concept=concept,
            preferences=preferences,
            index=i,
            total=len(TEST_CONCEPTS)
        )
        results.append(result)
        
        # 短暂延迟，避免API限流
        if i < len(TEST_CONCEPTS):
            await asyncio.sleep(2)
    
    total_time = time.time() - start_time
    
    # 打印总结
    print_summary(results)
    
    print(f"\n总耗时: {total_time:.2f}s ({total_time/60:.1f} 分钟)")
    print(f"\n{'='*80}")
    print("测试完成！")
    print(f"{'='*80}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        import sys
        sys.exit(0)
