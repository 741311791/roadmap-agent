#!/usr/bin/env python3
"""
资源推荐质量测试脚本

测试 ResourceRecommenderAgent 推荐的资源URL有效性
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import httpx
import structlog
from app.agents.factory import AgentFactory
from app.models.domain import Concept, LearningPreferences
from app.config.settings import settings

logger = structlog.get_logger()


async def verify_url(url: str, timeout: float = 10.0) -> tuple[bool, int | None, str]:
    """
    验证单个URL的有效性
    
    Args:
        url: 要验证的URL
        timeout: 超时时间（秒）
        
    Returns:
        (is_valid, status_code, message)
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.head(url)
            
            if response.status_code == 200:
                return True, 200, "✅ 有效"
            elif 200 <= response.status_code < 300:
                return True, response.status_code, f"✅ 有效 (重定向到 {response.url})"
            elif response.status_code == 404:
                return False, 404, "❌ 404 Not Found"
            elif response.status_code == 403:
                return False, 403, "❌ 403 Forbidden (可能需要浏览器访问)"
            elif response.status_code >= 500:
                return False, response.status_code, f"❌ {response.status_code} 服务器错误"
            else:
                return False, response.status_code, f"⚠️  {response.status_code}"
                
    except httpx.TimeoutException:
        return False, None, "❌ 超时"
    except httpx.ConnectError:
        return False, None, "❌ 连接失败"
    except Exception as e:
        return False, None, f"❌ 错误: {str(e)[:50]}"


async def test_resource_recommendation(concept_name: str, concept_desc: str, keywords: list[str]):
    """
    测试单个概念的资源推荐质量
    
    Args:
        concept_name: 概念名称
        concept_desc: 概念描述
        keywords: 关键词列表
    """
    print(f"\n{'='*80}")
    print(f"🔍 测试概念: {concept_name}")
    print(f"{'='*80}")
    
    # 创建 Agent
    factory = AgentFactory(settings)
    recommender = factory.create_resource_recommender()
    
    # 构建测试概念
    concept = Concept(
        concept_id=f"test-{concept_name.lower().replace(' ', '-')}",
        name=concept_name,
        description=concept_desc,
        difficulty="medium",
        estimated_hours=8,
        keywords=keywords,
    )
    
    # 用户偏好
    preferences = LearningPreferences(
        learning_goal="学习和掌握技术概念",
        available_hours_per_week=10,
        motivation="提升技能",
        current_level="intermediate",  # 可选值: "beginner", "intermediate", "advanced"
        career_background="软件工程师",
        content_preference=["visual", "text"],
        preferred_language="zh",
    )
    
    try:
        # 执行推荐
        print(f"\n⏳ 正在调用 ResourceRecommenderAgent...")
        result = await recommender.recommend(
            concept=concept,
            context={"stage_name": "测试阶段", "module_name": "测试模块"},
            user_preferences=preferences,
        )
        
        print(f"\n✅ 推荐完成!")
        print(f"📊 推荐资源数量: {len(result.resources)}")
        print(f"🔎 使用的搜索查询: {', '.join(result.search_queries_used)}")
        
        # 验证每个资源的URL
        print(f"\n{'─'*80}")
        print(f"📋 资源列表及URL验证:")
        print(f"{'─'*80}")
        
        valid_count = 0
        invalid_count = 0
        
        for i, resource in enumerate(result.resources, 1):
            print(f"\n{i}. {resource.title}")
            print(f"   类型: {resource.type}")
            print(f"   相关性: {resource.relevance_score:.2f}")
            print(f"   URL: {resource.url}")
            print(f"   描述: {resource.description[:80]}...")
            
            # 验证URL
            print(f"   验证中...", end=" ", flush=True)
            is_valid, status_code, message = await verify_url(resource.url)
            
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
            
            status_str = f"[{status_code}]" if status_code else ""
            print(f"\r   状态: {message} {status_str}")
        
        # 统计结果
        total_count = len(result.resources)
        valid_rate = (valid_count / total_count * 100) if total_count > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"📈 统计结果:")
        print(f"   总资源数: {total_count}")
        print(f"   有效资源: {valid_count} ({valid_rate:.1f}%)")
        print(f"   无效资源: {invalid_count} ({(100-valid_rate):.1f}%)")
        print(f"{'='*80}")
        
        # 评估结果
        if valid_rate >= 90:
            print(f"✅ 优秀! URL有效率 >= 90%")
        elif valid_rate >= 70:
            print(f"⚠️  一般，URL有效率在 70%-90% 之间")
        else:
            print(f"❌ 较差，URL有效率 < 70%，需要优化!")
        
        return {
            "concept": concept_name,
            "total": total_count,
            "valid": valid_count,
            "invalid": invalid_count,
            "valid_rate": valid_rate,
        }
        
    except Exception as e:
        print(f"\n❌ 推荐失败: {str(e)}")
        logger.error("resource_recommendation_failed", concept=concept_name, error=str(e))
        return None


