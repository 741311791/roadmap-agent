"""
直接测试 litellm（不使用 instructor）
"""
import asyncio
import litellm
import json


async def test_litellm_direct():
    """直接测试 litellm 调用"""
    print("=" * 80)
    print("测试直接调用 litellm（不使用 instructor）")
    print("=" * 80)
    
    messages = [
        {"role": "system", "content": "你是一个助手，请用 JSON 格式回答。"},
        {"role": "user", "content": "请用 JSON 格式告诉我 Python 是什么。JSON 应该包含 answer 和 confidence 两个字段。"}
    ]
    
    try:
        print("\n正在调用 litellm...")
        print(f"模型: openai/qwen-plus")
        
        import os
        api_key = os.getenv("ARCHITECT_API_KEY")
        api_base = os.getenv("ARCHITECT_BASE_URL")
        
        print(f"API Key: {'已设置' if api_key else '未设置'}")
        print(f"API Base: {api_base}")
        
        # 直接调用 litellm
        response = await litellm.acompletion(
            model="openai/qwen-plus",
            messages=messages,
            api_key=api_key,
            api_base=api_base,
            custom_llm_provider="openai",
            response_format={"type": "json_object"},
            max_tokens=500,
        )
        
        print("\n✅ 调用成功!")
        content = response.choices[0].message.content
        print(f"响应长度: {len(content)} 字符")
        print(f"响应内容:\n{content}")
        
        # 解析 JSON
        data = json.loads(content)
        print(f"\n解析后的数据: {data}")
        
    except Exception as e:
        print(f"\n❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_litellm_direct())
