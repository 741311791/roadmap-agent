#!/usr/bin/env python3
"""
人工审核测试脚本

功能：
1. 查找处于 human_review_pending 状态的任务
2. 交互式地批准或拒绝任务
3. 重置指定任务状态为 human_review_pending

使用方法：
    # 交互式审核现有任务（默认）
    cd backend
    uv run python scripts/test_human_review.py
    
    # 重置指定任务为待审核状态
    cd backend
    uv run python scripts/test_human_review.py --reset <task_id>
    
    # 只列出所有任务
    cd backend
    uv run python scripts/test_human_review.py --list
"""
import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

import httpx
import structlog

logger = structlog.get_logger()

# ============================================================
# 配置常量
# ============================================================

# FastAPI 服务地址
FASTAPI_BASE_URL = "http://localhost:8000"

# 测试用户
TEST_USER_EMAIL = "e2e_test_permanent@example.com"
TEST_USER_PASSWORD = "Test123456!"

# API 端点配置
TASKS_ENDPOINT = f"{FASTAPI_BASE_URL}/api/v1/tasks"


# ============================================================
# HTTP 客户端
# ============================================================

async def login(client: httpx.AsyncClient) -> str:
    """
    用户登录，获取 access_token
    
    Returns:
        access_token
    """
    logger.info("user_login_start", email=TEST_USER_EMAIL)
    
    # FastAPI Users 登录端点：/auth/jwt/login
    # 使用 form data 而不是 JSON
    response = await client.post(
        f"{FASTAPI_BASE_URL}/api/v1/auth/jwt/login",
        data={  # ✅ 使用 data 而不是 json（FastAPI Users 要求）
            "username": TEST_USER_EMAIL,  # ✅ 字段名是 username 而不是 email
            "password": TEST_USER_PASSWORD,
        },
    )
    
    if response.status_code != 200:
        logger.error(
            "user_login_failed",
            status_code=response.status_code,
            response=response.text,
        )
        raise RuntimeError(f"登录失败: {response.text}")
    
    data = response.json()
    # FastAPI Users 直接返回 token，不包装在 data 字段中
    # 响应格式: {"access_token": "...", "token_type": "bearer"}
    access_token = data["access_token"]
    
    logger.info("user_login_success", email=TEST_USER_EMAIL)
    return access_token


