"""
流式传输功能测试脚本

测试 /api/v1/roadmaps/generate-stream 端点

运行方式:
    # 仅测试需求分析和框架设计
    python scripts/test_streaming.py
    
    # 测试完整流程（包括教程生成）
    python scripts/test_streaming.py --full
    
    # 使用完整流式端点
    python scripts/test_streaming.py --full-endpoint
"""
import asyncio
import httpx
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

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


def print_header(text: str):
    print(f"\n{Colors.HEADER}{'=' * 70}")
    print(f"{text}")
    print(f"{'=' * 70}{Colors.END}\n")


def print_section(text: str):
    print(f"\n{Colors.CYAN}{'-' * 50}")
    print(f"{text}")
    print(f"{'-' * 50}{Colors.END}")


async def test_streaming_endpoint(include_tutorials: bool = False, use_full_endpoint: bool = False):
    """测试流式端点"""
    print_header("🚀 流式传输功能测试")
    
    mode = "完整流程（含教程生成）" if include_tutorials else "需求分析 + 框架设计"
    print(f"{Colors.BOLD}测试模式: {mode}{Colors.END}")
    print()
    
    # 测试请求数据
    test_request = {
        "user_id": "test-user-123",
        "session_id": "test-session-456",
        "preferences": {
            "learning_goal": "学习 Python Agent 开发，能够独立开发一个完整的 多Agent 应用",
            "available_hours_per_week": 10,
            "motivation": "职业转型",
            "current_level": "beginner",
            "career_background": "市场营销 3 年经验",
            "content_preference": ["text", "interactive"]
        },
        "additional_context": "希望重点学习LangGraph"
    }
    
    # 选择端点
    if use_full_endpoint:
        url = "http://localhost:8000/api/v1/roadmaps/generate-full-stream"
    else:
        url = f"http://localhost:8000/api/v1/roadmaps/generate-stream?include_tutorials={str(include_tutorials).lower()}"
    
    print(f"📡 连接到: {url}")
    print(f"📝 学习目标: {test_request['preferences']['learning_goal']}")
    print()
    
    # 统计变量
    stats = {
        "chunk_count": 0,
        "start_time": datetime.now(),
        "intent_chunks": 0,
        "architect_chunks": 0,
        "tutorial_chunks": 0,
        "tutorials_total": 0,
        "tutorials_completed": 0,
        "tutorials_failed": 0,
        "current_batch": 0,
        "current_tutorials": {},  # concept_id -> accumulated content length
    }
    
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:  # 10 分钟超时
            async with client.stream(
                "POST",
                url,
                json=test_request,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status_code != 200:
                    print(f"{Colors.RED}❌ 错误: HTTP {response.status_code}{Colors.END}")
                    print(await response.aread())
                    return
                
                print(f"{Colors.GREEN}✅ 连接成功，开始接收流式数据...{Colors.END}\n")
                
                current_agent = None
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    # 提取 JSON 数据
                    json_str = line[6:]  # 去掉 "data: " 前缀
                    
                    try:
                        event = json.loads(json_str)
                        event_type = event.get("type")
                        agent = event.get("agent", "system")
                        
                        # 处理不同类型的事件
                        if event_type == "chunk":
                            # 流式文本片段（需求分析/框架设计）
                            content = event.get("content", "")
                            
                            # 检测 agent 变化
                            if agent != current_agent and agent != "system":
                                if current_agent:
                                    print("\n")
                                current_agent = agent
                                agent_name = {
                                    "intent_analyzer": "🧠 需求分析师",
                                    "curriculum_architect": "📚 课程架构师"
                                }.get(agent, agent)
                                print_section(f"{agent_name} 开始工作...")
                            
                            print(content, end="", flush=True)
                            stats["chunk_count"] += 1
                            if agent == "intent_analyzer":
                                stats["intent_chunks"] += 1
                            elif agent == "curriculum_architect":
                                stats["architect_chunks"] += 1
                        
                        elif event_type == "complete":
                            # 阶段完成
                            print("\n")
                            print(f"\n{Colors.GREEN}✅ {agent} 完成{Colors.END}")
                            data = event.get("data", {})
                            
                            if agent == "intent_analyzer":
                                tech_stack = data.get("key_technologies", [])
                                print(f"   关键技术: {', '.join(tech_stack[:5])}")
                            elif agent == "curriculum_architect":
                                framework = data.get("framework", {})
                                stages = framework.get("stages", [])
                                print(f"   阶段数: {len(stages)}")
                                print(f"   总时长: {framework.get('total_estimated_hours', 0)} 小时")
                        
                        # ===== 教程生成相关事件 =====
                        elif event_type == "tutorials_start":
                            stats["tutorials_total"] = event.get("total_count", 0)
                            batch_size = event.get("batch_size", 2)
                            print_header(f"📖 教程生成开始 - 共 {stats['tutorials_total']} 个教程，每批 {batch_size} 个")
                        
                        elif event_type == "batch_start":
                            stats["current_batch"] = event.get("batch_index", 0)
                            total_batches = event.get("total_batches", 0)
                            concepts = event.get("concepts", [])
                            print_section(f"📦 批次 {stats['current_batch']}/{total_batches} - 教程: {', '.join(concepts)}")
                        
                        elif event_type == "tutorial_start":
                            concept_id = event.get("concept_id", "")
                            concept_name = event.get("concept_name", "")
                            stats["current_tutorials"][concept_id] = 0
                            print(f"\n   🔵 开始: [{concept_id}] {concept_name}")
                        
                        elif event_type == "tutorial_chunk":
                            concept_id = event.get("concept_id", "")
                            content = event.get("content", "")
                            stats["tutorial_chunks"] += 1
                            
                            # 更新当前教程的内容长度
                            if concept_id in stats["current_tutorials"]:
                                stats["current_tutorials"][concept_id] += len(content)
                            
                            # 每 10 个 chunk 打印一次进度点
                            if stats["tutorial_chunks"] % 10 == 0:
                                print(".", end="", flush=True)
                        
                        elif event_type == "tutorial_complete":
                            concept_id = event.get("concept_id", "")
                            data = event.get("data", {})
                            stats["tutorials_completed"] += 1
                            
                            content_len = stats["current_tutorials"].get(concept_id, 0)
                            print(f"\n   {Colors.GREEN}✅ 完成: [{concept_id}] - {content_len} 字符{Colors.END}")
                            if data.get("content_url"):
                                print(f"      S3 URL: {data['content_url'][:60]}...")
                        
                        elif event_type == "tutorial_error":
                            concept_id = event.get("concept_id", "")
                            error = event.get("error", "")
                            stats["tutorials_failed"] += 1
                            print(f"\n   {Colors.RED}❌ 失败: [{concept_id}] - {error[:50]}{Colors.END}")
                        
                        elif event_type == "batch_complete":
                            progress = event.get("progress", {})
                            completed = progress.get("completed", 0)
                            total = progress.get("total", 0)
                            percentage = progress.get("percentage", 0)
                            print(f"\n   📊 批次完成 - 进度: {completed}/{total} ({percentage}%)")
                        
                        elif event_type == "tutorials_done":
                            summary = event.get("summary", {})
                            print_section(f"📖 教程生成完成")
                            print(f"   总数: {summary.get('total', 0)}")
                            print(f"   成功: {Colors.GREEN}{summary.get('succeeded', 0)}{Colors.END}")
                            print(f"   失败: {Colors.RED}{summary.get('failed', 0)}{Colors.END}")
                            print(f"   成功率: {summary.get('success_rate', 0)}%")
                        
                        elif event_type == "error":
                            # 错误
                            error = event.get("error") or event.get("message", "Unknown error")
                            print(f"\n\n{Colors.RED}❌ 错误 ({agent}): {error}{Colors.END}\n")
                        
                        elif event_type == "done":
                            # 全部完成
                            elapsed = (datetime.now() - stats["start_time"]).total_seconds()
                            
                            print_header("🎉 流式传输完成！")
                            
                            summary = event.get("summary", {})
                            framework = summary.get("framework", {})
                            
                            print(f"📊 {Colors.BOLD}最终结果:{Colors.END}")
                            print(f"   路线图ID: {framework.get('roadmap_id', 'N/A')}")
                            print(f"   标题: {framework.get('title', 'N/A')}")
                            print(f"   总时长: {framework.get('total_estimated_hours', 0)} 小时")
                            print(f"   推荐周数: {framework.get('recommended_completion_weeks', 0)} 周")
                            print(f"   阶段数: {len(framework.get('stages', []))}")
                            
                            # 统计模块和概念数
                            total_modules = sum(
                                len(stage.get("modules", []))
                                for stage in framework.get("stages", [])
                            )
                            total_concepts = sum(
                                len(module.get("concepts", []))
                                for stage in framework.get("stages", [])
                                for module in stage.get("modules", [])
                            )
                            print(f"   模块数: {total_modules}")
                            print(f"   概念数: {total_concepts}")
                            
                            # 教程统计（如果有）
                            tutorials_summary = summary.get("tutorials")
                            if tutorials_summary:
                                print()
                                print(f"📖 {Colors.BOLD}教程生成统计:{Colors.END}")
                                print(f"   总数: {tutorials_summary.get('total', 0)}")
                                print(f"   成功: {tutorials_summary.get('succeeded', 0)}")
                                print(f"   失败: {tutorials_summary.get('failed', 0)}")
                            
                            print()
                            print(f"⏱️  {Colors.BOLD}性能统计:{Colors.END}")
                            print(f"   总耗时: {elapsed:.1f} 秒")
                            print(f"   需求分析片段: {stats['intent_chunks']}")
                            print(f"   框架设计片段: {stats['architect_chunks']}")
                            if stats["tutorial_chunks"] > 0:
                                print(f"   教程生成片段: {stats['tutorial_chunks']}")
                            print(f"   总片段数: {stats['chunk_count'] + stats['tutorial_chunks']}")
                    
                    except json.JSONDecodeError as e:
                        print(f"\n{Colors.YELLOW}⚠️  JSON 解析错误: {e}{Colors.END}")
                        print(f"   原始数据: {json_str[:100]}...")
                        continue
    
    except httpx.ConnectError:
        print(f"{Colors.RED}❌ 无法连接到服务器{Colors.END}")
        print("   请确保后端服务正在运行: uvicorn app.main:app --reload")
    except httpx.ReadTimeout:
        print(f"{Colors.RED}❌ 读取超时{Colors.END}")
        print("   教程生成可能需要较长时间，请检查服务器日志")
    except Exception as e:
        print(f"\n{Colors.RED}❌ 测试失败: {str(e)}{Colors.END}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="测试流式传输功能",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 仅测试需求分析和框架设计
    python scripts/test_streaming.py
    
    # 测试完整流程（包括教程生成）
    python scripts/test_streaming.py --full
    
    # 使用完整流式端点
    python scripts/test_streaming.py --full-endpoint
        """
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="包含教程生成阶段（使用 include_tutorials=true 参数）"
    )
    parser.add_argument(
        "--full-endpoint",
        action="store_true",
        help="使用 /generate-full-stream 端点"
    )
    
    args = parser.parse_args()
    
    include_tutorials = args.full or args.full_endpoint
    use_full_endpoint = args.full_endpoint
    
    print()
    asyncio.run(test_streaming_endpoint(
        include_tutorials=include_tutorials,
        use_full_endpoint=use_full_endpoint
    ))
    print()


if __name__ == "__main__":
    main()
