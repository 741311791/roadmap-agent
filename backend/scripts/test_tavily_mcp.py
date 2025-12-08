"""
Tavily MCP 连通性测试脚本

测试通过 OpenAI 的 MCP 功能调用 Tavily 搜索服务
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI
from app.config.settings import settings


def test_tavily_mcp_connectivity():
    """
    测试 Tavily MCP 服务的连通性
    
    测试步骤：
    1. 初始化 OpenAI 客户端
    2. 配置 Tavily MCP 工具
    3. 发送测试查询
    4. 验证响应
    """
    print("=" * 60)
    print("Tavily MCP 连通性测试")
    print("=" * 60)
    
    # 检查必需的环境变量
    print("\n步骤 1: 检查配置")
    print("-" * 60)
    
    tavily_api_key = settings.TAVILY_API_KEY
    openai_api_key = settings.RECOMMENDER_API_KEY
    
    if not tavily_api_key or tavily_api_key == "your_tavily_api_key_here":
        print("❌ 错误: TAVILY_API_KEY 未配置")
        print("请在 .env 文件中设置 TAVILY_API_KEY")
        return False
    
    if not openai_api_key or openai_api_key == "your_openai_api_key_here":
        print("❌ 错误: RECOMMENDER_API_KEY (OpenAI) 未配置")
        print("请在 .env 文件中设置 RECOMMENDER_API_KEY")
        return False
    
    print(f"✓ Tavily API Key: {tavily_api_key[:10]}...")
    print(f"✓ OpenAI API Key: {openai_api_key[:10]}...")
    
    # 初始化 OpenAI 客户端
    print("\n步骤 2: 初始化 OpenAI 客户端")
    print("-" * 60)
    
    try:
        # 增加超时时间到 60 秒
        # 如果需要代理，可以设置环境变量 HTTP_PROXY 和 HTTPS_PROXY
        client = OpenAI(
            api_key=openai_api_key,
            timeout=60.0,  # 增加超时时间
            max_retries=2,
        )
        print("✓ OpenAI 客户端初始化成功")
        
        # 检查是否配置了代理
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        if http_proxy or https_proxy:
            print(f"  使用代理配置:")
            if http_proxy:
                print(f"    HTTP_PROXY: {http_proxy}")
            if https_proxy:
                print(f"    HTTPS_PROXY: {https_proxy}")
        else:
            print("  未检测到代理配置")
            
    except Exception as e:
        print(f"❌ OpenAI 客户端初始化失败: {e}")
        return False
    
    # 构建 Tavily MCP 服务 URL
    tavily_mcp_url = f"https://mcp.tavily.com/mcp/?tavilyApiKey={tavily_api_key}"
    
    print("\n步骤 3: 配置 Tavily MCP 工具")
    print("-" * 60)
    print(f"MCP 服务 URL: {tavily_mcp_url[:50]}...")
    
    # 发送测试请求
    print("\n步骤 4: 发送测试查询")
    print("-" * 60)
    print("查询: 'Python 官方文档'")
    
    try:
        response = client.responses.create(
            model="gpt-4.1",  # MCP 需要使用 gpt-4.1 模型
            input="请使用 Tavily 搜索工具搜索 'Python 官方文档'，并返回搜索结果",
            tools=[
                {
                    "type": "mcp",
                    "server_label": "tavily",
                    "server_url": tavily_mcp_url,
                    "require_approval": "never",
                }
            ],
        )
        
        print("\n步骤 5: 验证响应")
        print("-" * 60)
        
        # 打印响应内容（responses API 返回格式不同）
        if hasattr(response, 'output_text'):
            print(f"✓ 响应成功")
            print(f"\n响应内容:")
            print(f"{response.output_text[:500]}...")
        elif hasattr(response, 'output'):
            print(f"✓ 响应成功")
            print(f"\n响应输出:")
            print(f"{str(response.output)[:500]}...")
        else:
            print(f"✓ 响应成功")
            print(f"\n完整响应:")
            print(f"{str(response)[:500]}...")
        
        print("\n" + "=" * 60)
        print("✅ Tavily MCP 连通性测试成功！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        
        # 根据错误类型提供建议
        error_type = type(e).__name__
        if error_type == "AuthenticationError":
            print("\n💡 解决建议:")
            print("   1. 检查 .env 文件中的 RECOMMENDER_API_KEY 是否正确")
            print("   2. 确保使用的是有效的 OpenAI API 密钥")
            print("   3. 访问 https://platform.openai.com/account/api-keys 获取密钥")
        elif "Timeout" in error_type or "ConnectionError" in error_type:
            print("\n💡 解决建议:")
            print("   1. 检查网络连接")
            print("   2. 如果在国内，可能需要配置代理")
            print("   3. 设置环境变量: export HTTPS_PROXY=your_proxy_url")
        
        # 打印详细的错误信息
        import traceback
        print("\n详细错误堆栈:")
        traceback.print_exc()
        
        print("\n" + "=" * 60)
        print("❌ Tavily MCP 连通性测试失败")
        print("=" * 60)
        return False


def test_tavily_mcp_search_functionality():
    """
    测试 Tavily MCP 搜索功能的完整性
    
    测试多个搜索场景：
    1. 基础搜索
    2. 带语言偏好的搜索
    3. 带内容类型的搜索
    """
    print("\n" + "=" * 60)
    print("Tavily MCP 搜索功能测试")
    print("=" * 60)
    
    tavily_api_key = settings.TAVILY_API_KEY
    openai_api_key = settings.RECOMMENDER_API_KEY
    
    client = OpenAI(
        api_key=openai_api_key,
        timeout=60.0,
        max_retries=2,
    )
    tavily_mcp_url = f"https://mcp.tavily.com/mcp/?tavilyApiKey={tavily_api_key}"
    
    test_cases = [
        {
            "name": "基础搜索",
            "query": "React Hooks 教程",
        },
        {
            "name": "中文搜索",
            "query": "Python 机器学习中文教程",
        },
        {
            "name": "视频资源搜索",
            "query": "JavaScript 视频教程 YouTube",
        },
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试用例 {i}/{len(test_cases)}: {test_case['name']}")
        print("-" * 60)
        print(f"查询: {test_case['query']}")
        
        try:
            response = client.responses.create(
                model="gpt-4.1",
                input=f"请使用 Tavily 搜索工具搜索: {test_case['query']}",
                tools=[
                    {
                        "type": "mcp",
                        "server_label": "tavily",
                        "server_url": tavily_mcp_url,
                        "require_approval": "never",
                    }
                ],
            )
            
            if hasattr(response, 'output_text'):
                content_preview = response.output_text[:200]
                print(f"✓ 返回内容: {content_preview}...")
            else:
                print(f"✓ 响应成功")
            
            print(f"✅ 测试用例 {i} 通过")
            
        except Exception as e:
            print(f"❌ 测试用例 {i} 失败: {e}")
    
    print("\n" + "=" * 60)
    print("搜索功能测试完成")
    print("=" * 60)


if __name__ == "__main__":
    # 运行连通性测试
    connectivity_success = test_tavily_mcp_connectivity()
    
    if connectivity_success:
        # 如果连通性测试通过，运行功能测试
        print("\n\n")
        test_tavily_mcp_search_functionality()
    else:
        print("\n⚠️  连通性测试失败，跳过功能测试")
        sys.exit(1)