async def get_user_tasks(
    client: httpx.AsyncClient,
    token: str,
) -> list[dict]:
    """
    获取当前用户的任务列表
    
    Args:
        client: HTTP 客户端
        token: 访问令牌
        
    Returns:
        任务列表
    
    Note:
        使用 /tasks/my 端点，从 JWT token 自动提取 user_id
    """
    response = await client.get(
        f"{FASTAPI_BASE_URL}/api/v1/tasks/my",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    if response.status_code != 200:
        logger.error(
            "get_user_tasks_failed",
            status_code=response.status_code,
            response=response.text,
        )
        return []
    
    data = response.json()
    tasks = data["data"]["tasks"]
    
    logger.info(
        "user_tasks_fetched",
        total_tasks=len(tasks),
        pending_count=data["data"]["pending_count"],
        processing_count=data["data"]["processing_count"],
    )
    
    return tasks


async def reset_task_to_review(
    client: httpx.AsyncClient,
    token: str,
    task_id: str,
) -> bool:
    """
    重置任务状态为 human_review_pending
    
    Args:
        client: HTTP 客户端
        token: 访问令牌
        task_id: 任务 ID
        
    Returns:
        是否成功
    """
    logger.info("reset_task_to_review_start", task_id=task_id)
    
    # 调用后端 API 重置状态
    # 注意：需要后端提供相应的 API 端点
    # 这里假设使用内部管理端点
    response = await client.post(
        f"{FASTAPI_BASE_URL}/api/v1/tasks/{task_id}/reset-to-review",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    if response.status_code != 200:
        logger.error(
            "reset_task_to_review_failed",
            task_id=task_id,
            status_code=response.status_code,
            response=response.text,
        )
        return False
    
    data = response.json()
    
    logger.info(
        "reset_task_to_review_success",
        task_id=task_id,
        result=data.get("data"),
    )
    
    return True


async def get_task_status(
    client: httpx.AsyncClient,
    token: str,
    task_id: str,
) -> dict:
    """
    查询任务状态
    
    Returns:
        任务状态信息
    """
    response = await client.get(
        f"{FASTAPI_BASE_URL}/api/v1/tasks/{task_id}/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    if response.status_code != 200:
        logger.error(
            "get_task_status_failed",
            task_id=task_id,
            status_code=response.status_code,
        )
        return {}
    
    data = response.json()
    return data["data"]


async def submit_approval(
    client: httpx.AsyncClient,
    token: str,
    task_id: str,
    approved: bool,
    feedback: str | None = None,
) -> bool:
    """
    提交审核决策
    
    Args:
        client: HTTP 客户端
        token: 访问令牌
        task_id: 任务 ID
        approved: 是否批准
        feedback: 反馈意见（拒绝时提供）
        
    Returns:
        是否成功
    """
    logger.info(
        "submit_approval_start",
        task_id=task_id,
        approved=approved,
        has_feedback=bool(feedback),
    )
    
    request_data = {
        "approved": approved,
        "feedback": feedback,
    }
    
    response = await client.post(
        f"{FASTAPI_BASE_URL}/api/v1/tasks/{task_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json=request_data,
    )
    
    if response.status_code != 200:
        logger.error(
            "submit_approval_failed",
            task_id=task_id,
            status_code=response.status_code,
            response=response.text,
        )
        return False
    
    data = response.json()
    result = data["data"]
    
    logger.info(
        "submit_approval_success",
        task_id=task_id,
        status=result["status"],
        message=result["message"],
    )
    
    return True


async def get_user_info(
    client: httpx.AsyncClient,
    token: str,
) -> dict:
    """
    获取当前用户信息
    
    Returns:
        用户信息（包含 user_id）
    """
    response = await client.get(
        f"{FASTAPI_BASE_URL}/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    
    if response.status_code != 200:
        logger.error(
            "get_user_info_failed",
            status_code=response.status_code,
        )
        raise RuntimeError("获取用户信息失败")
    
    # FastAPI Users 直接返回用户对象，不包装在 data 字段中
    # 响应格式: {"id": "...", "email": "...", ...}
    data = response.json()
    return data


# ============================================================
# 主流程
# ============================================================

async def interactive_review_main():
    """交互式审核任务的主流程"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 步骤 1: 登录
        token = await login(client)
        
        # 步骤 2: 获取用户信息
        user_info = await get_user_info(client, token)
        user_id = user_info["id"]
        
        logger.info(
            "user_info_fetched",
            user_id=user_id,
            email=user_info["email"],
        )
        
        print(f"\n{'='*70}")
        print(f"📋 用户信息")
        print(f"{'='*70}")
        print(f"  User ID: {user_id}")
        print(f"  Email: {user_info['email']}")
        print(f"  Username: {user_info.get('username', 'N/A')}")
        print(f"{'='*70}\n")
        
        # 步骤 3: 查找待审核任务
        tasks = await get_user_tasks(client, token)
        
        print(f"📊 任务统计：总共 {len(tasks)} 个任务")
        if tasks:
            status_counts = {}
            for task in tasks:
                status = task.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            print("   状态分布：")
            for status, count in status_counts.items():
                print(f"   - {status}: {count}")
        print()
        
        pending_review_tasks = [
            t for t in tasks
            if t.get("status") == "human_review_pending"
        ]
        
        if not pending_review_tasks:
            print("📭 没有找到待审核的任务")
            print("\n💡 提示：")
            print("   - 使用 --list 查看所有任务")
            print("   - 使用 --reset <task_id> 重置任务状态为待审核\n")
            return
        
        print(f"\n找到 {len(pending_review_tasks)} 个待审核任务：")
        print("="*70)
        for i, task in enumerate(pending_review_tasks, 1):
            print(f"  {i}. Task ID: {task['task_id']}")
            print(f"     标题: {task.get('title', '无标题')}")
            print(f"     创建时间: {task.get('created_at', 'N/A')}")
            print()
        
        # 选择要审核的任务
        choice = input(f"请选择要审核的任务（1-{len(pending_review_tasks)}）: ").strip()
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(pending_review_tasks):
                print("❌ 无效的选择")
                return
            task_id = pending_review_tasks[idx]["task_id"]
        except ValueError:
            print("❌ 无效的选择")
            return
        
        # 步骤 4: 提交审核决策
        print(f"\n{'='*70}")
        print(f"准备审核任务: {task_id}")
        print(f"{'='*70}\n")
        
        action = input("请选择操作 (1=批准, 2=拒绝): ").strip()
        
        if action == "1":
            approved = True
            user_feedback = None
            print("✅ 选择：批准")
        elif action == "2":
            approved = False
            user_feedback = input("请输入反馈意见: ").strip()
            if not user_feedback:
                user_feedback = "需要修改"
            print(f"❌ 选择：拒绝，反馈: {user_feedback}")
        else:
            print("❌ 无效的选择")
            return
        
        # 提交审核
        print("\n提交审核决策...")
        success = await submit_approval(
            client,
            token,
            task_id,
            approved,
            user_feedback,
        )
        
        if success:
            print("\n" + "="*70)
            if approved:
                print("✅ 审核已批准！工作流将继续生成内容")
            else:
                print(f"❌ 审核已拒绝！工作流将根据反馈修改路线图")
                print(f"   反馈: {user_feedback}")
            print("="*70 + "\n")
        else:
            print("\n❌ 提交审核失败\n")


async def list_tasks_main():
    """列出所有任务的主流程"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 步骤 1: 登录
        token = await login(client)
        
        # 步骤 2: 获取用户信息
        user_info = await get_user_info(client, token)
        user_id = user_info["id"]
        
        logger.info(
            "user_info_fetched",
            user_id=user_id,
            email=user_info["email"],
        )
        
        print(f"\n{'='*70}")
        print(f"📋 用户信息")
        print(f"{'='*70}")
        print(f"  User ID: {user_id}")
        print(f"  Email: {user_info['email']}")
        print(f"  Username: {user_info.get('username', 'N/A')}")
        print(f"{'='*70}\n")
        
        # 步骤 3: 获取任务列表
        tasks = await get_user_tasks(client, token)
        
        if not tasks:
            print("📭 没有找到任何任务\n")
            return
        
        print(f"{'='*70}")
        print(f"📊 任务列表（共 {len(tasks)} 个任务）")
        print(f"{'='*70}\n")
        
        # 按状态分组
        status_groups = {}
        for task in tasks:
            status = task.get("status", "unknown")
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(task)
        
        # 显示任务
        for status, task_list in sorted(status_groups.items()):
            print(f"\n[{status.upper()}] - {len(task_list)} 个任务:")
            print("-" * 70)
            for task in task_list:
                task_id = task.get("task_id", "N/A")
                title = task.get("title", "无标题")
                created_at = task.get("created_at", "N/A")
                current_step = task.get("current_step", "N/A")
                
                print(f"  • Task ID: {task_id}")
                print(f"    标题: {title}")
                print(f"    创建时间: {created_at}")
                print(f"    当前步骤: {current_step}")
                print()
        
        print(f"{'='*70}\n")
        print("💡 提示：使用 --reset <task_id> 可以将任务重置为待审核状态\n")


async def reset_task_main(task_id: str):
    """重置任务状态的主流程"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 步骤 1: 登录
        token = await login(client)
        
        # 步骤 2: 获取用户信息
        user_info = await get_user_info(client, token)
        
        print(f"\n{'='*70}")
        print(f"🔄 重置任务状态")
        print(f"{'='*70}")
        print(f"  用户: {user_info['email']}")
        print(f"  Task ID: {task_id}")
        print(f"  目标状态: human_review_pending")
        print(f"{'='*70}\n")
        
        # 步骤 3: 重置任务状态
        print("正在重置任务状态...")
        success = await reset_task_to_review(client, token, task_id)
        
        if success:
            print("\n✅ 任务状态已成功重置为 human_review_pending")
            print("   现在可以通过前端或 API 进行人工审核")
        else:
            print("\n❌ 重置任务状态失败")
            print("   可能原因：")
            print("   1. Task ID 不存在")
            print("   2. 无权限操作该任务")
            print("   3. 后端 API 端点未实现")
        
        print()


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="人工审核测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 交互式审核待审核任务（默认）
  python scripts/test_human_review.py
  
  # 列出所有任务
  python scripts/test_human_review.py --list
  
  # 重置指定任务为待审核状态
  python scripts/test_human_review.py --reset <task_id>
        """,
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有任务（不进行审核）",
    )
    
    parser.add_argument(
        "--reset",
        type=str,
        metavar="TASK_ID",
        help="重置指定 task_id 的状态为 human_review_pending",
    )
    
    args = parser.parse_args()
    
    # 运行主流程
    try:
        if args.reset:
            # 重置模式
            asyncio.run(reset_task_main(args.reset))
        elif args.list:
            # 列表模式
            asyncio.run(list_tasks_main())
        else:
            # 交互式审核模式（默认）
            asyncio.run(interactive_review_main())
    except KeyboardInterrupt:
        print("\n\n⚠️  已取消")
        sys.exit(0)
    except Exception as e:
        logger.error("main_error", error=str(e), exc_info=True)
        print(f"\n❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
