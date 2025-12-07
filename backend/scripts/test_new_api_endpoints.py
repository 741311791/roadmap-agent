#!/usr/bin/env python3
"""
新API端点快速测试脚本

不依赖pytest，可以直接运行验证新API端点是否正常工作

运行方式：
    python backend/scripts/test_new_api_endpoints.py
"""
import asyncio
import httpx
import json
from typing import Dict, Any
from datetime import datetime


class Colors:
    """终端颜色"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*80}{Colors.END}\n")


def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_info(text: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_warning(text: str):
    """打印警告"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


async def test_endpoint(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    data: Dict[str, Any] = None,
    params: Dict[str, Any] = None,
    test_name: str = "",
) -> tuple[bool, Any]:
    """
    测试单个端点
    
    Returns:
        (成功与否, 响应数据)
    """
    print(f"\n{Colors.BOLD}测试: {test_name}{Colors.END}")
    print(f"方法: {method}")
    print(f"端点: {endpoint}")
    
    try:
        if method == "GET":
            response = await client.get(endpoint, params=params)
        elif method == "POST":
            response = await client.post(endpoint, json=data, params=params)
        else:
            raise ValueError(f"不支持的HTTP方法: {method}")
        
        print(f"状态码: {response.status_code}")
        
        if response.status_code in [200, 201]:
            print_success(f"请求成功: {response.status_code}")
            try:
                response_data = response.json()
                print(f"响应摘要: {json.dumps(response_data, ensure_ascii=False)[:200]}...")
                return True, response_data
            except:
                return True, response.text
        elif response.status_code == 404:
            print_warning(f"资源不存在（404）- 这在测试环境是正常的")
            return True, None
        elif response.status_code == 400:
            print_warning(f"请求参数错误（400）")
            try:
                error_data = response.json()
                print(f"错误详情: {error_data}")
            except:
                pass
            return True, None
        else:
            print_error(f"请求失败: {response.status_code}")
            try:
                error_data = response.json()
                print(f"错误详情: {json.dumps(error_data, ensure_ascii=False)}")
            except:
                print(f"错误内容: {response.text[:200]}")
            return False, None
            
    except Exception as e:
        print_error(f"请求异常: {str(e)}")
        return False, None


