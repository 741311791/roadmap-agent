#!/usr/bin/env python3
"""
快速验证工具定义
检查 ResourceRecommenderAgent 的工具定义是否包含所有高级参数
"""
import sys
from pathlib import Path
import json

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.agents.resource_recommender import ResourceRecommenderAgent


def main():
    print("\n" + "="*60)
    print("🔍 ResourceRecommenderAgent 工具定义验证")
    print("="*60)
    
    # 创建 Agent
    agent = ResourceRecommenderAgent()
    
    # 获取工具定义
    tools = agent._get_tools_definition()
    
    if not tools:
        print("❌ 错误：没有找到工具定义")
        sys.exit(1)
    
    print(f"\n✅ 找到 {len(tools)} 个工具定义\n")
    
    # 检查 web_search 工具
    web_search_tool = None
    for tool in tools:
        if tool["function"]["name"] == "web_search":
            web_search_tool = tool
            break
    
    if not web_search_tool:
        print("❌ 错误：未找到 web_search 工具")
        sys.exit(1)
    
    print("📋 工具名称: web_search")
    print(f"📝 工具描述: {web_search_tool['function']['description'][:100]}...")
    print("\n" + "-"*60)
    print("参数检查")
    print("-"*60)
    
    properties = web_search_tool["function"]["parameters"]["properties"]
    required_params = web_search_tool["function"]["parameters"].get("required", [])
    
    # 必需参数
    basic_params = {
        "query": "搜索查询字符串（必需）",
        "max_results": "最大结果数量（可选）",
    }
    
    # 高级参数（Tavily 特有）
    advanced_params = {
        "time_range": "时间筛选（可选，但强烈推荐）",
        "search_depth": "搜索深度（可选）",
        "include_domains": "优先域名列表（可选）",
        "exclude_domains": "排除域名列表（可选）",
    }
    
    # 检查基础参数
    print("\n✅ 基础参数:")
    for param, desc in basic_params.items():
        if param in properties:
            is_required = param in required_params
            status = "必需" if is_required else "可选"
            print(f"  ✅ {param} ({status})")
            print(f"     {properties[param].get('description', 'N/A')[:80]}...")
        else:
            print(f"  ❌ {param} - 缺失")
    
    # 检查高级参数
    print("\n🆕 Tavily 高级参数:")
    all_advanced_present = True
    for param, desc in advanced_params.items():
        if param in properties:
            print(f"  ✅ {param} ({desc})")
            param_def = properties[param]
            print(f"     类型: {param_def.get('type', 'N/A')}")
            if "enum" in param_def:
                print(f"     可选值: {', '.join(param_def['enum'])}")
            print(f"     说明: {param_def.get('description', 'N/A')[:100]}...")
        else:
            print(f"  ❌ {param} - 缺失")
            all_advanced_present = False
    
    # 总结
    print("\n" + "="*60)
    print("验证总结")
    print("="*60)
    
    if all_advanced_present:
        print("✅ 所有高级参数都已定义")
        print("✅ 工具定义符合 Tavily SDK 规范")
        print("\n🎉 验证通过！可以使用高级搜索功能：")
        print("   - 时间筛选 (time_range)")
        print("   - 域名筛选 (include_domains, exclude_domains)")
        print("   - 搜索深度控制 (search_depth)")
    else:
        print("❌ 缺少部分高级参数")
        print("⚠️ 无法充分利用 Tavily API 的高级功能")
        sys.exit(1)
    
    # 显示完整的工具定义（JSON 格式）
    print("\n" + "-"*60)
    print("完整工具定义（JSON 格式）")
    print("-"*60)
    print(json.dumps(web_search_tool, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

