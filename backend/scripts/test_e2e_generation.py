#!/usr/bin/env python3
"""
端到端测试：完整的路线图生成流程（使用标准库）

测试流程：
1. 发起路线图生成请求
2. 监听任务状态变化
3. 验证每个阶段是否成功
4. 检查最终生成的路线图数据
"""
import asyncio
import sys
import os
import time
import json
from datetime import datetime
from urllib import request, parse, error

# 配置
BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"
TIMEOUT = 300  # 5 分钟超时

# 测试数据
TEST_USER_REQUEST = {
    "user_id": f"test-user-{int(time.time())}",
    "session_id": f"test-session-{int(time.time())}",
    "preferences": {
        "learning_goal": "学习 Python Web 开发，掌握 FastAPI 框架和异步编程",
        "available_hours_per_week": 10,
        "motivation": "职业发展",
        "current_level": "intermediate",
        "career_background": "后端开发 2 年经验",
        "content_preference": ["text", "hands_on"],
        "preferred_language": "zh"
    }
}


class Colors:
    """终端颜色"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}\n")


def print_success(text: str):
    """打印成功信息"""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text: str):
    """打印错误信息"""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text: str):
    """打印警告信息"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text: str):
    """打印信息"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")


def print_step(text: str):
    """打印步骤"""
    print(f"{Colors.CYAN}➤ {text}{Colors.END}")


def http_get(url: str, timeout: int = 10) -> tuple[bool, dict | None]:
    """发送 GET 请求"""
    try:
        req = request.Request(url, method='GET')
        req.add_header('Content-Type', 'application/json')
        
        with request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                return True, data
            else:
                return False, None
    except error.HTTPError as e:
        print_error(f"HTTP Error {e.code}: {e.reason}")
        return False, None
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False, None


def http_post(url: str, data: dict, timeout: int = 30) -> tuple[bool, dict | None]:
    """发送 POST 请求"""
    try:
        json_data = json.dumps(data).encode('utf-8')
        req = request.Request(url, data=json_data, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        with request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                response_data = json.loads(response.read().decode('utf-8'))
                return True, response_data
            else:
                return False, None
    except error.HTTPError as e:
        print_error(f"HTTP Error {e.code}: {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            print_error(f"响应: {error_body}")
        except:
            pass
        return False, None
    except Exception as e:
        print_error(f"请求失败: {e}")
        return False, None


def test_health_check() -> bool:
    """测试健康检查端点"""
    print_step("测试后端服务健康状态...")
    
    try:
        req = request.Request(f"{BASE_URL}/health", method='GET')
        with request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print_success("后端服务运行正常")
                return True
            else:
                print_error(f"健康检查失败: HTTP {response.status}")
                return False
    except error.URLError as e:
        print_error(f"无法连接到后端服务: {e.reason}")
        print_info(f"请确保后端服务已启动在端口 8000")
        print_info(f"命令: cd backend && uv run uvicorn app.main:app --reload")
        return False
    except Exception as e:
        print_error(f"健康检查失败: {e}")
        return False


def create_roadmap_task() -> tuple[bool, str | None]:
    """创建路线图生成任务"""
    print_step("发起路线图生成请求...")
    print_info(f"学习目标: {TEST_USER_REQUEST['preferences']['learning_goal']}")
    
    success, data = http_post(f"{API_V1}/roadmaps/generate", TEST_USER_REQUEST)
    
    if success and data:
        task_id = data.get("task_id")
        print_success(f"任务创建成功")
        print_info(f"Task ID: {task_id}")
        return True, task_id
    else:
        print_error("任务创建失败")
        return False, None


def poll_task_status(task_id: str) -> tuple[bool, dict | None]:
    """轮询任务状态直到完成或失败"""
    print_step("监听任务进度...")
    
    start_time = time.time()
    last_step = None
    step_times = {}
    
    while True:
        # 检查超时
        elapsed = time.time() - start_time
        if elapsed > TIMEOUT:
            print_error(f"任务超时 ({TIMEOUT}秒)")
            return False, None
        
        # 获取任务状态
        success, data = http_get(f"{API_V1}/roadmaps/{task_id}/status")
        
        if not success:
            print_error("获取任务状态失败")
            return False, None
        
        status = data.get("status")
        current_step = data.get("current_step")
        error_msg = data.get("error_message")
        roadmap_id = data.get("roadmap_id")
        
        # 记录步骤变化
        if current_step != last_step:
            if last_step:
                step_duration = time.time() - step_times[last_step]
                print_success(f"步骤 '{last_step}' 完成 (耗时: {step_duration:.1f}秒)")
            
            if current_step and current_step != "failed":
                print_info(f"当前步骤: {current_step}")
                step_times[current_step] = time.time()
            
            last_step = current_step
        
        # 检查终止状态
        if status == "completed":
            total_time = time.time() - start_time
            print_success(f"任务完成！(总耗时: {total_time:.1f}秒)")
            print_info(f"Roadmap ID: {roadmap_id}")
            
            # 打印步骤耗时统计
            if step_times:
                print("\n步骤耗时统计:")
                for step in step_times:
                    # 计算该步骤的实际耗时
                    duration = 0
                    if step in step_times:
                        duration = time.time() - step_times[step]
                    print(f"  {step:30s} ~{duration:6.1f}秒")
            
            return True, data
        
        elif status == "failed":
            print_error(f"任务失败")
            print_error(f"失败步骤: {current_step}")
            print_error(f"错误信息: {error_msg}")
            return False, data
        
        # 等待后再次查询
        time.sleep(2)


def verify_roadmap(roadmap_id: str) -> bool:
    """验证路线图数据"""
    print_step("验证路线图数据...")
    
    success, roadmap = http_get(f"{API_V1}/roadmaps/{roadmap_id}")
    
    if not success:
        print_error("获取路线图失败")
        return False
    
    # 验证基本字段
    checks = {
        "roadmap_id 匹配": roadmap.get("roadmap_id") == roadmap_id,
        "title 存在": bool(roadmap.get("title")),
        "stages 存在": bool(roadmap.get("stages")),
        "stages 数量 > 0": len(roadmap.get("stages", [])) > 0,
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        if passed:
            print_success(f"{check_name}")
        else:
            print_error(f"{check_name}")
            all_passed = False
    
    # 详细信息
    if all_passed:
        stages = roadmap.get("stages", [])
        total_modules = sum(len(stage.get("modules", [])) for stage in stages)
        total_concepts = sum(
            len(module.get("concepts", []))
            for stage in stages
            for module in stage.get("modules", [])
        )
        
        print_info(f"路线图标题: {roadmap.get('title')}")
        print_info(f"阶段数量: {len(stages)}")
        print_info(f"模块总数: {total_modules}")
        print_info(f"概念总数: {total_concepts}")
    
    return all_passed


def run_e2e_test() -> bool:
    """运行完整的端到端测试"""
    print_header("路线图生成端到端测试")
    
    test_start = datetime.now()
    results = {}
    
    # 1. 健康检查
    print_header("阶段 1: 健康检查")
    health_ok = test_health_check()
    results["health_check"] = health_ok
    
    if not health_ok:
        print_error("健康检查失败，终止测试")
        return False
    
    # 2. 创建任务
    print_header("阶段 2: 创建生成任务")
    create_ok, task_id = create_roadmap_task()
    results["create_task"] = create_ok
    
    if not create_ok:
        print_error("任务创建失败，终止测试")
        return False
    
    # 3. 监听任务进度
    print_header("阶段 3: 监听任务进度")
    poll_ok, task_data = poll_task_status(task_id)
    results["task_execution"] = poll_ok
    
    if not poll_ok:
        print_error("任务执行失败")
        
        # 打印详细错误信息
        if task_data:
            print_info("任务详情:")
            print(json.dumps(task_data, indent=2, ensure_ascii=False))
        
        return False
    
    # 4. 验证路线图
    print_header("阶段 4: 验证路线图数据")
    roadmap_id = task_data.get("roadmap_id")
    
    if not roadmap_id:
        print_error("未获取到 roadmap_id")
        results["verify_roadmap"] = False
        return False
    
    verify_ok = verify_roadmap(roadmap_id)
    results["verify_roadmap"] = verify_ok
    
    # 测试总结
    print_header("测试总结")
    
    test_end = datetime.now()
    total_duration = (test_end - test_start).total_seconds()
    
    print(f"测试开始时间: {test_start.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试结束时间: {test_end.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {total_duration:.1f} 秒")
    print()
    
    print("测试结果:")
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name:30s} {status}")
    
    all_passed = all(results.values())
    
    print()
    if all_passed:
        print_success("🎉 所有测试通过！系统运行正常。")
        print_info(f"生成的路线图 ID: {roadmap_id}")
        print_info(f"访问地址: http://localhost:3000/app/roadmap/{roadmap_id}")
        return True
    else:
        print_error("部分测试失败，请检查后端日志")
        return False


def main():
    """主函数"""
    try:
        success = run_e2e_test()
        return 0 if success else 1
    except KeyboardInterrupt:
        print_warning("\n\n测试被用户中断")
        return 130
    except Exception as e:
        print_error(f"\n\n测试执行异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
