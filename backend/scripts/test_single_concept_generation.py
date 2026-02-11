#!/usr/bin/env python3
"""
单 Concept 内容生成 API 测试脚本

功能：
1. 使用固定测试用户登录
2. 调用单 Concept 内容生成接口
3. 显示生成结果

使用方法：
    cd backend
    uv run python scripts/test_single_concept_generation.py --roadmap-id <roadmap_id> --concept-id <concept_id>
    
    或使用自动模式（自动查找可用的 roadmap 和 concept）：
    uv run python scripts/test_single_concept_generation.py --auto

注意：
    - 需要先有一个完整的 roadmap（包含 Framework）
    - concept_id 格式为 "C-<stage>-<module>-<concept>"
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

import httpx
import structlog

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = structlog.get_logger()

# ============================================================
# 配置常量
# ============================================================

# FastAPI 服务地址
FASTAPI_BASE_URL = "http://localhost:8000"

# 测试用户
TEST_USER_EMAIL = "e2e_test_permanent@example.com"
TEST_USER_PASSWORD = "Test123456!"


# ============================================================
# 辅助函数
# ============================================================

async def login_and_get_token(client: httpx.AsyncClient) -> str:
    """
    登录并获取JWT token
    
    Returns:
        JWT token字符串
    """
    print(f"\n{'='*70}")
    print(f"🔐 步骤1: 用户登录")
    print(f"{'='*70}")
    print(f"   用户邮箱: {TEST_USER_EMAIL}")
    
    try:
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
        return token
        
    except Exception as e:
        print(f"   ❌ 登录异常: {e}")
        sys.exit(1)


async def find_available_roadmap_and_concept(
    client: httpx.AsyncClient,
    token: str,
) -> tuple[str, str, str]:
    """
    自动查找可用的 roadmap 和 concept
    
    Returns:
        (roadmap_id, concept_id, concept_name)
    """
    print(f"\n{'='*70}")
    print(f"🔍 步骤2: 自动查找可用的 Roadmap 和 Concept")
    print(f"{'='*70}")
    
    try:
        # 先获取当前用户信息
        me_response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if me_response.status_code != 200:
            print(f"   ❌ 获取用户信息失败: HTTP {me_response.status_code}")
            sys.exit(1)
        
        user_data = me_response.json()
        user_id = user_data.get("id")
        
        print(f"   当前用户 ID: {user_id}")
        
        # 获取用户的 roadmap 列表
        response = await client.get(
            f"/api/v1/users/{user_id}/roadmaps",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code != 200:
            print(f"   ❌ 查询 Roadmap 列表失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            sys.exit(1)
        
        result = response.json()
        items = result.get("data", {}).get("roadmaps", [])
        
        if not items:
            print(f"   ❌ 未找到任何 Roadmap")
            print(f"   提示: 请先运行 test_roadmap_generation.py 创建一个 Roadmap")
            sys.exit(1)
        
        # 查找有 Framework 数据的 roadmap
        for roadmap in items:
            roadmap_id = roadmap.get("roadmap_id")
            print(f"   检查 Roadmap: {roadmap_id}")
            
            # 获取 roadmap 详情
            detail_response = await client.get(
                f"/api/v1/roadmaps/{roadmap_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if detail_response.status_code != 200:
                continue
            
            detail_result = detail_response.json()
            roadmap_data = detail_result.get("data", {})
            
            # stages 字段直接在 data 下
            stages = roadmap_data.get("stages", [])
            
            if not stages:
                print(f"   ⚠️ Roadmap {roadmap_id} 没有 stages 数据，跳过")
                continue
            
            # 查找第一个可用的 concept
            for stage in stages:
                for module in stage.get("modules", []):
                    concepts = module.get("concepts", [])
                    if concepts:
                        # 使用第一个 concept
                        concept = concepts[0]
                        concept_id = concept.get("concept_id")
                        concept_name = concept.get("name")
                        
                        print(f"   ✅ 找到可用的 Concept")
                        print(f"      Roadmap ID: {roadmap_id}")
                        print(f"      Roadmap Title: {roadmap_data.get('title')}")
                        print(f"      Concept ID: {concept_id}")
                        print(f"      Concept Name: {concept_name}")
                        print(f"      Stage: {stage.get('name')}")
                        print(f"      Module: {module.get('name')}")
                        
                        return roadmap_id, concept_id, concept_name
        
        print(f"   ❌ 未找到包含 Concept 的 Roadmap")
        print(f"   提示: 请先运行 test_roadmap_generation.py 创建一个完整的 Roadmap")
        sys.exit(1)
        
    except Exception as e:
        print(f"   ❌ 查询异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def generate_single_concept_content(
    client: httpx.AsyncClient,
    token: str,
    roadmap_id: str,
    concept_id: str,
    force_regenerate: bool = False,
) -> dict:
    """
    调用单 Concept 内容生成接口
    
    Returns:
        生成结果数据
    """
    print(f"\n{'='*70}")
    print(f"🚀 步骤3: 生成单 Concept 内容")
    print(f"{'='*70}")
    print(f"   Roadmap ID: {roadmap_id}")
    print(f"   Concept ID: {concept_id}")
    print(f"   Force Regenerate: {force_regenerate}")
    
    request_data = {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "force_regenerate": force_regenerate,
    }
    
    try:
        print(f"\n   ⏳ 正在调用 API...")
        start_time = datetime.now()
        
        response = await client.post(
            "/api/v1/content/subgraph/generate-single-concept",
            json=request_data,
            headers={"Authorization": f"Bearer {token}"},
            timeout=300.0,  # 5分钟超时
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        if response.status_code != 200:
            print(f"   ❌ API 调用失败: HTTP {response.status_code}")
            print(f"   响应: {response.text}")
            sys.exit(1)
        
        result = response.json()
        
        # ✅ 适配新的 ResponseModel 格式 (code, msg, data)
        if result.get("code") != 200:
            print(f"   ❌ 生成失败: {result.get('msg')}")
            print(f"   详情: {result}")
            sys.exit(1)
        
        data = result.get("data", {})
        
        # Celery 异步任务：返回任务 ID
        if "celery_task_id" in data:
            celery_task_id = data.get("celery_task_id")
            print(f"   ✅ 任务已提交到 Celery")
            print(f"   耗时: {elapsed:.2f}秒")
            print(f"   Celery Task ID: {celery_task_id}")
            print(f"   状态: {data.get('status')}")
            print(f"   消息: {data.get('message')}")
            
            # 返回任务信息（用于后续轮询）
            return {
                "celery_task_id": celery_task_id,
                "roadmap_id": data.get("roadmap_id"),
                "concept_id": data.get("concept_id"),
                "status": data.get("status"),
            }
        else:
            # 同步模式（旧逻辑，兼容）
            print(f"   ✅ 内容生成成功")
            print(f"   耗时: {elapsed:.2f}秒")
            return data
        
    except httpx.TimeoutException:
        print(f"   ❌ 请求超时（超过5分钟）")
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def poll_task_status(
    client: httpx.AsyncClient,
    token: str,
    celery_task_id: str,
    max_attempts: int = 60,
) -> dict:
    """
    轮询 Celery 任务状态
    
    Args:
        client: HTTP 客户端
        token: 认证 Token
        celery_task_id: Celery 任务 ID
        max_attempts: 最大轮询次数（默认 60 次，10 分钟）
        
    Returns:
        任务结果
    """
    print(f"\n{'='*70}")
    print(f"⏳ 步骤4: 轮询任务状态")
    print(f"{'='*70}")
    print(f"   Celery Task ID: {celery_task_id}")
    print(f"   最大轮询次数: {max_attempts}")
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.get(
                f"/api/v1/content/subgraph/task/{celery_task_id}/status",
                headers={"Authorization": f"Bearer {token}"},
            )
            
            if response.status_code != 200:
                print(f"   ❌ 查询状态失败: HTTP {response.status_code}")
                await asyncio.sleep(10)
                continue
            
            result = response.json()
            data = result.get("data", {})
            
            task_status = data.get("status")
            
            print(f"   [{attempt}/{max_attempts}] 状态: {task_status}", end="\r")
            
            if task_status == "SUCCESS":
                task_result = data.get("result", {})
                print(f"\n   ✅ 任务执行成功")
                return task_result
            
            elif task_status == "FAILURE":
                error = data.get("error", "Unknown error")
                print(f"\n   ❌ 任务执行失败")
                print(f"   错误: {error}")
                sys.exit(1)
            
            elif task_status in ["PENDING", "STARTED", "RETRY"]:
                await asyncio.sleep(10)  # 每 10 秒查询一次
            
            else:
                print(f"\n   ⚠️  未知状态: {task_status}")
                await asyncio.sleep(10)
                
        except Exception as e:
            print(f"\n   ⚠️  查询异常: {e}")
            await asyncio.sleep(10)
    
    print(f"\n   ❌ 轮询超时（{max_attempts * 10} 秒）")
    sys.exit(1)


def display_generation_result(result: dict):
    """
    显示生成结果
    """
    print(f"\n{'='*70}")
    print(f"📊 步骤5: 生成结果详情")
    print(f"{'='*70}")
    
    # Celery 任务结果格式
    if "save_status" in result:
        save_status = result.get("save_status", {})
        
        print(f"\n   基本信息:")
        print(f"   - Roadmap ID: {result.get('roadmap_id')}")
        print(f"   - Concept ID: {result.get('concept_id')}")
        print(f"   - 执行成功: {'✅ 是' if result.get('success') else '❌ 否'}")
        
        # 解析 save_status（可能是嵌套的）
        if isinstance(save_status, dict):
            actual_status = save_status.get("save_status", save_status)
            
            print(f"\n   保存状态:")
            print(f"   - Tutorial: {actual_status.get('tutorial', 'N/A')}")
            print(f"   - Resource: {actual_status.get('resource', 'N/A')}")
            print(f"   - Quiz: {actual_status.get('quiz', 'N/A')}")
            print(f"   - 元数据已保存: {'✅ 是' if actual_status.get('metadata_saved') else '❌ 否'}")
        
        return
    
    # 旧格式兼容（同步模式）
    concept_id = result.get("concept_id")
    concept_name = result.get("concept_name")
    saved = result.get("saved", False)
    
    print(f"\n   基本信息:")
    print(f"   - Concept ID: {concept_id}")
    print(f"   - Concept Name: {concept_name}")
    print(f"   - 已保存: {'✅ 是' if saved else '❌ 否'}")
    
    # 教程内容
    tutorial = result.get("tutorial")
    if tutorial:
        print(f"\n   📝 教程内容:")
        print(f"      - 标题: {tutorial.get('title', 'N/A')}")
        print(f"      - 估计时长: {tutorial.get('estimated_hours', 0):.1f}小时")
        print(f"      - 难度: {tutorial.get('difficulty_level', 'N/A')}")
        
        content = tutorial.get("content", {})
        if content:
            print(f"      - 概述长度: {len(content.get('overview', '')) if content.get('overview') else 0} 字符")
            
            key_points = content.get("key_points", [])
            print(f"      - 核心要点数: {len(key_points)}")
            if key_points:
                print(f"        示例: {key_points[0][:50]}..." if len(key_points[0]) > 50 else f"        示例: {key_points[0]}")
            
            practical_applications = content.get("practical_applications", [])
            print(f"      - 实战应用数: {len(practical_applications)}")
            if practical_applications:
                app = practical_applications[0]
                print(f"        示例: {app.get('scenario', 'N/A')[:50]}...")
            
            examples = content.get("examples", [])
            print(f"      - 示例代码数: {len(examples)}")
            
            common_pitfalls = content.get("common_pitfalls", [])
            print(f"      - 常见陷阱数: {len(common_pitfalls)}")
    
    # 学习资源
    resources = result.get("resources", {})
    if resources:
        print(f"\n   🔗 学习资源:")
        
        official_docs = resources.get("official_docs", [])
        print(f"      - 官方文档数: {len(official_docs)}")
        if official_docs:
            doc = official_docs[0]
            print(f"        示例: {doc.get('title', 'N/A')} - {doc.get('url', 'N/A')[:50]}...")
        
        tutorials = resources.get("tutorials", [])
        print(f"      - 教程资源数: {len(tutorials)}")
        
        videos = resources.get("videos", [])
        print(f"      - 视频资源数: {len(videos)}")
        
        practice_sites = resources.get("practice_sites", [])
        print(f"      - 练习网站数: {len(practice_sites)}")
    
    # 测验
    quiz = result.get("quiz")
    if quiz:
        print(f"\n   ❓ 测验:")
        
        questions = quiz.get("questions", [])
        print(f"      - 题目数: {len(questions)}")
        
        if questions:
            q = questions[0]
            print(f"      - 示例题目:")
            print(f"        类型: {q.get('question_type', 'N/A')}")
            print(f"        难度: {q.get('difficulty', 'N/A')}")
            print(f"        问题: {q.get('question_text', 'N/A')[:80]}...")


async def verify_saved_content(
    client: httpx.AsyncClient,
    token: str,
    roadmap_id: str,
    concept_id: str,
):
    """
    验证内容是否已保存到数据库
    """
    print(f"\n{'='*70}")
    print(f"🔍 步骤5: 验证数据库保存状态")
    print(f"{'='*70}")
    
    try:
        # 查询 Concept 状态
        response = await client.get(
            f"/api/v1/content/{roadmap_id}/concept-status/{concept_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        
        if response.status_code != 200:
            print(f"   ⚠️ 查询状态失败: HTTP {response.status_code}")
            return
        
        result = response.json()
        status_data = result.get("data", {})
        
        print(f"   ✅ 状态查询成功:")
        print(f"      - Concept ID: {status_data.get('concept_id')}")
        print(f"      - Status: {status_data.get('status')}")
        print(f"      - 有教程: {'✅' if status_data.get('has_tutorial') else '❌'}")
        print(f"      - 有资源: {'✅' if status_data.get('has_resources') else '❌'}")
        print(f"      - 有测验: {'✅' if status_data.get('has_quiz') else '❌'}")
        print(f"      - 错误信息: {status_data.get('error_message', 'N/A')}")
        
    except Exception as e:
        print(f"   ⚠️ 验证异常: {e}")


# ============================================================
# 主函数
# ============================================================

async def main():
    """主测试流程"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="测试单 Concept 内容生成 API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 自动模式（推荐）
  python scripts/test_single_concept_generation.py --auto
  
  # 手动指定 Roadmap 和 Concept
  python scripts/test_single_concept_generation.py \\
    --roadmap-id roadmap_abc123 \\
    --concept-id C-1-1-1
  
  # 强制重新生成
  python scripts/test_single_concept_generation.py \\
    --roadmap-id roadmap_abc123 \\
    --concept-id C-1-1-1 \\
    --force-regenerate
        """
    )
    
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自动查找可用的 Roadmap 和 Concept"
    )
    parser.add_argument(
        "--roadmap-id",
        type=str,
        help="Roadmap ID"
    )
    parser.add_argument(
        "--concept-id",
        type=str,
        help="Concept ID (格式: C-<stage>-<module>-<concept>)"
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="强制重新生成（即使已存在）"
    )
    
    args = parser.parse_args()
    
    # 验证参数
    if not args.auto and (not args.roadmap_id or not args.concept_id):
        parser.error("必须提供 --auto 或同时提供 --roadmap-id 和 --concept-id")
    
    print(f"\n{'#'*70}")
    print(f"# 单 Concept 内容生成 API 测试脚本")
    print(f"# 服务地址: {FASTAPI_BASE_URL}")
    print(f"# 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'#'*70}")
    
    # 创建HTTP客户端
    async with httpx.AsyncClient(
        base_url=FASTAPI_BASE_URL,
        timeout=30.0,
    ) as client:
        try:
            # 步骤1: 登录
            token = await login_and_get_token(client)
            
            # 步骤2: 获取 roadmap_id 和 concept_id
            if args.auto:
                roadmap_id, concept_id, concept_name = await find_available_roadmap_and_concept(
                    client, token
                )
            else:
                roadmap_id = args.roadmap_id
                concept_id = args.concept_id
                concept_name = "Unknown"
            
            # 步骤3: 生成内容（提交 Celery 任务）
            task_info = await generate_single_concept_content(
                client,
                token,
                roadmap_id,
                concept_id,
                force_regenerate=args.force_regenerate,
            )
            
            # 步骤4: 轮询任务状态（如果是 Celery 异步模式）
            if "celery_task_id" in task_info:
                result = await poll_task_status(
                    client=client,
                    token=token,
                    celery_task_id=task_info["celery_task_id"],
                    max_attempts=60,  # 最多轮询 10 分钟
                )
            else:
                # 同步模式（旧逻辑）
                result = task_info
            
            # 步骤5: 显示结果
            display_generation_result(result)
            
            # 步骤6: 验证保存状态
            await verify_saved_content(client, token, roadmap_id, concept_id)
            
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
    asyncio.run(main())

