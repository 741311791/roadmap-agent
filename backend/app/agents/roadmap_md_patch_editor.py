"""
基于 Markdown 补丁的路线图编辑器（性能优化版）

设计思路：
  传统方案：LLM 输出完整 JSON（20k+ tokens）→ 慢、贵、容易出错
  本方案：JSON → Markdown → LLM 输出 SEARCH/REPLACE 补丁 → 应用补丁 → 解析回 JSON
  
  核心优势：
  - LLM 只需输出"差异"而非"全量"，Token 消耗减少 80%+
  - SEARCH/REPLACE 格式是 Aider 验证过的最小化改动模式
  - Markdown 比 JSON 更易于 LLM 理解和精确定位修改点

模块划分：
  RoadmapMdConverter  - 双向转换器（RoadmapFramework ↔ Markdown）
  apply_search_replace_patch - Aider 风格补丁应用器
  MdPatchEditorAgent  - 集成 LLM 调用的编辑 Agent
"""

import json
import re
import time
from typing import Optional
from openai import AsyncOpenAI

import structlog

from app.models.domain import (
    RoadmapFramework,
    Stage,
    Module,
    Concept,
    EditPlan,
    LearningPreferences,
    RoadmapEditOutput,
)
from app.agents.framework_diff import compute_modified_node_ids
from app.agents.framework_normalizer import normalize_framework_ids
from app.config.settings import settings

logger = structlog.get_logger()


# ═══════════════════════════════════════════════════════════════════════════════
# 0. 仅规范化新增节点的 ID（不破坏已有 ID）
# ═══════════════════════════════════════════════════════════════════════════════

def normalize_new_node_ids(framework: RoadmapFramework) -> RoadmapFramework:
    """
    仅将"新增节点"的临时 ID（如 c-new-1、m-new-2、s-new-3）替换为规范 ID，
    对已有节点的 ID 保持不变。
    
    与 normalize_framework_ids 的区别：
      normalize_framework_ids  → 按位置全量重排所有 ID（会改变原有节点 ID）
      normalize_new_node_ids   → 只补全 *-new-* 临时 ID，原有 ID 不动
      
    使用场景：Md Patch 编辑器——只有 LLM 新增的节点需要生成正式 ID，
    原有节点的 ID 必须保持稳定（保证运营字段按 ID 可追溯）。
    """
    # 收集所有已经存在的合法 ID，避免新 ID 冲突
    existing_stage_ids: set[str] = set()
    existing_module_ids: set[str] = set()
    existing_concept_ids: set[str] = set()

    for s in framework.stages:
        if not s.stage_id.startswith("s-new-"):
            existing_stage_ids.add(s.stage_id)
        for m in s.modules:
            if not m.module_id.startswith("m-new-"):
                existing_module_ids.add(m.module_id)
            for c in m.concepts:
                if not c.concept_id.startswith("c-new-"):
                    existing_concept_ids.add(c.concept_id)

    # 旧 ID → 新 ID 映射（仅针对 *-new-* 节点）
    id_mapping: dict[str, str] = {}

    new_stages: list[Stage] = []
    for stage in framework.stages:
        # Stage：若为新增临时 ID，按 order 生成规范 ID
        if stage.stage_id.startswith("s-new-"):
            candidate = f"s-{stage.order}"
            # 若有冲突，往后找可用 ID
            counter = stage.order
            while candidate in existing_stage_ids:
                counter += 1
                candidate = f"s-{counter}"
            id_mapping[stage.stage_id] = candidate
            existing_stage_ids.add(candidate)
            resolved_stage_id = candidate
        else:
            resolved_stage_id = stage.stage_id

        stage_order = stage.order
        new_modules: list[Module] = []

        for module_idx, module in enumerate(stage.modules, start=1):
            if module.module_id.startswith("m-new-"):
                # 找该 Stage 内未占用的 Module 序号
                m_candidate = f"m-{stage_order}-{module_idx}"
                idx = module_idx
                while m_candidate in existing_module_ids:
                    idx += 1
                    m_candidate = f"m-{stage_order}-{idx}"
                id_mapping[module.module_id] = m_candidate
                existing_module_ids.add(m_candidate)
                resolved_module_id = m_candidate
            else:
                resolved_module_id = module.module_id

            new_concepts: list[Concept] = []
            for concept_idx, concept in enumerate(module.concepts, start=1):
                if concept.concept_id.startswith("c-new-"):
                    # 找该 Module 内未占用的 Concept 序号，并加上 roadmap_id 前缀确保全局唯一
                    c_candidate = f"{framework.roadmap_id}:c-{stage_order}-{module_idx}-{concept_idx}"
                    cidx = concept_idx
                    while c_candidate in existing_concept_ids:
                        cidx += 1
                        c_candidate = f"{framework.roadmap_id}:c-{stage_order}-{module_idx}-{cidx}"
                    id_mapping[concept.concept_id] = c_candidate
                    existing_concept_ids.add(c_candidate)
                    resolved_concept_id = c_candidate
                else:
                    resolved_concept_id = concept.concept_id

                new_concepts.append(concept.model_copy(update={"concept_id": resolved_concept_id}))

            new_modules.append(module.model_copy(update={
                "module_id": resolved_module_id,
                "concepts": new_concepts,
            }))

        new_stages.append(stage.model_copy(update={
            "stage_id": resolved_stage_id,
            "modules": new_modules,
        }))

    # 更新所有 prerequisites 中的旧 ID 引用
    for stage in new_stages:
        for module in stage.modules:
            for concept in module.concepts:
                updated_prereqs = [id_mapping.get(p, p) for p in concept.prerequisites]
                concept.prerequisites = updated_prereqs

    if id_mapping:
        logger.info(
            "new_node_ids_normalized",
            roadmap_id=framework.roadmap_id,
            renamed_count=len(id_mapping),
            id_mapping=id_mapping,
        )

    return framework.model_copy(update={"stages": new_stages})


