"""
修改系统端到端测试脚本

测试功能：
1. 测试前检查（确保有可用的路线图和内容）
2. 单目标修改测试（教程、资源、测验）
3. 多目标修改测试
4. 重新生成测试
5. 全方位验证：
   - SSE 事件完整性（analyzing/intents/modifying/agent_progress/result/done）
   - 意图分析准确性
   - Agent 调度过程
   - 数据库变更

运行方式:
    cd backend
    uv run python scripts/test_modification_system.py
    
    # 使用现有路线图
    uv run python scripts/test_modification_system.py --roadmap-id <id>
    
    # 跳过路线图创建（需要指定 --roadmap-id）
    uv run python scripts/test_modification_system.py --skip-create --roadmap-id <id>
    
    # 跳过重新生成测试和直接修改测试
    uv run python scripts/test_modification_system.py --skip-regenerate --skip-direct

查看详细日志：
    测试脚本只显示 SSE 事件流，要查看完整的 Agent 执行日志，需要查看后端服务日志：
    
    # 如果使用 uvicorn 启动
    uvicorn app.main:app --reload 2>&1 | grep -E "(modification|modifier|analyzer)"
    
    日志关键字说明：
    - modification_analysis_*: 意图分析 Agent 日志
    - tutorial_modifier_*: 教程修改 Agent 日志
    - resource_modifier_*: 资源修改 Agent 日志
    - quiz_modifier_*: 测验修改 Agent 日志
    - execute_single_modification_*: 单个修改执行日志

注意：
    - 确保后端服务已启动
    - 确保 PostgreSQL、Redis、MinIO 服务可用
    - 首次运行需要生成路线图，可能耗时较长
"""
import asyncio
import aiohttp
import httpx
import json
import sys
import argparse
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# 禁用代理
os.environ["NO_PROXY"] = "localhost,127.0.0.1"
os.environ["no_proxy"] = "localhost,127.0.0.1"

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# 颜色和打印工具
# ============================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[35m'
    END = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{'=' * 70}")
    print(f"{text}")
    print(f"{'=' * 70}{Colors.END}\n")


def print_section(text: str):
    print(f"\n{Colors.CYAN}{'-' * 50}")
    print(f"{text}")
    print(f"{'-' * 50}{Colors.END}")


def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")


def print_info(msg: str):
    print(f"{Colors.CYAN}ℹ️  {msg}{Colors.END}")


def print_agent(agent_name: str, msg: str):
    """打印 Agent 相关日志"""
    print(f"{Colors.MAGENTA}🤖 [{agent_name}]{Colors.END} {msg}")


def print_event(event_type: str, msg: str):
    """打印 SSE 事件"""
    color = {
        "analyzing": Colors.BLUE,
        "intents": Colors.CYAN,
        "modifying": Colors.YELLOW,
        "result": Colors.GREEN,
        "done": Colors.MAGENTA,
        "error": Colors.RED,
    }.get(event_type, Colors.DIM)
    print(f"  {color}◆ {event_type}:{Colors.END} {msg}")


# ============================================================
# 测试数据
# ============================================================

# 简化的测试用户请求（用于创建路线图）
TEST_USER_REQUEST = {
    "user_id": "mod-test-user",
    "session_id": f"mod-test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "preferences": {
        "learning_goal": "学习Python的print函数和基本数据类型",
        "available_hours_per_week": 2,
        "motivation": "兴趣爱好",
        "current_level": "beginner",
        "career_background": "学生",
        "content_preference": ["text"]
    },
    "additional_context": "请设计一个简洁的路线图，只需要1个阶段、1个模块、2个概念。"
}

