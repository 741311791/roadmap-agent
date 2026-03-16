"""
Curriculum Architect Agent（课程架构师）

Plan-and-Execute 并行生成模式：
1. Planner：生成路线图 Stage 级大纲（RoadmapOutline）
2. Executor（并行）：为每个 Stage 并行生成详细 Module/Concept（SimplifiedStage）
3. Merger：合并所有 Stage、修正依赖、规范化 ID，输出完整 RoadmapFramework

外部契约不变：execute() 仍然返回 CurriculumDesignOutput(framework=RoadmapFramework)
"""
import asyncio
from app.agents.base import BaseAgent
from app.agents.framework_normalizer import normalize_framework_ids
from app.models.domain import (
    CurriculumDesignInput,
    CurriculumDesignOutput,
    SimplifiedRoadmapFramework,
    SimplifiedStage,
    RoadmapFramework,
    Stage,
    Module,
    Concept,
)
from app.config.settings import settings
import structlog
from pydantic import BaseModel, Field
from typing import Dict, List, Set, Tuple

logger = structlog.get_logger()


# ============================================================
# Plan-and-Execute 内部中间模型（不对外暴露）
# ============================================================

class PlannedStage(BaseModel):
    """路线图规划阶段的 Stage 大纲（不含 Module/Concept 细节）"""
    stage_id: str = Field(..., description="Stage ID，如 'stage-1'")
    name: str = Field(..., description="Stage 名称")
    description: str = Field(..., description="Stage 描述")
    order: int = Field(..., ge=1, description="Stage 顺序")
    estimated_hours: float = Field(..., ge=1.0, description="预计学习时长（小时）")
    focus_areas: list[str] = Field(..., min_length=1, description="核心学习重点关键词列表")


class RoadmapOutline(BaseModel):
    """路线图大纲（Planner 阶段产出，不含 Module/Concept 详细内容）"""
    roadmap_id: str = Field(..., description="路线图唯一 ID")
    title: str = Field(..., description="路线图标题")
    total_estimated_hours: float = Field(..., description="总预计学习时长（小时）")
    recommended_completion_weeks: int = Field(..., ge=1, description="推荐完成周数")
    stages: list[PlannedStage] = Field(..., min_length=1, description="Stage 大纲列表")


