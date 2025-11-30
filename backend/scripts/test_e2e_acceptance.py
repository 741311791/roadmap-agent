"""
端到端验收测试脚本

测试功能：
1. 环境检查（PostgreSQL、Redis、MinIO）
2. 完整工作流测试（包括 Concept 级别进度事件）
3. 全方位验证：
   - WebSocket 事件完整性（包括 concept_start/complete/failed）
   - Checkpoint 状态
   - 数据库元数据表（roadmap_tasks, roadmap_metadata, tutorial_metadata）
   - MinIO 存储（教程文件）
   - API 响应

运行方式:
    cd backend
    uv run python scripts/test_e2e_acceptance.py
    
    # 快速模式（跳过教程生成）
    uv run python scripts/test_e2e_acceptance.py --quick
    
    # 自定义超时
    uv run python scripts/test_e2e_acceptance.py --timeout 900

⚠️  重要：运行测试前的后端配置
    
    测试脚本无法动态修改后端服务器的配置。请在启动后端服务器前，
    确保 .env 文件或环境变量包含以下配置：
    
    # 推荐的测试配置（加快测试速度）
    SKIP_HUMAN_REVIEW=true
    SKIP_STRUCTURE_VALIDATION=true
    SKIP_RESOURCE_RECOMMENDATION=true
    SKIP_QUIZ_GENERATION=true
    
    # 完整测试（包含教程生成）
    SKIP_TUTORIAL_GENERATION=false
    
    # 快速测试（跳过教程生成）
    SKIP_TUTORIAL_GENERATION=true
    
    修改配置后需要重启后端服务器：
    uvicorn app.main:app --reload

注意：
    - 确保后端服务已启动
    - 确保 PostgreSQL、Redis、MinIO 服务可用
    - 首次运行可能需要较长时间（LLM 调用）
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


# ============================================================
# 测试数据
# ============================================================

# 简化的测试用户请求（设计成只生成小型路线图）
TEST_USER_REQUEST = {
    "user_id": "e2e-test-user",
    "session_id": f"e2e-test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    "preferences": {
        # 非常简单的学习目标，确保生成的路线图较小
        "learning_goal": "学习Python的print函数基本用法",
        "available_hours_per_week": 2,  # 较少时间，生成更少内容
        "motivation": "兴趣爱好",
        "current_level": "beginner",
        "career_background": "学生",
        "content_preference": ["text"]
    },
    # 明确要求生成简单的路线图
    "additional_context": "请设计一个非常简洁的路线图，只需要1个阶段、1个模块、最多2个概念即可。这是用于系统测试。"
}


# ============================================================
# 测试结果收集器
# ============================================================

@dataclass
class TestResult:
    """单个测试结果"""
    name: str
    passed: bool
    details: str = ""
    duration: float = 0.0


@dataclass
class WebSocketEvent:
    """WebSocket 事件记录"""
    event_type: str
    timestamp: str
    data: Dict[str, Any]


@dataclass
class AcceptanceTestReport:
    """验收测试报告"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    task_id: Optional[str] = None
    roadmap_id: Optional[str] = None
    
    # 环境检查结果
    env_checks: List[TestResult] = field(default_factory=list)
    
    # WebSocket 事件记录
    ws_events: List[WebSocketEvent] = field(default_factory=list)
    ws_expected_events: Dict[str, bool] = field(default_factory=lambda: {
        "connected": False,
        "progress_intent_analysis": False,
        "progress_curriculum_design": False,
        "progress_content_generation": False,
        "concept_start": False,
        "concept_complete": False,
        "completed": False,
    })
    
    # 验证结果
    validation_results: List[TestResult] = field(default_factory=list)
    
    def add_env_check(self, name: str, passed: bool, details: str = ""):
        self.env_checks.append(TestResult(name=name, passed=passed, details=details))
    
    def add_ws_event(self, event: dict):
        ws_event = WebSocketEvent(
            event_type=event.get("type", "unknown"),
            timestamp=event.get("timestamp", ""),
            data=event
        )
        self.ws_events.append(ws_event)
        
        # 标记预期事件
        event_type = event.get("type", "")
        if event_type == "connected":
            self.ws_expected_events["connected"] = True
        elif event_type == "progress":
            step = event.get("step", "")
            if step == "intent_analysis":
                self.ws_expected_events["progress_intent_analysis"] = True
            elif step == "curriculum_design":
                self.ws_expected_events["progress_curriculum_design"] = True
            elif step == "content_generation":
                self.ws_expected_events["progress_content_generation"] = True
        elif event_type == "concept_start":
            self.ws_expected_events["concept_start"] = True
        elif event_type in ("concept_complete", "concept_failed"):
            self.ws_expected_events["concept_complete"] = True
        elif event_type == "completed":
            self.ws_expected_events["completed"] = True
    
    def add_validation(self, name: str, passed: bool, details: str = ""):
        self.validation_results.append(TestResult(name=name, passed=passed, details=details))
    
    def print_summary(self):
        """打印测试报告摘要"""
        print_header("📊 验收测试报告")
        
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        print(f"{Colors.BOLD}测试信息{Colors.END}")
        print(f"  Task ID: {self.task_id or 'N/A'}")
        print(f"  Roadmap ID: {self.roadmap_id or 'N/A'}")
        print(f"  总耗时: {duration:.1f}s")
        print()
        
        # 环境检查结果
        print(f"{Colors.BOLD}环境检查{Colors.END}")
        env_passed = sum(1 for r in self.env_checks if r.passed)
        env_total = len(self.env_checks)
        for result in self.env_checks:
            status = f"{Colors.GREEN}PASS{Colors.END}" if result.passed else f"{Colors.RED}FAIL{Colors.END}"
            print(f"  [{status}] {result.name}")
            if result.details and not result.passed:
                print(f"       {Colors.DIM}{result.details}{Colors.END}")
        print(f"  结果: {env_passed}/{env_total} 通过")
        print()
        
        # WebSocket 事件统计
        print(f"{Colors.BOLD}WebSocket 事件{Colors.END}")
        print(f"  总事件数: {len(self.ws_events)}")
        for event_name, received in self.ws_expected_events.items():
            status = f"{Colors.GREEN}✓{Colors.END}" if received else f"{Colors.RED}✗{Colors.END}"
            print(f"  [{status}] {event_name}")
        ws_passed = sum(1 for v in self.ws_expected_events.values() if v)
        ws_total = len(self.ws_expected_events)
        print(f"  结果: {ws_passed}/{ws_total} 预期事件已收到")
        print()
        
        # 验证结果
        print(f"{Colors.BOLD}功能验证{Colors.END}")
        val_passed = sum(1 for r in self.validation_results if r.passed)
        val_total = len(self.validation_results)
        for result in self.validation_results:
            status = f"{Colors.GREEN}PASS{Colors.END}" if result.passed else f"{Colors.RED}FAIL{Colors.END}"
            print(f"  [{status}] {result.name}")
            if result.details:
                print(f"       {Colors.DIM}{result.details}{Colors.END}")
        print(f"  结果: {val_passed}/{val_total} 通过")
        print()
        
        # 总体结果
        total_passed = env_passed + ws_passed + val_passed
        total_tests = env_total + ws_total + val_total
        
        if total_passed == total_tests:
            print(f"{Colors.GREEN}{Colors.BOLD}🎉 验收测试全部通过！({total_passed}/{total_tests}){Colors.END}")
        else:
            print(f"{Colors.RED}{Colors.BOLD}❌ 验收测试部分失败 ({total_passed}/{total_tests}){Colors.END}")


