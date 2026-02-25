"""
Markdown 补丁编辑器验证测试

测试目标：
  1. RoadmapMdConverter.json_to_md - 验证 JSON → Markdown 转换格式正确
  2. apply_search_replace_patch     - 验证 Aider 风格补丁应用器
  3. RoadmapMdConverter.md_to_json  - 验证 Markdown → JSON 无损回收
  4. Round-trip 完整性              - 验证未修改部分原样保留（ID、运营字段等）
  5. MdPatchEditorAgent.execute     - 端到端 LLM 集成测试（调用真实 API）

运行方式（仅在 backend/ 目录下）：
  # 运行所有测试（含 LLM 调用）
  pytest tests/agents/test_roadmap_md_patch_editor.py -v
  
  # 跳过 LLM 调用（只测本地逻辑）
  pytest tests/agents/test_roadmap_md_patch_editor.py -v -m "not llm"
  
  # 仅运行 LLM 端到端测试
  pytest tests/agents/test_roadmap_md_patch_editor.py -v -m "llm"
"""

import asyncio
import json
import sys
import time

import pytest

# 将 backend 目录加入 Python 路径（支持直接运行 python 脚本）
if __name__ == "__main__":
    sys.path.insert(0, "/Users/louie/Documents/Vibecoding/roadmap-agent/backend")

