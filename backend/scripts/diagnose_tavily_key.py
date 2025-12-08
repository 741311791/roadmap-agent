#!/usr/bin/env python3
"""
诊断 Tavily API Key 问题
对比硬编码 key 和环境变量 key 的行为
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from tavily import TavilyClient
from app.config.settings import settings


def test_hardcoded_key():
    """测试硬编码的 API Key（从 test_tavily.py）"""
    print("\n" + "="*60)
    print("测试 1：硬编码 API Key")
    print("="*60)
    
    # 这是用户成功测试脚本中的 key
    hardcoded_key = "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"
    
    print(f"API Key: {hardcoded_key[:15]}...")
    
    try:
        client = TavilyClient(hardcoded_key)
        response = client.search(
            query="test query",
            search_depth="basic",  # 使用 basic 避免配额问题
            max_results=2,
        )
        print(f"✅ 成功！返回 {len(response.get('results', []))} 个结果")
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_env_key():
    """测试环境变量中的 API Key"""
    print("\n" + "="*60)
    print("测试 2：环境变量 API Key")
    print("="*60)
    
    # 从环境变量读取
    env_key = settings.TAVILY_API_KEY
    
    if not env_key or env_key == "your_tavily_api_key_here":
        print("❌ 环境变量 TAVILY_API_KEY 未配置")
        return False
    
    print(f"API Key: {env_key[:15]}...")
    
    try:
        client = TavilyClient(env_key)
        response = client.search(
            query="test query",
            search_depth="basic",
            max_results=2,
        )
        print(f"✅ 成功！返回 {len(response.get('results', []))} 个结果")
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def test_direct_env():
    """直接从 os.environ 读取（绕过 settings）"""
    print("\n" + "="*60)
    print("测试 3：直接从 os.environ 读取")
    print("="*60)
    
    direct_key = os.environ.get("TAVILY_API_KEY")
    
    if not direct_key:
        print("❌ 环境变量 TAVILY_API_KEY 未设置")
        return False
    
    print(f"API Key: {direct_key[:15]}...")
    
    try:
        client = TavilyClient(direct_key)
        response = client.search(
            query="test query",
            search_depth="basic",
            max_results=2,
        )
        print(f"✅ 成功！返回 {len(response.get('results', []))} 个结果")
        return True
    except Exception as e:
        print(f"❌ 失败：{e}")
        return False


def compare_keys():
    """对比两个 key 是否相同"""
    print("\n" + "="*60)
    print("Key 对比")
    print("="*60)
    
    hardcoded = "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"
    env_key = settings.TAVILY_API_KEY
    direct_key = os.environ.get("TAVILY_API_KEY")
    
    print(f"硬编码 Key: {hardcoded[:20]}...{hardcoded[-10:]}")
    print(f"Settings Key: {env_key[:20] if env_key else 'None'}...{env_key[-10:] if env_key and len(env_key) > 10 else ''}")
    print(f"直接环境变量: {direct_key[:20] if direct_key else 'None'}...{direct_key[-10:] if direct_key and len(direct_key) > 10 else ''}")
    
    if hardcoded == env_key:
        print("\n✅ 硬编码 Key 与 Settings Key 相同")
    else:
        print("\n❌ 硬编码 Key 与 Settings Key 不同！")
        print("   这可能是问题的根源")
    
    if env_key == direct_key:
        print("✅ Settings Key 与环境变量 Key 相同")
    else:
        print("❌ Settings Key 与环境变量 Key 不同！")


def main():
    print("\n🔍 Tavily API Key 诊断工具")
    print("="*60)
    
    # 对比 keys
    compare_keys()
    
    # 测试硬编码 key
    result1 = test_hardcoded_key()
    
    # 测试环境变量 key
    result2 = test_env_key()
    
    # 测试直接环境变量
    result3 = test_direct_env()
    
    # 总结
    print("\n" + "="*60)
    print("诊断总结")
    print("="*60)
    
    print(f"硬编码 Key: {'✅ 可用' if result1 else '❌ 不可用'}")
    print(f"Settings Key: {'✅ 可用' if result2 else '❌ 不可用'}")
    print(f"直接环境变量: {'✅ 可用' if result3 else '❌ 不可用'}")
    
    if result1 and not result2:
        print("\n💡 建议：")
        print("   硬编码 Key 可用但环境变量 Key 不可用")
        print("   请检查 .env 文件中的 TAVILY_API_KEY 是否正确")
        print("   或者在代码中直接使用硬编码的 dev key")
    elif result1 and result2:
        print("\n✅ 两个 Key 都可用，问题可能在其他地方")
    else:
        print("\n⚠️ 需要进一步调查")


if __name__ == "__main__":
    main()

