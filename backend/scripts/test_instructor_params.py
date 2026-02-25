"""
测试 instructor 的参数传递
"""
import asyncio
import instructor
from litellm import acompletion
from pydantic import BaseModel, Field
import os


class SimpleOutput(BaseModel):
    """简单输出"""
    answer: str = Field(..., description="回答")
    confidence: float = Field(..., ge=0, le=1, description="置信度")


async def test_instructor_params():
    """测试不同的参数组合"""
    
    client = instructor.from_litellm(acompletion)
    
    api_key = os.getenv("ARCHITECT_API_KEY")
    api_base = os.getenv("ARCHITECT_BASE_URL")
    
    messages = [
        {"role": "system", "content": "请用 JSON 格式回答。"},
        {"role": "user", "content": "Python 是什么？"}
    ]
    
    # 测试1：最小参数（按官方文档）
    print("=" * 80)
    print("测试1：最小参数（model + messages + response_model）")
    print("=" * 80)
    try:
        response = await client.chat.completions.create(
            model="openai/qwen-plus",
            response_model=SimpleOutput,
            messages=messages,
            max_retries=2,
        )
        print(f"✅ 成功! {response}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 测试2：添加 api_key 和 api_base
    print("\n" + "=" * 80)
    print("测试2：添加 api_key 和 api_base")
    print("=" * 80)
    try:
        response = await client.chat.completions.create(
            model="openai/qwen-plus",
            response_model=SimpleOutput,
            messages=messages,
            max_retries=2,
            api_key=api_key,
            api_base=api_base,
        )
        print(f"✅ 成功! {response}")
    except Exception as e:
        print(f"❌ 失败: {e}")
    
    # 测试3：添加 custom_llm_provider
    print("\n" + "=" * 80)
    print("测试3：添加 custom_llm_provider")
    print("=" * 80)
    try:
        response = await client.chat.completions.create(
            model="openai/qwen-plus",
            response_model=SimpleOutput,
            messages=messages,
            max_retries=2,
            api_key=api_key,
            api_base=api_base,
            custom_llm_provider="openai",
        )
        print(f"✅ 成功! {response}")
    except Exception as e:
        print(f"❌ 失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_instructor_params())
