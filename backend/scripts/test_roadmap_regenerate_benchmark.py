"""
REGENERATE 路径 benchmark 脚本。

对比对象：
1. RoadmapEditorAgent（旧全量编辑路径）
2. FastFullRegenerateEditorAgent（新 REGENERATE 快路径）
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.roadmap_editor import RoadmapEditorAgent
from app.agents.roadmap_regenerate_editor import FastFullRegenerateEditorAgent
from app.models.domain import (
    Concept,
    EditPlan,
    LearningPreferences,
    Module,
    RoadmapEditInput,
    RoadmapFramework,
    Stage,
    StageEditTask,
)
from app.utils.cost_tracker import cost_tracker


def create_sample_framework() -> RoadmapFramework:
    """创建基准测试用路线图。"""
    return RoadmapFramework(
        roadmap_id="benchmark-regenerate-roadmap",
        title="全栈开发学习路线图",
        total_estimated_hours=60.0,
        recommended_completion_weeks=8,
        stages=[
            Stage(
                stage_id="stage-1",
                name="编程基础",
                description="语言基础与工程环境",
                order=1,
                modules=[
                    Module(
                        module_id="module-1-1",
                        name="Python 基础",
                        description="掌握基础语法与模块化开发",
                        concepts=[
                            Concept(
                                concept_id="concept-1-1-1",
                                name="变量与控制流",
                                description="理解变量、条件和循环",
                                estimated_hours=6.0,
                                difficulty="easy",
                                keywords=["python", "syntax", "control-flow"],
                                prerequisites=[],
                            ),
                            Concept(
                                concept_id="concept-1-1-2",
                                name="函数与模块",
                                description="掌握函数设计与模块拆分",
                                estimated_hours=6.0,
                                difficulty="medium",
                                keywords=["function", "module", "python"],
                                prerequisites=["concept-1-1-1"],
                            ),
                        ],
                    )
                ],
            ),
            Stage(
                stage_id="stage-2",
                name="全栈开发基础",
                description="学习 API 和前端交互",
                order=2,
                modules=[
                    Module(
                        module_id="module-2-1",
                        name="FastAPI 与 React",
                        description="完成全栈接口与页面基础",
                        concepts=[
                            Concept(
                                concept_id="concept-2-1-1",
                                name="FastAPI 路由",
                                description="定义 RESTful API",
                                estimated_hours=8.0,
                                difficulty="medium",
                                keywords=["fastapi", "api", "routing"],
                                prerequisites=["concept-1-1-2"],
                            ),
                            Concept(
                                concept_id="concept-2-1-2",
                                name="React 组件",
                                description="搭建交互式页面",
                                estimated_hours=8.0,
                                difficulty="medium",
                                keywords=["react", "components", "ui"],
                                prerequisites=["concept-1-1-1"],
                            ),
                        ],
                    )
                ],
            ),
            Stage(
                stage_id="stage-3",
                name="整合与部署",
                description="完成项目交付",
                order=3,
                modules=[
                    Module(
                        module_id="module-3-1",
                        name="部署实践",
                        description="测试、部署和监控",
                        concepts=[
                            Concept(
                                concept_id="concept-3-1-1",
                                name="Docker 部署",
                                description="容器化部署基础",
                                estimated_hours=8.0,
                                difficulty="medium",
                                keywords=["docker", "deployment", "container"],
                                prerequisites=["concept-2-1-1"],
                            ),
                        ],
                    )
                ],
            ),
        ],
    )


def create_preferences() -> LearningPreferences:
    """创建测试用用户偏好。"""
    return LearningPreferences(
        learning_goal="转向后端开发专精方向",
        available_hours_per_week=10,
        motivation="希望半年内完成岗位切换",
        current_level="intermediate",
        career_background="具备 Python 开发基础，希望减少前端内容，强化后端工程能力",
        content_preference=["text", "hands_on"],
        primary_language="zh",
        secondary_language="en",
    )


def create_regenerate_plan() -> EditPlan:
    """构造 REGENERATE 编辑计划。"""
    return EditPlan(
        feedback_summary="学习目标已从全栈开发改为后端开发专精，需要整图重建并移除大部分前端内容。",
        tasks=[
            StageEditTask(
                action="REGENERATE",
                stage_id=None,
                instruction="根据新的后端开发专精目标重建路线图，重点强化 API 设计、数据库、缓存、异步任务、部署和工程实践，移除不再必要的前端学习内容。",
            )
        ],
    )


def collect_agent_stats(agent_id: str) -> dict:
    """汇总成本统计。"""
    aggregated = {"total_cost": 0.0, "total_tokens": 0, "call_count": 0}
    for candidate_agent_id, stats in cost_tracker.usage_by_agent.items():
        if candidate_agent_id == agent_id or candidate_agent_id.startswith(f"{agent_id}_"):
            aggregated["total_cost"] += stats.get("total_cost", 0.0)
            aggregated["total_tokens"] += stats.get("total_tokens", 0)
            aggregated["call_count"] += stats.get("call_count", 0)
    return aggregated


async def run_benchmark(editor_name: str, agent) -> dict:
    """运行单个编辑器 benchmark。"""
    framework = create_sample_framework()
    preferences = create_preferences()
    edit_plan = create_regenerate_plan()
    cost_tracker.reset()

    input_data = RoadmapEditInput(
        existing_framework=framework,
        user_preferences=preferences,
        edit_plan=edit_plan,
        modification_context=f"benchmark::{editor_name}",
    )
    start = time.perf_counter()
    result = await agent.execute(input_data)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    is_valid, issues = result.framework.validate_structure()
    stats = collect_agent_stats(getattr(agent, "agent_id", editor_name))
    return {
        "editor_name": editor_name,
        "elapsed_ms": elapsed_ms,
        "call_count": stats.get("call_count", 0),
        "total_tokens": stats.get("total_tokens", 0),
        "total_cost": stats.get("total_cost", 0.0),
        "modified_node_ids_count": len(result.modified_node_ids),
        "total_estimated_hours": result.framework.total_estimated_hours,
        "recommended_completion_weeks": result.framework.recommended_completion_weeks,
        "stages_count": len(result.framework.stages),
        "validate_structure_passed": is_valid,
        "issues_count": len(issues),
        "summary": result.modification_summary,
    }


async def main() -> None:
    """执行 benchmark。"""
    print("=" * 80)
    print("Roadmap Regenerate Benchmark")
    print("=" * 80)

    legacy_agent = RoadmapEditorAgent()
    fast_agent = FastFullRegenerateEditorAgent()

    legacy_metrics = await run_benchmark("legacy_regenerate_editor", legacy_agent)
    print("Legacy regenerate editor completed:")
    print(json.dumps(legacy_metrics, ensure_ascii=False, indent=2))
    print("-" * 80)

    fast_metrics = await run_benchmark("fast_full_regenerate_editor", fast_agent)
    print("Fast regenerate editor completed:")
    print(json.dumps(fast_metrics, ensure_ascii=False, indent=2))
    print("-" * 80)

    comparison = {
        "legacy_editor": legacy_metrics,
        "fast_regenerate_editor": fast_metrics,
        "delta": {
            "elapsed_ms_saved": legacy_metrics["elapsed_ms"] - fast_metrics["elapsed_ms"],
            "token_saved": legacy_metrics["total_tokens"] - fast_metrics["total_tokens"],
            "call_saved": legacy_metrics["call_count"] - fast_metrics["call_count"],
        },
    }

    output_dir = project_root / "scripts" / "benchmark_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "roadmap_regenerate_benchmark.json"
    output_file.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("Benchmark comparison:")
    print(json.dumps(comparison["delta"], ensure_ascii=False, indent=2))
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
