#!/usr/bin/env python3
"""
路线图生成接口测试脚本

功能：
1. 使用固定测试用户登录
2. 提交路线图生成请求
3. 轮询任务状态直到完成
4. 显示最终结果
5. [可选] 使用Mock路线图数据测试内容生成

使用方法：
    # 完整测试（真实路线图生成 + 真实内容生成）
    cd backend
    uv run python scripts/test_roadmap_generation.py

    # 使用Mock路线图测试内容生成
    cd backend
    uv run python scripts/test_roadmap_generation.py --mock-roadmap

注意：
    此脚本会自动跳过人工审核阶段（SKIP_HUMAN_REVIEW=true）
"""
import argparse
import asyncio
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

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

# 轮询配置
POLL_INTERVAL = 3  # 每3秒查询一次
MAX_POLL_ATTEMPTS = 200  # 最多轮询200次（10分钟）


# ============================================================
# Mock路线图数据
# ============================================================

# 简化的Mock路线图框架（仅用于内容生成测试）
MOCK_ROADMAP_FRAMEWORK = {
    "stages": [
        {
            "stage_id": "stage-1",
            "name": "基础入门",
            "description": "学习基础概念",
            "order": 1,
            "modules": [
                {
                    "module_id": "module-1-1",
                    "name": "核心概念",
                    "description": "理解核心概念",
                    "order": 1,
                    "concepts": [
                        {
                            "concept_id": "concept-1-1-1",
                            "name": "基本语法",
                            "description": "学习基本语法规则",
                            "order": 1,
                            "estimated_hours": 2.0,
                            "difficulty": "easy",
                        },
                        {
                            "concept_id": "concept-1-1-2",
                            "name": "数据类型",
                            "description": "理解各种数据类型",
                            "order": 2,
                            "estimated_hours": 1.5,
                            "difficulty": "easy",
                        },
                    ],
                },
            ],
        },
        {
            "stage_id": "stage-2",
            "name": "进阶实战",
            "description": "动手实践项目",
            "order": 2,
            "modules": [
                {
                    "module_id": "module-2-1",
                    "name": "实战项目",
                    "description": "构建实际项目",
                    "order": 1,
                    "concepts": [
                        {
                            "concept_id": "concept-2-1-1",
                            "name": "项目搭建",
                            "description": "搭建项目框架",
                            "order": 1,
                            "estimated_hours": 3.0,
                            "difficulty": "medium",
                        },
                    ],
                },
            ],
        },
    ],
    "total_estimated_hours": 6.5,
    "recommended_completion_weeks": 2,
}


# ============================================================
# 辅助函数
# ============================================================