class CurriculumArchitectAgent(BaseAgent):
    """
    课程架构师 Agent
    
    配置从环境变量加载:
    - ARCHITECT_PROVIDER: 模型提供商(默认: anthropic)
    - ARCHITECT_MODEL: 模型名称(默认: claude-3-5-sonnet-20241022)
    - ARCHITECT_BASE_URL: 自定义 API 端点(可选)
    - ARCHITECT_API_KEY: API 密钥(必需)
    
    性能优化:
    - 使用简化的 response_model 提升结构化提取速度
    - 转换后补充完整字段的默认值
    - 自动检查并修复依赖关系
    """

    OUTLINE_PROMPT_TEMPLATE = "curriculum_architect_outline.j2"
    STAGE_PROMPT_TEMPLATE = "curriculum_architect_stage.j2"
    
    def __init__(
        self,
        agent_id: str = "curriculum_architect",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.ARCHITECT_PROVIDER,
            model_name=model_name or settings.ARCHITECT_MODEL,
            base_url=base_url or settings.ARCHITECT_BASE_URL,
            api_key=api_key or settings.ARCHITECT_API_KEY,
            temperature=0.1,
        )
    
    def _convert_to_full_framework(self, simplified: SimplifiedRoadmapFramework) -> RoadmapFramework:
        """
        将简化的路线图框架转换为完整框架
        
        补充所有后续阶段需要的字段默认值：
        - content_status: "pending"
        - tutorial_id: None
        - content_ref: None
        - content_version: "v1"
        - content_summary: None
        - resources_status: "pending"
        - resources_id: None
        - resources_count: 0
        - quiz_status: "pending"
        - quiz_id: None
        - quiz_questions_count: 0
        
        性能优化：使用列表推导式替代嵌套 for 循环
        
        Args:
            simplified: 简化的路线图框架
            
        Returns:
            完整的路线图框架
        """
        logger.debug(
            "converting_simplified_to_full_framework",
            roadmap_id=simplified.roadmap_id,
            stages_count=len(simplified.stages),
        )
        
        # ⚡ 使用辅助函数 + 列表推导式替代嵌套循环
        def _convert_concept(s_concept) -> Concept:
            """转换单个 Concept（补充默认值）"""
            return Concept(
                # 第一阶段提取的字段
                concept_id=s_concept.concept_id,
                name=s_concept.name,
                description=s_concept.description,
                estimated_hours=s_concept.estimated_hours,
                prerequisites=s_concept.prerequisites,
                difficulty=s_concept.difficulty,
                keywords=s_concept.keywords,
                # 补充默认值（后续阶段填充）
                content_status="pending",
                tutorial_id=None,
                content_ref=None,
                content_version="v1",
                content_summary=None,
                resources_status="pending",
                resources_id=None,
                resources_count=0,
                quiz_status="pending",
                quiz_id=None,
                quiz_questions_count=0,
            )
        
        def _convert_module(s_module) -> Module:
            """转换单个 Module"""
            return Module(
                module_id=s_module.module_id,
                name=s_module.name,
                description=s_module.description,
                concepts=[_convert_concept(c) for c in s_module.concepts],
            )
        
        def _convert_stage(s_stage) -> Stage:
            """转换单个 Stage"""
            return Stage(
                stage_id=s_stage.stage_id,
                name=s_stage.name,
                description=s_stage.description,
                order=s_stage.order,
                modules=[_convert_module(m) for m in s_stage.modules],
            )
        
        # ⚡ 一行列表推导式完成所有转换
        full_stages = [_convert_stage(s) for s in simplified.stages]
        
        # 构建完整框架
        full_framework = RoadmapFramework(
            roadmap_id=simplified.roadmap_id,
            title=simplified.title,
            stages=full_stages,
            total_estimated_hours=simplified.total_estimated_hours,
            recommended_completion_weeks=simplified.recommended_completion_weeks,
        )
        
        logger.debug(
            "conversion_completed",
            roadmap_id=full_framework.roadmap_id,
            modules_count=sum(len(stage.modules) for stage in full_framework.stages),
            concepts_count=sum(
                len(module.concepts)
                for stage in full_framework.stages
                for module in stage.modules
            ),
        )
        
        return full_framework
    
    def _check_and_fix_dependencies(self, framework: RoadmapFramework) -> Tuple[RoadmapFramework, List[str]]:
        """
        检查并修复依赖关系
        
        执行以下检查和修复：
        1. 检查前置概念是否存在于路线图中（不存在则移除）
        2. 检查是否存在循环依赖（存在则移除循环边）
        3. 检查前置概念的顺序是否合理（前置概念应出现在当前概念之前）
        
        性能优化：
        - 一次性构建概念映射（位置 + 对象引用）
        - 使用字典查找替代嵌套循环查找
        
        Args:
            framework: 完整的路线图框架
            
        Returns:
            (修复后的框架, 修复日志列表)
        """
        logger.info(
            "checking_dependencies",
            roadmap_id=framework.roadmap_id,
        )
        
        fixes: List[str] = []
        
        # ⚡ 1. 一次性构建所有映射（避免重复遍历）
        # concept_id -> (stage_order, module_idx, concept_idx)
        concept_positions: Dict[str, Tuple[int, int, int]] = {}
        # concept_id -> Concept 对象（用于快速查找和修改）
        concept_map: Dict[str, Concept] = {}
        
        for stage in framework.stages:
            for module_idx, module in enumerate(stage.modules):
                for concept_idx, concept in enumerate(module.concepts):
                    concept_positions[concept.concept_id] = (stage.order, module_idx, concept_idx)
                    concept_map[concept.concept_id] = concept
        
        all_concept_ids = set(concept_map.keys())
        
        logger.debug(
            "dependency_check_prepared",
            total_concepts=len(all_concept_ids),
        )
        
        # ⚡ 2. 批量检查并修复所有概念的前置关系
        for concept_id, concept in concept_map.items():
            current_pos = concept_positions[concept_id]
            valid_prereqs = []
            
            for prereq_id in concept.prerequisites:
                # 检查 1: 前置概念是否存在
                if prereq_id not in all_concept_ids:
                    fix_msg = f"移除不存在的前置概念: {concept_id} -> {prereq_id}"
                    fixes.append(fix_msg)
                    logger.warning(
                        "invalid_prerequisite_removed",
                        concept_id=concept_id,
                        invalid_prereq=prereq_id,
                    )
                    continue
                
                # 检查 2: 前置概念是否在当前概念之前
                prereq_pos = concept_positions[prereq_id]
                if prereq_pos >= current_pos:
                    fix_msg = f"移除顺序错误的前置概念: {concept_id} -> {prereq_id} (前置概念应出现在更早的位置)"
                    fixes.append(fix_msg)
                    logger.warning(
                        "invalid_prerequisite_order",
                        concept_id=concept_id,
                        prereq_id=prereq_id,
                        current_pos=current_pos,
                        prereq_pos=prereq_pos,
                    )
                    continue
                
                valid_prereqs.append(prereq_id)
            
            # 更新为有效的前置列表
            concept.prerequisites = valid_prereqs
        
        # ⚡ 3. 检查循环依赖（使用 DFS + 字典查找）
        cycles = self._detect_cycles(concept_map)
        if cycles:
            for cycle in cycles:
                # 移除循环中的最后一条边
                last_concept_id = cycle[-1]
                prev_concept_id = cycle[-2]
                
                # ⚡ 使用字典直接查找（O(1)），不需要嵌套循环
                concept = concept_map.get(last_concept_id)
                if concept and prev_concept_id in concept.prerequisites:
                    concept.prerequisites.remove(prev_concept_id)
                    fix_msg = f"移除循环依赖边: {last_concept_id} -> {prev_concept_id}"
                    fixes.append(fix_msg)
                    logger.warning(
                        "cycle_removed",
                        cycle=" -> ".join(cycle),
                        removed_edge=f"{last_concept_id} -> {prev_concept_id}",
                    )
        
        logger.info(
            "dependency_check_completed",
            roadmap_id=framework.roadmap_id,
            fixes_count=len(fixes),
        )
        
        return framework, fixes
    
    def _detect_cycles(self, concept_map: Dict[str, Concept]) -> List[List[str]]:
        """
        使用 DFS 检测循环依赖
        
        性能优化：直接使用 concept_map，避免重复遍历 framework
        
        Args:
            concept_map: 概念映射字典 (concept_id -> Concept)
            
        Returns:
            循环列表（每个循环是概念 ID 列表）
        """
        # ⚡ 构建邻接表（直接从 concept_map，不需要遍历 framework）
        graph: Dict[str, List[str]] = {
            cid: concept.prerequisites
            for cid, concept in concept_map.items()
        }
        
        # DFS 检测循环
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # 找到循环
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        for node in graph:
            if node not in visited:
                dfs(node)
        
        return cycles
    
    def _prepare_prompt_context(self, input_data: CurriculumDesignInput) -> dict:
        """
        准备 Prompt 模板的上下文变量
        
        Args:
            input_data: 课程设计输入
            
        Returns:
            包含所有模板变量的字典
        """
        intent = input_data.intent_analysis
        prefs = input_data.user_preferences
        
        # 获取语言偏好
        lang_prefs = prefs.get_language_preferences()
        primary_lang = lang_prefs.primary_language
        secondary_lang = lang_prefs.secondary_language if lang_prefs.secondary_language != primary_lang else None
        
        return {
            # 用户目标和需求分析
            "user_goal": prefs.learning_goal,
            "parsed_goal": intent.parsed_goal,
            "key_technologies": intent.key_technologies,
            "difficulty_profile": intent.difficulty_profile,
            "time_constraint": intent.time_constraint,
            "recommended_focus": intent.recommended_focus,
            "user_profile_summary": intent.user_profile_summary,
            "skill_gap_analysis": intent.skill_gap_analysis,
            "personalized_suggestions": intent.personalized_suggestions,
            
            # 用户画像
            "current_level": prefs.current_level,
            "career_background": prefs.career_background,
            "available_hours_per_week": prefs.available_hours_per_week,
            "motivation": prefs.motivation,
            
            # 语言偏好
            "primary_language": primary_lang,
            "secondary_language": secondary_lang,
            
            # Roadmap ID（关键！必须保持一致）
            "roadmap_id": intent.roadmap_id,
        }
    
    # ============================================================
    # Plan-and-Execute 并行生成方法
    # ============================================================

    def _format_outline_text(self, outline: "RoadmapOutline") -> str:
        """
        生成供 Stage Prompt 使用的大纲摘要文本

        Args:
            outline: 路线图大纲

        Returns:
            供模板变量注入的纯文本摘要
        """
        lines = [
            f"路线图：{outline.title}",
            f"总学习时长：{outline.total_estimated_hours} 小时 | 推荐完成周数：{outline.recommended_completion_weeks} 周",
            "",
            "各阶段概览：",
        ]
        for s in outline.stages:
            focus_text = "、".join(s.focus_areas[:4]) if s.focus_areas else "（待定）"
            lines += [
                f"  Stage {s.order}（{s.stage_id}）：{s.name}",
                f"    描述：{s.description}",
                f"    预计 {s.estimated_hours:.1f} 小时 | 核心重点：{focus_text}",
            ]
        return "\n".join(lines)

    def _format_previous_stages_text(
        self,
        outline: "RoadmapOutline",
        current_stage_order: int,
    ) -> str:
        """
        生成当前 Stage 可见的前序阶段摘要

        这样做的原因：
        - Stage 生成只需要知道前面已经规划了什么，避免重复注入整份路线图大纲
        - 同时保留跨 Stage 前置关系所需的最小上下文

        Args:
            outline: 路线图大纲
            current_stage_order: 当前 Stage 顺序

        Returns:
            前序阶段摘要文本；如果没有前序阶段则返回固定提示
        """
        previous_stages = [
            stage for stage in outline.stages if stage.order < current_stage_order
        ]
        if not previous_stages:
            return "无前序 Stage。请只在本 Stage 内建立 prerequisites。"

        lines = ["前序 Stage 摘要："]
        for stage in previous_stages:
            focus_text = "、".join(stage.focus_areas[:3]) if stage.focus_areas else "（无）"
            lines += [
                f"- Stage {stage.order}（{stage.stage_id}）：{stage.name}",
                f"  重点：{focus_text}",
            ]
        return "\n".join(lines)

    def _build_stage_prompt_context(
        self,
        prompt_context: dict,
        planned_stage: "PlannedStage",
        outline: "RoadmapOutline",
    ) -> dict:
        """
        构建 Stage 生成所需的最小 Prompt 上下文

        只保留当前 Stage 真正需要的信息，避免把完整路线图和过多全局说明重复注入到每个并发任务。

        Args:
            prompt_context: 全局上下文
            planned_stage: 当前 Stage 规划信息
            outline: 路线图大纲

        Returns:
            精简后的 Stage prompt 上下文字典
        """
        return {
            "user_goal": prompt_context["user_goal"],
            "parsed_goal": prompt_context["parsed_goal"],
            "key_technologies": prompt_context["key_technologies"],
            "current_level": prompt_context["current_level"],
            "available_hours_per_week": prompt_context["available_hours_per_week"],
            "motivation": prompt_context["motivation"],
            "primary_language": prompt_context["primary_language"],
            "stage_id": planned_stage.stage_id,
            "stage_name": planned_stage.name,
            "stage_description": planned_stage.description,
            "current_stage_order": planned_stage.order,
            "total_stages": len(outline.stages),
            "stage_estimated_hours": planned_stage.estimated_hours,
            "focus_areas": planned_stage.focus_areas,
            "previous_stages_text": self._format_previous_stages_text(
                outline,
                planned_stage.order,
            ),
        }

    async def _plan_roadmap_outline(
        self, input_data: CurriculumDesignInput
    ) -> "RoadmapOutline":
        """
        第一阶段（Planner）：生成路线图 Stage 级大纲

        不生成 Module 和 Concept 的详细内容，只确定：
        - 路线图标题、总时长、推荐周数
        - 每个 Stage 的名称、描述、顺序、预计时长和核心学习重点

        Args:
            input_data: 课程设计输入

        Returns:
            RoadmapOutline: Stage 级大纲，供并行 Stage 生成阶段使用
        """
        roadmap_id = input_data.intent_analysis.roadmap_id

        logger.info("plan_execute_planning_outline", roadmap_id=roadmap_id)

        prompt_context = self._prepare_prompt_context(input_data)
        system_prompt = self._load_system_prompt(
            self.OUTLINE_PROMPT_TEMPLATE,
            **prompt_context,
        )
        messages = [{"role": "system", "content": system_prompt}]

        try:
            outline = await self._call_llm(
                messages,
                response_model=RoadmapOutline,
                use_two_stage=False,
            )
        except Exception as exc:
            logger.warning(
                "plan_execute_outline_direct_parse_failed",
                roadmap_id=roadmap_id,
                error=str(exc),
                fallback="two_stage_generation",
            )
            outline = await self._call_llm(
                messages,
                response_model=RoadmapOutline,
                use_two_stage=True,
            )

        outline.roadmap_id = roadmap_id

        if not outline.stages:
            raise ValueError(
                f"Planner 返回了空的 stages 数组，roadmap_id={roadmap_id}。"
                f"请检查模型配置或切换到更强大的模型。"
            )

        logger.info(
            "plan_execute_outline_generated",
            roadmap_id=roadmap_id,
            title=outline.title[:40],
            stages_count=len(outline.stages),
            total_hours=outline.total_estimated_hours,
        )

        return outline

    async def _generate_stage(
        self,
        planned_stage: "PlannedStage",
        outline: "RoadmapOutline",
        prompt_context: dict,
    ) -> SimplifiedStage:
        """
        第二阶段（Executor）：为单个 PlannedStage 并行生成详细的 Module/Concept 结构

        Args:
            planned_stage: 来自 Planner 的 Stage 大纲信息
            outline: 完整路线图大纲（用于构建前序阶段摘要）
            prompt_context: 全局 prompt 上下文（用户信息等）

        Returns:
            SimplifiedStage: 包含完整 Module/Concept 的 Stage 对象
        """
        logger.info(
            "plan_execute_generating_stage",
            stage_id=planned_stage.stage_id,
            stage_name=planned_stage.name,
            order=planned_stage.order,
            estimated_hours=planned_stage.estimated_hours,
        )

        stage_context = self._build_stage_prompt_context(
            prompt_context,
            planned_stage,
            outline,
        )

        system_prompt = self._load_system_prompt(
            self.STAGE_PROMPT_TEMPLATE,
            **stage_context,
        )
        messages = [{"role": "system", "content": system_prompt}]

        try:
            stage_result = await self._call_llm(
                messages,
                response_model=SimplifiedStage,
                use_two_stage=False,
            )
        except Exception as exc:
            logger.warning(
                "plan_execute_stage_direct_parse_failed",
                stage_id=planned_stage.stage_id,
                error=str(exc),
                fallback="two_stage_generation",
            )
            stage_result = await self._call_llm(
                messages,
                response_model=SimplifiedStage,
                use_two_stage=True,
            )

        # 用规划值覆盖，确保 stage_id 和 order 与 Planner 一致
        stage_result.stage_id = planned_stage.stage_id
        stage_result.order = planned_stage.order

        concepts_count = sum(len(m.concepts) for m in stage_result.modules)
        logger.info(
            "plan_execute_stage_generated",
            stage_id=planned_stage.stage_id,
            modules_count=len(stage_result.modules),
            concepts_count=concepts_count,
        )

        return stage_result

    def _merge_to_simplified_framework(
        self,
        outline: "RoadmapOutline",
        stages: list[SimplifiedStage],
    ) -> SimplifiedRoadmapFramework:
        """
        第三阶段（Merger）：将大纲元信息与并行生成的 Stage 结果合并

        Args:
            outline: Planner 输出的路线图大纲
            stages: 所有并行生成的 SimplifiedStage 列表

        Returns:
            SimplifiedRoadmapFramework: 可传入后处理流程的完整简化框架
        """
        sorted_stages = sorted(stages, key=lambda s: s.order)

        return SimplifiedRoadmapFramework(
            roadmap_id=outline.roadmap_id,
            title=outline.title,
            total_estimated_hours=outline.total_estimated_hours,
            recommended_completion_weeks=outline.recommended_completion_weeks,
            stages=sorted_stages,
        )

    async def execute(self, input_data: CurriculumDesignInput) -> CurriculumDesignOutput:
        """
        Plan-and-Execute 模式执行课程设计

        三阶段并行加速流程：
        1. Planner：生成 Stage 级大纲（1 次 LLM 调用）
        2. Executor（并行）：asyncio.gather 并行为每个 Stage 生成 Module/Concept
        3. Merger：合并结果，复用现有依赖修复和 ID 规范化逻辑

        外部输出契约与 execute() 完全一致：返回 CurriculumDesignOutput(framework=RoadmapFramework)

        Args:
            input_data: CurriculumDesignInput 对象

        Returns:
            CurriculumDesignOutput: 课程设计输出（包含完整的 framework）
        """
        roadmap_id = input_data.intent_analysis.roadmap_id
        prompt_context = self._prepare_prompt_context(input_data)

        logger.info(
            "plan_execute_started",
            roadmap_id=roadmap_id,
            mode="plan_and_execute",
            tech_stack_count=len(input_data.intent_analysis.key_technologies),
        )

        # ============ 阶段 1: Planner ============
        outline = await self._plan_roadmap_outline(input_data)
        # ============ 阶段 2: 并行 Stage 生成 ============
        logger.info(
            "plan_execute_stage_fanout_started",
            roadmap_id=roadmap_id,
            stages_count=len(outline.stages),
        )

        stage_tasks = [
            self._generate_stage(planned_stage, outline, prompt_context)
            for planned_stage in outline.stages
        ]
        simplified_stages: list[SimplifiedStage] = list(
            await asyncio.gather(*stage_tasks)
        )

        logger.info(
            "plan_execute_stage_fanout_completed",
            roadmap_id=roadmap_id,
            generated_stages=len(simplified_stages),
        )

        # ============ 阶段 3: 合并 + 后处理（复用现有逻辑）============
        simplified_framework = self._merge_to_simplified_framework(
            outline, simplified_stages
        )
        simplified_framework.roadmap_id = roadmap_id

        if not simplified_framework.stages:
            raise ValueError(
                f"合并后 stages 为空，roadmap_id={roadmap_id}。"
                f"请检查各 Stage 生成是否均成功返回。"
            )

        full_framework = self._convert_to_full_framework(simplified_framework)
        full_framework, fixes = self._check_and_fix_dependencies(full_framework)

        if fixes:
            logger.warning(
                "plan_execute_dependencies_fixed",
                roadmap_id=roadmap_id,
                fixes_count=len(fixes),
                fixes=fixes[:5],
            )

        full_framework = normalize_framework_ids(full_framework)

        total_modules = sum(len(s.modules) for s in full_framework.stages)
        total_concepts = sum(
            len(m.concepts) for s in full_framework.stages for m in s.modules
        )

        logger.info(
            "plan_execute_completed",
            roadmap_id=roadmap_id,
            title=full_framework.title[:40],
            stages_count=len(full_framework.stages),
            modules_count=total_modules,
            concepts_count=total_concepts,
            total_hours=full_framework.total_estimated_hours,
            completion_weeks=full_framework.recommended_completion_weeks,
            dependencies_fixed=len(fixes),
        )

        return CurriculumDesignOutput(framework=full_framework)