async def main():
    """主测试流程"""
    print("🚀 ResourceRecommender 资源质量测试")
    print("━" * 80)
    
    # 测试用例
    test_cases = [
        {
            "name": "React Hooks",
            "desc": "React 16.8引入的函数组件状态管理机制",
            "keywords": ["React", "Hooks", "useState", "useEffect", "函数组件"]
        },
        {
            "name": "Python 异步编程",
            "desc": "Python asyncio异步编程基础",
            "keywords": ["Python", "asyncio", "异步", "async", "await"]
        },
        {
            "name": "Docker 容器化",
            "desc": "使用Docker进行应用容器化",
            "keywords": ["Docker", "容器", "镜像", "Dockerfile", "容器化"]
        },
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n📝 测试案例 {i}/{len(test_cases)}")
        result = await test_resource_recommendation(
            concept_name=test_case["name"],
            concept_desc=test_case["desc"],
            keywords=test_case["keywords"],
        )
        
        if result:
            results.append(result)
        
        # 避免请求过快
        if i < len(test_cases):
            print(f"\n⏸️  等待 3 秒后继续...")
            await asyncio.sleep(3)
    
    # 总体统计
    if results:
        print(f"\n\n{'='*80}")
        print(f"📊 总体统计报告")
        print(f"{'='*80}")
        
        total_resources = sum(r["total"] for r in results)
        total_valid = sum(r["valid"] for r in results)
        total_invalid = sum(r["invalid"] for r in results)
        overall_valid_rate = (total_valid / total_resources * 100) if total_resources > 0 else 0
        
        print(f"\n测试概念数: {len(results)}")
        print(f"推荐资源总数: {total_resources}")
        print(f"有效资源: {total_valid} ({overall_valid_rate:.1f}%)")
        print(f"无效资源: {total_invalid} ({(100-overall_valid_rate):.1f}%)")
        
        print(f"\n各概念详情:")
        for r in results:
            print(f"  - {r['concept']}: {r['valid']}/{r['total']} 有效 ({r['valid_rate']:.1f}%)")
        
        print(f"\n{'='*80}")
        
        # 最终评估
        if overall_valid_rate >= 90:
            print(f"✅ 总体评估: 优秀! 继续保持!")
        elif overall_valid_rate >= 70:
            print(f"⚠️  总体评估: 一般，建议实施URL验证方案")
        else:
            print(f"❌ 总体评估: 较差，强烈建议立即优化!")
            print(f"\n💡 建议措施:")
            print(f"   1. 添加URL有效性验证")
            print(f"   2. 配置Tavily API Key并启用时间筛选")
            print(f"   3. 增强Prompt，避免推荐过时资源")
            print(f"   4. 查看详细分析报告: RESOURCE_RECOMMENDER_ANALYSIS.md")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()