# ============================================================
# 环境检查
# ============================================================

async def check_postgresql(report: AcceptanceTestReport) -> bool:
    """检查 PostgreSQL 连接"""
    print_info("检查 PostgreSQL 连接...")
    
    try:
        from app.db.session import AsyncSessionLocal
        from sqlalchemy import text
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            result.fetchone()
        
        report.add_env_check("PostgreSQL", True, "连接成功")
        print_success("PostgreSQL 连接正常")
        return True
    except Exception as e:
        report.add_env_check("PostgreSQL", False, str(e))
        print_error(f"PostgreSQL 连接失败: {e}")
        return False


async def check_redis(report: AcceptanceTestReport) -> bool:
    """检查 Redis 连接"""
    print_info("检查 Redis 连接...")
    
    try:
        from app.db.redis_client import redis_client
        
        await redis_client.connect()
        await redis_client._client.ping()
        
        report.add_env_check("Redis", True, "连接成功")
        print_success("Redis 连接正常")
        return True
    except Exception as e:
        report.add_env_check("Redis", False, str(e))
        print_error(f"Redis 连接失败: {e}")
        return False


async def check_minio(report: AcceptanceTestReport) -> bool:
    """检查 MinIO 连接"""
    print_info("检查 MinIO 连接...")
    
    try:
        from app.db.minio_init import check_minio_connection, ensure_bucket_exists
        
        connected = await check_minio_connection()
        if not connected:
            raise Exception("无法连接到 MinIO")
        
        bucket_ready = await ensure_bucket_exists()
        if not bucket_ready:
            raise Exception("Bucket 初始化失败")
        
        report.add_env_check("MinIO", True, "连接成功，Bucket 已就绪")
        print_success("MinIO 连接正常")
        return True
    except Exception as e:
        report.add_env_check("MinIO", False, str(e))
        print_error(f"MinIO 连接失败: {e}")
        return False


