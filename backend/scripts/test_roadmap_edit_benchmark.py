"""
路线图编辑阶段 benchmark 脚本。

对比对象：
1. EditPlanAnalyzerAgent
2. RoadmapEditorAgent（旧全量编辑路径）
3. JsonPatchEditorAgent（新局部 patch 路径）
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.edit_plan_analyzer import EditPlanAnalyzerAgent
from app.agents.json_patch_editor import JsonPatchEditorAgent
from app.agents.roadmap_editor import RoadmapEditorAgent
from app.models.domain import (
    Concept,
    EditPlanAnalyzerInput,
    LearningPreferences,
    Module,
    RoadmapEditInput,
    RoadmapFramework,
    Stage,
)
from app.utils.cost_tracker import cost_tracker


def create_sample_framework() -> RoadmapFramework:
    """构造符合当前 schema 的示例路线图。"""
    return RoadmapFramework(
        roadmap_id="benchmark-roadmap-fullstack",
        title="全栈开发学习路线图",
        total_estimated_hours=51.0,
        recommended_completion_weeks=6,
        stages=[
            Stage(
                stage_id="stage-1",
                name="编程基础与工程环境",
                description="建立语言基础、开发环境和工程习惯。",
                order=1,
                modules=[
                    Module(
                        module_id="module-1-1",
                        name="Python 与 JavaScript 基础",
                        description="掌握基础语法与常用工程实践。",
                        concepts=[
                            Concept(
                                concept_id="concept-1-1-1",
                                name="Python 语法基础",
                                description="变量、流程控制、函数与模块。",
                                estimated_hours=6.0,
                                difficulty="easy",
                                keywords=["python", "syntax"],
                                prerequisites=[],
                                content_status="completed",
                                tutorial_id="tut-1-1-1",
                                content_ref="s3://bucket/concept-1-1-1.md",
                                resources_status="completed",
                                resources_id="res-1-1-1",
                                resources_count=3,
                                quiz_status="completed",
                                quiz_id="quiz-1-1-1",
                                quiz_questions_count=5,
                            ),
                            Concept(
                                concept_id="concept-1-1-2",
                                name="异步编程基础",
                                description="理解异步任务和事件循环。",
                                estimated_hours=4.0,
                                difficulty="medium",
                                keywords=["async", "event-loop"],
                                prerequisites=["concept-1-1-1"],
                            ),
                        ],
                    ),
                ],
            ),
            Stage(
                stage_id="stage-2",
                name="Web 应用开发",
                description="掌握后端接口与前端基础能力。",
                order=2,
                modules=[
                    Module(
                        module_id="module-2-1",
                        name="FastAPI 接口开发",
                        description="学习 REST API、依赖注入和异常处理。",
                        concepts=[
                            Concept(
                                concept_id="concept-2-1-1",
                                name="路由与请求处理",
                                description="掌握接口定义和参数校验。",
                                estimated_hours=5.0,
                                difficulty="medium",
                                keywords=["fastapi", "routing"],
                                prerequisites=["concept-1-1-2"],
                            ),
                            Concept(
                                concept_id="concept-2-1-2",
                                name="高级依赖注入",
                                description="处理复杂依赖与资源生命周期。",
                                estimated_hours=7.0,
                                difficulty="hard",
                                keywords=["dependency-injection", "lifecycle"],
                                prerequisites=["concept-2-1-1"],
                            ),
                        ],
                    ),
                    Module(
                        module_id="module-2-2",
                        name="React 前端基础",
                        description="组件、状态与页面组织。",
                        concepts=[
                            Concept(
                                concept_id="concept-2-2-1",
                                name="组件与 Props",
                                description="理解组件拆分与单向数据流。",
                                estimated_hours=5.0,
                                difficulty="medium",
                                keywords=["react", "props"],
                                prerequisites=["concept-1-1-1"],
                            ),
                        ],
                    ),
                ],
            ),
            Stage(
                stage_id="stage-3",
                name="项目整合与部署",
                description="完成全栈整合、测试与部署。",
                order=3,
                modules=[
                    Module(
                        module_id="module-3-1",
                        name="项目部署基础",
                        description="部署、监控与基础运维。",
                        concepts=[
                            Concept(
                                concept_id="concept-3-1-1",
                                name="容器化部署",
                                description="理解 Docker 打包与部署流程。",
                                estimated_hours=6.0,
                                difficulty="medium",
                                keywords=["docker", "deployment"],
                                prerequisites=["concept-2-1-1"],
                            ),
                            Concept(
                                concept_id="concept-3-1-2",
                                name="自动化测试与发布",
                                description="建立基础 CI/CD 认知。",
                                estimated_hours=5.0,
                                difficulty="medium",
                                keywords=["ci", "cd", "testing"],
                                prerequisites=["concept-3-1-1"],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def create_preferences() -> LearningPreferences:
    """构造示例用户偏好。"""
    return LearningPreferences(
        learning_goal="成为能够独立交付中小型 Web 项目的全栈开发工程师",
        available_hours_per_week=8,
        motivation="希望在半年内完成转岗准备",
        current_level="intermediate",
        career_background="有数据分析与 Python 使用经验，希望补齐 Web 开发能力",
        content_preference=["text", "hands_on"],
        primary_language="zh",
        secondary_language="en",
    )


def build_feedback() -> str:
    """构造用于 analyzer 的统一反馈文本。"""
    return (
        "请在第一阶段后补一个数据库基础阶段，覆盖 SQL 基础、关系模型设计和 ORM 入门；"
        "第二阶段有点太难了，请删掉高级依赖注入，整体更适合转岗学习；"
        "最后再加一点实战导向，让部署阶段包含一个小型全栈项目演练。"
    )


async def run_analyzer(
    framework: RoadmapFramework,
    preferences: LearningPreferences,
    feedback: str,
) -> tuple[dict, object]:
    """运行编辑计划分析。"""
    cost_tracker.reset()
    agent = EditPlanAnalyzerAgent()
    input_data = EditPlanAnalyzerInput(
        user_feedback=feedback,
        existing_framework=framework,
        user_preferences=preferences,
    )
    start = time.perf_counter()
    result = await agent.execute(input_data)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    stats = cost_tracker.get_agent_stats(agent.agent_id) or {}
    return (
        {
            "elapsed_ms": elapsed_ms,
            "tasks_count": len(result.edit_plan.tasks),
            "confidence": result.confidence,
            "agent_stats": stats,
            "edit_plan": result.edit_plan.model_dump(),
        },
        result,
    )


async def run_editor_benchmark(
    editor_name: str,
    agent,
    framework: RoadmapFramework,
    preferences: LearningPreferences,
    edit_plan,
) -> dict:
    """运行单个编辑器 benchmark。"""
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
    stats = _collect_agent_stats(getattr(agent, "agent_id", editor_name))
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


def _collect_agent_stats(agent_id: str) -> dict:
    """汇总某个 Agent 的成本统计。"""
    aggregated = {
        "total_cost": 0.0,
        "total_tokens": 0,
        "call_count": 0,
    }
    for candidate_agent_id, stats in cost_tracker.usage_by_agent.items():
        if candidate_agent_id == agent_id or candidate_agent_id.startswith(f"{agent_id}_"):
            aggregated["total_cost"] += stats.get("total_cost", 0.0)
            aggregated["total_tokens"] += stats.get("total_tokens", 0)
            aggregated["call_count"] += stats.get("call_count", 0)
    return aggregated


async def main() -> None:
    """执行 benchmark。"""
    framework = create_sample_framework()
    preferences = create_preferences()
    feedback = build_feedback()

    print("=" * 80)
    print("Roadmap Edit Benchmark")
    print("=" * 80)
    print("Feedback:")
    print(feedback)
    print("-" * 80)

    analyzer_metrics, analyzer_result = await run_analyzer(
        framework=framework,
        preferences=preferences,
        feedback=feedback,
    )
    print("Analyzer completed:")
    print(json.dumps(analyzer_metrics, ensure_ascii=False, indent=2))
    print("-" * 80)

    legacy_agent = RoadmapEditorAgent()
    patch_agent = JsonPatchEditorAgent()

    legacy_metrics = await run_editor_benchmark(
        editor_name="legacy_full_editor",
        agent=legacy_agent,
        framework=framework,
        preferences=preferences,
        edit_plan=analyzer_result.edit_plan,
    )
    print("Legacy editor completed:")
    print(json.dumps(legacy_metrics, ensure_ascii=False, indent=2))
    print("-" * 80)

    patch_metrics = await run_editor_benchmark(
        editor_name="json_patch_editor",
        agent=patch_agent,
        framework=framework,
        preferences=preferences,
        edit_plan=analyzer_result.edit_plan,
    )
    print("JSON Patch editor completed:")
    print(json.dumps(patch_metrics, ensure_ascii=False, indent=2))
    print("-" * 80)

    comparison = {
        "feedback": feedback,
        "analyzer": analyzer_metrics,
        "legacy_editor": legacy_metrics,
        "json_patch_editor": patch_metrics,
        "delta": {
            "elapsed_ms_saved": legacy_metrics["elapsed_ms"] - patch_metrics["elapsed_ms"],
            "token_saved": legacy_metrics["total_tokens"] - patch_metrics["total_tokens"],
            "call_saved": legacy_metrics["call_count"] - patch_metrics["call_count"],
        },
    }

    output_dir = project_root / "scripts" / "benchmark_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "roadmap_edit_benchmark.json"
    output_file.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Benchmark comparison:")
    print(json.dumps(comparison["delta"], ensure_ascii=False, indent=2))
    print(f"Output saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
