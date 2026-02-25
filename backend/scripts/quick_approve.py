#!/usr/bin/env python3
"""快速批准脚本（用于测试）"""
import asyncio
import httpx

async def quick_approve():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 登录
        login_resp = await client.post(
            'http://localhost:8000/api/v1/auth/jwt/login',
            data={'username': 'e2e_test_permanent@example.com', 'password': 'Test123456!'}
        )
        token = login_resp.json()['access_token']
        print('✅ 登录成功')
        
        # 获取任务列表
        tasks_resp = await client.get(
            'http://localhost:8000/api/v1/tasks/my',
            headers={'Authorization': f'Bearer {token}'}
        )
        tasks = tasks_resp.json()['data']['tasks']
        pending_tasks = [t for t in tasks if t['status'] == 'human_review_pending']
        
        if not pending_tasks:
            print('❌ 没有待审核任务')
            return
        
        task_id = pending_tasks[0]['task_id']
        title = pending_tasks[0].get('title', '无标题')
        print(f'📋 审批任务: {task_id}')
        print(f'   标题: {title}')
        
        # 提交审批
        approval_resp = await client.post(
            f'http://localhost:8000/api/v1/tasks/{task_id}/approve',
            headers={'Authorization': f'Bearer {token}'},
            json={'approved': True, 'feedback': None}
        )
        
        result = approval_resp.json()
        print(f'✅ {result["data"]["message"]}')
        print(f'   Celery Task ID: {result["data"].get("celery_task_id", "N/A")}')

asyncio.run(quick_approve())