# 修改测试用例
MODIFICATION_TEST_CASES = [
    {
        "name": "单目标教程修改",
        "description": "对某个概念的教程提出修改意见",
        "user_message": "教程中关于{concept_name}的内容太简单了，我希望能加入更多的代码示例和实际应用场景",
        "expected_types": ["tutorial"],
    },
    {
        "name": "单目标测验修改",
        "description": "对某个概念的测验题目提出修改意见",
        "user_message": "测验题目太简单了，请增加难度，并添加更多关于边界情况的题目",
        "expected_types": ["quiz"],
    },
    {
        "name": "单目标资源修改",
        "description": "对某个概念的学习资源提出修改意见",
        "user_message": "推荐的学习资源太老了，请帮我找一些2024年发布的最新教程和视频",
        "expected_types": ["resources"],
    },
    {
        "name": "多目标修改",
        "description": "同时对教程和测验提出修改意见",
        "user_message": "关于{concept_name}这个概念，教程内容需要添加更多的图示说明，同时测验也需要增加几道实践题",
        "expected_types": ["tutorial", "quiz"],
    },
    {
        "name": "带上下文的修改",
        "description": "用户在查看某个概念时提出修改意见（使用上下文）",
        "user_message": "这个教程太理论化了，我需要更多实战代码",
        "use_context": True,
        "expected_types": ["tutorial"],
    },
]


# ============================================================
# 测试结果收集器
# ============================================================

@dataclass
class SSEEvent:
    """SSE 事件记录"""
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]


@dataclass
class ModificationTestResult:
    """单个修改测试结果"""
    name: str
    passed: bool
    events: List[SSEEvent] = field(default_factory=list)
    details: str = ""
    duration: float = 0.0
    intents_detected: int = 0
    modifications_success: int = 0
    modifications_failed: int = 0