async def login_and_get_token(client: httpx.AsyncClient) -> tuple[str, str]:
    """
    登录并获取JWT token和用户ID
    
    Returns:
        (JWT token字符串, 用户ID)
    """
    print(f"\n{'='*70}")
    print(f"🔐 步骤1: 用户登录")
    print(f"{'='*70}")
    print(f"   用户邮箱: {TEST_USER_EMAIL}")
    
    try:
        # 登录获取 token
        response = await client.post(
            "/api/v1/auth/jwt/login",
            data={
                "username": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            print(f"   ❌ 登录失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            sys.exit(1)
        
        token = response.json()["access_token"]
        print(f"   ✅ 登录成功")
        print(f"   Token: {token[:30]}...")
        
        # 获取用户信息（包含 user_id）
        user_response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if user_response.status_code != 200:
            print(f"   ❌ 获取用户信息失败")
            sys.exit(1)
        
        user_info = user_response.json()
        user_id = user_info["id"]
        print(f"   User ID: {user_id}")
        
        return token, user_id
        
    except Exception as e:
        print(f"   ❌ 登录异常: {e}")
        sys.exit(1)


async def submit_roadmap_generation(
    client: httpx.AsyncClient,
    token: str,
    user_id: str,
) -> str:
    """
    提交路线图生成请求
    
    Args:
        client: HTTP 客户端
        token: 访问令牌
        user_id: 用户 ID（从登录后获取）
    
    Returns:
        任务ID
    """
    print(f"\n{'='*70}")
    print(f"📝 步骤2: 提交路线图生成请求")
    print(f"{'='*70}")
    
    # 构造请求数据（使用实际的 user_id）
    request_data = {
        "user_id": user_id,  # ✅ 使用登录用户的实际 ID
        "session_id": f"test-session-{uuid.uuid4().hex[:8]}",
        "preferences": {
            "learning_goal": "成为全栈开发工程师",
            "available_hours_per_week": 15,
            "motivation": "转行进入技术领域，希望在6个月内找到初级开发工作",
            "current_level": "beginner",
            "career_background": "市场营销3年经验，对编程有浓厚兴趣",
            "content_preference": ["text", "hands_on", "visual"],
            "target_deadline": None,
        },
        "additional_context": "希望能够掌握前后端开发技能，特别关注实战项目经验",
    }
    
    print(f"   学习目标: {request_data['preferences']['learning_goal']}")
    print(f"   当前水平: {request_data['preferences']['current_level']}")
    print(f"   每周时间: {request_data['preferences']['available_hours_per_week']}小时")
    
    try:
        response = await client.post(
            "/api/v1/tasks/generate",
            json=request_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code != 200:
            print(f"   ❌ 请求失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            sys.exit(1)
        
        result = response.json()
        if result.get("code") != 200:
            print(f"   ❌ 业务错误: {result}")
            sys.exit(1)
        
        task_id = result["data"]["task_id"]
        print(f"   ✅ 任务已创建")
        print(f"   任务ID: {task_id}")
        print(f"   初始状态: {result['data']['status']}")
        return task_id
        
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        sys.exit(1)


async def replace_roadmap_with_mock(roadmap_id: str):
    """
    用Mock数据替换路线图的curriculum字段
    
    Args:
        roadmap_id: 路线图ID
    """
    print(f"\n{'='*70}")
    print(f"🔧 Mock路线图替换")
    print(f"{'='*70}")
    print(f"   正在将路线图 {roadmap_id} 的curriculum替换为Mock数据...")
    
    try:
        from app.db.session import async_session_maker
        from app.crud.crud_roadmap import get_roadmap_crud
        
        async with async_session_maker() as session:
            roadmap_crud = get_roadmap_crud()
            
            # 1. 获取路线图
            roadmap = await roadmap_crud.get_by_roadmap_id(session, roadmap_id)
            if not roadmap:
                print(f"   ❌ 路线图不存在")
                return False
            
            # 2. 替换curriculum字段
            roadmap.curriculum = MOCK_ROADMAP_FRAMEWORK
            roadmap.total_estimated_hours = MOCK_ROADMAP_FRAMEWORK["total_estimated_hours"]
            roadmap.recommended_completion_weeks = MOCK_ROADMAP_FRAMEWORK["recommended_completion_weeks"]
            
            await session.commit()
            
            print(f"   ✅ Mock数据替换成功")
            print(f"   Mock路线图结构:")
            print(f"      - 阶段数: {len(MOCK_ROADMAP_FRAMEWORK['stages'])}")
            print(f"      - 模块数: 2")
            print(f"      - 概念数: 3")
            print(f"      - 总学时: {MOCK_ROADMAP_FRAMEWORK['total_estimated_hours']}小时")
            return True
            
    except Exception as e:
        print(f"   ❌ 替换失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def poll_task_status(
    client: httpx.AsyncClient,
    token: str,
    task_id: str,
    use_mock_roadmap: bool = False,
) -> dict:
    """
    轮询任务状态直到完成
    
    Args:
        client: HTTP客户端
        token: JWT token
        task_id: 任务ID
        use_mock_roadmap: 是否使用Mock路线图数据
    
    Returns:
        最终的任务状态数据
    """
    print(f"\n{'='*70}")
    print(f"🔄 步骤3: 轮询任务状态")
    print(f"{'='*70}")
    print(f"   轮询间隔: {POLL_INTERVAL}秒")
    print(f"   最大次数: {MAX_POLL_ATTEMPTS}次")
    print(f"   最大等待时间: {MAX_POLL_ATTEMPTS * POLL_INTERVAL // 60}分钟")
    print(f"   注意: 工作流将自动跳过 human_review 阶段")
    if use_mock_roadmap:
        print(f"   🔧 Mock路线图模式: ✅ 已启用")
    print()
    
    start_time = datetime.now()
    status_history = []
    mock_replaced = False  # 标记是否已替换Mock数据
    
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        try:
            response = await client.get(
                f"/api/v1/tasks/{task_id}/status",
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if response.status_code != 200:
                print(f"   ⚠️ 查询失败 [{attempt}]: HTTP {response.status_code}")
                await asyncio.sleep(POLL_INTERVAL)
                continue
            
            result = response.json()
            task_data = result.get("data", {})
            status = task_data.get("status", "unknown")
            current_step = task_data.get("current_step", "unknown")
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # 记录状态变化
            status_key = f"{status}:{current_step}"
            if not status_history or status_history[-1]["status"] != status_key:
                status_history.append({
                    "status": status_key,
                    "elapsed": elapsed,
                    "attempt": attempt,
                })
                print(f"   [{elapsed:6.1f}s] {status:20s} -> {current_step}")
            
            # 🔧 Mock路线图模式：在进入内容生成前替换数据
            if use_mock_roadmap and not mock_replaced:
                # 检测到即将进入或已进入content_generation阶段
                if current_step in ["content_generation_queued", "content_generation"]:
                    roadmap_id = task_data.get("roadmap_id")
                    if roadmap_id:
                        print(f"\n   {'─'*66}")
                        print(f"   🎯 检测到进入内容生成阶段，触发Mock数据替换...")
                        success = await replace_roadmap_with_mock(roadmap_id)
                        if success:
                            mock_replaced = True
                            print(f"   ✅ Mock数据已替换，内容生成将使用简化框架")
                        else:
                            print(f"   ⚠️ Mock数据替换失败，将使用原始路线图数据")
                        print(f"   {'─'*66}\n")
            
            # 检查终止条件
            if status in ["completed", "failed", "cancelled"]:
                total_elapsed = (datetime.now() - start_time).total_seconds()
                print(f"\n   {'='*66}")
                print(f"   任务终止: {status}")
                print(f"   总耗时: {total_elapsed:.1f}秒 ({total_elapsed/60:.1f}分钟)")
                print(f"   总查询次数: {attempt}次")
                print(f"   {'='*66}")
                
                if status == "failed":
                    error_msg = task_data.get("error_message", "未知错误")
                    print(f"\n   ❌ 任务失败: {error_msg}")
                    sys.exit(1)
                elif status == "cancelled":
                    print(f"\n   🚫 任务已取消")
                    sys.exit(1)
                else:
                    print(f"\n   ✅ 任务成功完成")
                    return task_data
            
            await asyncio.sleep(POLL_INTERVAL)
            
        except Exception as e:
            print(f"   ⚠️ 查询异常 [{attempt}]: {e}")
            await asyncio.sleep(POLL_INTERVAL)
    
    # 超时
    print(f"\n   ❌ 任务超时: 在{MAX_POLL_ATTEMPTS * POLL_INTERVAL}秒内未完成")
    sys.exit(1)


async def get_roadmap_details(
    client: httpx.AsyncClient,
    token: str,
    roadmap_id: str,
) -> dict:
    """
    获取路线图详情
    
    Returns:
        路线图详细数据
    """
    print(f"\n{'='*70}")
    print(f"📚 步骤4: 获取路线图详情")
    print(f"{'='*70}")
    
    try:
        response = await client.get(
            f"/api/v1/roadmaps/{roadmap_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code != 200:
            print(f"   ❌ 查询失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            sys.exit(1)
        
        result = response.json()
        if result.get("code") != 200:
            print(f"   ❌ 业务错误: {result}")
            sys.exit(1)
        
        roadmap = result["data"]
        
        # 显示路线图摘要
        print(f"   ✅ 路线图详情获取成功")
        print(f"\n   路线图ID: {roadmap.get('roadmap_id')}")
        print(f"   标题: {roadmap.get('title')}")
        print(f"   总学时: {roadmap.get('total_estimated_hours')}小时")
        print(f"   推荐完成周数: {roadmap.get('recommended_completion_weeks')}周")
        print(f"   状态: {roadmap.get('status')}")
        
        # 显示课程结构
        curriculum = roadmap.get("curriculum", {})
        stages = curriculum.get("stages", [])
        print(f"\n   课程结构:")
        print(f"   - 阶段数: {len(stages)}")
        
        total_modules = 0
        total_concepts = 0
        for i, stage in enumerate(stages, 1):
            modules = stage.get("modules", [])
            total_modules += len(modules)
            stage_concepts = sum(len(m.get("concepts", [])) for m in modules)
            total_concepts += stage_concepts
            print(f"     阶段 {i}: {stage.get('name')}")
            print(f"       - 模块数: {len(modules)}")
            print(f"       - 概念数: {stage_concepts}")
        
        print(f"\n   总计:")
        print(f"   - 总模块数: {total_modules}")
        print(f"   - 总概念数: {total_concepts}")
        
        return roadmap
        
    except Exception as e:
        print(f"   ❌ 查询异常: {e}")
        sys.exit(1)


async def cleanup_test_data(
    client: httpx.AsyncClient,
    token: str,
    roadmap_id: str,
    skip_cleanup: bool = False,
):
    """
    清理测试数据（可选）
    
    Args:
        client: HTTP客户端
        token: JWT token
        roadmap_id: 路线图ID
        skip_cleanup: 是否跳过清理
    """
    print(f"\n{'='*70}")
    print(f"🧹 步骤5: 清理测试数据")
    print(f"{'='*70}")
    
    if skip_cleanup:
        print(f"   ⏭️  已跳过清理，测试数据保留")
        print(f"   路线图ID: {roadmap_id}")
        return
    
    print(f"   提示: 如需保留测试数据供查看，请按 Ctrl+C 取消")
    print(f"   将在5秒后开始清理...")
    
    try:
        await asyncio.sleep(5)
        
        # 使用数据库直接删除（需要导入相关模块）
        from app.db.session import async_session_maker
        from app.crud.crud_roadmap import get_roadmap_crud
        
        async with async_session_maker() as session:
            roadmap_crud = get_roadmap_crud()
            success = await roadmap_crud.delete_roadmap(session, roadmap_id)
            await session.commit()
            
            if success:
                print(f"   ✅ 测试数据已清理")
            else:
                print(f"   ⚠️ 未找到路线图或已被删除")
                
    except KeyboardInterrupt:
        print(f"\n   🛑 清理已取消，测试数据保留")
    except Exception as e:
        print(f"   ⚠️ 清理失败: {e}")


# ============================================================
# 主函数
# ============================================================

async def main(use_mock_roadmap: bool = False, skip_cleanup: bool = False):
    """
    主测试流程
    
    Args:
        use_mock_roadmap: 是否使用Mock路线图数据
        skip_cleanup: 是否跳过清理测试数据
    """
    print(f"\n{'#'*70}")
    print(f"# 路线图生成接口测试脚本")
    print(f"# 服务地址: {FASTAPI_BASE_URL}")
    print(f"# 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# 跳过人工审核: ✅ 已启用 (SKIP_HUMAN_REVIEW=true)")
    if use_mock_roadmap:
        print(f"# Mock路线图模式: ✅ 已启用")
        print(f"#   - 路线图生成: 使用真实用户请求")
        print(f"#   - 内容生成: 使用简化Mock数据")
    else:
        print(f"# Mock路线图模式: ❌ 未启用（完整测试）")
    if skip_cleanup:
        print(f"# 清理测试数据: ❌ 已禁用（数据将保留）")
    print(f"{'#'*70}")
    
    # 创建HTTP客户端
    async with httpx.AsyncClient(
        base_url=FASTAPI_BASE_URL,
        timeout=30.0,
    ) as client:
        try:
            # 步骤1: 登录并获取用户ID
            token, user_id = await login_and_get_token(client)
            
            # 步骤2: 提交生成请求（使用实际的 user_id）
            task_id = await submit_roadmap_generation(client, token, user_id)
            
            # 步骤3: 轮询任务状态
            task_data = await poll_task_status(
                client, token, task_id,
                use_mock_roadmap=use_mock_roadmap
            )
            
            # 步骤4: 获取路线图详情
            roadmap_id = task_data.get("roadmap_id")
            if roadmap_id:
                roadmap = await get_roadmap_details(client, token, roadmap_id)
                
                # 步骤5: 清理测试数据（可选）
                await cleanup_test_data(
                    client, token, roadmap_id,
                    skip_cleanup=skip_cleanup
                )
            else:
                print(f"\n   ⚠️ 未返回 roadmap_id，跳过详情查询")
            
            print(f"\n{'#'*70}")
            print(f"# ✅ 测试完成")
            print(f"{'#'*70}\n")
            
        except KeyboardInterrupt:
            print(f"\n\n{'='*70}")
            print(f"🛑 测试被用户中断")
            print(f"{'='*70}\n")
            sys.exit(0)
        except Exception as e:
            print(f"\n\n{'='*70}")
            print(f"❌ 测试过程中发生未预期的错误")
            print(f"错误类型: {type(e).__name__}")
            print(f"错误信息: {str(e)}")
            print(f"{'='*70}\n")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="路线图生成接口测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 完整测试（真实路线图 + 真实内容）
  uv run python scripts/test_roadmap_generation.py
  
  # Mock路线图测试（真实路线图生成 + Mock内容生成）
  uv run python scripts/test_roadmap_generation.py --mock-roadmap
  
  # 不清理测试数据
  uv run python scripts/test_roadmap_generation.py --no-cleanup
  
  # Mock模式 + 保留数据
  uv run python scripts/test_roadmap_generation.py --mock-roadmap --no-cleanup
        """
    )
    parser.add_argument(
        "--mock-roadmap",
        action="store_true",
        help="使用Mock路线图数据测试内容生成（路线图生成阶段仍使用真实数据）",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="测试完成后不清理数据",
    )
    
    args = parser.parse_args()
    
    # 运行主流程
    asyncio.run(main(
        use_mock_roadmap=args.mock_roadmap,
        skip_cleanup=args.no_cleanup
    ))