# ═══════════════════════════════════════════════════════════════════════════════
# 1. 双向转换器
# ═══════════════════════════════════════════════════════════════════════════════

class RoadmapMdConverter:
    """
    RoadmapFramework ↔ Markdown 双向无损转换器
    
    Markdown 格式设计原则：
      - 暴露给 LLM 修改的字段：name/description/difficulty/hours/prerequisites/keywords
      - 隐藏在 HTML 注释中的字段：所有 ID、内容状态、引用 ID 等运营字段
      - 新增节点（LLM 生成，无 ID）：md_to_json 时自动生成规范 ID
    
    格式示例：
      # Stage: 设计思维与基础构建 <!-- {"stage_id": "s-1", "order": 1} -->
      > 建立用户中心设计思维，掌握 UI/UX 核心原则
      
      ## Module: UI/UX 设计核心原则 <!-- {"module_id": "m-1-1"} -->
      > 理解数字产品设计的基本逻辑
      
      ### Concept: 用户中心设计与设计流程 <!-- {"concept_id": "c-1-1-1", "hours": 3.0, "difficulty": "medium"} -->
      > 掌握以用户为中心的设计理念
      - 前置: c-1-1-2, c-1-1-3
      - 关键词: 双钻模型, 设计流程, 同理心地图
    """

    # ── JSON → Markdown ──────────────────────────────────────────────────────

    def json_to_md(self, framework: RoadmapFramework) -> str:
        """
        将 RoadmapFramework 转换为结构化 Markdown
        
        Args:
            framework: 路线图框架 Pydantic 对象
            
        Returns:
            带元数据注释的 Markdown 字符串
        """
        lines: list[str] = []

        # 文档头：存放路线图级别的元数据（不被 LLM 修改）
        header_meta = {
            "roadmap_id": framework.roadmap_id,
            "total_hours": framework.total_estimated_hours,
            "weeks": framework.recommended_completion_weeks,
        }
        lines.append(f"<!-- ROADMAP_META {json.dumps(header_meta, ensure_ascii=False)} -->")
        lines.append(f"# 路线图: {framework.title}")
        lines.append("")

        for stage in framework.stages:
            lines.extend(self._stage_to_md(stage))

        return "\n".join(lines)

    def _stage_to_md(self, stage: Stage) -> list[str]:
        """将单个 Stage 转换为 Markdown 行列表"""
        lines: list[str] = []

        stage_meta = json.dumps(
            {"stage_id": stage.stage_id, "order": stage.order},
            ensure_ascii=False,
        )
        lines.append(f"# Stage: {stage.name} <!-- {stage_meta} -->")
        lines.append(f"> {stage.description}")
        lines.append("")

        for module in stage.modules:
            lines.extend(self._module_to_md(module))

        return lines

    def _module_to_md(self, module: Module) -> list[str]:
        """将单个 Module 转换为 Markdown 行列表"""
        lines: list[str] = []

        module_meta = json.dumps(
            {"module_id": module.module_id},
            ensure_ascii=False,
        )
        lines.append(f"## Module: {module.name} <!-- {module_meta} -->")
        lines.append(f"> {module.description}")
        lines.append("")

        for concept in module.concepts:
            lines.extend(self._concept_to_md(concept))

        return lines

    def _concept_to_md(self, concept: Concept) -> list[str]:
        """将单个 Concept 转换为 Markdown 行列表"""
        lines: list[str] = []

        # 内容运营字段全部藏进注释，LLM 不需要看到
        concept_meta = json.dumps(
            {
                "concept_id": concept.concept_id,
                "hours": concept.estimated_hours,
                "difficulty": concept.difficulty,
                # 以下字段保留但不暴露给编辑
                "_content_status": concept.content_status,
                "_tutorial_id": concept.tutorial_id,
                "_resources_status": concept.resources_status,
                "_resources_id": concept.resources_id,
                "_resources_count": concept.resources_count,
                "_quiz_status": concept.quiz_status,
                "_quiz_id": concept.quiz_id,
                "_quiz_questions_count": concept.quiz_questions_count,
            },
            ensure_ascii=False,
        )
        lines.append(f"### Concept: {concept.name} <!-- {concept_meta} -->")
        lines.append(f"> {concept.description}")

        if concept.prerequisites:
            lines.append(f"- 前置: {', '.join(concept.prerequisites)}")
        else:
            lines.append("- 前置: []")

        kw_str = ", ".join(concept.keywords) if concept.keywords else ""
        lines.append(f"- 关键词: {kw_str}")
        lines.append("")

        return lines

    # ── Markdown → JSON ──────────────────────────────────────────────────────

    def md_to_json(self, md_text: str, original_framework: RoadmapFramework) -> RoadmapFramework:
        """
        将修改后的 Markdown 解析回 RoadmapFramework
        
        处理逻辑：
        - 有 concept_id / module_id / stage_id 的节点：直接复用原始运营字段
        - 无 ID 的节点（LLM 新增）：生成临时 ID，运营字段置为默认值
        
        Args:
            md_text: 经过 LLM 修改后的 Markdown 文本
            original_framework: 原始框架（用于恢复运营字段）
            
        Returns:
            重建的 RoadmapFramework
        """
        # 从文档头提取路线图级元数据
        roadmap_meta = self._extract_roadmap_meta(md_text)
        roadmap_id = roadmap_meta.get("roadmap_id", original_framework.roadmap_id)

        # 建立原始节点查找表（按 ID 快速定位）
        original_concepts: dict[str, Concept] = {
            c.concept_id: c
            for s in original_framework.stages
            for m in s.modules
            for c in m.concepts
        }
        original_modules: dict[str, Module] = {
            m.module_id: m
            for s in original_framework.stages
            for m in s.modules
        }
        original_stages: dict[str, Stage] = {
            s.stage_id: s
            for s in original_framework.stages
        }

        # 用于生成新 ID 的计数器
        stage_counter = [0]
        module_counter = [0]
        concept_counter = [0]

        stages: list[Stage] = []
        current_stage: Optional[dict] = None
        current_module: Optional[dict] = None

        lines = md_text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # ── Stage 行（`# Stage: NAME <!-- meta -->`）────────────────────
            stage_match = re.match(
                r"^# Stage: (.+?)\s+<!--\s*(\{.*?\})\s*-->", line
            )
            if stage_match:
                # 先保存上一个 Module（防止 Module 尚未被追加到 Stage）
                if current_module is not None and current_stage is not None:
                    current_stage["modules"].append(
                        self._finalize_module(current_module, original_modules)
                    )
                    current_module = None
                # 再保存上一个 Stage
                if current_stage is not None:
                    stages.append(self._finalize_stage(current_stage, original_stages))
                stage_name = stage_match.group(1).strip()
                try:
                    stage_meta = json.loads(stage_match.group(2))
                except json.JSONDecodeError:
                    stage_meta = {}

                # 读取下一行作为描述（`> ...`）
                desc_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                stage_desc = desc_line.lstrip("> ").strip() if desc_line.startswith(">") else ""

                current_stage = {
                    "stage_id": stage_meta.get("stage_id"),  # None → 新增 Stage
                    "order": stage_meta.get("order", len(stages) + 1),
                    "name": stage_name,
                    "description": stage_desc,
                    "modules": [],
                }
                current_module = None
                i += 2
                continue

            # ── Module 行（`## Module: NAME <!-- meta -->`）──────────────────
            module_match = re.match(
                r"^## Module: (.+?)\s+<!--\s*(\{.*?\})\s*-->", line
            )
            if module_match and current_stage is not None:
                # 先保存上一个 Module（flush 已积累的 Concept 列表）
                if current_module is not None:
                    current_stage["modules"].append(
                        self._finalize_module(current_module, original_modules)
                    )
                module_name = module_match.group(1).strip()
                try:
                    module_meta = json.loads(module_match.group(2))
                except json.JSONDecodeError:
                    module_meta = {}

                desc_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
                module_desc = desc_line.lstrip("> ").strip() if desc_line.startswith(">") else ""

                current_module = {
                    "module_id": module_meta.get("module_id"),  # None → 新增
                    "name": module_name,
                    "description": module_desc,
                    "concepts": [],
                }
                i += 2
                continue

            # ── Concept 行（`### Concept: NAME <!-- meta -->`）───────────────
            concept_match = re.match(
                r"^### Concept: (.+?)\s+<!--\s*(\{.*?\})\s*-->", line
            )
            if concept_match and current_module is not None:
                concept_name = concept_match.group(1).strip()
                try:
                    concept_meta = json.loads(concept_match.group(2))
                except json.JSONDecodeError:
                    concept_meta = {}

                # 读取后续行（描述、前置、关键词）
                concept_desc = ""
                prerequisites: list[str] = []
                keywords: list[str] = []

                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if next_line.startswith("> "):
                        concept_desc = next_line[2:].strip()
                    elif next_line.startswith("- 前置: "):
                        prereq_str = next_line[len("- 前置: "):].strip()
                        if prereq_str and prereq_str != "[]":
                            prerequisites = [p.strip() for p in prereq_str.split(",") if p.strip()]
                    elif next_line.startswith("- 关键词: "):
                        kw_str = next_line[len("- 关键词: "):].strip()
                        if kw_str:
                            keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
                    elif next_line.startswith("#") or (next_line == "" and j > i + 3):
                        break
                    j += 1

                concept_data = {
                    "concept_id": concept_meta.get("concept_id"),
                    "name": concept_name,
                    "description": concept_desc,
                    "estimated_hours": float(concept_meta.get("hours", 3.0)),
                    "difficulty": concept_meta.get("difficulty", "medium"),
                    "prerequisites": prerequisites,
                    "keywords": keywords,
                    "_meta": concept_meta,  # 保留完整 meta 用于恢复运营字段
                }
                current_module["concepts"].append(concept_data)
                i = j
                continue

            i += 1

        # 保存最后一个 Module 和 Stage
        if current_module is not None and current_stage is not None:
            current_stage["modules"].append(
                self._finalize_module(current_module, original_modules)
            )
        if current_stage is not None:
            stages.append(self._finalize_stage(current_stage, original_stages))

        # 重算总时长
        total_hours = sum(
            c.estimated_hours
            for s in stages
            for m in s.modules
            for c in m.concepts
        )

        # 重建 Framework
        rebuilt = RoadmapFramework(
            roadmap_id=roadmap_id,
            title=original_framework.title,
            stages=stages,
            total_estimated_hours=round(total_hours, 1),
            recommended_completion_weeks=original_framework.recommended_completion_weeks,
        )

        # 仅规范化新增节点的临时 ID，原有节点 ID 保持不变
        return normalize_new_node_ids(rebuilt)

    def _finalize_stage(
        self, stage_dict: dict, original_stages: dict[str, Stage]
    ) -> Stage:
        """将解析出的 Stage 字典转换为 Stage 对象，处理新增 Stage 的 ID"""
        stage_id = stage_dict["stage_id"]
        if stage_id is None:
            # 新增 Stage：生成临时 ID（后续由 normalize_framework_ids 规范化）
            stage_id = f"s-new-{stage_dict['order']}"

        modules_raw = stage_dict.pop("modules", [])
        modules: list[Module] = modules_raw  # 已经是 Module 对象（由 _finalize_module 处理）

        return Stage(
            stage_id=stage_id,
            name=stage_dict["name"],
            description=stage_dict["description"],
            order=stage_dict["order"],
            modules=modules,
        )

    def _finalize_module(
        self, module_dict: dict, original_modules: dict[str, Module]
    ) -> Module:
        """
        将解析出的 Module 字典转换为 Module 对象，恢复或生成 ID
        
        匹配策略：
          1. module_id 精确匹配
          2. module_name 模糊匹配（LLM 可能修改了 HTML 注释中的 ID）
          3. 均无匹配 → 新增 Module，生成临时 ID
        """
        module_id = module_dict["module_id"]
        module_name = module_dict["name"]

        # 策略 1 & 2：ID 精确 + 名称回退
        if module_id and module_id in original_modules:
            resolved_id = module_id
        else:
            orig_by_name = next(
                (m for m in original_modules.values() if m.name == module_name),
                None,
            )
            resolved_id = orig_by_name.module_id if orig_by_name else None

        if resolved_id is None:
            resolved_id = f"m-new-{len(original_modules) + 1}"

        concepts_raw = module_dict.pop("concepts", [])
        concepts = self._finalize_concepts(concepts_raw, original_modules)

        return Module(
            module_id=resolved_id,
            name=module_name,
            description=module_dict["description"],
            concepts=concepts,
        )

    def _finalize_concepts(
        self, concepts_raw: list[dict], original_modules: dict[str, Module]
    ) -> list[Concept]:
        """
        将解析出的 Concept 字典列表转换为 Concept 对象列表，恢复运营字段
        
        匹配策略（优先级递减）：
          1. concept_id 精确匹配（最可靠）
          2. concept_name 模糊匹配（防止 LLM 修改了 HTML 注释中的 ID）
          3. 均无匹配 → 视为新增 Concept，运营字段置默认值
        """
        # 建立所有原始 Concept 的快查表（ID → Concept）
        all_original_concepts_by_id: dict[str, Concept] = {
            c.concept_id: c
            for m in original_modules.values()
            for c in m.concepts
        }
        # 按名称建立副表（名称 → Concept），用于 ID 丢失时的回退匹配
        all_original_concepts_by_name: dict[str, Concept] = {
            c.name: c
            for m in original_modules.values()
            for c in m.concepts
        }

        concepts: list[Concept] = []
        new_concept_counter = 0

        for c_dict in concepts_raw:
            concept_id = c_dict.get("concept_id")
            concept_name = c_dict["name"]
            meta = c_dict.get("_meta", {})

            # ── 策略 1: 按 concept_id 精确匹配 ────────────────────────────
            orig = all_original_concepts_by_id.get(concept_id) if concept_id else None

            # ── 策略 2: 按名称回退匹配（LLM 可能修改了 HTML 注释中的 ID）──
            if orig is None:
                orig = all_original_concepts_by_name.get(concept_name)

            if orig is not None:
                # 已有原始节点：恢复运营字段，使用原始 concept_id
                concepts.append(Concept(
                    concept_id=orig.concept_id,
                    name=concept_name,
                    description=c_dict["description"],
                    estimated_hours=c_dict["estimated_hours"],
                    prerequisites=c_dict["prerequisites"],
                    difficulty=c_dict["difficulty"],
                    keywords=c_dict["keywords"],
                    content_status=orig.content_status,
                    tutorial_id=orig.tutorial_id,
                    content_ref=orig.content_ref,
                    content_version=orig.content_version,
                    content_summary=orig.content_summary,
                    resources_status=orig.resources_status,
                    resources_id=orig.resources_id,
                    resources_count=orig.resources_count,
                    quiz_status=orig.quiz_status,
                    quiz_id=orig.quiz_id,
                    quiz_questions_count=orig.quiz_questions_count,
                ))
            else:
                # 新增 Concept：运营字段全部使用默认值（从 meta 中尽量恢复）
                new_concept_counter += 1
                concepts.append(Concept(
                    concept_id=concept_id or f"c-new-{new_concept_counter}",
                    name=concept_name,
                    description=c_dict["description"],
                    estimated_hours=c_dict["estimated_hours"],
                    prerequisites=c_dict["prerequisites"],
                    difficulty=c_dict["difficulty"],
                    keywords=c_dict["keywords"],
                    content_status=meta.get("_content_status", "pending"),
                    tutorial_id=meta.get("_tutorial_id"),
                    content_ref=None,
                    content_version="v1",
                    content_summary=None,
                    resources_status=meta.get("_resources_status", "pending"),
                    resources_id=meta.get("_resources_id"),
                    resources_count=meta.get("_resources_count", 0),
                    quiz_status=meta.get("_quiz_status", "pending"),
                    quiz_id=meta.get("_quiz_id"),
                    quiz_questions_count=meta.get("_quiz_questions_count", 0),
                ))

        return concepts

    def _extract_roadmap_meta(self, md_text: str) -> dict:
        """从文档头部提取路线图级元数据"""
        match = re.search(r"<!-- ROADMAP_META (\{.*?\}) -->", md_text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return {}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Aider 风格补丁应用器
# ═══════════════════════════════════════════════════════════════════════════════

def apply_search_replace_patch(original_text: str, patch_text: str) -> tuple[str, bool]:
    """
    应用 Aider 风格的 SEARCH/REPLACE 补丁
    
    补丁格式：
        <<<<<<< SEARCH
        需要精确匹配的原文内容
        =======
        替换后的新内容
        >>>>>>> REPLACE
    
    Args:
        original_text: 原始 Markdown 文本
        patch_text: 包含一个或多个 SEARCH/REPLACE 块的补丁文本
        
    Returns:
        (修改后的文本, 是否所有补丁都成功应用)
    """
    # 提取所有 SEARCH/REPLACE 块
    pattern = r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE"
    blocks = re.findall(pattern, patch_text, re.DOTALL)

    if not blocks:
        logger.warning("md_patch_no_blocks_found", patch_preview=patch_text[:200])
        return original_text, False

    result = original_text
    all_success = True

    for idx, (search_text, replace_text) in enumerate(blocks):
        search_text = search_text.strip("\n")
        replace_text = replace_text.strip("\n")

        if search_text not in result:
            # 尝试忽略行尾空格的宽松匹配
            search_normalized = re.sub(r" +\n", "\n", search_text)
            result_normalized = re.sub(r" +\n", "\n", result)

            if search_normalized in result_normalized:
                # 在规范化后的文本中找到了 → 在原文中精确定位
                start_idx = result_normalized.index(search_normalized)
                end_idx = start_idx + len(search_normalized)
                result = result[:start_idx] + replace_text + result[end_idx:]
                logger.debug("md_patch_applied_fuzzy", block_idx=idx)
            else:
                logger.warning(
                    "md_patch_search_not_found",
                    block_idx=idx,
                    search_preview=search_text[:100],
                )
                all_success = False
        else:
            result = result.replace(search_text, replace_text, 1)
            logger.debug("md_patch_applied_exact", block_idx=idx)

    return result, all_success


# ═══════════════════════════════════════════════════════════════════════════════
# 3. MdPatchEditorAgent
# ═══════════════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT = """\
你是一个 Markdown 编辑助手，专门用于修改学习路线图文档。

## 修改规则
1. 仅返回需要修改的部分，使用严格的 SEARCH/REPLACE 格式
2. SEARCH 块中的内容必须与原文 **完全一致**（包括空格、换行、注释）
3. 一次可以返回多个 SEARCH/REPLACE 块
4. 不要返回整个文档
5. 不要修改 HTML 注释（`<!-- ... -->`）中的元数据，除非需要更改名称
6. 新增节点时，在 `<!-- ... -->` 注释中不要填写 ID（填写 `"concept_id": null`）
7. 新增节点必须遵循现有的缩进和格式规范

## 返回格式（必须严格遵守）
<<<<<<< SEARCH
原文中需要被替换的精确内容
=======
修改后的新内容
>>>>>>> REPLACE

如需多处修改，重复上述块。
"""


class MdPatchEditorAgent:
    """
    基于 Markdown 补丁的路线图编辑 Agent
    
    性能对比（估算）：
    - 传统方案：输出完整 JSON ~20k tokens，耗时 30-60s
    - 本方案：输出差异补丁 ~1-3k tokens，耗时 3-8s
    
    配置从环境变量加载（复用 EDITOR_* 配置）
    """

    def __init__(
        self,
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.model_name = model_name or settings.EDITOR_MODEL
        self._client = AsyncOpenAI(
            api_key=api_key or settings.EDITOR_API_KEY,
            base_url=base_url or settings.EDITOR_BASE_URL or None,
        )
        self.converter = RoadmapMdConverter()

    async def execute(
        self,
        existing_framework: RoadmapFramework,
        edit_plan: EditPlan,
        user_preferences: LearningPreferences,
    ) -> RoadmapEditOutput:
        """
        基于 Markdown 补丁修改路线图框架
        
        执行流程：
          Step A: JSON → Markdown
          Step B: LLM 生成 SEARCH/REPLACE 补丁
          Step C: 应用补丁 → 新 Markdown
          Step D: Markdown → JSON（恢复运营字段）
          Step E: Diff 计算 modified_node_ids
          Step F: 生成修改总结
          
        Args:
            existing_framework: 现有路线图框架
            edit_plan: 结构化修改计划
            user_preferences: 用户偏好
            
        Returns:
            修改后的路线图框架 + 修改元数据
        """
        t0 = time.time()
        logger.info(
            "md_patch_editor_started",
            roadmap_id=existing_framework.roadmap_id,
            tasks_count=len(edit_plan.tasks),
            model=self.model_name,
        )

        # ── Step A: JSON → Markdown ──────────────────────────────────────────
        original_md = self.converter.json_to_md(existing_framework)
        logger.info(
            "md_patch_step_a_done",
            md_chars=len(original_md),
            md_lines=original_md.count("\n"),
        )

        # ── Step B: LLM 生成补丁 ─────────────────────────────────────────────
        user_message = self._build_user_message(
            original_md=original_md,
            edit_plan=edit_plan,
            user_preferences=user_preferences,
        )
        patch_text = await self._call_llm_for_patch(user_message)
        logger.info(
            "md_patch_step_b_done",
            patch_chars=len(patch_text),
            elapsed_s=round(time.time() - t0, 2),
        )

        # ── Step C: 应用补丁 ─────────────────────────────────────────────────
        new_md, patch_success = apply_search_replace_patch(original_md, patch_text)
        if not patch_success:
            logger.warning("md_patch_partial_failure", roadmap_id=existing_framework.roadmap_id)

        logger.info("md_patch_step_c_done", patch_success=patch_success)

        # ── Step D: Markdown → JSON ──────────────────────────────────────────
        updated_framework = self.converter.md_to_json(new_md, existing_framework)

        # 强制保持原始 roadmap_id
        updated_framework.roadmap_id = existing_framework.roadmap_id

        # 仅规范化新增节点的临时 ID（c-new-X → c-{n}-{n}-{n}），
        # 保持已有节点 ID 不变（避免 normalize_framework_ids 全量重排破坏运营字段追溯）
        updated_framework = normalize_new_node_ids(updated_framework)

        logger.info(
            "md_patch_step_d_done",
            stages_count=len(updated_framework.stages),
            total_hours=updated_framework.total_estimated_hours,
        )

        # ── Step E: Diff 计算 ────────────────────────────────────────────────
        modified_node_ids = compute_modified_node_ids(
            old_framework=existing_framework,
            new_framework=updated_framework,
        )

        # ── Step F: 生成修改总结 ─────────────────────────────────────────────
        modification_summary = self._build_summary(
            edit_plan=edit_plan,
            old_framework=existing_framework,
            new_framework=updated_framework,
            modified_node_ids=modified_node_ids,
        )

        total_elapsed = round(time.time() - t0, 2)
        logger.info(
            "md_patch_editor_done",
            roadmap_id=updated_framework.roadmap_id,
            modified_nodes=len(modified_node_ids),
            total_elapsed_s=total_elapsed,
        )

        return RoadmapEditOutput(
            framework=updated_framework,
            modification_summary=modification_summary,
            modified_node_ids=modified_node_ids,
        )

    def _build_user_message(
        self,
        original_md: str,
        edit_plan: EditPlan,
        user_preferences: LearningPreferences,
    ) -> str:
        """构建发送给 LLM 的用户消息"""
        tasks_text = "\n".join([
            f"- [{task.action}] 针对 {task.stage_id or '新 Stage'}: {task.instruction}"
            for task in edit_plan.tasks
        ])

        return f"""## 修改需求

**反馈摘要**: {edit_plan.feedback_summary}

**具体任务**:
{tasks_text}

**用户信息**:
- 学习目标: {user_preferences.learning_goal}
- 当前水平: {user_preferences.current_level}
- 每周时间: {user_preferences.available_hours_per_week} 小时

---

## 需要修改的路线图文档

{original_md}
"""

    async def _call_llm_for_patch(self, user_message: str) -> str:
        """
        调用 LLM 生成 SEARCH/REPLACE 补丁
        
        使用 temperature=0 确保输出精确、可重现
        """
        response = await self._client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""

    def _build_summary(
        self,
        edit_plan: EditPlan,
        old_framework: RoadmapFramework,
        new_framework: RoadmapFramework,
        modified_node_ids: list[str],
    ) -> str:
        """生成简洁的修改总结（无需额外 LLM 调用）"""
        task_summary = "；".join([
            f"{t.action} {t.stage_id or 'new'}"
            for t in edit_plan.tasks
        ])
        hours_diff = new_framework.total_estimated_hours - old_framework.total_estimated_hours
        hours_sign = "+" if hours_diff >= 0 else ""
        return (
            f"{edit_plan.feedback_summary}。"
            f"执行了 {len(edit_plan.tasks)} 个修改任务（{task_summary}），"
            f"修改了 {len(modified_node_ids)} 个节点，"
            f"总时长变化: {hours_sign}{hours_diff:.1f}h"
        )