async def check_api_server(report: AcceptanceTestReport, base_url: str) -> bool:
    """检查 API 服务器"""
    print_info("检查 API 服务器...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/health")
            # 即使没有 /health 端点，尝试其他端点
            if response.status_code == 404:
                response = await client.get(f"{base_url}/docs")
        
        report.add_env_check("API Server", True, f"HTTP {response.status_code}")
        print_success("API 服务器正常")
        return True
    except Exception as e:
        report.add_env_check("API Server", False, str(e))
        print_error(f"API 服务器连接失败: {e}")
        return False


# ============================================================
# WebSocket 监控器
# ============================================================

async def monitor_websocket(
    ws_url: str,
    task_id: str,
    report: AcceptanceTestReport,
    timeout_seconds: int = 600,
) -> bool:
    """
    监控 WebSocket 事件
    
    Args:
        ws_url: WebSocket URL
        task_id: 任务 ID
        report: 测试报告
        timeout_seconds: 超时时间
        
    Returns:
        是否成功完成监控
    """
    full_url = f"{ws_url}/api/v1/ws/{task_id}?include_history=true"
    
    print_info(f"连接 WebSocket: {full_url}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(full_url) as ws:
                print_success("WebSocket 连接成功")
                
                # 发送心跳
                await ws.send_str(json.dumps({"type": "ping"}))
                
                while True:
                    try:
                        msg = await asyncio.wait_for(
                            ws.receive(),
                            timeout=timeout_seconds
                        )
                        
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            event = json.loads(msg.data)
                            report.add_ws_event(event)
                            
                            # 打印事件
                            event_type = event.get("type", "unknown")
                            if event_type == "concept_start":
                                concept_name = event.get("concept_name", "")
                                progress = event.get("progress", {})
                                print(f"  {Colors.BLUE}→ concept_start:{Colors.END} {concept_name} ({progress.get('current')}/{progress.get('total')})")
                            elif event_type == "concept_complete":
                                concept_id = event.get("concept_id", "")
                                print(f"  {Colors.GREEN}✓ concept_complete:{Colors.END} {concept_id}")
                            elif event_type == "concept_failed":
                                concept_id = event.get("concept_id", "")
                                error = event.get("error", "")[:50]
                                print(f"  {Colors.RED}✗ concept_failed:{Colors.END} {concept_id} - {error}")
                            elif event_type == "progress":
                                step = event.get("step", "")
                                status = event.get("status", "")
                                print(f"  {Colors.CYAN}○ progress:{Colors.END} {step} - {status}")
                            elif event_type == "completed":
                                print(f"  {Colors.GREEN}★ completed{Colors.END}")
                            elif event_type == "failed":
                                error_msg = event.get("error", "未知错误")
                                step = event.get("step", "未知")
                                print(f"  {Colors.RED}★ failed: {error_msg[:100]}{Colors.END}")
                                print(f"    {Colors.DIM}失败步骤: {step}{Colors.END}")
                            elif event_type not in ("connected", "pong", "current_status"):
                                print(f"  {Colors.DIM}○ {event_type}{Colors.END}")
                            
                            # 检查终止事件
                            if event_type in ("completed", "failed", "closing"):
                                return event_type == "completed"
                        
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            print_warning("WebSocket 连接关闭")
                            return False
                    
                    except asyncio.TimeoutError:
                        print_error(f"WebSocket 超时 ({timeout_seconds}s)")
                        return False
    
    except Exception as e:
        print_error(f"WebSocket 错误: {e}")
        return False


# ============================================================
# 数据库验证
# ============================================================

async def validate_database(
    task_id: str,
    roadmap_id: str,
    report: AcceptanceTestReport,
    skip_tutorial: bool = False,
) -> List[str]:
    """
    验证数据库记录
    
    Returns:
        concept_ids: 路线图中的所有 concept_id 列表
    """
    print_section("验证数据库记录")
    
    from app.db.session import AsyncSessionLocal
    from app.db.repositories.roadmap_repo import RoadmapRepository
    
    concept_ids = []
    
    async with AsyncSessionLocal() as session:
        repo = RoadmapRepository(session)
        
        # 1. 验证任务记录
        print_info("检查 roadmap_tasks 表...")
        task = await repo.get_task(task_id)
        if task:
            task_valid = task.status == "completed"
            report.add_validation(
                "Database: roadmap_tasks",
                task_valid,
                f"status={task.status}, step={task.current_step}"
            )
            if task_valid:
                print_success(f"任务记录存在且状态正确 (status={task.status})")
            else:
                print_error(f"任务状态异常: {task.status}")
        else:
            report.add_validation("Database: roadmap_tasks", False, "任务记录不存在")
            print_error("任务记录不存在")
        
        # 2. 验证需求分析元数据（A1: 需求分析师产出）
        print_info("检查 intent_analysis_metadata 表...")
        intent_analysis = await repo.get_intent_analysis_metadata(task_id)
        if intent_analysis:
            report.add_validation(
                "Database: intent_analysis_metadata",
                True,
                f"key_technologies={len(intent_analysis.key_technologies)}"
            )
            print_success(f"需求分析元数据存在 (技术栈: {intent_analysis.key_technologies[:3]})")
        else:
            report.add_validation("Database: intent_analysis_metadata", False, "需求分析元数据不存在")
            print_error("需求分析元数据不存在")
        
        # 3. 验证路线图元数据
        print_info("检查 roadmap_metadata 表...")
        roadmap_meta = await repo.get_roadmap_metadata(roadmap_id)
        if roadmap_meta:
            report.add_validation(
                "Database: roadmap_metadata",
                True,
                f"title={roadmap_meta.title}"
            )
            print_success(f"路线图元数据存在 (title={roadmap_meta.title})")
            
            # 从框架数据中提取所有 concept_id，并验证 concept 结构
            framework_data = roadmap_meta.framework_data
            has_resource_fields = False
            has_quiz_fields = False
            
            for stage in framework_data.get("stages", []):
                for module in stage.get("modules", []):
                    for concept in module.get("concepts", []):
                        concept_ids.append(concept.get("concept_id"))
                        # 检查是否有新增的资源和测验字段
                        if "resources_status" in concept:
                            has_resource_fields = True
                        if "quiz_status" in concept:
                            has_quiz_fields = True
            
            print(f"    {Colors.DIM}发现 {len(concept_ids)} 个概念{Colors.END}")
            print(f"    {Colors.DIM}Concept 包含资源字段: {has_resource_fields}{Colors.END}")
            print(f"    {Colors.DIM}Concept 包含测验字段: {has_quiz_fields}{Colors.END}")
        else:
            report.add_validation("Database: roadmap_metadata", False, "路线图元数据不存在")
            print_error("路线图元数据不存在")
        
        # 4. 验证教程元数据（A4: 教程生成器产出）
        if not skip_tutorial and concept_ids:
            print_info("检查 tutorial_metadata 表...")
            tutorials_found = 0
            
            for concept_id in concept_ids:
                tutorial = await repo.get_latest_tutorial(roadmap_id, concept_id)
                if tutorial:
                    tutorials_found += 1
                    # 验证 tutorial_id 是否为 UUID 格式
                    is_uuid = len(tutorial.tutorial_id) == 36 and tutorial.tutorial_id.count('-') == 4
                    id_format = "UUID" if is_uuid else "旧格式"
                    print(f"    {Colors.GREEN}✓{Colors.END} {concept_id}: {tutorial.title[:25]}... (ID格式: {id_format})")
                else:
                    print(f"    {Colors.RED}✗{Colors.END} {concept_id}: 未找到")
            
            tutorials_valid = tutorials_found == len(concept_ids)
            report.add_validation(
                "Database: tutorial_metadata",
                tutorials_valid,
                f"{tutorials_found}/{len(concept_ids)} 教程记录"
            )
            if tutorials_valid:
                print_success(f"所有教程元数据存在 ({tutorials_found}/{len(concept_ids)})")
            else:
                print_warning(f"部分教程元数据缺失 ({tutorials_found}/{len(concept_ids)})")
        elif skip_tutorial:
            print_info("跳过教程元数据检查（快速模式）")
            report.add_validation("Database: tutorial_metadata", True, "已跳过（快速模式）")
        
        # 5. 验证资源推荐元数据（A5: 资源推荐师产出）
        if not skip_tutorial and concept_ids:
            print_info("检查 resource_recommendation_metadata 表...")
            resources = await repo.get_resource_recommendations_by_roadmap(roadmap_id)
            resources_map = {r.concept_id: r for r in resources}
            resources_found = len(resources_map)
            
            for concept_id in concept_ids[:3]:  # 只显示前3个
                if concept_id in resources_map:
                    r = resources_map[concept_id]
                    print(f"    {Colors.GREEN}✓{Colors.END} {concept_id}: {r.resources_count} 个资源")
                else:
                    print(f"    {Colors.RED}✗{Colors.END} {concept_id}: 未找到")
            
            if len(concept_ids) > 3:
                print(f"    {Colors.DIM}... 还有 {len(concept_ids) - 3} 个概念{Colors.END}")
            
            resources_valid = resources_found == len(concept_ids)
            report.add_validation(
                "Database: resource_recommendation_metadata",
                resources_valid,
                f"{resources_found}/{len(concept_ids)} 资源推荐记录"
            )
            if resources_valid:
                print_success(f"所有资源推荐元数据存在 ({resources_found}/{len(concept_ids)})")
            else:
                print_warning(f"部分资源推荐元数据缺失 ({resources_found}/{len(concept_ids)})")
        elif skip_tutorial:
            print_info("跳过资源推荐元数据检查（快速模式）")
            report.add_validation("Database: resource_recommendation_metadata", True, "已跳过（快速模式）")
        
        # 6. 验证测验元数据（A6: 测验生成器产出）
        if not skip_tutorial and concept_ids:
            print_info("检查 quiz_metadata 表...")
            quizzes = await repo.get_quizzes_by_roadmap(roadmap_id)
            quizzes_map = {q.concept_id: q for q in quizzes}
            quizzes_found = len(quizzes_map)
            
            for concept_id in concept_ids[:3]:  # 只显示前3个
                if concept_id in quizzes_map:
                    q = quizzes_map[concept_id]
                    print(f"    {Colors.GREEN}✓{Colors.END} {concept_id}: {q.total_questions} 道题目")
                else:
                    print(f"    {Colors.RED}✗{Colors.END} {concept_id}: 未找到")
            
            if len(concept_ids) > 3:
                print(f"    {Colors.DIM}... 还有 {len(concept_ids) - 3} 个概念{Colors.END}")
            
            quizzes_valid = quizzes_found == len(concept_ids)
            report.add_validation(
                "Database: quiz_metadata",
                quizzes_valid,
                f"{quizzes_found}/{len(concept_ids)} 测验记录"
            )
            if quizzes_valid:
                print_success(f"所有测验元数据存在 ({quizzes_found}/{len(concept_ids)})")
            else:
                print_warning(f"部分测验元数据缺失 ({quizzes_found}/{len(concept_ids)})")
        elif skip_tutorial:
            print_info("跳过测验元数据检查（快速模式）")
            report.add_validation("Database: quiz_metadata", True, "已跳过（快速模式）")
    
    return concept_ids


# ============================================================
# MinIO 验证
# ============================================================

async def validate_minio(
    roadmap_id: str,
    concept_ids: List[str],
    report: AcceptanceTestReport,
    skip_tutorial: bool = False,
):
    """验证 MinIO 存储"""
    print_section("验证 MinIO 存储")
    
    if skip_tutorial:
        print_info("跳过 MinIO 验证（快速模式）")
        report.add_validation("MinIO: Tutorial Files", True, "已跳过（快速模式）")
        return
    
    if not concept_ids:
        print_warning("没有可验证的概念")
        report.add_validation("MinIO: Tutorial Files", False, "无概念 ID")
        return
    
    from app.tools.storage.s3_client import S3StorageTool
    from app.models.domain import S3DownloadRequest
    
    storage = S3StorageTool()
    files_found = 0
    
    for concept_id in concept_ids:
        # 尝试下载教程文件
        key = f"{roadmap_id}/concepts/{concept_id}/v1.md"
        
        try:
            request = S3DownloadRequest(key=key)
            result = await storage.download(request)
            
            if result.success and result.content:
                files_found += 1
                print(f"  {Colors.GREEN}✓{Colors.END} {concept_id}: {result.size_bytes} bytes")
            else:
                print(f"  {Colors.RED}✗{Colors.END} {concept_id}: 下载失败")
        except Exception as e:
            print(f"  {Colors.RED}✗{Colors.END} {concept_id}: {str(e)[:50]}")
    
    minio_valid = files_found == len(concept_ids)
    report.add_validation(
        "MinIO: Tutorial Files",
        minio_valid,
        f"{files_found}/{len(concept_ids)} 文件存在"
    )
    
    if minio_valid:
        print_success(f"所有教程文件已上传 ({files_found}/{len(concept_ids)})")
    else:
        print_warning(f"部分教程文件缺失 ({files_found}/{len(concept_ids)})")


# ============================================================
# Checkpoint 验证
# ============================================================

async def validate_checkpoint(
    task_id: str,
    report: AcceptanceTestReport,
):
    """验证 LangGraph Checkpoint"""
    print_section("验证 Checkpoint 状态")
    
    from app.db.session import AsyncSessionLocal
    from sqlalchemy import text
    
    async with AsyncSessionLocal() as session:
        # 查询 checkpoint 表
        try:
            result = await session.execute(
                text("""
                    SELECT thread_id, checkpoint_id, parent_checkpoint_id
                    FROM checkpoints
                    WHERE thread_id = :thread_id
                    ORDER BY checkpoint_id DESC
                    LIMIT 5
                """),
                {"thread_id": task_id}
            )
            checkpoints = result.fetchall()
            
            if checkpoints:
                report.add_validation(
                    "Checkpoint: State",
                    True,
                    f"{len(checkpoints)} 个 checkpoint 记录"
                )
                print_success(f"Checkpoint 记录存在 ({len(checkpoints)} 个)")
                for cp in checkpoints[:3]:
                    print(f"    {Colors.DIM}checkpoint_id: {cp[1][:20]}...{Colors.END}")
            else:
                report.add_validation("Checkpoint: State", False, "无 checkpoint 记录")
                print_warning("无 Checkpoint 记录")
        except Exception as e:
            # 可能是表不存在
            report.add_validation("Checkpoint: State", False, str(e)[:50])
            print_warning(f"Checkpoint 查询失败: {str(e)[:50]}")


# ============================================================
# API 验证
# ============================================================

async def validate_api(
    base_url: str,
    task_id: str,
    roadmap_id: str,
    report: AcceptanceTestReport,
):
    """验证 API 响应"""
    print_section("验证 API 响应")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. 验证状态查询 API
        print_info("检查 /status API...")
        try:
            response = await client.get(f"{base_url}/api/v1/roadmaps/{task_id}/status")
            if response.status_code == 200:
                data = response.json()
                report.add_validation(
                    "API: GET /status",
                    True,
                    f"status={data.get('status')}"
                )
                print_success(f"状态查询正常 (status={data.get('status')})")
            else:
                report.add_validation("API: GET /status", False, f"HTTP {response.status_code}")
                print_error(f"状态查询失败: HTTP {response.status_code}")
        except Exception as e:
            report.add_validation("API: GET /status", False, str(e)[:50])
            print_error(f"状态查询异常: {e}")
        
        # 2. 验证路线图获取 API
        print_info("检查 GET /{roadmap_id} API...")
        try:
            response = await client.get(f"{base_url}/api/v1/roadmaps/{roadmap_id}")
            if response.status_code == 200:
                data = response.json()
                stages_count = len(data.get("stages", []))
                report.add_validation(
                    "API: GET /{roadmap_id}",
                    True,
                    f"{stages_count} stages"
                )
                print_success(f"路线图获取正常 ({stages_count} stages)")
            else:
                report.add_validation("API: GET /{roadmap_id}", False, f"HTTP {response.status_code}")
                print_error(f"路线图获取失败: HTTP {response.status_code}")
        except Exception as e:
            report.add_validation("API: GET /{roadmap_id}", False, str(e)[:50])
            print_error(f"路线图获取异常: {e}")


# ============================================================
# 主测试流程
# ============================================================

async def run_acceptance_test(
    http_url: str = "http://localhost:8000",
    ws_url: str = "ws://localhost:8000",
    quick_mode: bool = False,
    timeout_seconds: int = 600,
):
    """
    运行完整的验收测试
    
    Args:
        http_url: HTTP API URL
        ws_url: WebSocket URL
        quick_mode: 快速模式（跳过教程生成）
        timeout_seconds: 超时时间
    """
    report = AcceptanceTestReport()
    
    print_header("🧪 端到端验收测试")
    print(f"HTTP URL: {http_url}")
    print(f"WebSocket URL: {ws_url}")
    print(f"模式: {'快速模式（跳过教程生成）' if quick_mode else '完整模式'}")
    print()
    
    # ==================== 第一阶段：环境检查 ====================
    print_section("第一阶段：环境检查")
    
    env_ok = True
    env_ok &= await check_api_server(report, http_url)
    env_ok &= await check_postgresql(report)
    env_ok &= await check_redis(report)
    env_ok &= await check_minio(report)
    
    if not env_ok:
        print_error("\n环境检查失败，无法继续测试")
        report.print_summary()
        return
    
    print_success("\n环境检查全部通过")
    
    # ==================== 第二阶段：工作流测试 ====================
    mode_desc = "快速模式" if quick_mode else "完整模式"
    print_section(f"第二阶段：工作流测试（{mode_desc}）")
    
    # 提示用户检查后端配置
    print_warning("请确保后端服务器已使用正确的配置启动！")
    print(f"    推荐的 .env 配置:")
    print(f"    SKIP_HUMAN_REVIEW=true")
    print(f"    SKIP_STRUCTURE_VALIDATION=true")
    print(f"    SKIP_RESOURCE_RECOMMENDATION=true")
    print(f"    SKIP_QUIZ_GENERATION=true")
    print(f"    SKIP_TUTORIAL_GENERATION={'true' if quick_mode else 'false'}")
    print()
    
    # 创建任务
    print_info("发起 /generate 请求...")
    print(f"    学习目标: {TEST_USER_REQUEST['preferences']['learning_goal']}")
    
    task_id = None
    roadmap_id = None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{http_url}/api/v1/roadmaps/generate",
                json=TEST_USER_REQUEST,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                print_error(f"创建任务失败: HTTP {response.status_code}")
                print(response.text)
                report.print_summary()
                return
            
            result = response.json()
            task_id = result.get("task_id")
            report.task_id = task_id
            
            print_success(f"任务创建成功: {task_id}")
    except Exception as e:
        print_error(f"创建任务异常: {e}")
        report.print_summary()
        return
    
    # 监控 WebSocket 事件
    print_info("开始监控 WebSocket 事件...")
    print(f"    预计耗时: {2 if quick_mode else 5}-{5 if quick_mode else 15} 分钟")
    print()
    
    ws_success = await monitor_websocket(
        ws_url=ws_url,
        task_id=task_id,
        report=report,
        timeout_seconds=timeout_seconds,
    )
    
    if ws_success:
        print_success("\n工作流执行完成")
    else:
        print_warning("\n工作流执行可能未完全完成")
    
    # 等待数据库写入完成
    await asyncio.sleep(3)
    
    # 查询任务状态获取更多信息
    print_info("查询任务最终状态...")
    try:
        from app.db.session import AsyncSessionLocal
        from app.db.repositories.roadmap_repo import RoadmapRepository
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            task = await repo.get_task(task_id)
            if task:
                print(f"    状态: {task.status}")
                print(f"    当前步骤: {task.current_step}")
                print(f"    Roadmap ID: {task.roadmap_id or 'N/A'}")
                if task.error_message:
                    print(f"    {Colors.RED}错误信息: {task.error_message[:200]}{Colors.END}")
    except Exception as e:
        print_warning(f"查询任务状态失败: {e}")
    
    # ==================== 第三阶段：全方位验证 ====================
    print_section("第三阶段：全方位验证")
    
    # 获取实际的 roadmap_id
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
    except Exception as e:
        print_warning(f"获取 roadmap_id 失败: {e}")
    
    if not roadmap_id:
        print_error("无法获取 roadmap_id，跳过部分验证")
        report.add_validation("Database: roadmap_metadata", False, "无 roadmap_id")
        report.add_validation("MinIO: Tutorial Files", False, "无 roadmap_id")
    else:
        # 验证数据库（并获取 concept_ids）
        concept_ids = await validate_database(task_id, roadmap_id, report, skip_tutorial=quick_mode)
        
        # 验证 MinIO
        await validate_minio(roadmap_id, concept_ids, report, skip_tutorial=quick_mode)
    
    # 验证 Checkpoint
    await validate_checkpoint(task_id, report)
    
    # 验证 API
    if roadmap_id:
        await validate_api(http_url, task_id, roadmap_id, report)
    else:
        report.add_validation("API: GET /status", False, "无 roadmap_id")
        report.add_validation("API: GET /{roadmap_id}", False, "无 roadmap_id")
    
    # ==================== 打印报告 ====================
    report.print_summary()


def main():
    parser = argparse.ArgumentParser(
        description="端到端验收测试脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 运行完整测试（包括教程生成）
    python scripts/test_e2e_acceptance.py
    
    # 快速模式（跳过教程生成，仅测试框架流程）
    python scripts/test_e2e_acceptance.py --quick
    
    # 自定义服务地址
    python scripts/test_e2e_acceptance.py --http-url http://localhost:8000
    
    # 设置超时时间
    python scripts/test_e2e_acceptance.py --timeout 900
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
        "--timeout",
        type=int,
        default=600,
        help="超时时间（秒）"
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        default=False,
        help="快速模式：跳过教程生成，仅测试框架生成流程"
    )
    
    args = parser.parse_args()
    
    print()
    asyncio.run(run_acceptance_test(
        http_url=args.http_url,
        ws_url=args.ws_url,
        quick_mode=args.quick,
        timeout_seconds=args.timeout,
    ))
    print()


if __name__ == "__main__":
    main()