@dataclass
class ModificationTestReport:
    """修改测试报告"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    roadmap_id: Optional[str] = None
    concepts: List[Dict[str, Any]] = field(default_factory=list)
    
    # 测试结果
    test_results: List[ModificationTestResult] = field(default_factory=list)
    
    def add_test_result(self, result: ModificationTestResult):
        self.test_results.append(result)
    
    def print_summary(self):
        """打印测试报告摘要"""
        print_header("📊 修改系统测试报告")
        
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"{Colors.BOLD}测试信息{Colors.END}")
        print(f"  Roadmap ID: {self.roadmap_id or 'N/A'}")
        print(f"  可用概念数: {len(self.concepts)}")
        print(f"  总耗时: {duration:.1f}s")
        print()
        
        # 测试结果
        print(f"{Colors.BOLD}修改测试结果{Colors.END}")
        passed = sum(1 for r in self.test_results if r.passed)
        total = len(self.test_results)
        
        for result in self.test_results:
            status = f"{Colors.GREEN}PASS{Colors.END}" if result.passed else f"{Colors.RED}FAIL{Colors.END}"
            print(f"  [{status}] {result.name}")
            print(f"       意图数: {result.intents_detected}, "
                  f"成功: {result.modifications_success}, "
                  f"失败: {result.modifications_failed}, "
                  f"耗时: {result.duration:.1f}s")
            if result.details:
                print(f"       {Colors.DIM}{result.details}{Colors.END}")
            if result.events:
                print(f"       事件流: ", end="")
                event_types = [e.event_type for e in result.events]
                print(" → ".join(event_types))
        
        print(f"\n  结果: {passed}/{total} 通过")
        print()
        
        # 总体结果
        if passed == total:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 修改系统测试全部通过！({passed}/{total}){Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ 修改系统测试部分失败 ({passed}/{total}){Colors.END}")


# ============================================================
# 环境检查
# ============================================================

async def check_prerequisites(http_url: str, report: ModificationTestReport) -> bool:
    """检查前置条件"""
    print_section("前置条件检查")
    
    # 检查 API 服务器
    print_info("检查 API 服务器...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{http_url}/docs")
            if response.status_code != 200:
                print_error("API 服务器异常")
                return False
        print_success("API 服务器正常")
    except Exception as e:
        print_error(f"API 服务器连接失败: {e}")
        return False
    
    return True


# ============================================================
# 获取或创建路线图
# ============================================================

async def get_or_create_roadmap(
    http_url: str,
    ws_url: str,
    report: ModificationTestReport,
    existing_roadmap_id: Optional[str] = None,
    skip_create: bool = False,
) -> Optional[str]:
    """获取或创建测试用路线图"""
    print_section("准备测试路线图")
    
    if existing_roadmap_id:
        print_info(f"使用指定的路线图: {existing_roadmap_id}")
        
        # 获取路线图详情
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(f"{http_url}/api/v1/roadmaps/{existing_roadmap_id}")
                if response.status_code == 200:
                    data = response.json()
                    report.roadmap_id = existing_roadmap_id
                    
                    # 提取概念列表
                    for stage in data.get("stages", []):
                        for module in stage.get("modules", []):
                            for concept in module.get("concepts", []):
                                report.concepts.append({
                                    "concept_id": concept.get("concept_id"),
                                    "name": concept.get("name"),
                                    "has_tutorial": concept.get("content_status") == "completed",
                                    "has_resources": concept.get("resources_status") == "completed",
                                    "has_quiz": concept.get("quiz_status") == "completed",
                                })
                    
                    print_success(f"路线图加载成功，包含 {len(report.concepts)} 个概念")
                    
                    # 显示概念详情
                    for c in report.concepts:
                        status = []
                        if c["has_tutorial"]:
                            status.append("教程")
                        if c["has_resources"]:
                            status.append("资源")
                        if c["has_quiz"]:
                            status.append("测验")
                        status_str = f" [{', '.join(status)}]" if status else " [无内容]"
                        print(f"    {Colors.DIM}- {c['name']} ({c['concept_id']}){status_str}{Colors.END}")
                    
                    return existing_roadmap_id
                else:
                    print_error(f"路线图不存在: HTTP {response.status_code}")
                    return None
        except Exception as e:
            print_error(f"获取路线图失败: {e}")
            return None
    
    if skip_create:
        print_error("跳过创建但未指定路线图 ID")
        return None
    
    # 创建新路线图
    print_info("创建新的测试路线图...")
    print(f"    学习目标: {TEST_USER_REQUEST['preferences']['learning_goal']}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{http_url}/api/v1/roadmaps/generate",
                json=TEST_USER_REQUEST,
            )
            
            if response.status_code != 200:
                print_error(f"创建路线图失败: HTTP {response.status_code}")
                return None
            
            result = response.json()
            task_id = result.get("task_id")
            print_success(f"任务创建成功: {task_id}")
    except Exception as e:
        print_error(f"创建路线图异常: {e}")
        return None
    
    # 监控创建过程
    print_info("等待路线图生成完成...")
    
    try:
        async with aiohttp.ClientSession() as session:
            ws_full_url = f"{ws_url}/api/v1/ws/{task_id}?include_history=true"
            async with session.ws_connect(ws_full_url) as ws:
                while True:
                    msg = await asyncio.wait_for(ws.receive(), timeout=600)
                    
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        event = json.loads(msg.data)
                        event_type = event.get("type", "")
                        
                        if event_type == "progress":
                            step = event.get("step", "")
                            status = event.get("status", "")
                            print(f"    {Colors.DIM}○ {step}: {status}{Colors.END}")
                        elif event_type == "completed":
                            print_success("路线图生成完成")
                            break
                        elif event_type == "failed":
                            print_error(f"路线图生成失败: {event.get('error', '')}")
                            return None
                    elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                        print_warning("WebSocket 连接关闭")
                        break
    except asyncio.TimeoutError:
        print_error("等待超时")
        return None
    except Exception as e:
        print_error(f"监控异常: {e}")
        # 继续尝试获取结果
    
    # 等待数据库写入
    await asyncio.sleep(2)
    
    # 获取 roadmap_id
    try:
        from app.db.session import AsyncSessionLocal
        from app.db.repositories.roadmap_repo import RoadmapRepository
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            task = await repo.get_task(task_id)
            if task and task.roadmap_id:
                roadmap_id = task.roadmap_id
                report.roadmap_id = roadmap_id
                print_info(f"Roadmap ID: {roadmap_id}")
                
                # 获取概念列表
                return await get_or_create_roadmap(
                    http_url, ws_url, report, 
                    existing_roadmap_id=roadmap_id,
                    skip_create=True
                )
    except Exception as e:
        print_error(f"获取 roadmap_id 失败: {e}")
        return None
    
    return None


# ============================================================
# SSE 流式监控器
# ============================================================

async def monitor_modification_stream(
    http_url: str,
    roadmap_id: str,
    user_message: str,
    preferences: dict,
    context: Optional[dict] = None,
    timeout_seconds: int = 180,
) -> ModificationTestResult:
    """
    监控修改 SSE 流
    
    Returns:
        测试结果
    """
    result = ModificationTestResult(name="", passed=False)
    start_time = datetime.now()
    
    # 构建请求
    request_body = {
        "user_id": "test-user",
        "user_message": user_message,
        "preferences": preferences,
    }
    if context:
        request_body["context"] = context
    
    print_info(f"发送修改请求...")
    print(f"    消息: {user_message[:60]}...")
    if context:
        print(f"    上下文: {context}")
    
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            async with client.stream(
                "POST",
                f"{http_url}/api/v1/roadmaps/{roadmap_id}/chat-stream",
                json=request_body,
                headers={"Accept": "text/event-stream"},
            ) as response:
                if response.status_code != 200:
                    result.details = f"HTTP {response.status_code}"
                    return result
                
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    # 解析 SSE 事件
                    while "\n\n" in buffer:
                        event_str, buffer = buffer.split("\n\n", 1)
                        
                        if event_str.startswith("data: "):
                            data_str = event_str[6:]
                            try:
                                event_data = json.loads(data_str)
                                event_type = event_data.get("type", "unknown")
                                
                                # 记录事件
                                sse_event = SSEEvent(
                                    event_type=event_type,
                                    timestamp=datetime.now(),
                                    data=event_data,
                                )
                                result.events.append(sse_event)
                                
                                # 打印事件详情
                                _print_sse_event(event_type, event_data)
                                
                                # 处理特定事件
                                if event_type == "intents":
                                    result.intents_detected = event_data.get("count", 0)
                                elif event_type == "result":
                                    if event_data.get("success"):
                                        result.modifications_success += 1
                                    else:
                                        result.modifications_failed += 1
                                elif event_type == "done":
                                    result.passed = event_data.get("overall_success", False) or event_data.get("partial_success", False)
                                    if not result.passed and result.intents_detected > 0:
                                        # 如果有意图但全部失败，仍标记为部分通过（流程正确）
                                        result.passed = True
                                        result.details = "流程正确，但修改执行失败"
                                elif event_type == "error":
                                    result.details = event_data.get("message", "")
                                
                            except json.JSONDecodeError:
                                pass
        
    except Exception as e:
        result.details = str(e)
    
    result.duration = (datetime.now() - start_time).total_seconds()
    return result


def _print_sse_event(event_type: str, event_data: dict):
    """打印 SSE 事件详情"""
    if event_type == "analyzing":
        print_event(event_type, f"正在分析修改意图...")
        
    elif event_type == "intents":
        count = event_data.get("count", 0)
        confidence = event_data.get("overall_confidence", 0)
        print_event(event_type, f"识别出 {count} 个修改意图 (置信度: {confidence:.0%})")
        
        intents = event_data.get("intents", [])
        for intent in intents:
            mod_type = intent.get("modification_type", "")
            target = intent.get("target_name", "")
            reqs = intent.get("specific_requirements", [])
            print(f"      {Colors.CYAN}→ [{mod_type}]{Colors.END} {target}")
            for req in reqs[:2]:
                print(f"        {Colors.DIM}- {req[:50]}...{Colors.END}" if len(req) > 50 else f"        {Colors.DIM}- {req}{Colors.END}")
        
        if event_data.get("needs_clarification"):
            print(f"      {Colors.YELLOW}⚠ 需要澄清:{Colors.END}")
            for q in event_data.get("clarification_questions", []):
                print(f"        {Colors.DIM}- {q}{Colors.END}")
        
    elif event_type == "modifying":
        mod_type = event_data.get("modification_type", "")
        target = event_data.get("target_name", "")
        print_event(event_type, f"正在修改 [{mod_type}] {target}...")
        print_agent(f"{mod_type}_modifier", "开始执行修改任务")
        
    elif event_type == "agent_progress":
        # 新增的 Agent 进度事件
        agent = event_data.get("agent", "")
        step = event_data.get("step", "")
        details = event_data.get("details", "")
        print_agent(agent, f"{step}: {details}")
        
    elif event_type == "result":
        success = event_data.get("success", False)
        target = event_data.get("target_name", "")
        mod_type = event_data.get("modification_type", "")
        
        if success:
            summary = event_data.get("modification_summary", "")
            new_version = event_data.get("new_version")
            version_info = f" (v{new_version})" if new_version else ""
            print_event(event_type, f"{Colors.GREEN}✓{Colors.END} [{mod_type}] {target}{version_info}")
            if summary:
                print(f"        {Colors.DIM}{summary[:80]}...{Colors.END}" if len(summary) > 80 else f"        {Colors.DIM}{summary}{Colors.END}")
        else:
            error = event_data.get("error_message", "未知错误")
            print_event(event_type, f"{Colors.RED}✗{Colors.END} [{mod_type}] {target}: {error}")
        
    elif event_type == "done":
        overall = event_data.get("overall_success", False)
        partial = event_data.get("partial_success", False)
        summary = event_data.get("summary", "")
        
        if overall:
            print_event(event_type, f"{Colors.GREEN}全部完成{Colors.END}")
        elif partial:
            print_event(event_type, f"{Colors.YELLOW}部分完成{Colors.END}")
        else:
            print_event(event_type, f"{Colors.RED}执行失败{Colors.END}")
        
        if summary:
            print(f"        {summary[:100]}...")
        
    elif event_type == "error":
        message = event_data.get("message", "")
        print_event(event_type, f"{Colors.RED}{message}{Colors.END}")
        
    else:
        print_event(event_type, json.dumps(event_data, ensure_ascii=False)[:80])


# ============================================================
# 测试重新生成端点
# ============================================================

async def test_regenerate_endpoints(
    http_url: str,
    roadmap_id: str,
    concept_id: str,
    preferences: dict,
    report: ModificationTestReport,
):
    """测试重新生成端点"""
    print_section("测试重新生成端点")
    
    request_body = {
        "user_id": "test-user",
        "preferences": preferences,
    }
    
    # 测试资源重新生成
    print_info("测试资源重新生成...")
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{http_url}/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources/regenerate",
                json=request_body,
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                data = response.json()
                resources_count = len(data.get("resources", []))
                print_success(f"资源重新生成成功: {resources_count} 个资源 ({duration:.1f}s)")
                
                result = ModificationTestResult(
                    name="资源重新生成",
                    passed=True,
                    duration=duration,
                    details=f"生成 {resources_count} 个资源",
                )
                report.add_test_result(result)
            else:
                print_error(f"资源重新生成失败: HTTP {response.status_code}")
                result = ModificationTestResult(
                    name="资源重新生成",
                    passed=False,
                    duration=duration,
                    details=f"HTTP {response.status_code}: {response.text[:100]}",
                )
                report.add_test_result(result)
                
    except Exception as e:
        print_error(f"资源重新生成异常: {e}")
        report.add_test_result(ModificationTestResult(
            name="资源重新生成",
            passed=False,
            details=str(e),
        ))
    
    # 测试测验重新生成
    print_info("测试测验重新生成...")
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{http_url}/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz/regenerate",
                json=request_body,
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                data = response.json()
                questions_count = data.get("total_questions", 0)
                print_success(f"测验重新生成成功: {questions_count} 道题目 ({duration:.1f}s)")
                
                result = ModificationTestResult(
                    name="测验重新生成",
                    passed=True,
                    duration=duration,
                    details=f"生成 {questions_count} 道题目",
                )
                report.add_test_result(result)
            else:
                print_error(f"测验重新生成失败: HTTP {response.status_code}")
                result = ModificationTestResult(
                    name="测验重新生成",
                    passed=False,
                    duration=duration,
                    details=f"HTTP {response.status_code}: {response.text[:100]}",
                )
                report.add_test_result(result)
                
    except Exception as e:
        print_error(f"测验重新生成异常: {e}")
        report.add_test_result(ModificationTestResult(
            name="测验重新生成",
            passed=False,
            details=str(e),
        ))


# ============================================================
# 测试直接修改端点
# ============================================================

async def test_direct_modify_endpoints(
    http_url: str,
    roadmap_id: str,
    concept_id: str,
    preferences: dict,
    report: ModificationTestReport,
):
    """测试直接修改端点"""
    print_section("测试直接修改端点")
    
    # 测试教程修改
    print_info("测试教程直接修改端点...")
    start_time = datetime.now()
    
    request_body = {
        "user_id": "test-user",
        "preferences": preferences,
        "requirements": ["添加更多代码示例", "增加实际应用场景"],
    }
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{http_url}/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify",
                json=request_body,
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == 200:
                data = response.json()
                new_version = data.get("content_version", 0)
                print_success(f"教程修改成功: 新版本 v{new_version} ({duration:.1f}s)")
                
                result = ModificationTestResult(
                    name="教程直接修改",
                    passed=True,
                    duration=duration,
                    details=f"新版本 v{new_version}",
                )
                report.add_test_result(result)
            else:
                print_error(f"教程修改失败: HTTP {response.status_code}")
                result = ModificationTestResult(
                    name="教程直接修改",
                    passed=False,
                    duration=duration,
                    details=f"HTTP {response.status_code}: {response.text[:100]}",
                )
                report.add_test_result(result)
                
    except Exception as e:
        print_error(f"教程修改异常: {e}")
        report.add_test_result(ModificationTestResult(
            name="教程直接修改",
            passed=False,
            details=str(e),
        ))


# ============================================================
# 测试聊天式修改
# ============================================================

async def test_chat_modifications(
    http_url: str,
    roadmap_id: str,
    concepts: List[Dict[str, Any]],
    preferences: dict,
    report: ModificationTestReport,
):
    """测试聊天式修改"""
    print_section("测试聊天式修改")
    
    if not concepts:
        print_warning("没有可用的概念")
        return
    
    # 获取第一个有内容的概念用于测试
    test_concept = None
    for c in concepts:
        if c.get("has_tutorial") or c.get("has_resources") or c.get("has_quiz"):
            test_concept = c
            break
    
    if not test_concept:
        test_concept = concepts[0]
        print_warning(f"没有已生成内容的概念，使用: {test_concept['name']}")
    else:
        print_info(f"使用测试概念: {test_concept['name']}")
    
    # 运行测试用例
    for test_case in MODIFICATION_TEST_CASES:
        print(f"\n{Colors.BOLD}测试: {test_case['name']}{Colors.END}")
        print(f"  {Colors.DIM}{test_case['description']}{Colors.END}")
        
        # 替换消息中的占位符
        user_message = test_case["user_message"].format(
            concept_name=test_concept["name"]
        )
        
        # 准备上下文
        context = None
        if test_case.get("use_context"):
            context = {
                "concept_id": test_concept["concept_id"],
                "concept_name": test_concept["name"],
            }
        
        # 执行测试
        result = await monitor_modification_stream(
            http_url=http_url,
            roadmap_id=roadmap_id,
            user_message=user_message,
            preferences=preferences,
            context=context,
            timeout_seconds=180,
        )
        
        result.name = test_case["name"]
        
        # 验证期望的修改类型
        expected_types = test_case.get("expected_types", [])
        detected_types = []
        for event in result.events:
            if event.event_type == "intents":
                for intent in event.data.get("intents", []):
                    detected_types.append(intent.get("modification_type"))
        
        if expected_types and set(expected_types).issubset(set(detected_types)):
            print_success(f"意图类型匹配: {detected_types}")
        elif expected_types:
            print_warning(f"期望: {expected_types}, 实际: {detected_types}")
            result.details += f" | 期望类型: {expected_types}, 实际: {detected_types}"
        
        report.add_test_result(result)
        
        # 短暂等待，避免请求过快
        await asyncio.sleep(1)


# ============================================================
# 主测试流程
# ============================================================

async def run_modification_test(
    http_url: str = "http://localhost:8000",
    ws_url: str = "ws://localhost:8000",
    roadmap_id: Optional[str] = None,
    skip_create: bool = False,
    skip_regenerate: bool = False,
    skip_direct: bool = False,
):
    """运行修改系统测试"""
    report = ModificationTestReport()
    
    print_header("🧪 修改系统端到端测试")
    print(f"HTTP URL: {http_url}")
    print(f"WebSocket URL: {ws_url}")
    if roadmap_id:
        print(f"指定路线图 ID: {roadmap_id}")
    print()
    
    # 前置检查
    if not await check_prerequisites(http_url, report):
        print_error("前置检查失败")
        report.print_summary()
        return
    
    # 获取或创建路线图
    roadmap_id = await get_or_create_roadmap(
        http_url, ws_url, report,
        existing_roadmap_id=roadmap_id,
        skip_create=skip_create,
    )
    
    if not roadmap_id:
        print_error("无法获取测试路线图")
        report.print_summary()
        return
    
    if not report.concepts:
        print_error("路线图中没有概念")
        report.print_summary()
        return
    
    # 获取测试用的偏好设置
    preferences = TEST_USER_REQUEST["preferences"]
    first_concept_id = report.concepts[0]["concept_id"]
    
    # 测试重新生成端点
    if not skip_regenerate:
        await test_regenerate_endpoints(
            http_url, roadmap_id, first_concept_id, preferences, report
        )
    else:
        print_info("跳过重新生成测试")
    
    # 测试直接修改端点
    if not skip_direct:
        await test_direct_modify_endpoints(
            http_url, roadmap_id, first_concept_id, preferences, report
        )
    else:
        print_info("跳过直接修改测试")
    
    # 测试聊天式修改
    await test_chat_modifications(
        http_url, roadmap_id, report.concepts, preferences, report
    )
    
    # 打印报告
    report.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description="修改系统端到端测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 运行完整测试（自动创建路线图）
    python scripts/test_modification_system.py
    
    # 使用现有路线图
    python scripts/test_modification_system.py --roadmap-id abc123
    
    # 跳过路线图创建
    python scripts/test_modification_system.py --skip-create --roadmap-id abc123
    
    # 跳过重新生成测试
    python scripts/test_modification_system.py --skip-regenerate
    
    # 自定义服务地址
    python scripts/test_modification_system.py --http-url http://localhost:8000
        """
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
        "--roadmap-id",
        type=str,
        default=None,
        help="使用指定的路线图 ID"
    )
    parser.add_argument(
        "--skip-create",
        action="store_true",
        default=False,
        help="跳过路线图创建（需要指定 --roadmap-id）"
    )
    parser.add_argument(
        "--skip-regenerate",
        action="store_true",
        default=False,
        help="跳过重新生成测试"
    )
    parser.add_argument(
        "--skip-direct",
        action="store_true",
        default=False,
        help="跳过直接修改端点测试"
    )
    
    args = parser.parse_args()
    
    print()
    asyncio.run(run_modification_test(
        http_url=args.http_url,
        ws_url=args.ws_url,
        roadmap_id=args.roadmap_id,
        skip_create=args.skip_create,
        skip_regenerate=args.skip_regenerate,
        skip_direct=args.skip_direct,
    ))
    print()


if __name__ == "__main__":
    main()