from app.agents.roadmap_md_patch_editor import (
    RoadmapMdConverter,
    MdPatchEditorAgent,
    apply_search_replace_patch,
)
from app.models.domain import (
    RoadmapFramework,
    EditPlan,
    StageEditTask,
    LearningPreferences,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 测试数据
# ═══════════════════════════════════════════════════════════════════════════════

FRAMEWORK_JSON = {
    "roadmap_id": "uiuxfigma-d139e2a1",
    "title": "UI/UX 设计师转型实战路线（开发者友好版）",
    "stages": [
        {
            "stage_id": "s-1",
            "name": "设计思维与基础构建",
            "description": "建立用户中心设计思维，掌握 UI/UX 核心原则与 Figma 基础操作，为后续高保真设计打下坚实基础",
            "order": 1,
            "modules": [
                {
                    "module_id": "m-1-1",
                    "name": "UI/UX 设计核心原则",
                    "description": "理解数字产品设计的基本逻辑、视觉语言与用户体验底层原理",
                    "concepts": [
                        {
                            "concept_id": "c-1-1-1",
                            "name": "用户中心设计与设计流程",
                            "description": "掌握以用户为中心的设计理念，了解从需求到交付的完整设计流程（双钻模型、设计冲刺等）",
                            "estimated_hours": 3.0,
                            "prerequisites": [],
                            "difficulty": "medium",
                            "keywords": ["用户中心设计", "双钻模型", "设计流程", "同理心地图", "问题定义"],
                            "content_status": "pending",
                            "tutorial_id": None,
                            "content_ref": None,
                            "content_version": "v1",
                            "content_summary": None,
                            "resources_status": "pending",
                            "resources_id": None,
                            "resources_count": 0,
                            "quiz_status": "pending",
                            "quiz_id": None,
                            "quiz_questions_count": 0,
                        },
                        {
                            "concept_id": "c-1-1-2",
                            "name": "视觉设计基础（排版、色彩、间距）",
                            "description": "学习排版层级、色彩心理学、网格系统与留白原则，建立基础视觉感知能力",
                            "estimated_hours": 4.0,
                            "prerequisites": [],
                            "difficulty": "medium",
                            "keywords": ["网格系统", "色彩对比度", "字体层级", "视觉重量", "WCAG 可访问性"],
                            "content_status": "pending",
                            "tutorial_id": None,
                            "content_ref": None,
                            "content_version": "v1",
                            "content_summary": None,
                            "resources_status": "pending",
                            "resources_id": None,
                            "resources_count": 0,
                            "quiz_status": "pending",
                            "quiz_id": None,
                            "quiz_questions_count": 0,
                        },
                    ],
                }
            ],
        },
        {
            "stage_id": "s-4",
            "name": "副业项目整合与作品集打造",
            "description": "通过真实副业项目整合所学技能，产出高质量作品集并建立设计决策表达能力",
            "order": 4,
            "modules": [
                {
                    "module_id": "m-4-1",
                    "name": "端到端项目实战",
                    "description": "以副业项目为载体，完整走通 UI/UX 设计全流程",
                    "concepts": [
                        {
                            "concept_id": "c-4-1-1",
                            "name": "项目规划与范围界定",
                            "description": "定义副业项目目标、用户范围、MVP 功能清单，制定合理设计节奏",
                            "estimated_hours": 3.0,
                            "prerequisites": ["c-1-1-1"],
                            "difficulty": "medium",
                            "keywords": ["项目范围", "MVP", "时间估算", "需求对齐", "优先级排序"],
                            "content_status": "completed",
                            "tutorial_id": "tut-001",
                            "content_ref": "s3://bucket/c-4-1-1/v1.md",
                            "content_version": "v1",
                            "content_summary": "已完成的项目规划教程",
                            "resources_status": "completed",
                            "resources_id": "res-001",
                            "resources_count": 5,
                            "quiz_status": "completed",
                            "quiz_id": "quiz-001",
                            "quiz_questions_count": 10,
                        },
                        {
                            "concept_id": "c-4-1-2",
                            "name": "全流程设计执行",
                            "description": "独立完成从用户研究、线框图、高保真原型到设计系统搭建的完整流程",
                            "estimated_hours": 8.0,
                            "prerequisites": ["c-4-1-1"],
                            "difficulty": "hard",
                            "keywords": ["端到端设计", "跨模块整合", "设计系统应用", "原型验证", "迭代记录"],
                            "content_status": "pending",
                            "tutorial_id": None,
                            "content_ref": None,
                            "content_version": "v1",
                            "content_summary": None,
                            "resources_status": "pending",
                            "resources_id": None,
                            "resources_count": 0,
                            "quiz_status": "pending",
                            "quiz_id": None,
                            "quiz_questions_count": 0,
                        },
                    ],
                }
            ],
        },
    ],
    "total_estimated_hours": 18.0,
    "recommended_completion_weeks": 4,
}

EDIT_PLAN_DATA = {
    "feedback_summary": "增加经典案例拆解模块，如苹果官网UI/UX分析",
    "tasks": [
        {
            "action": "UPDATE",
            "stage_id": "s-4",
            "instruction": "在 Stage 4（副业项目整合与作品集打造）中新增一个模块 '经典产品UI/UX案例拆解'，包含对苹果官网、Airbnb、Notion 等标杆产品的界面结构、交互逻辑、视觉层次、设计系统应用的深度拆解练习；每个案例配Figma可编辑文件与分析模板，强调设计决策背后的用户目标与业务逻辑。",
        }
    ],
}

USER_PREFERENCES = LearningPreferences(
    learning_goal="转型为 UI/UX 设计师，建立副业接单能力",
    current_level="intermediate",
    available_hours_per_week=10,
    motivation="副业转型，增加收入来源",
    career_background="前端开发工程师 3 年经验",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 辅助工具
# ═══════════════════════════════════════════════════════════════════════════════

def load_framework() -> RoadmapFramework:
    """加载测试用路线图框架"""
    return RoadmapFramework.model_validate(FRAMEWORK_JSON)


def load_edit_plan() -> EditPlan:
    """加载测试用修改计划"""
    return EditPlan.model_validate(EDIT_PLAN_DATA)


def print_separator(title: str) -> None:
    width = 70
    print(f"\n{'═' * width}")
    print(f"  {title}")
    print(f"{'═' * width}")


def print_md_preview(md_text: str, max_lines: int = 40) -> None:
    """打印 Markdown 预览（带行号）"""
    lines = md_text.split("\n")
    for i, line in enumerate(lines[:max_lines], 1):
        print(f"  {i:3d} | {line}")
    if len(lines) > max_lines:
        print(f"  ... （共 {len(lines)} 行，已截断）")


# ═══════════════════════════════════════════════════════════════════════════════
# 单元测试 - JSON → Markdown 转换
# ═══════════════════════════════════════════════════════════════════════════════

class TestJsonToMd:
    """验证 JSON → Markdown 转换的格式正确性"""

    def setup_method(self):
        self.converter = RoadmapMdConverter()
        self.framework = load_framework()
        self.md = self.converter.json_to_md(self.framework)

    def test_roadmap_meta_header_exists(self):
        """验证文档头包含路线图元数据注释"""
        assert "<!-- ROADMAP_META" in self.md
        assert "uiuxfigma-d139e2a1" in self.md

    def test_stage_format(self):
        """验证 Stage 行格式：# Stage: NAME <!-- {meta} -->"""
        assert '# Stage: 设计思维与基础构建 <!-- {"stage_id": "s-1", "order": 1} -->' in self.md
        assert '# Stage: 副业项目整合与作品集打造 <!-- {"stage_id": "s-4", "order": 4} -->' in self.md

    def test_module_format(self):
        """验证 Module 行格式：## Module: NAME <!-- {meta} -->"""
        assert '## Module: UI/UX 设计核心原则 <!-- {"module_id": "m-1-1"} -->' in self.md
        assert '## Module: 端到端项目实战 <!-- {"module_id": "m-4-1"} -->' in self.md

    def test_concept_format(self):
        """验证 Concept 行包含 ID 和关键字段"""
        assert '### Concept: 用户中心设计与设计流程 <!-- ' in self.md
        assert '"concept_id": "c-1-1-1"' in self.md
        assert '"hours": 3.0' in self.md
        assert '"difficulty": "medium"' in self.md

    def test_concept_description_line(self):
        """验证 Concept 描述行格式（> 开头）"""
        assert "> 掌握以用户为中心的设计理念" in self.md

    def test_concept_prerequisites_line(self):
        """验证前置关系行格式"""
        assert "- 前置: c-1-1-1" in self.md or "- 前置: []" in self.md

    def test_concept_keywords_line(self):
        """验证关键词行格式"""
        assert "- 关键词: 双钻模型" in self.md or "- 关键词: 用户中心设计" in self.md

    def test_operational_fields_hidden_in_comment(self):
        """验证运营字段（content_status 等）隐藏在注释中，不暴露给 LLM"""
        # 运营字段应在注释中（_ 前缀）
        assert "_content_status" in self.md
        assert "_tutorial_id" in self.md
        # 但不以普通文本形式暴露
        lines_without_comment = [
            l for l in self.md.split("\n")
            if "<!--" not in l and "content_status" in l
        ]
        assert len(lines_without_comment) == 0, "content_status 不应以纯文本形式暴露"

    def test_completed_concept_meta_preserved(self):
        """验证已完成内容的运营字段保留在注释中"""
        assert '"_tutorial_id": "tut-001"' in self.md
        assert '"_resources_count": 5' in self.md
        assert '"_quiz_questions_count": 10' in self.md


# ═══════════════════════════════════════════════════════════════════════════════
# 单元测试 - 补丁应用器
# ═══════════════════════════════════════════════════════════════════════════════

class TestApplyPatch:
    """验证 SEARCH/REPLACE 补丁应用逻辑"""

    def test_basic_replace(self):
        """验证基本替换"""
        original = "Hello World\nFoo Bar\nBaz"
        patch = "<<<<<<< SEARCH\nHello World\n=======\nHello Python\n>>>>>>> REPLACE"
        result, success = apply_search_replace_patch(original, patch)
        assert success is True
        assert "Hello Python" in result
        assert "Hello World" not in result

    def test_multiline_replace(self):
        """验证多行替换"""
        original = "## Module: 端到端项目实战 <!-- {\"module_id\": \"m-4-1\"} -->\n> 旧描述\n"
        new_desc = "> 以副业项目为载体，完整走通 UI/UX 设计全流程（更新版）"
        patch = (
            "<<<<<<< SEARCH\n"
            "## Module: 端到端项目实战 <!-- {\"module_id\": \"m-4-1\"} -->\n"
            "> 旧描述\n"
            "=======\n"
            "## Module: 端到端项目实战 <!-- {\"module_id\": \"m-4-1\"} -->\n"
            f"{new_desc}\n"
            ">>>>>>> REPLACE"
        )
        result, success = apply_search_replace_patch(original, patch)
        assert success is True
        assert "更新版" in result

    def test_multiple_blocks(self):
        """验证多个补丁块"""
        original = "A\nB\nC\nD"
        patch = (
            "<<<<<<< SEARCH\nA\n=======\nAlpha\n>>>>>>> REPLACE\n\n"
            "<<<<<<< SEARCH\nC\n=======\nGamma\n>>>>>>> REPLACE"
        )
        result, success = apply_search_replace_patch(original, patch)
        assert success is True
        assert "Alpha" in result
        assert "Gamma" in result
        assert "B" in result  # 未修改的行应保留
        assert "D" in result  # 未修改的行应保留

    def test_search_not_found(self):
        """验证 SEARCH 内容不存在时返回 False"""
        original = "Hello World"
        patch = "<<<<<<< SEARCH\nNot Exist\n=======\nReplacement\n>>>>>>> REPLACE"
        result, success = apply_search_replace_patch(original, patch)
        assert success is False
        assert result == original  # 原文不变

    def test_no_patch_blocks(self):
        """验证没有补丁块时返回 False"""
        original = "Hello World"
        patch = "这是普通文本，不含任何补丁块"
        result, success = apply_search_replace_patch(original, patch)
        assert success is False
        assert result == original

    def test_trailing_space_tolerance(self):
        """验证对行尾空格的容错处理"""
        original = "Hello World  \nFoo Bar"
        patch = "<<<<<<< SEARCH\nHello World\n=======\nHello Python\n>>>>>>> REPLACE"
        result, success = apply_search_replace_patch(original, patch)
        # 宽松匹配应该成功
        assert success is True


# ═══════════════════════════════════════════════════════════════════════════════
# 单元测试 - Markdown → JSON（Round-Trip）
# ═══════════════════════════════════════════════════════════════════════════════

class TestMdToJson:
    """验证 Markdown → JSON 的无损回收"""

    def setup_method(self):
        self.converter = RoadmapMdConverter()
        self.original_framework = load_framework()

    def test_pure_roundtrip_no_modification(self):
        """验证不做任何修改的 round-trip：还原框架与原始完全一致"""
        md = self.converter.json_to_md(self.original_framework)
        restored = self.converter.md_to_json(md, self.original_framework)

        assert restored.roadmap_id == self.original_framework.roadmap_id
        assert restored.title == self.original_framework.title
        assert len(restored.stages) == len(self.original_framework.stages)

        # 验证 Stage 还原
        for orig_stage, new_stage in zip(self.original_framework.stages, restored.stages):
            assert new_stage.stage_id == orig_stage.stage_id
            assert new_stage.name == orig_stage.name
            assert new_stage.order == orig_stage.order
            assert len(new_stage.modules) == len(orig_stage.modules)

            # 验证 Module 还原
            for orig_mod, new_mod in zip(orig_stage.modules, new_stage.modules):
                assert new_mod.module_id == orig_mod.module_id
                assert new_mod.name == orig_mod.name
                assert len(new_mod.concepts) == len(orig_mod.concepts)

                # 验证 Concept 还原
                for orig_c, new_c in zip(orig_mod.concepts, new_mod.concepts):
                    assert new_c.concept_id == orig_c.concept_id
                    assert new_c.name == orig_c.name
                    assert new_c.estimated_hours == orig_c.estimated_hours
                    assert new_c.difficulty == orig_c.difficulty

    def test_operational_fields_preserved_after_roundtrip(self):
        """验证已完成内容的运营字段在 round-trip 后完整恢复"""
        md = self.converter.json_to_md(self.original_framework)
        restored = self.converter.md_to_json(md, self.original_framework)

        # 找到 c-4-1-1（有已完成内容的 Concept）
        target_concept = None
        for stage in restored.stages:
            for module in stage.modules:
                for concept in module.concepts:
                    if concept.concept_id == "c-4-1-1":
                        target_concept = concept
                        break

        assert target_concept is not None
        assert target_concept.content_status == "completed"
        assert target_concept.tutorial_id == "tut-001"
        assert target_concept.content_ref == "s3://bucket/c-4-1-1/v1.md"
        assert target_concept.resources_status == "completed"
        assert target_concept.resources_id == "res-001"
        assert target_concept.resources_count == 5
        assert target_concept.quiz_status == "completed"
        assert target_concept.quiz_id == "quiz-001"
        assert target_concept.quiz_questions_count == 10

    def test_new_concept_added_via_patch(self):
        """验证 LLM 新增的 Concept（无 ID）能被正确解析并生成 ID"""
        md = self.converter.json_to_md(self.original_framework)

        # 模拟 LLM 在 m-4-1 下插入一个新 Concept（无 concept_id）
        new_concept_block = (
            '### Concept: 经典产品UI/UX案例拆解 <!-- {"concept_id": null, "hours": 5.0, "difficulty": "medium"} -->\n'
            '> 对苹果官网、Airbnb、Notion 等标杆产品的界面结构进行深度拆解练习\n'
            '- 前置: c-4-1-1\n'
            '- 关键词: 苹果官网, Airbnb, Notion, 界面分析, 设计决策\n'
        )
        # 找到 m-4-1 模块的末尾，在最后一个 concept 后插入新 concept
        insert_after = "- 关键词: 端到端设计, 跨模块整合, 设计系统应用, 原型验证, 迭代记录"
        md_with_new = md.replace(
            insert_after,
            insert_after + "\n\n" + new_concept_block.rstrip()
        )

        restored = self.converter.md_to_json(md_with_new, self.original_framework)

        # 找到 Stage 4 的 Module m-4-1
        s4 = next(s for s in restored.stages if s.stage_id == "s-4")
        m4_1 = next(m for m in s4.modules if m.module_id == "m-4-1")

        # 应该有 3 个 Concept（原来 2 个 + 新增 1 个）
        assert len(m4_1.concepts) == 3, f"期望 3 个 Concept，实际: {len(m4_1.concepts)}"

        # 新增 Concept 应有合法 ID
        new_concept = m4_1.concepts[2]
        assert new_concept.name == "经典产品UI/UX案例拆解"
        assert new_concept.concept_id is not None
        assert new_concept.estimated_hours == 5.0
        assert "c-4-1-1" in new_concept.prerequisites
        assert "苹果官网" in new_concept.keywords
        # 运营字段应为默认值
        assert new_concept.content_status == "pending"
        assert new_concept.tutorial_id is None


# ═══════════════════════════════════════════════════════════════════════════════
# 单元测试 - 完整 SEARCH/REPLACE 补丁 Round-Trip 仿真
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullPatchRoundTrip:
    """
    不调用真实 LLM，手动构造 SEARCH/REPLACE 补丁，
    验证整个 JSON → MD → 补丁 → MD → JSON 流程
    """

    def setup_method(self):
        self.converter = RoadmapMdConverter()
        self.original_framework = load_framework()

    def test_add_new_module_via_patch(self):
        """
        模拟 LLM 在 Stage 4 添加新 Module 的操作：
        通过 SEARCH/REPLACE 在最后一个 Module 后插入新 Module
        """
        original_md = self.converter.json_to_md(self.original_framework)

        # 构造模拟 LLM 输出的补丁（在 m-4-1 末尾之后添加新 Module）
        # 找到 Stage 4 末尾的一个固定标志行
        search_anchor = "- 关键词: 端到端设计, 跨模块整合, 设计系统应用, 原型验证, 迭代记录"
        new_module_block = """- 关键词: 端到端设计, 跨模块整合, 设计系统应用, 原型验证, 迭代记录

## Module: 经典产品UI/UX案例拆解 <!-- {"module_id": null} -->
> 通过拆解苹果官网、Airbnb、Notion 等标杆产品，培养设计眼力与决策表达能力

### Concept: 苹果官网界面结构深度拆解 <!-- {"concept_id": null, "hours": 4.0, "difficulty": "medium"} -->
> 分析苹果官网的信息层次、视觉语言、交互节奏及设计系统应用，配 Figma 分析模板
- 前置: c-4-1-1
- 关键词: 苹果官网, 信息层次, 视觉节奏, 设计系统, 案例拆解

### Concept: Airbnb 与 Notion 交互逻辑拆解 <!-- {"concept_id": null, "hours": 4.0, "difficulty": "medium"} -->
> 对比分析 Airbnb 预订流程与 Notion 工作台的交互逻辑、用户目标与业务目标的设计平衡
- 前置: c-4-1-1
- 关键词: Airbnb, Notion, 交互逻辑, 用户目标, 业务逻辑"""

        patch = (
            f"<<<<<<< SEARCH\n{search_anchor}\n"
            f"=======\n{new_module_block}\n"
            ">>>>>>> REPLACE"
        )

        new_md, success = apply_search_replace_patch(original_md, patch)
        assert success is True, "补丁应用失败"

        restored = self.converter.md_to_json(new_md, self.original_framework)

        # Stage 4 应该现在有 2 个 Module
        s4 = next(s for s in restored.stages if s.stage_id == "s-4")
        assert len(s4.modules) == 2, f"期望 2 个 Module，实际: {len(s4.modules)}"

        # 新增的 Module 应被正确解析
        new_module = s4.modules[1]
        assert new_module.name == "经典产品UI/UX案例拆解"
        assert new_module.module_id is not None and new_module.module_id != ""
        assert len(new_module.concepts) == 2

        # 验证新增 Concept
        concept_1 = new_module.concepts[0]
        assert concept_1.name == "苹果官网界面结构深度拆解"
        assert concept_1.estimated_hours == 4.0
        assert concept_1.content_status == "pending"
        assert concept_1.tutorial_id is None

        concept_2 = new_module.concepts[1]
        assert concept_2.name == "Airbnb 与 Notion 交互逻辑拆解"
        assert "Airbnb" in concept_2.keywords

        # 验证原有 Concept 的运营字段未受影响
        orig_concept = s4.modules[0].concepts[0]
        assert orig_concept.concept_id == "c-4-1-1"
        assert orig_concept.content_status == "completed"
        assert orig_concept.tutorial_id == "tut-001"
        assert orig_concept.quiz_questions_count == 10

        print_separator("补丁 Round-Trip 测试：新增 Module")
        print(f"  ✅ Stage 4 模块数量: {len(s4.modules)}")
        print(f"  ✅ 新增模块名称: {new_module.name}")
        print(f"  ✅ 新增模块 ID: {new_module.module_id}")
        print(f"  ✅ 新增 Concept 数量: {len(new_module.concepts)}")
        print(f"  ✅ 原有已完成 Concept 运营字段保留: tutorial_id={orig_concept.tutorial_id}")
        print(f"  ✅ 总时长: {restored.total_estimated_hours}h（新增 8h）")

    def test_update_existing_concept_name(self):
        """验证修改现有 Concept 名称后，原有运营字段保留"""
        original_md = self.converter.json_to_md(self.original_framework)

        old_concept_line = "### Concept: 项目规划与范围界定 <!-- "
        new_name = "项目启动与范围界定（含 AI 辅助规划）"

        # 找到该行并替换名称
        lines = original_md.split("\n")
        new_lines = []
        for line in lines:
            if line.startswith("### Concept: 项目规划与范围界定 <!-- "):
                line = line.replace("项目规划与范围界定", new_name)
            new_lines.append(line)
        new_md = "\n".join(new_lines)

        restored = self.converter.md_to_json(new_md, self.original_framework)

        s4 = next(s for s in restored.stages if s.stage_id == "s-4")
        c = s4.modules[0].concepts[0]

        assert c.name == new_name
        # 关键：ID 和运营字段应保持不变
        assert c.concept_id == "c-4-1-1"
        assert c.content_status == "completed"
        assert c.tutorial_id == "tut-001"


# ═══════════════════════════════════════════════════════════════════════════════
# LLM 集成测试（调用真实 API）
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.llm
class TestMdPatchEditorLLM:
    """端到端 LLM 集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_edit_with_real_llm(self):
        """
        完整端到端测试：调用真实 LLM，验证修改结果符合预期
        
        预期结果：
          - Stage 4 新增一个 '经典产品UI/UX案例拆解' 相关模块或 Concept
          - 原有已完成的 Concept（c-4-1-1）运营字段完整保留
          - 总时长增加（新增了 Concept）
          - roadmap_id 不变
        """
        framework = load_framework()
        edit_plan = load_edit_plan()

        agent = MdPatchEditorAgent()

        print_separator("LLM 端到端测试开始")
        t0 = time.time()

        result = await agent.execute(
            existing_framework=framework,
            edit_plan=edit_plan,
            user_preferences=USER_PREFERENCES,
        )

        elapsed = time.time() - t0
        print(f"\n  ✅ 执行耗时: {elapsed:.2f}s")

        # 基础断言
        assert result.framework is not None
        assert result.framework.roadmap_id == framework.roadmap_id
        assert result.modification_summary != ""

        # Stage 数量应该不变（只是在 Stage 4 内部修改）
        assert len(result.framework.stages) == len(framework.stages)

        # Stage 4 应该有更多内容
        orig_s4 = next(s for s in framework.stages if s.stage_id == "s-4")
        new_s4 = next(s for s in result.framework.stages if s.stage_id == "s-4")

        orig_concept_count = sum(len(m.concepts) for m in orig_s4.modules)
        new_concept_count = sum(len(m.concepts) for m in new_s4.modules)

        print(f"  ✅ Stage 4 原 Concept 数: {orig_concept_count}")
        print(f"  ✅ Stage 4 新 Concept 数: {new_concept_count}")
        assert new_concept_count > orig_concept_count, (
            f"Stage 4 的 Concept 数量应该增加，"
            f"原: {orig_concept_count}，新: {new_concept_count}"
        )

        # 验证原有已完成 Concept 的运营字段保留
        restored_c = None
        for s in result.framework.stages:
            for m in s.modules:
                for c in m.concepts:
                    if c.concept_id == "c-4-1-1":
                        restored_c = c
                        break

        assert restored_c is not None, "c-4-1-1 应该保留在修改后的框架中"
        assert restored_c.content_status == "completed", "已完成状态不应被重置"
        assert restored_c.tutorial_id == "tut-001", "tutorial_id 不应丢失"
        assert restored_c.quiz_questions_count == 10, "quiz_questions_count 不应丢失"

        print(f"  ✅ c-4-1-1 运营字段保留: content_status={restored_c.content_status}, "
              f"tutorial_id={restored_c.tutorial_id}")
        print(f"  ✅ modified_node_ids: {result.modified_node_ids}")
        print(f"  ✅ 修改总结: {result.modification_summary}")
        print(f"  ✅ 总时长: {framework.total_estimated_hours}h → "
              f"{result.framework.total_estimated_hours}h")


# ═══════════════════════════════════════════════════════════════════════════════
# 独立运行入口（python 脚本模式）
# ═══════════════════════════════════════════════════════════════════════════════

async def run_demo():
    """
    完整演示运行（含真实 LLM 调用）
    适合直接用 python 运行查看效果
    """
    framework = load_framework()
    edit_plan = load_edit_plan()

    # ── Step 1: 查看 JSON → Markdown 转换结果 ────────────────────────────────
    print_separator("Step 1: JSON → Markdown 转换")
    converter = RoadmapMdConverter()
    original_md = converter.json_to_md(framework)
    print_md_preview(original_md, max_lines=50)
    print(f"\n  共 {len(original_md)} 字符，{original_md.count(chr(10))} 行")

    # ── Step 2: 测试手动构造补丁（无需 LLM）────────────────────────────────
    print_separator("Step 2: 手动补丁测试（无 LLM）")
    manual_patch = """<<<<<<< SEARCH
## Module: 端到端项目实战 <!-- {"module_id": "m-4-1"} -->
> 以副业项目为载体，完整走通 UI/UX 设计全流程
=======
## Module: 端到端项目实战 <!-- {"module_id": "m-4-1"} -->
> 以副业项目为载体，完整走通 UI/UX 设计全流程（含 AI 辅助环节）
>>>>>>> REPLACE"""

    new_md_manual, success = apply_search_replace_patch(original_md, manual_patch)
    print(f"  补丁应用结果: {'✅ 成功' if success else '❌ 失败'}")
    if success:
        restored_manual = converter.md_to_json(new_md_manual, framework)
        s4 = next(s for s in restored_manual.stages if s.stage_id == "s-4")
        m4_1 = s4.modules[0]
        print(f"  m-4-1 新描述: {m4_1.description}")

    # ── Step 3: LLM 端到端测试 ───────────────────────────────────────────────
    print_separator("Step 3: LLM 端到端测试")
    print(f"  修改计划: {edit_plan.feedback_summary}")
    print(f"  任务数量: {len(edit_plan.tasks)}")
    print(f"  任务详情: {edit_plan.tasks[0].instruction[:80]}...")

    agent = MdPatchEditorAgent()
    t0 = time.time()
    result = await agent.execute(
        existing_framework=framework,
        edit_plan=edit_plan,
        user_preferences=USER_PREFERENCES,
    )
    elapsed = time.time() - t0

    print(f"\n  ⏱️  总耗时: {elapsed:.2f}s")
    print(f"  📊 修改节点: {len(result.modified_node_ids)} 个")
    print(f"     {result.modified_node_ids}")
    print(f"  📝 修改总结: {result.modification_summary}")
    print(f"\n  🗂️  Stage 4 模块数量:")
    s4_new = next(s for s in result.framework.stages if s.stage_id == "s-4")
    for m in s4_new.modules:
        print(f"     - {m.module_id}: {m.name} ({len(m.concepts)} concepts)")

    print_separator("Step 4: 运营字段保留验证")
    for s in result.framework.stages:
        for m in s.modules:
            for c in m.concepts:
                if c.concept_id == "c-4-1-1":
                    print(f"  c-4-1-1 ({c.name}):")
                    print(f"    content_status   = {c.content_status}")
                    print(f"    tutorial_id      = {c.tutorial_id}")
                    print(f"    resources_count  = {c.resources_count}")
                    print(f"    quiz_questions   = {c.quiz_questions_count}")
                    print(f"  ✅ 运营字段完整保留！")


if __name__ == "__main__":
    asyncio.run(run_demo())
