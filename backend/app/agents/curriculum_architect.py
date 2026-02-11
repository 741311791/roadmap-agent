"""
Curriculum Architect Agent(课程架构师)
"""
from app.agents.base import BaseAgent
from app.agents.framework_normalizer import normalize_framework_ids
from app.models.domain import (
    CurriculumDesignInput,
    CurriculumDesignOutput,
    SimplifiedRoadmapFramework,
    RoadmapFramework,
    Stage,
    Module,
    Concept,
)
from app.config.settings import settings
import structlog
from typing import Dict, List, Set, Tuple

logger = structlog.get_logger()


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
    
    async def execute(self, input_data: CurriculumDesignInput) -> CurriculumDesignOutput:
        """
        设计三层学习路线图框架
        
        性能优化：
        1. 使用简化的 response_model 提升结构化提取速度（减少无效字段）
        2. 转换后补充完整字段的默认值
        3. 自动检查并修复依赖关系
        
        Args:
            input_data: CurriculumDesignInput 对象(包含 intent_analysis 和 user_preferences)
            
        Returns:
            CurriculumDesignOutput: 课程设计输出（包含完整的 framework）
        """
        intent_analysis = input_data.intent_analysis
        roadmap_id = intent_analysis.roadmap_id
        
        logger.info(
            "curriculum_design_started",
            roadmap_id=roadmap_id,
            tech_stack_count=len(intent_analysis.key_technologies),
            current_level=input_data.user_preferences.current_level,
        )
        
        # 准备 Prompt 上下文变量
        logger.debug("curriculum_design_preparing_context", roadmap_id=roadmap_id)
        prompt_context = self._prepare_prompt_context(input_data)
        
        # 加载并渲染 Prompt 模板
        logger.debug("curriculum_design_loading_prompt", template="curriculum_architect.j2")
        system_prompt = self._load_system_prompt("curriculum_architect.j2", **prompt_context)
        
        # 构建消息列表（只需要 system prompt，所有信息都在模板中）
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # ⭐ 性能优化：使用简化的 response_model
        logger.info(
            "curriculum_design_calling_llm",
            model=self.model_name,
            provider=self.model_provider,
            use_two_stage=True,
            optimization="使用简化的 response_model 提升结构化提取速度",
        )
        
        simplified_framework = await self._call_llm(
            messages,
            response_model=SimplifiedRoadmapFramework,  # ⭐ 使用简化模型
            use_two_stage=True,
        )
        
        # 确保使用正确的 roadmap_id
        simplified_framework.roadmap_id = roadmap_id
        
        # ====================================================================
        # 关键验证：确保 LLM 生成了非空的课程结构
        # ====================================================================
        if not simplified_framework.stages:
            logger.error(
                "curriculum_design_empty_stages",
                roadmap_id=roadmap_id,
                model=self.model_name,
                provider=self.model_provider,
                message="LLM 返回了空的 stages 数组，课程结构生成失败。"
                        "建议使用更强大的模型（如 Claude 或 GPT-4）进行课程设计。",
            )
            raise ValueError(
                f"课程设计失败：LLM 返回空的学习阶段列表。"
                f"当前模型 {self.model_provider}/{self.model_name} 可能无法处理复杂的嵌套 JSON 结构。"
                f"请检查模型配置或切换到 Claude/GPT-4 等更强大的模型。"
            )
        
        # ⭐ 转换为完整框架（补充默认值）
        logger.info(
            "converting_to_full_framework",
            roadmap_id=roadmap_id,
        )
        full_framework = self._convert_to_full_framework(simplified_framework)
        
        # ⭐ 检查并修复依赖关系
        logger.info(
            "checking_dependencies",
            roadmap_id=roadmap_id,
        )
        full_framework, fixes = self._check_and_fix_dependencies(full_framework)
        
        if fixes:
            logger.warning(
                "dependencies_fixed",
                roadmap_id=roadmap_id,
                fixes_count=len(fixes),
                fixes=fixes[:5],  # 只记录前 5 个修复
            )
        
        # ⭐ ID规范化：确保所有Stage、Module、Concept的ID符合规范
        logger.info("curriculum_design_normalizing_ids", roadmap_id=roadmap_id)
        full_framework = normalize_framework_ids(full_framework)
        
        # 统计路线图结构
        total_modules = sum(len(stage.modules) for stage in full_framework.stages)
        total_concepts = sum(
            len(module.concepts)
            for stage in full_framework.stages
            for module in stage.modules
        )
        
        logger.info(
            "curriculum_design_success",
            roadmap_id=full_framework.roadmap_id,
            title=full_framework.title[:30] + "..." if len(full_framework.title) > 30 else full_framework.title,
            stages_count=len(full_framework.stages),
            modules_count=total_modules,
            concepts_count=total_concepts,
            total_hours=full_framework.total_estimated_hours,
            completion_weeks=full_framework.recommended_completion_weeks,
            dependencies_fixed=len(fixes),
        )
        
        # 构建输出
        result = CurriculumDesignOutput(framework=full_framework)
        
        return result
