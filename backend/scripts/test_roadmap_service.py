#!/usr/bin/env python3
"""
路线图生成服务测试脚本

用法:
    python scripts/test_roadmap_service.py
    或
    uv run python scripts/test_roadmap_service.py

功能:
    - 测试路线图生成 API
    - 轮询任务状态
    - 查看生成的路线图
    - 测试人工审核流程
"""
import asyncio
import json
import sys
from datetime import datetime
from typing import Dict, Any
import httpx

# 尝试导入 rich，如果没有则使用简单的打印
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    # 简单的控制台输出类
    class SimpleConsole:
        def print(self, *args, **kwargs):
            print(*args)
    
    class SimpleTable:
        def __init__(self, *args, **kwargs):
            self.rows = []
            self.title = kwargs.get('title', '')
        
        def add_column(self, *args, **kwargs):
            pass
        
        def add_row(self, *args):
            self.rows.append(args)
    
    class SimpleProgress:
        def __init__(self, *args, **kwargs):
            self.task = None
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def add_task(self, *args, **kwargs):
            return 0
        
        def update(self, task, **kwargs):
            desc = kwargs.get('description', '')
            if desc:
                print(f"\r{desc}", end='', flush=True)
        
        def stop(self):
            print()

if HAS_RICH:
    console = Console()
    Table = Table
    Progress = Progress
    SpinnerColumn = SpinnerColumn
    TextColumn = TextColumn
    box = box
    
    def print_styled(text, style=None):
        """打印带样式的文本"""
        console.print(text, style=style)
else:
    console = SimpleConsole()
    Table = SimpleTable
    Progress = SimpleProgress
    SpinnerColumn = None
    TextColumn = None
    box = None
    
    def print_styled(text, style=None):
        """打印文本（忽略样式）"""
        # 移除 rich 标记
        import re
        text = re.sub(r'\[.*?\]', '', str(text))
        console.print(text)

# 默认配置
DEFAULT_BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


