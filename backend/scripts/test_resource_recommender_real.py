"""
ResourceRecommenderAgent 实战测试脚本

目标：
1) 使用真实 LLM + Tavily（API 或 MCP）进行资源推荐
2) 遇到直连失败时，自动落到代理（Tavily API 已在工具层支持代理重试，OpenAI/MCP 走全局代理）

使用说明：
1. 确保已配置以下环境变量（假定均已配置）：
   - RECOMMENDER_API_KEY（OpenAI，用于 MCP）
   - TAVILY_API_KEY
   - HTTP_PROXY / HTTPS_PROXY（如需代理）
2. 运行脚本：uv run python scripts/test_resource_recommender_real.py
"""

import sys
import asyncio
import os
from contextlib import contextmanager
from pathlib import Path

# 将项目根目录加入路径，确保可导入应用模块
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.resource_recommender import ResourceRecommenderAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    ResourceRecommendationInput,
)


def _mask(val: str, keep: int = 6) -> str:
    """
    简单脱敏工具
    
    Args:
        val: 原始字符串
        keep: 前缀保留长度
    
    Returns:
        脱敏后的字符串
    """
    return val[:keep] + "..." if val else "(未配置)"


def print_env_summary() -> None:
    """
    打印关键环境配置摘要（脱敏）
    """
    tavily = _mask(os.environ.get("TAVILY_API_KEY", ""))
    openai_key = _mask(os.environ.get("RECOMMENDER_API_KEY", ""))
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    print("环境配置摘要：")
    print(f"  TAVILY_API_KEY     : {tavily}")
    print(f"  RECOMMENDER_API_KEY: {openai_key}")
    print(f"  HTTP_PROXY         : {http_proxy or '(未配置)'}")
    print(f"  HTTPS_PROXY        : {https_proxy or '(未配置)'}")
    print()


@contextmanager
def temporarily_disable_proxy_for_llm():
    """
    临时移除 HTTP(S)_PROXY，避免 LLM 经由不可用的本地代理（如 127.0.0.1:17890）。
    退出时自动恢复，防止影响 Tavily API 的代理回退逻辑。
    """
    original = {
        "HTTP_PROXY": os.environ.get("HTTP_PROXY"),
        "http_proxy": os.environ.get("http_proxy"),
        "HTTPS_PROXY": os.environ.get("HTTPS_PROXY"),
        "https_proxy": os.environ.get("https_proxy"),
    }
    for key in list(original.keys()):
        if key in os.environ:
            os.environ.pop(key)
    try:
        yield
    finally:
        for key, val in original.items():
            if val is not None:
                os.environ[key] = val


async def main() -> int:
    """
    运行 ResourceRecommenderAgent 实战测试
    
    Returns:
        进程退出码（0 表示成功，1 表示失败）
    """
    print("🚀 ResourceRecommenderAgent 实战测试")
    print("=" * 70)
    print_env_summary()

    # 构造示例输入
    concept = Concept(
        concept_id="concept-react-hooks",
        name="React Hooks",
        description="理解 useState、useEffect 等核心 Hooks 的原理与实践",
        estimated_hours=6,
        prerequisites=[],
        difficulty="medium",
        keywords=["react", "hooks", "useState", "useEffect"],
    )

    prefs = LearningPreferences(
        learning_goal="掌握 React Hooks 并能在项目中熟练使用",
        available_hours_per_week=8,
        motivation="升级技能",
        current_level="intermediate",
        career_background="前端工程师 2 年",
        content_preference=["visual", "text"],
        primary_language="zh",
        secondary_language="en",
    )

    input_data = ResourceRecommendationInput(
        concept=concept,
        context={"stage_name": "前端进阶", "module_name": "React 实战"},
        user_preferences=prefs,
    )

    agent = ResourceRecommenderAgent()

    print("开始执行资源推荐...\n")
    try:
        # 如果本地代理不可用导致连接错误，可设置环境变量 SKIP_LLM_PROXY=true 临时关闭 LLM 代理
        if os.environ.get("SKIP_LLM_PROXY", "").lower() in {"1", "true", "yes"}:
            print("⚠️  已启用 SKIP_LLM_PROXY，临时关闭 LLM 的 HTTP(S)_PROXY 变量\n")
            with temporarily_disable_proxy_for_llm():
                result = await agent.execute(input_data)
        else:
            result = await agent.execute(input_data)

        print("✅ 资源推荐成功")
        print("生成 ID       :", result.id)
        print("关联概念      :", result.concept_id)
        print("使用搜索查询  :", result.search_queries_used)
        print("生成时间      :", result.generated_at)
        print("资源数量      :", len(result.resources))

        for idx, r in enumerate(result.resources[:5], 1):
            print(f"\n资源 {idx}:")
            print(f"  标题    : {r.title[:100]}")
            print(f"  URL     : {r.url}")
            print(f"  类型    : {r.type}")
            print(f"  语言    : {r.language}")
            print(f"  相关性  : {r.relevance_score}")
            if r.confidence_score is not None:
                print(f"  置信度  : {r.confidence_score}")
            if r.published_date:
                print(f"  发布日期: {r.published_date}")

    except Exception as e:
        print("❌ 资源推荐失败:", e)
        import traceback

        traceback.print_exc()
        return 1

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

