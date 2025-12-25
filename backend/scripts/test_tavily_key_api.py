#!/usr/bin/env python3
"""
测试 Tavily API Key 管理端点

使用方法：
    python test_tavily_key_api.py
"""
import asyncio
import httpx
from datetime import datetime

# 配置
BASE_URL = "http://localhost:8000"  # 根据实际情况修改
API_PREFIX = "/api/v1"

# 测试用的 API Key（请替换为实际的超级管理员 Token）
AUTH_TOKEN = "your_superuser_token_here"


async def test_get_keys():
    """测试获取所有 Keys"""
    print("\n" + "="*60)
    print("测试: 获取所有 Tavily API Keys")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}{API_PREFIX}/admin/tavily-keys",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"总数: {data['total']}")
            print(f"Keys: {len(data['keys'])} 个")
            
            for key in data['keys']:
                print(f"\n  - Key: {key['api_key']}")
                print(f"    配额: {key['remaining_quota']}/{key['plan_limit']}")
                print(f"    创建时间: {key['created_at']}")
        else:
            print(f"错误: {response.text}")


async def test_add_single_key():
    """测试添加单个 Key"""
    print("\n" + "="*60)
    print("测试: 添加单个 Tavily API Key")
    print("="*60)
    
    test_key = f"tvly-test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/admin/tavily-keys",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            json={
                "api_key": test_key,
                "plan_limit": 1000
            }
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"成功添加 Key: {data['api_key']}")
            print(f"配额: {data['remaining_quota']}/{data['plan_limit']}")
            return test_key
        else:
            print(f"错误: {response.text}")
            return None


async def test_batch_add_keys():
    """测试批量添加 Keys"""
    print("\n" + "="*60)
    print("测试: 批量添加 Tavily API Keys")
    print("="*60)
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    test_keys = [
        {"api_key": f"tvly-batch-1-{timestamp}", "plan_limit": 1000},
        {"api_key": f"tvly-batch-2-{timestamp}", "plan_limit": 2000},
        {"api_key": f"tvly-batch-3-{timestamp}", "plan_limit": 1500},
    ]
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}{API_PREFIX}/admin/tavily-keys/batch",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            json={"keys": test_keys}
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"成功: {data['success']} 个")
            print(f"失败: {data['failed']} 个")
            
            if data['errors']:
                print("\n错误详情:")
                for err in data['errors']:
                    print(f"  - {err['api_key']}: {err['error']}")
            
            return [k['api_key'] for k in test_keys]
        else:
            print(f"错误: {response.text}")
            return []


async def test_update_key(api_key: str):
    """测试更新 Key 配额"""
    print("\n" + "="*60)
    print(f"测试: 更新 Tavily API Key - {api_key}")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{BASE_URL}{API_PREFIX}/admin/tavily-keys/{api_key}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            json={
                "remaining_quota": 500,
                "plan_limit": 2000
            }
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"更新成功:")
            print(f"  配额: {data['remaining_quota']}/{data['plan_limit']}")
            print(f"  更新时间: {data['updated_at']}")
        else:
            print(f"错误: {response.text}")


async def test_delete_key(api_key: str):
    """测试删除 Key"""
    print("\n" + "="*60)
    print(f"测试: 删除 Tavily API Key - {api_key}")
    print("="*60)
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{BASE_URL}{API_PREFIX}/admin/tavily-keys/{api_key}",
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        )
        
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"删除成功: {data['message']}")
        else:
            print(f"错误: {response.text}")


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("Tavily API Key 管理端点测试")
    print("="*60)
    
    if AUTH_TOKEN == "your_superuser_token_here":
        print("\n❌ 错误: 请先设置有效的超级管理员 Token")
        print("在脚本中修改 AUTH_TOKEN 变量")
        return
    
    try:
        # 1. 获取当前所有 Keys
        await test_get_keys()
        
        # 2. 添加单个 Key
        single_key = await test_add_single_key()
        
        # 3. 批量添加 Keys
        batch_keys = await test_batch_add_keys()
        
        # 4. 更新 Key（如果添加成功）
        if single_key:
            await asyncio.sleep(1)  # 等待数据库更新
            await test_update_key(single_key)
        
        # 5. 再次获取所有 Keys（查看变化）
        await test_get_keys()
        
        # 6. 清理测试数据（删除测试 Keys）
        print("\n" + "="*60)
        print("清理测试数据")
        print("="*60)
        
        if single_key:
            await test_delete_key(single_key)
        
        for key in batch_keys:
            await test_delete_key(key)
        
        # 7. 最后再次获取所有 Keys
        await test_get_keys()
        
        print("\n" + "="*60)
        print("✅ 所有测试完成!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