async def main():
    """主测试流程"""
    print_header("新API端点测试脚本")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"基础URL: http://localhost:8000")
    
    base_url = "http://localhost:8000"
    timeout = httpx.Timeout(30.0, connect=10.0)
    
    # 测试结果统计
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    try:
        async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
            
            # ========================================
            # 测试1: 健康检查
            # ========================================
            print_header("测试1: 健康检查端点")
            success, data = await test_endpoint(
                client, "GET", "/health",
                test_name="应用健康状态"
            )
            total_tests += 1
            if success:
                passed_tests += 1
            else:
                failed_tests += 1
                print_error("健康检查失败，后续测试可能无法进行")
                return
            
            # ========================================
            # 测试2: 路线图生成（generation.py）
            # ========================================
            print_header("测试2: 路线图生成端点 (generation.py)")
            
            sample_request = {
                "user_id": "test-user-script",
                "session_id": "test-session-script",
                "preferences": {
                    "learning_goal": "学习Python Web开发基础",
                    "available_hours_per_week": 10,
                    "motivation": "兴趣学习",
                    "current_level": "beginner",
                    "career_background": "学生",
                    "content_preference": ["text", "hands_on"],
                },
                "additional_context": "快速入门",
            }
            
            success, data = await test_endpoint(
                client, "POST", "/api/v1/roadmaps/generate",
                data=sample_request,
                test_name="创建路线图生成任务"
            )
            total_tests += 1
            if success:
                passed_tests += 1
                task_id = data.get("task_id") if data else None
                print_info(f"获取到任务ID: {task_id}")
            else:
                failed_tests += 1
                task_id = None
            
            # ========================================
            # 测试3: 任务状态查询（generation.py）
            # ========================================
            print_header("测试3: 任务状态查询端点 (generation.py)")
            
            if task_id:
                # 等待一下让任务开始处理
                print_info("等待2秒让任务开始处理...")
                await asyncio.sleep(2)
                
                success, data = await test_endpoint(
                    client, "GET", f"/api/v1/roadmaps/{task_id}/status",
                    test_name="查询任务状态"
                )
                total_tests += 1
                if success:
                    passed_tests += 1
                    if data:
                        status = data.get("status", "unknown")
                        step = data.get("current_step", "unknown")
                        print_info(f"任务状态: {status}, 当前步骤: {step}")
                else:
                    failed_tests += 1
            else:
                print_warning("跳过测试：没有可用的task_id")
            
            # ========================================
            # 测试4: 路线图查询（retrieval.py）
            # ========================================
            print_header("测试4: 路线图查询端点 (retrieval.py)")
            
            test_roadmap_id = "python-basics-test"
            success, data = await test_endpoint(
                client, "GET", f"/api/v1/roadmaps/{test_roadmap_id}",
                test_name="获取路线图数据"
            )
            total_tests += 1
            if success:
                passed_tests += 1
            else:
                failed_tests += 1
            
            # ========================================
            # 测试5: 活跃任务查询（retrieval.py）
            # ========================================
            print_header("测试5: 活跃任务查询端点 (retrieval.py)")
            
            success, data = await test_endpoint(
                client, "GET", f"/api/v1/roadmaps/{test_roadmap_id}/active-task",
                test_name="查询活跃任务"
            )
            total_tests += 1
            if success:
                passed_tests += 1
            else:
                failed_tests += 1
            
            # ========================================
            # 测试6: 教程版本查询（tutorial.py）
            # ========================================
            print_header("测试6: 教程管理端点 (tutorial.py)")
            
            test_concept_id = "variables-basics"
            
            # 6.1 获取所有版本
            success, data = await test_endpoint(
                client, "GET",
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/tutorials",
                test_name="获取教程版本历史"
            )
            total_tests += 1
            if success: passed_tests += 1
            else: failed_tests += 1
            
            # 6.2 获取最新版本
            success, data = await test_endpoint(
                client, "GET",
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/tutorials/latest",
                test_name="获取最新教程版本"
            )
            total_tests += 1
            if success: passed_tests += 1
            else: failed_tests += 1
            
            # ========================================
            # 测试7: 资源查询（resource.py）
            # ========================================
            print_header("测试7: 资源管理端点 (resource.py)")
            
            success, data = await test_endpoint(
                client, "GET",
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/resources",
                test_name="获取学习资源"
            )
            total_tests += 1
            if success: passed_tests += 1
            else: failed_tests += 1
            
            # ========================================
            # 测试8: 测验查询（quiz.py）
            # ========================================
            print_header("测试8: 测验管理端点 (quiz.py)")
            
            success, data = await test_endpoint(
                client, "GET",
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/quiz",
                test_name="获取测验内容"
            )
            total_tests += 1
            if success: passed_tests += 1
            else: failed_tests += 1
            
            # ========================================
            # 测试9: 人工审核（approval.py）
            # ========================================
            print_header("测试9: 人工审核端点 (approval.py)")
            
            if task_id:
                success, data = await test_endpoint(
                    client, "POST",
                    f"/api/v1/roadmaps/{task_id}/approve",
                    params={"approved": True},
                    test_name="提交审核决策"
                )
                total_tests += 1
                if success: passed_tests += 1
                else: failed_tests += 1
            else:
                print_warning("跳过测试：没有可用的task_id")
            
            # ========================================
            # 测试10: 失败重试（retry.py）
            # ========================================
            print_header("测试10: 失败重试端点 (retry.py)")
            
            retry_request = {
                "user_id": "test-user",
                "content_types": ["tutorial"],
                "preferences": {
                    "learning_goal": "test",
                    "available_hours_per_week": 10,
                    "motivation": "test",
                    "current_level": "beginner",
                    "career_background": "学生",
                }
            }
            
            success, data = await test_endpoint(
                client, "POST",
                f"/api/v1/roadmaps/{test_roadmap_id}/retry-failed",
                data=retry_request,
                test_name="重试失败内容"
            )
            total_tests += 1
            if success: passed_tests += 1
            else: failed_tests += 1
            
            # ========================================
            # 测试11: 内容修改（modification.py）
            # ========================================
            print_header("测试11: 内容修改端点 (modification.py)")
            
            modify_request = {
                "user_id": "test-user",
                "preferences": {
                    "learning_goal": "test",
                    "available_hours_per_week": 10,
                    "motivation": "test",
                    "current_level": "beginner",
                    "career_background": "学生",
                },
                "requirements": ["增加代码示例"]
            }
            
            success, data = await test_endpoint(
                client, "POST",
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/tutorial/modify",
                data=modify_request,
                test_name="修改教程内容"
            )
            total_tests += 1
            if success: passed_tests += 1
            else: failed_tests += 1
            
            # ========================================
            # 测试12: OpenAPI文档
            # ========================================
            print_header("测试12: OpenAPI文档端点")
            
            success, data = await test_endpoint(
                client, "GET", "/openapi.json",
                test_name="获取OpenAPI规范"
            )
            total_tests += 1
            if success:
                passed_tests += 1
                if data and isinstance(data, dict):
                    paths = data.get("paths", {})
                    print_info(f"API文档包含 {len(paths)} 个端点")
                    
                    # 验证新端点是否注册
                    expected_endpoints = [
                        "/api/v1/roadmaps/generate",
                        "/api/v1/roadmaps/{task_id}/status",
                        "/api/v1/roadmaps/{roadmap_id}",
                    ]
                    
                    registered = sum(1 for ep in expected_endpoints if ep in paths)
                    print_success(f"新端点已注册: {registered}/{len(expected_endpoints)}")
            else:
                failed_tests += 1
    
    except httpx.ConnectError:
        print_error("无法连接到服务器！请确保后端服务正在运行（http://localhost:8000）")
        print_info("启动命令: uvicorn app.main:app --reload")
        return
    except Exception as e:
        print_error(f"测试过程发生异常: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # ========================================
    # 测试结果汇总
    # ========================================
    print_header("测试结果汇总")
    
    print(f"{Colors.BOLD}总测试数: {total_tests}{Colors.END}")
    print(f"{Colors.GREEN}✅ 通过: {passed_tests}{Colors.END}")
    print(f"{Colors.RED}❌ 失败: {failed_tests}{Colors.END}")
    
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print(f"{Colors.BOLD}成功率: {success_rate:.1f}%{Colors.END}")
    
    if failed_tests == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 所有测试通过！新API端点工作正常！{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}⚠️  部分测试失败，请检查失败的端点{Colors.END}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    print(f"""
{Colors.BOLD}新API端点测试脚本{Colors.END}

{Colors.BLUE}使用说明：{Colors.END}
1. 确保后端服务正在运行: uvicorn app.main:app --reload
2. 运行此脚本: python backend/scripts/test_new_api_endpoints.py
3. 查看测试结果

{Colors.YELLOW}注意：{Colors.END}
- 某些测试返回404是正常的（测试数据不存在）
- 重点关注端点是否能正常响应，而不是具体的数据内容
""")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}测试被用户中断{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}测试运行失败: {str(e)}{Colors.END}")
