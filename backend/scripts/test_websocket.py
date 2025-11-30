"""
WebSocket 实时推送功能测试脚本

测试功能：
1. 创建后台任务（/generate）
2. 通过 WebSocket 订阅任务进度
3. 验证各阶段事件是否正确推送

运行方式:
    # 确保后端服务正在运行
    cd backend
    uv run python scripts/test_websocket.py
    
    # 或者指定任务 ID 来订阅已有任务
    uv run python scripts/test_websocket.py --task-id <task_id>
"""
import asyncio
import aiohttp
import json
import sys
import argparse
import os
from pathlib import Path
from datetime import datetime

# 禁用代理，避免代理问题
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


# 颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{'=' * 70}")
    print(f"{text}")
    print(f"{'=' * 70}{Colors.END}\n")


def print_event(event: dict):
    """格式化打印事件"""
    event_type = event.get("type", "unknown")
    timestamp = event.get("timestamp", "")
    
    # 根据事件类型选择颜色
    color = Colors.BLUE
    icon = "📢"
    
    if event_type == "connected":
        color = Colors.GREEN
        icon = "🔗"
    elif event_type == "progress":
        step = event.get("step", "")
        status = event.get("status", "")
        if status == "completed":
            color = Colors.GREEN
            icon = "✅"
        else:
            color = Colors.CYAN
            icon = "⏳"
    elif event_type == "human_review_required":
        color = Colors.YELLOW
        icon = "👀"
    elif event_type == "completed":
        color = Colors.GREEN
        icon = "🎉"
    elif event_type == "failed":
        color = Colors.RED
        icon = "❌"
    elif event_type == "error":
        color = Colors.RED
        icon = "⚠️"
    elif event_type == "current_status":
        color = Colors.DIM
        icon = "📊"
    elif event_type == "pong":
        color = Colors.DIM
        icon = "💓"
    elif event_type == "closing":
        color = Colors.YELLOW
        icon = "👋"
    
    # 格式化输出
    print(f"{color}{icon} [{event_type}]{Colors.END}", end=" ")
    
    if event_type == "progress":
        step = event.get("step", "")
        status = event.get("status", "")
        message = event.get("message", "")
        print(f"{Colors.BOLD}{step}{Colors.END} - {status}")
        if message:
            print(f"   {Colors.DIM}{message}{Colors.END}")
        if event.get("data"):
            print(f"   {Colors.DIM}data: {json.dumps(event['data'], ensure_ascii=False)[:100]}{Colors.END}")
    
    elif event_type == "human_review_required":
        roadmap_title = event.get("roadmap_title", "")
        stages_count = event.get("stages_count", 0)
        print(f"{Colors.BOLD}{roadmap_title}{Colors.END}")
        print(f"   阶段数: {stages_count}")
        print(f"   {Colors.YELLOW}请通过 /approve 端点提交审核结果{Colors.END}")
    
    elif event_type == "completed":
        roadmap_id = event.get("roadmap_id", "")
        tutorials_count = event.get("tutorials_count", 0)
        failed_count = event.get("failed_count", 0)
        print(f"路线图 ID: {Colors.BOLD}{roadmap_id}{Colors.END}")
        if tutorials_count:
            print(f"   教程数: {tutorials_count}, 失败: {failed_count}")
    
    elif event_type == "failed":
        error = event.get("error", "")
        step = event.get("step", "")
        print(f"{Colors.RED}{error[:100]}{Colors.END}")
        if step:
            print(f"   失败步骤: {step}")
    
    elif event_type == "current_status":
        status = event.get("status", "")
        step = event.get("current_step", "")
        print(f"状态: {status}, 步骤: {step}")
    
    elif event_type == "connected":
        print(event.get("message", ""))
    
    elif event_type == "closing":
        print(event.get("message", ""))
    
    else:
        # 通用处理
        message = event.get("message", "")
        if message:
            print(message)
        else:
            print(json.dumps(event, ensure_ascii=False)[:100])