class RoadmapTester:
    """路线图服务测试器"""
    
    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url
        self.api_url = f"{base_url}{API_PREFIX}"
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        await self.client.aclose()
    
    async def check_health(self) -> bool:
        """检查服务健康状态"""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                data = response.json()
                console.print(f"✅ 服务健康: {data}")
                return True
            else:
                console.print(f"❌ 服务不健康: {response.status_code}")
                return False
        except Exception as e:
            console.print(f"❌ 无法连接到服务: {e}")
            return False
    
    async def generate_roadmap(self, user_request: Dict[str, Any]) -> str | None:
        """发送路线图生成请求"""
        try:
            response = await self.client.post(
                f"{self.api_url}/roadmaps/generate",
                json=user_request
            )
            response.raise_for_status()
            data = response.json()
            task_id = data.get("task_id")
            
            console.print(f"\n✅ 路线图生成任务已创建")
            console.print(f"   任务 ID: {task_id}")
            console.print(f"   状态: {data.get('status')}")
            
            return task_id
        except httpx.HTTPStatusError as e:
            console.print(f"❌ HTTP 错误: {e.response.status_code}")
            console.print(f"   响应: {e.response.text}")
            return None
        except Exception as e:
            console.print(f"❌ 请求失败: {e}")
            return None
    
    async def get_status(self, task_id: str) -> Dict[str, Any] | None:
        """查询任务状态"""
        try:
            response = await self.client.get(
                f"{self.api_url}/roadmaps/{task_id}/status"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            console.print(f"❌ 查询状态失败: {e.response.status_code}")
            return None
        except Exception as e:
            console.print(f"❌ 查询状态异常: {e}")
            return None
    
    async def wait_for_completion(
        self, 
        task_id: str, 
        max_wait_seconds: int = 300,
        poll_interval: int = 3
    ) -> Dict[str, Any] | None:
        """轮询等待任务完成"""
        start_time = datetime.now()
        
        if HAS_RICH:
            progress_items = [SpinnerColumn(), TextColumn("[progress.description]{task.description}")]
        else:
            progress_items = []
        
        with Progress(*progress_items, console=console) as progress:
            task = progress.add_task(f"等待任务完成 (ID: {task_id[:8]}...)", total=None)
            
            while True:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > max_wait_seconds:
                    console.print(f"\n⏱️  超时: 等待超过 {max_wait_seconds} 秒")
                    return None
                
                status = await self.get_status(task_id)
                if not status:
                    console.print(f"\n❌ 任务不存在: {task_id}")
                    return None
                
                current_status = status.get("status", "unknown")
                current_step = status.get("current_step", "unknown")
                
                progress.update(
                    task,
                    description=f"状态: {current_status} | 步骤: {current_step} | 已等待: {int(elapsed)}s"
                )
                
                # 检查是否完成或失败
                if current_status in ["completed", "failed", "human_review_pending"]:
                    progress.stop()
                    return status
                
                await asyncio.sleep(poll_interval)
    
    async def get_roadmap(self, roadmap_id: str) -> Dict[str, Any] | None:
        """获取完整路线图"""
        try:
            response = await self.client.get(
                f"{self.api_url}/roadmaps/{roadmap_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                console.print(f"❌ 路线图不存在: {roadmap_id}")
                return None
            console.print(f"❌ 获取路线图失败: {e.response.status_code}")
            return None
        except Exception as e:
            console.print(f"❌ 获取路线图异常: {e}")
            return None
    
    async def approve_roadmap(
        self, 
        task_id: str, 
        approved: bool = True,
        feedback: str | None = None
    ) -> Dict[str, Any] | None:
        """人工审核路线图"""
        try:
            response = await self.client.post(
                f"{self.api_url}/roadmaps/{task_id}/approve",
                params={"approved": approved, "feedback": feedback}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            console.print(f"❌ 审核失败: {e.response.status_code}")
            console.print(f"   响应: {e.response.text}")
            return None
        except Exception as e:
            console.print(f"❌ 审核异常: {e}")
            return None
    
    def print_status(self, status: Dict[str, Any]):
        """打印任务状态"""
        if HAS_RICH:
            table = Table(title="任务状态", box=box.ROUNDED)
            table.add_column("字段")
            table.add_column("值")
        else:
            table = Table(title="任务状态")
            console.print("\n=== 任务状态 ===")
        
        for key, value in status.items():
            if key == "roadmap_framework" and value:
                # 简化显示路线图框架
                display_value = f"已生成 ({value.get('title', 'N/A')})"
            elif isinstance(value, dict):
                display_value = json.dumps(value, ensure_ascii=False, indent=2)[:100]
            elif isinstance(value, list):
                display_value = f"列表 ({len(value)} 项)"
            else:
                display_value = str(value)
            
            table.add_row(key, display_value)
            if not HAS_RICH:
                console.print(f"  {key}: {display_value}")
        
        if HAS_RICH:
            console.print(table)
        else:
            console.print("")
    
    def print_roadmap_summary(self, roadmap: Dict[str, Any]):
        """打印路线图摘要"""
        title = roadmap.get("title", "N/A")
        roadmap_id = roadmap.get("roadmap_id", "N/A")
        stages = roadmap.get("stages", [])
        total_hours = roadmap.get("total_estimated_hours", 0)
        weeks = roadmap.get("recommended_completion_weeks", 0)
        
        if HAS_RICH:
            console.print(f"\n📚 [bold cyan]路线图: {title}[/bold cyan]")
        else:
            console.print(f"\n📚 路线图: {title}")
        console.print(f"   ID: {roadmap_id}")
        console.print(f"   总时长: {total_hours:.1f} 小时")
        console.print(f"   推荐周期: {weeks} 周")
        console.print(f"   阶段数: {len(stages)}")
        
        # 打印阶段摘要
        for i, stage in enumerate(stages, 1):
            stage_name = stage.get("name", "N/A")
            modules = stage.get("modules", [])
            stage_hours = sum(
                sum(c.get("estimated_hours", 0) for c in m.get("concepts", []))
                for m in modules
            )
            
            if HAS_RICH:
                console.print(f"\n   [bold yellow]阶段 {i}: {stage_name}[/bold yellow]")
            else:
                console.print(f"\n   阶段 {i}: {stage_name}")
            console.print(f"      模块数: {len(modules)}")
            console.print(f"      预估时长: {stage_hours:.1f} 小时")
            
            for j, module in enumerate(modules, 1):
                module_name = module.get("name", "N/A")
                concepts = module.get("concepts", [])
                console.print(f"      - 模块 {j}: {module_name} ({len(concepts)} 个概念)")


async def test_scenario_1_full_stack_web():
    """测试场景 1: 全栈 Web 开发"""
    console.print("\n" + "="*60)
    console.print("测试场景 1: 全栈 Web 开发学习路线")
    console.print("="*60)
    
    request = {
        "user_id": "test-user-001",
        "session_id": f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "preferences": {
            "learning_goal": "成为全栈 Web 开发工程师",
            "available_hours_per_week": 15,
            "motivation": "转行进入技术领域",
            "current_level": "beginner",
            "career_background": "市场营销 3 年经验",
            "content_preference": ["text", "interactive", "project"],
            "target_deadline": None
        },
        "additional_context": "希望能在 6 个月内找到初级开发工作"
    }
    
    async with RoadmapTester() as tester:
        # 检查健康状态
        if not await tester.check_health():
            return False
        
        # 生成路线图
        task_id = await tester.generate_roadmap(request)
        if not task_id:
            return False
        
        # 等待完成
        status = await tester.wait_for_completion(task_id, max_wait_seconds=600)
        if not status:
            return False
        
        # 打印状态
        tester.print_status(status)
        
        # 如果完成，获取路线图
        if status.get("status") == "completed":
            roadmap_id = status.get("roadmap_id")
            if roadmap_id:
                roadmap = await tester.get_roadmap(roadmap_id)
                if roadmap:
                    tester.print_roadmap_summary(roadmap)
        
        return True


async def test_scenario_2_python_data_science():
    """测试场景 2: Python 数据分析"""
    console.print("\n" + "="*60)
    console.print("测试场景 2: Python 数据分析学习路线")
    console.print("="*60)
    
    request = {
        "user_id": "test-user-002",
        "session_id": f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "preferences": {
            "learning_goal": "掌握 Python 数据分析和机器学习",
            "available_hours_per_week": 20,
            "motivation": "提升数据分析能力，为职业发展做准备",
            "current_level": "intermediate",
            "career_background": "金融分析师，有 Excel 和 SQL 基础",
            "content_preference": ["text", "interactive"],
            "target_deadline": None
        },
        "additional_context": "希望重点学习 Pandas、NumPy 和 Scikit-learn"
    }
    
    async with RoadmapTester() as tester:
        if not await tester.check_health():
            return False
        
        task_id = await tester.generate_roadmap(request)
        if not task_id:
            return False
        
        status = await tester.wait_for_completion(task_id, max_wait_seconds=600)
        if status:
            tester.print_status(status)
            
            if status.get("status") == "completed":
                roadmap_id = status.get("roadmap_id")
                if roadmap_id:
                    roadmap = await tester.get_roadmap(roadmap_id)
                    if roadmap:
                        tester.print_roadmap_summary(roadmap)
        
        return True


async def test_scenario_3_human_review():
    """测试场景 3: 人工审核流程"""
    console.print("\n" + "="*60)
    console.print("测试场景 3: 人工审核流程")
    console.print("="*60)
    
    request = {
        "user_id": "test-user-003",
        "session_id": f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "preferences": {
            "learning_goal": "学习 React 前端开发",
            "available_hours_per_week": 10,
            "motivation": "兴趣学习",
            "current_level": "beginner",
            "career_background": "学生",
            "content_preference": ["text", "video"],
            "target_deadline": None
        },
        "additional_context": "希望学习 React 18 最新特性"
    }
    
    async with RoadmapTester() as tester:
        if not await tester.check_health():
            return False
        
        task_id = await tester.generate_roadmap(request)
        if not task_id:
            return False
        
        # 等待到人工审核阶段
        status = await tester.wait_for_completion(task_id, max_wait_seconds=600)
        if not status:
            return False
        
        if status.get("status") == "human_review_pending":
            console.print("\n✅ 已到达人工审核阶段")
            
            # 模拟批准
            console.print("\n📝 模拟批准路线图...")
            result = await tester.approve_roadmap(task_id, approved=True)
            if result:
                console.print("✅ 审核成功")
                
                # 继续等待完成
                final_status = await tester.wait_for_completion(task_id, max_wait_seconds=300)
                if final_status:
                    tester.print_status(final_status)
        
        return True


async def test_scenario_4_quick_test():
    """测试场景 4: 快速测试（跳过可选节点）"""
    console.print("\n" + "="*60)
    console.print("测试场景 4: 快速测试（跳过验证和审核）")
    console.print("="*60)
    console.print("注意: 需要设置环境变量 SKIP_STRUCTURE_VALIDATION=true 和 SKIP_HUMAN_REVIEW=true")
    
    request = {
        "user_id": "test-user-004",
        "session_id": f"test-session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "preferences": {
            "learning_goal": "学习 Git 版本控制",
            "available_hours_per_week": 5,
            "motivation": "工作需要",
            "current_level": "beginner",
            "career_background": "软件工程师",
            "content_preference": ["text"],
            "target_deadline": None
        },
        "additional_context": "快速学习 Git 基础命令"
    }
    
    async with RoadmapTester() as tester:
        if not await tester.check_health():
            return False
        
        task_id = await tester.generate_roadmap(request)
        if not task_id:
            return False
        
        status = await tester.wait_for_completion(task_id, max_wait_seconds=300)
        if status:
            tester.print_status(status)
        
        return True


async def main():
    """主函数"""
    if HAS_RICH:
        console.print("\n🚀 [bold]路线图生成服务测试脚本[/bold]\n")
    else:
        console.print("\n🚀 路线图生成服务测试脚本\n")
    
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="测试路线图生成服务")
    parser.add_argument(
        "--scenario",
        type=int,
        choices=[1, 2, 3, 4],
        help="选择测试场景 (1=全栈Web, 2=Python数据分析, 3=人工审核, 4=快速测试)"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API 基础 URL (默认: {DEFAULT_BASE_URL})"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="运行所有测试场景"
    )
    
    args = parser.parse_args()
    
    scenarios = {
        1: test_scenario_1_full_stack_web,
        2: test_scenario_2_python_data_science,
        3: test_scenario_3_human_review,
        4: test_scenario_4_quick_test,
    }
    
    if args.all:
        # 运行所有场景
        results = []
        for i, test_func in scenarios.items():
            try:
                result = await test_func()
                results.append((i, result))
            except Exception as e:
                console.print(f"\n❌ 场景 {i} 执行异常: {e}")
                results.append((i, False))
        
        # 汇总结果
        console.print("\n" + "="*60)
        console.print("测试结果汇总")
        console.print("="*60)
        
        table = Table(box=box.ROUNDED)
        table.add_column("场景")
        table.add_column("结果")
        
        for scenario_num, success in results:
            status = "✅ 通过" if success else "❌ 失败"
            table.add_row(f"场景 {scenario_num}", status)
        
        console.print(table)
        
    elif args.scenario:
        # 运行指定场景
        await scenarios[args.scenario]()
    else:
        # 默认运行场景 1
        console.print("未指定场景，运行默认场景 1...\n")
        await test_scenario_1_full_stack_web()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

