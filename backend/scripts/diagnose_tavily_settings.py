#!/usr/bin/env python3
"""
诊断 Tavily API Key 配置问题
检查 settings 是否正确读取了 .env 文件中的 API Key
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config.settings import settings
import os

print("=" * 60)
print("Tavily API Key 配置诊断")
print("=" * 60)

# 1. 检查环境变量
print("\n1. 环境变量检查:")
env_key = os.getenv("TAVILY_API_KEY")
if env_key:
    print(f"   ✅ TAVILY_API_KEY 在环境变量中: {env_key[:20]}...")
else:
    print(f"   ❌ TAVILY_API_KEY 不在环境变量中")

# 2. 检查 settings
print("\n2. Settings 配置检查:")
settings_key = settings.TAVILY_API_KEY
if settings_key and settings_key != "your_tavily_api_key_here":
    print(f"   ✅ settings.TAVILY_API_KEY 已配置: {settings_key[:20]}...")
else:
    print(f"   ❌ settings.TAVILY_API_KEY 未配置或为默认值")
    print(f"   当前值: {settings_key}")

# 3. 对比两者是否一致
print("\n3. 一致性检查:")
if env_key and settings_key:
    if env_key == settings_key:
        print(f"   ✅ 环境变量和 settings 中的 API Key 一致")
    else:
        print(f"   ❌ 环境变量和 settings 中的 API Key 不一致！")
        print(f"   环境变量: {env_key[:20]}...")
        print(f"   settings:  {settings_key[:20]}...")
else:
    print(f"   ⚠️ 无法对比（其中一个未配置）")

# 4. 测试直接调用 Tavily API
print("\n4. 直接调用 Tavily API 测试:")
try:
    from tavily import TavilyClient
    
    # 使用 settings 中的 key
    if settings_key and settings_key != "your_tavily_api_key_here":
        print(f"   使用 settings 中的 key 测试...")
        client = TavilyClient(api_key=settings_key)
        response = client.search(
            query="测试查询",
            max_results=1,
            search_depth="basic"
        )
        print(f"   ✅ API 调用成功！返回 {len(response.get('results', []))} 个结果")
    else:
        print(f"   ⚠️ 跳过：settings 中的 key 无效")
        
except Exception as e:
    error_msg = str(e)
    if "usage limit" in error_msg.lower():
        print(f"   ⚠️ API 配额限制: {error_msg}")
    else:
        print(f"   ❌ API 调用失败: {error_msg}")

# 5. 检查 .env 文件
print("\n5. .env 文件检查:")
env_file = backend_dir / ".env"
if env_file.exists():
    print(f"   ✅ .env 文件存在: {env_file}")
    with open(env_file, 'r') as f:
        for line in f:
            if line.strip().startswith('TAVILY_API_KEY'):
                print(f"   内容: {line.strip()[:50]}...")
else:
    print(f"   ❌ .env 文件不存在: {env_file}")

print("\n" + "=" * 60)
print("诊断完成")
print("=" * 60)

