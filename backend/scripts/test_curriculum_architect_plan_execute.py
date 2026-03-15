"""
CurriculumArchitectAgent Plan-and-Execute 模式验证脚本

验证目标：
1. Phase 1（本地原型）：验证 outline→stage→merge 的合并逻辑、ID 衔接、
   依赖修复、validate_structure() 是否通过，不调用真实 LLM。
2. Phase 2（真实 LLM 验证）：运行新版 plan-and-execute 路径，输出总耗时、
   Planner 耗时、Stage 并行耗时、结构规模和结构校验结果，并将结果落盘。

用法：
    # 运行全部验证（本地原型 + 真实 LLM 验证）
    python scripts/test_curriculum_architect_plan_execute.py

    # 只运行本地原型验证（无需 LLM 调用，速度极快）
    python scripts/test_curriculum_architect_plan_execute.py --local

    # 只运行真实 LLM 验证
    python scripts/test_curriculum_architect_plan_execute.py --benchmark

    # 使用 Gemini 模型（通过 OpenAI 兼容网关）
    python scripts/test_curriculum_architect_plan_execute.py --benchmark --gemini

    # 使用 Claude 模型（推荐，效果更好）
    python scripts/test_curriculum_architect_plan_execute.py --benchmark --claude

"""
import asyncio
import sys
import time
import json
import argparse
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.agents.curriculum_architect import (
    CurriculumArchitectAgent,
    PlannedStage,
    RoadmapOutline,
)
from app.agents.framework_normalizer import normalize_framework_ids
from app.models.domain import (
    CurriculumDesignInput,
    CurriculumDesignOutput,
    IntentAnalysisOutput,
    LearningPreferences,
    SimplifiedStage,
    SimplifiedModule,
    SimplifiedConcept,
    SimplifiedRoadmapFramework,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


# ============================================================
# 共用 Mock 数据
# ============================================================

def create_mock_intent_analysis() -> IntentAnalysisOutput:
    """创建模拟的意图分析输出"""
    return IntentAnalysisOutput(
        parsed_goal="学习 Python Web 开发，能够独立开发和部署一个完整的 Web 应用",
        key_technologies=[
            "Python",
            "FastAPI",
            "SQLAlchemy",
            "PostgreSQL",
            "Docker",
            "Redis",
        ],
        difficulty_profile="中级难度，需要扎实的 Python 基础和数据库知识",
        time_constraint="建议投入 3-6 个月学习，每周 10-15 小时",
        recommended_focus=[
            "FastAPI 框架核心特性和最佳实践",
            "数据库设计与 ORM 使用",
            "异步编程与性能优化",
            "Docker 容器化部署",
        ],
        user_profile_summary="有 2 年 Python 基础经验，做过简单的脚本开发，希望转向 Web 开发",
        skill_gap_analysis=[
            "缺乏 Web 框架实战经验",
            "数据库设计能力不足",
            "对容器化部署不熟悉",
        ],
        personalized_suggestions=[
            "从 FastAPI 快速入门开始，边学边做",
            "重点练习数据库设计和 SQL 查询",
            "通过实战项目巩固所学知识",
        ],
        roadmap_id="python-web-dev-plan-execute-test-001",
    )


def create_mock_learning_preferences() -> LearningPreferences:
    """创建模拟的学习偏好"""
    return LearningPreferences(
        learning_goal="成为 Python Web 开发工程师",
        available_hours_per_week=12,
        motivation="转行进入互联网行业",
        current_level="intermediate",
        career_background="2 年 Python 脚本开发经验，做过数据分析工作",
        content_preference=["visual", "hands_on"],
        primary_language="zh",
        secondary_language="en",
    )


def create_mock_input() -> CurriculumDesignInput:
    """创建标准测试输入"""
    return CurriculumDesignInput(
        intent_analysis=create_mock_intent_analysis(),
        user_preferences=create_mock_learning_preferences(),
    )


# ============================================================
# Phase 1：本地原型验证（不调用真实 LLM）
# ============================================================

def create_mock_outline() -> RoadmapOutline:
    """创建模拟的路线图大纲（模拟 Planner 输出）"""
    return RoadmapOutline(
        roadmap_id="python-web-dev-plan-execute-test-001",
        title="Python Web 开发完整学习路线",
        total_estimated_hours=120.0,
        recommended_completion_weeks=10,
        stages=[
            PlannedStage(
                stage_id="stage-1",
                name="Python 基础强化",
                description="巩固 Python 核心语法，建立扎实的编程基础",
                order=1,
                estimated_hours=30.0,
                focus_areas=["Python 语法", "面向对象编程", "函数式编程", "标准库"],
            ),
            PlannedStage(
                stage_id="stage-2",
                name="Web 框架入门",
                description="掌握 FastAPI 框架和 HTTP 基础，构建第一个 API 服务",
                order=2,
                estimated_hours=50.0,
                focus_areas=["FastAPI", "HTTP 协议", "RESTful API", "数据库 ORM"],
            ),
            PlannedStage(
                stage_id="stage-3",
                name="生产环境实践",
                description="学习 Docker 容器化、测试、CI/CD，将应用部署到生产环境",
                order=3,
                estimated_hours=40.0,
                focus_areas=["Docker", "自动化测试", "CI/CD", "云部署"],
            ),
        ],
    )


def create_mock_stages() -> list[SimplifiedStage]:
    """创建模拟的 Stage 生成结果（模拟并行 Executor 输出）"""
    stage1 = SimplifiedStage(
        stage_id="stage-1",
        name="Python 基础强化",
        description="巩固 Python 核心语法，建立扎实的编程基础",
        order=1,
        modules=[
            SimplifiedModule(
                module_id="mod-1-1",
                name="Python 核心语法",
                description="掌握 Python 的基本数据类型、控制流和函数",
                concepts=[
                    SimplifiedConcept(
                        concept_id="c-1-1-1",
                        name="变量与数据类型",
                        description="掌握 Python 的基本数据类型（int, str, list, dict 等）及类型转换",
                        estimated_hours=2.0,
                        prerequisites=[],
                        difficulty="easy",
                        keywords=["数据类型", "变量", "类型转换", "字符串操作"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-1-1-2",
                        name="函数与模块",
                        description="理解函数定义、参数传递、返回值和模块导入机制",
                        estimated_hours=3.0,
                        prerequisites=["c-1-1-1"],
                        difficulty="medium",
                        keywords=["函数", "参数", "模块", "import", "作用域"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-1-1-3",
                        name="错误处理与异常",
                        description="学习 try/except 机制，编写健壮的错误处理代码",
                        estimated_hours=2.5,
                        prerequisites=["c-1-1-2"],
                        difficulty="medium",
                        keywords=["异常", "try-except", "错误处理", "raise"],
                    ),
                ],
            ),
            SimplifiedModule(
                module_id="mod-1-2",
                name="面向对象编程",
                description="掌握 OOP 核心概念，用类和对象组织复杂逻辑",
                concepts=[
                    SimplifiedConcept(
                        concept_id="c-1-2-1",
                        name="类与对象",
                        description="理解类的定义、实例化、属性和方法",
                        estimated_hours=4.0,
                        prerequisites=["c-1-1-2"],
                        difficulty="medium",
                        keywords=["类", "对象", "OOP", "实例化", "__init__"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-1-2-2",
                        name="继承与多态",
                        description="理解继承链、方法重写和多态性在实际开发中的应用",
                        estimated_hours=4.0,
                        prerequisites=["c-1-2-1"],
                        difficulty="medium",
                        keywords=["继承", "多态", "super()", "方法重写"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-1-2-3",
                        name="装饰器与上下文管理器",
                        description="掌握 Python 装饰器原理和 with 语句的高级用法",
                        estimated_hours=5.0,
                        prerequisites=["c-1-2-1"],
                        difficulty="hard",
                        keywords=["装饰器", "上下文管理器", "with", "@property"],
                    ),
                ],
            ),
        ],
    )

    stage2 = SimplifiedStage(
        stage_id="stage-2",
        name="Web 框架入门",
        description="掌握 FastAPI 框架和 HTTP 基础，构建第一个 API 服务",
        order=2,
        modules=[
            SimplifiedModule(
                module_id="mod-2-1",
                name="FastAPI 基础",
                description="理解 FastAPI 的核心特性：路由、依赖注入、数据验证",
                concepts=[
                    SimplifiedConcept(
                        concept_id="c-2-1-1",
                        name="FastAPI 路由与请求处理",
                        description="掌握路由定义、路径参数、查询参数和请求体的处理方式",
                        estimated_hours=3.0,
                        prerequisites=["c-1-1-2"],
                        difficulty="medium",
                        keywords=["FastAPI", "路由", "路径参数", "HTTP 方法"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-2-1-2",
                        name="Pydantic 数据验证",
                        description="使用 Pydantic 模型自动验证请求和响应数据，提高 API 可靠性",
                        estimated_hours=3.0,
                        prerequisites=["c-2-1-1"],
                        difficulty="medium",
                        keywords=["Pydantic", "数据验证", "BaseModel", "类型注解"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-2-1-3",
                        name="依赖注入系统",
                        description="理解 FastAPI 的依赖注入机制，实现可复用的公共逻辑",
                        estimated_hours=4.0,
                        prerequisites=["c-2-1-2"],
                        difficulty="hard",
                        keywords=["依赖注入", "Depends", "中间件", "认证"],
                    ),
                ],
            ),
            SimplifiedModule(
                module_id="mod-2-2",
                name="数据库集成",
                description="集成 PostgreSQL 数据库，掌握 SQLAlchemy ORM 的使用",
                concepts=[
                    SimplifiedConcept(
                        concept_id="c-2-2-1",
                        name="SQLAlchemy 模型定义",
                        description="定义 ORM 模型，理解表结构和字段类型映射",
                        estimated_hours=4.0,
                        prerequisites=["c-2-1-1"],
                        difficulty="medium",
                        keywords=["SQLAlchemy", "ORM", "模型", "数据库表"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-2-2-2",
                        name="数据库查询与事务",
                        description="使用 Session 执行 CRUD 操作，理解事务管理和异步 Session",
                        estimated_hours=5.0,
                        prerequisites=["c-2-2-1"],
                        difficulty="hard",
                        keywords=["CRUD", "Session", "事务", "AsyncSession"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-2-2-3",
                        name="Alembic 数据库迁移",
                        description="使用 Alembic 管理数据库 Schema 变更，实现版本化迁移",
                        estimated_hours=3.0,
                        prerequisites=["c-2-2-1"],
                        difficulty="medium",
                        keywords=["Alembic", "数据库迁移", "Schema", "版本管理"],
                    ),
                ],
            ),
        ],
    )

    stage3 = SimplifiedStage(
        stage_id="stage-3",
        name="生产环境实践",
        description="学习 Docker 容器化、测试、CI/CD，将应用部署到生产环境",
        order=3,
        modules=[
            SimplifiedModule(
                module_id="mod-3-1",
                name="容器化与部署",
                description="掌握 Docker 容器化技术，将 FastAPI 应用打包并部署",
                concepts=[
                    SimplifiedConcept(
                        concept_id="c-3-1-1",
                        name="Docker 基础",
                        description="理解容器化概念，编写 Dockerfile，构建和运行容器",
                        estimated_hours=4.0,
                        prerequisites=["c-2-1-1"],
                        difficulty="medium",
                        keywords=["Docker", "容器", "Dockerfile", "镜像"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-3-1-2",
                        name="Docker Compose 多服务编排",
                        description="使用 Docker Compose 编排 FastAPI + PostgreSQL + Redis 多服务栈",
                        estimated_hours=5.0,
                        prerequisites=["c-3-1-1"],
                        difficulty="hard",
                        keywords=["Docker Compose", "多容器", "服务编排", "环境变量"],
                    ),
                ],
            ),
            SimplifiedModule(
                module_id="mod-3-2",
                name="测试与质量保证",
                description="编写单元测试和集成测试，保障代码质量",
                concepts=[
                    SimplifiedConcept(
                        concept_id="c-3-2-1",
                        name="pytest 单元测试",
                        description="使用 pytest 编写单元测试，理解 fixture 和测试覆盖率",
                        estimated_hours=4.0,
                        prerequisites=["c-1-1-3"],
                        difficulty="medium",
                        keywords=["pytest", "单元测试", "fixture", "测试覆盖率"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-3-2-2",
                        name="FastAPI 接口测试",
                        description="使用 TestClient 对 API 端点进行集成测试，模拟真实请求",
                        estimated_hours=4.0,
                        prerequisites=["c-3-2-1", "c-2-1-1"],
                        difficulty="medium",
                        keywords=["TestClient", "集成测试", "接口测试", "mock"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-3-2-3",
                        name="CI/CD 流水线搭建",
                        description="使用 GitHub Actions 配置自动化测试和部署流水线",
                        estimated_hours=5.0,
                        prerequisites=["c-3-1-2", "c-3-2-1"],
                        difficulty="hard",
                        keywords=["GitHub Actions", "CI/CD", "自动化部署", "流水线"],
                    ),
                ],
            ),
        ],
    )

    return [stage1, stage2, stage3]


async def test_local_prototype() -> bool:
    """
    Phase 1：本地原型验证

    使用 mock 数据验证以下逻辑（不调用真实 LLM）：
    - _merge_to_simplified_framework() 合并正确
    - _convert_to_full_framework() 字段补充完整
    - _check_and_fix_dependencies() 依赖修复正常
    - normalize_framework_ids() ID 规范化正确
    - validate_structure() 最终结构合法

    Returns:
        True 表示验证通过，False 表示失败
    """
    print()
    print("=" * 80)
    print("Phase 1：本地原型验证（无 LLM 调用）")
    print("=" * 80)

    agent = CurriculumArchitectAgent()
    outline = create_mock_outline()
    mock_stages = create_mock_stages()

    print(f"\n[1/5] 模拟 Planner 输出：")
    print(f"  路线图标题：{outline.title}")
    print(f"  总学习时长：{outline.total_estimated_hours} 小时")
    print(f"  推荐完成周数：{outline.recommended_completion_weeks} 周")
    print(f"  Stage 数量：{len(outline.stages)}")
    for s in outline.stages:
        print(f"    - Stage {s.order}（{s.stage_id}）：{s.name}，{s.estimated_hours}h")
        print(f"      核心重点：{', '.join(s.focus_areas)}")

    print(f"\n[2/5] 模拟并行 Stage 生成结果：")
    for stage in mock_stages:
        concepts_count = sum(len(m.concepts) for m in stage.modules)
        print(
            f"  - {stage.stage_id}（order={stage.order}）：{stage.name} → "
            f"{len(stage.modules)} 模块，{concepts_count} 概念"
        )

    print(f"\n[3/5] 测试 _merge_to_simplified_framework()...")
    simplified_framework = agent._merge_to_simplified_framework(outline, mock_stages)
    assert simplified_framework.roadmap_id == outline.roadmap_id, "roadmap_id 不匹配"
    assert simplified_framework.title == outline.title, "title 不匹配"
    assert len(simplified_framework.stages) == 3, f"期望 3 个 Stage，实际 {len(simplified_framework.stages)}"
    # 验证按 order 排序
    orders = [s.order for s in simplified_framework.stages]
    assert orders == sorted(orders), f"stages 未按 order 排序: {orders}"
    print(f"  ✓ 合并成功：{len(simplified_framework.stages)} 个 Stage，按 order 正确排序")

    print(f"\n[4/5] 测试后处理流程（convert → fix_deps → normalize）...")
    full_framework = agent._convert_to_full_framework(simplified_framework)
    full_framework, fixes = agent._check_and_fix_dependencies(full_framework)
    full_framework = normalize_framework_ids(full_framework)

    total_modules = sum(len(s.modules) for s in full_framework.stages)
    total_concepts = sum(
        len(m.concepts) for s in full_framework.stages for m in s.modules
    )

    print(f"  ✓ 转换完成：{len(full_framework.stages)} Stages / {total_modules} Modules / {total_concepts} Concepts")
    print(f"  ✓ 依赖修复：{len(fixes)} 处修复")

    # 验证 ID 规范化结果
    first_stage = full_framework.stages[0]
    print(f"  ✓ 规范化后 Stage ID 示例：{first_stage.stage_id}")
    first_module = first_stage.modules[0]
    print(f"  ✓ 规范化后 Module ID 示例：{first_module.module_id}")
    first_concept = first_module.concepts[0]
    print(f"  ✓ 规范化后 Concept ID 示例：{first_concept.concept_id}")

    # 验证默认字段补充
    assert first_concept.content_status == "pending", "content_status 默认值错误"
    assert first_concept.tutorial_id is None, "tutorial_id 应为 None"
    assert first_concept.resources_status == "pending", "resources_status 默认值错误"
    assert first_concept.quiz_status == "pending", "quiz_status 默认值错误"
    print(f"  ✓ Concept 默认字段补充正确（content/resources/quiz status = pending）")

    print(f"\n[5/5] 运行 validate_structure()...")
    is_valid, issues = full_framework.validate_structure()

    if is_valid:
        print(f"  ✓ 结构验证通过，无问题")
    else:
        print(f"  ⚠️  发现 {len(issues)} 个问题：")
        for issue in issues[:5]:
            print(f"    - [{issue.severity}] {issue.issue}")

    print()
    print("=" * 80)
    if is_valid:
        print("✅ Phase 1 通过：本地原型合并逻辑正确，结构验证通过")
    else:
        print(f"❌ Phase 1 失败：结构验证发现 {len(issues)} 个问题")
    print("=" * 80)

    return is_valid


# ============================================================
# Phase 2：真实 LLM 验证
# ============================================================

def _print_framework_stats(label: str, result: CurriculumDesignOutput, elapsed: float):
    """打印框架统计信息"""
    framework = result.framework
    total_modules = sum(len(s.modules) for s in framework.stages)
    total_concepts = sum(
        len(m.concepts) for s in framework.stages for m in s.modules
    )
    is_valid, issues = framework.validate_structure()

    print(f"\n  [{label}]")
    print(f"    标题：{framework.title}")
    print(f"    结构：{len(framework.stages)} Stages × ~{total_modules // max(len(framework.stages), 1)} Modules × ~{total_concepts // max(total_modules, 1)} Concepts")
    print(f"    总计：{total_modules} 模块，{total_concepts} 概念")
    print(f"    总学时：{framework.total_estimated_hours}h / {framework.recommended_completion_weeks} 周")
    print(f"    结构校验：{'✅ 通过' if is_valid else f'❌ {len(issues)} 个问题'}")
    print(f"    耗时：{elapsed:.2f}s")

    return {
        "stages": len(framework.stages),
        "modules": total_modules,
        "concepts": total_concepts,
        "total_hours": framework.total_estimated_hours,
        "is_valid": is_valid,
        "issues_count": len(issues),
        "elapsed": elapsed,
    }


async def run_plan_execute(
    agent: CurriculumArchitectAgent, input_data: CurriculumDesignInput
):
    """运行 plan-and-execute 方案（新版并行生成）"""
    print("\n[New] 运行 plan-and-execute 并行生成方案...")
    print("  ⏳ 阶段 1：生成 Stage 级大纲（Planner）...")

    timings: dict[str, float] = {}
    total_start = time.time()

    # Planner 阶段
    outline_start = time.time()
    outline = await agent._plan_roadmap_outline(input_data)
    timings["planner"] = time.time() - outline_start

    print(
        f"  ✓ Planner 完成（{timings['planner']:.2f}s）："
        f"{len(outline.stages)} 个 Stage，总 {outline.total_estimated_hours}h"
    )
    for ps in outline.stages:
        print(
            f"    - Stage {ps.order}：{ps.name}（{ps.estimated_hours}h）"
            f" | 重点：{', '.join(ps.focus_areas[:3])}"
        )

    # 并行 Stage 生成阶段
    print(f"\n  ⏳ 阶段 2：并行生成 {len(outline.stages)} 个 Stage...")
    prompt_context = agent._prepare_prompt_context(input_data)

    stages_start = time.time()
    stage_tasks = [
        agent._generate_stage(ps, outline, prompt_context)
        for ps in outline.stages
    ]
    stages = list(await asyncio.gather(*stage_tasks))
    timings["stages_parallel"] = time.time() - stages_start

    for stage in sorted(stages, key=lambda s: s.order):
        concepts_count = sum(len(m.concepts) for m in stage.modules)
        print(
            f"  ✓ {stage.stage_id}（{stage.name}）："
            f"{len(stage.modules)} 模块，{concepts_count} 概念"
        )
    print(f"  → 并行生成耗时：{timings['stages_parallel']:.2f}s")

    # Merger + 后处理阶段
    print(f"\n  ⏳ 阶段 3：合并、修正依赖、规范化 ID...")
    simplified_framework = agent._merge_to_simplified_framework(outline, stages)
    simplified_framework.roadmap_id = outline.roadmap_id
    full_framework = agent._convert_to_full_framework(simplified_framework)
    full_framework, fixes = agent._check_and_fix_dependencies(full_framework)
    full_framework = normalize_framework_ids(full_framework)

    timings["total"] = time.time() - total_start

    if fixes:
        print(f"  ⚠️  依赖修复：{len(fixes)} 处（跨 Stage 依赖已清理）")

    result = CurriculumDesignOutput(framework=full_framework)
    return result, timings


def print_verification_summary(
    new_stats: dict,
    new_timings: dict,
):
    """打印新版方案验证结果"""
    print()
    print("=" * 80)
    print("验证结果汇总")
    print("=" * 80)
    print(f"\n⏱️  耗时明细：")
    print(f"  总耗时            : {new_timings['total']:.2f}s")
    print(f"  Planner 阶段      : {new_timings.get('planner', 0):.2f}s")
    print(f"  并行 Stage 生成   : {new_timings.get('stages_parallel', 0):.2f}s")
    print(f"\n📊 结构规模：")
    print(f"  Stages            : {new_stats['stages']}")
    print(f"  Modules           : {new_stats['modules']}")
    print(f"  Concepts          : {new_stats['concepts']}")
    print(f"  总学时(h)         : {new_stats['total_hours']}")
    print(f"\n🔍 结构校验：")
    print(
        f"  {'✅ 通过' if new_stats['is_valid'] else f'❌ {new_stats['issues_count']} 个问题'}"
    )

    print()
    print("=" * 80)
    overall_pass = new_stats["is_valid"]
    if overall_pass:
        print("✅ 验证通过：新版 plan-and-execute 结构合法")
    else:
        print("❌ 验证失败：结构校验未通过，请检查 Stage/Concept 生成质量")
    print("=" * 80)


def save_results(
    new_result: CurriculumDesignOutput,
    output_dir: Path,
):
    """保存新版方案输出到 JSON 文件"""
    output_dir.mkdir(exist_ok=True)

    new_file = output_dir / "plan_execute_output.json"
    with open(new_file, "w", encoding="utf-8") as f:
        json.dump(new_result.model_dump(), f, ensure_ascii=False, indent=2)
    print(f"\n  ✓ 新版输出已保存到：{new_file}")


async def run_benchmark(
    agent: CurriculumArchitectAgent,
    input_data: CurriculumDesignInput,
):
    """
    Phase 2：真实 LLM 验证

    Args:
        agent: 已配置的 CurriculumArchitectAgent 实例
        input_data: 测试输入数据
    """
    print()
    print("=" * 80)
    print("Phase 2：真实 LLM 验证")
    print("=" * 80)
    print(f"\n模型配置：{agent.model_provider} / {agent.model_name}")
    print(f"测试输入：{input_data.intent_analysis.parsed_goal}")
    print(f"Roadmap ID：{input_data.intent_analysis.roadmap_id}")

    new_result, new_timings = await run_plan_execute(agent, input_data)
    new_stats = _print_framework_stats("新版 plan-and-execute", new_result, new_timings["total"])
    print_verification_summary(new_stats, new_timings)

    output_dir = project_root / "scripts"
    save_results(new_result, output_dir)

    return new_result


# ============================================================
# 入口
# ============================================================

async def main():
    parser = argparse.ArgumentParser(
        description="CurriculumArchitectAgent Plan-and-Execute 验证脚本"
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="只运行本地原型验证（无 LLM 调用）",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="运行真实 LLM 验证（仅新版 plan-and-execute）",
    )
    parser.add_argument(
        "--claude",
        action="store_true",
        help="使用 Claude 模型（更强的 JSON 结构化能力）",
    )
    parser.add_argument(
        "--gemini",
        action="store_true",
        help="使用 Gemini 模型（通过 OpenAI 兼容网关）",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="只显示配置诊断信息",
    )
    args = parser.parse_args()

    if args.diagnose:
        print("\n配置诊断：")
        print(f"  Provider：{settings.ARCHITECT_PROVIDER}")
        print(f"  Model：{settings.ARCHITECT_MODEL}")
        print(f"  Base URL：{settings.ARCHITECT_BASE_URL or '（默认）'}")
        print(f"  API Key：{'已配置' if settings.ARCHITECT_API_KEY else '未配置'}")
        print(f"  Gemini Model：{settings.GEMINI_MODEL}")
        print(f"  Gemini Base URL：{settings.get_gemini_openai_base_url or '（默认）'}")
        print(f"  Gemini API Key：{'已配置' if settings.GEMINI_API_KEY else '未配置'}")
        return

    if args.claude and args.gemini:
        print("❌ 错误：不能同时指定 --claude 和 --gemini")
        sys.exit(1)

    if args.gemini:
        agent = CurriculumArchitectAgent(
            model_provider="openai",
            model_name=settings.GEMINI_MODEL,
            base_url=settings.get_gemini_openai_base_url,
            api_key=settings.GEMINI_API_KEY,
        )
    elif args.claude:
        agent = CurriculumArchitectAgent(
            model_provider="anthropic",
            model_name="claude-3-5-sonnet-20241022",
            base_url=None,
            api_key=settings.ARCHITECT_API_KEY,
        )
    else:
        agent = CurriculumArchitectAgent()

    if args.local:
        success = await test_local_prototype()
        sys.exit(0 if success else 1)

    elif args.benchmark:
        input_data = create_mock_input()
        await run_benchmark(agent, input_data)

    else:
        # 默认：本地原型 + 真实 LLM 验证（完整验证）
        print("\n运行完整验证：Phase 1（本地原型）+ Phase 2（真实 LLM 验证）")

        local_ok = await test_local_prototype()
        if not local_ok:
            print("\n❌ Phase 1 失败，中止 Phase 2")
            sys.exit(1)

        print("\n本地原型验证通过，继续运行真实 LLM 验证...")
        input_data = create_mock_input()
        await run_benchmark(agent, input_data)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断测试")
        sys.exit(1)