async def create_task(base_url: str) -> str:
    """
    创建一个简单的路线图生成任务
    
    Returns:
        task_id
    """
    # 使用非常简单的学习目标，确保只生成 1 个 Stage 和少量 Concept
    test_request = {
        "user_id": "test-ws-user",
        "session_id": "test-ws-session",
        "preferences": {
            # 简单目标：只学习一个小知识点
            "learning_goal": "学习Python的print函数基础用法",
            "available_hours_per_week": 2,  # 每周只有2小时
            "motivation": "兴趣",
            "current_level": "beginner",
            "career_background": "学生",
            "content_preference": ["text"]
        },
        "additional_context": "只需要一个阶段，包含1-2个概念即可，不需要太详细"
    }
    
    url = f"{base_url}/api/v1/roadmaps/generate"
    
    print(f"{Colors.CYAN}📤 创建任务...{Colors.END}")
    print(f"   目标: {test_request['preferences']['learning_goal']}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json=test_request,
            headers={"Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status != 200:
                text = await response.text()
                print(f"{Colors.RED}❌ 创建任务失败: HTTP {response.status}{Colors.END}")
                print(text)
                raise Exception("创建任务失败")
            
            result = await response.json()
            task_id = result.get("task_id")
            
            print(f"{Colors.GREEN}✅ 任务创建成功{Colors.END}")
            print(f"   Task ID: {Colors.BOLD}{task_id}{Colors.END}")
            
            return task_id


async def subscribe_websocket(
    ws_url: str,
    task_id: str,
    include_history: bool = True,
    timeout_seconds: int = 300,
):
    """
    订阅 WebSocket 事件
    
    Args:
        ws_url: WebSocket 基础 URL
        task_id: 任务 ID
        include_history: 是否请求历史状态
        timeout_seconds: 超时时间
    """
    full_url = f"{ws_url}/api/v1/ws/{task_id}?include_history={str(include_history).lower()}"
    
    print(f"\n{Colors.CYAN}🔌 连接 WebSocket...{Colors.END}")
    print(f"   URL: {full_url}")
    
    event_count = 0
    start_time = datetime.now()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(full_url) as ws:
                print(f"{Colors.GREEN}✅ WebSocket 连接成功{Colors.END}\n")
                
                # 发送心跳检测
                await ws.send_str(json.dumps({"type": "ping"}))
                
                # 监听事件
                while True:
                    try:
                        # 设置接收超时
                        msg = await asyncio.wait_for(
                            ws.receive(),
                            timeout=timeout_seconds
                        )
                        
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            event = json.loads(msg.data)
                            event_count += 1
                            
                            # 打印事件
                            print_event(event)
                            
                            # 检查是否是终止事件
                            event_type = event.get("type")
                            if event_type in ("completed", "failed", "closing"):
                                print(f"\n{Colors.DIM}连接即将关闭...{Colors.END}")
                                break
                            
                            # 如果是人工审核请求，提示用户
                            if event_type == "human_review_required":
                                print(f"\n{Colors.YELLOW}💡 提示: 任务在等待人工审核{Colors.END}")
                                print(f"   可以使用以下命令批准:")
                                print(f"   curl -X POST 'http://localhost:8000/api/v1/roadmaps/{task_id}/approve?approved=true'")
                                print(f"\n{Colors.DIM}继续监听事件...按 Ctrl+C 退出{Colors.END}\n")
                        
                        elif msg.type == aiohttp.WSMsgType.CLOSED:
                            print(f"\n{Colors.YELLOW}🔌 WebSocket 连接已关闭{Colors.END}")
                            break
                        
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            print(f"\n{Colors.RED}❌ WebSocket 错误: {ws.exception()}{Colors.END}")
                            break
                    
                    except asyncio.TimeoutError:
                        print(f"\n{Colors.YELLOW}⏰ 接收超时 ({timeout_seconds}s){Colors.END}")
                        break
    
    except aiohttp.ClientError as e:
        print(f"\n{Colors.RED}❌ 连接错误: {e}{Colors.END}")
        raise
    
    except Exception as e:
        print(f"\n{Colors.RED}❌ WebSocket 错误: {e}{Colors.END}")
        raise
    
    finally:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n{Colors.DIM}{'─' * 50}{Colors.END}")
        print(f"📊 {Colors.BOLD}统计{Colors.END}")
        print(f"   接收事件数: {event_count}")
        print(f"   总耗时: {elapsed:.1f}s")


async def test_websocket_full(
    http_url: str = "http://localhost:8000",
    ws_url: str = "ws://localhost:8000",
    task_id: str | None = None,
):
    """
    完整的 WebSocket 测试流程
    """
    print_header("🧪 WebSocket 实时推送功能测试")
    
    if task_id:
        print(f"使用已有任务: {Colors.BOLD}{task_id}{Colors.END}")
    else:
        # 创建新任务
        task_id = await create_task(http_url)
    
    # 订阅 WebSocket
    await subscribe_websocket(ws_url, task_id)
    
    print_header("🏁 测试完成")


async def test_websocket_only(
    ws_url: str = "ws://localhost:8000",
    task_id: str = None,
):
    """
    仅测试 WebSocket 订阅（不创建任务）
    """
    if not task_id:
        print(f"{Colors.RED}❌ 请提供 task_id{Colors.END}")
        return
    
    print_header("🔌 WebSocket 订阅测试")
    print(f"订阅任务: {Colors.BOLD}{task_id}{Colors.END}")
    
    await subscribe_websocket(ws_url, task_id)


def main():
    parser = argparse.ArgumentParser(
        description="测试 WebSocket 实时推送功能",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 创建新任务并订阅
    python scripts/test_websocket.py
    
    # 订阅已有任务
    python scripts/test_websocket.py --task-id abc-123-def
    
    # 自定义服务地址
    python scripts/test_websocket.py --http-url http://localhost:8000 --ws-url ws://localhost:8000
        """
    )
    parser.add_argument(
        "--task-id",
        type=str,
        help="已有的任务 ID（如不提供则创建新任务）"
    )
    parser.add_argument(
        "--http-url",
        type=str,
        default="http://localhost:8000",
        help="HTTP API 地址"
    )
    parser.add_argument(
        "--ws-url",
        type=str,
        default="ws://localhost:8000",
        help="WebSocket 地址"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="WebSocket 接收超时时间（秒）"
    )
    
    args = parser.parse_args()
    
    print()
    asyncio.run(test_websocket_full(
        http_url=args.http_url,
        ws_url=args.ws_url,
        task_id=args.task_id,
    ))
    print()


if __name__ == "__main__":
    main()

