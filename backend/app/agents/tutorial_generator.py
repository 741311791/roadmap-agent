"""
Tutorial Generator Agent（研究 / 写作两阶段模式）
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Literal

import structlog
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.config.settings import settings
from app.models.domain import (
    Concept,
    LearningPreferences,
    S3UploadRequest,
    TutorialGenerationInput,
    TutorialGenerationOutput,
)
from app.tools.mcp_loader import load_context7_tools

logger = structlog.get_logger()

DEVELOPMENT_SCENARIO_HINTS = {
    "api",
    "sdk",
    "framework",
    "library",
    "frontend",
    "backend",
    "database",
    "docker",
    "kubernetes",
    "redis",
    "celery",
    "react",
    "next.js",
    "vue",
    "nuxt",
    "svelte",
    "python",
    "typescript",
    "javascript",
    "fastapi",
    "django",
    "flask",
    "sqlalchemy",
    "pydantic",
    "langgraph",
    "openai",
    "anthropic",
    "prompt",
    "middleware",
    "hook",
    "state management",
    "deployment",
    "authentication",
    "orm",
    "cli",
    "http",
    "rest",
    "graphql",
    "git",
    "linux",
    "terminal",
    "代码",
    "编程",
    "框架",
    "接口",
    "数据库",
    "部署",
    "前端",
    "后端",
    "中间件",
    "异步",
    "状态管理",
    "认证",
}

OFFICIAL_DOC_HINTS = {
    "react",
    "next.js",
    "fastapi",
    "pydantic",
    "sqlalchemy",
    "langgraph",
    "celery",
    "docker",
    "kubernetes",
    "redis",
    "openai",
    "anthropic",
    "typescript",
    "tailwind",
    "hook",
    "hooks",
    "router",
    "middleware",
    "deployment",
    "authentication",
    "state management",
    "api",
    "sdk",
    "官方文档",
    "最佳实践",
}

VERSION_HINTS = {
    "v1",
    "v2",
    "v3",
    "react 18",
    "react 19",
    "next 13",
    "next 14",
    "next 15",
    "pydantic 1",
    "pydantic 2",
    "python 3",
}

BASIC_DEVELOPMENT_CONCEPT_HINTS = {
    "变量",
    "数据类型",
    "循环",
    "条件判断",
    "数组",
    "对象",
    "函数",
    "类",
    "字符串",
    "number",
    "string",
    "array",
    "object",
    "function",
    "class",
    "loop",
    "condition",
}


class TutorialMetadataDraft(BaseModel):
    """
    教程元数据草稿

    Args:
        title: 教程标题
        summary: 摘要
        estimated_completion_time: 预计完成时间（分钟）

    Returns:
        None

    Raises:
        ValueError: 当字段不满足约束时
    """

    title: str = Field(..., description="教程标题")
    summary: str = Field(..., max_length=500, description="教程摘要")
    estimated_completion_time: int = Field(..., ge=1, description="预计完成时间（分钟）")


class TutorialDraft(BaseModel):
    """
    教程写作阶段的结构化输出

    Args:
        markdown_content: 完整 Markdown 教程正文
        metadata: 教程元数据

    Returns:
        None

    Raises:
        ValueError: 当字段不满足约束时
    """

    markdown_content: str = Field(..., min_length=1, description="Markdown 教程正文")
    metadata: TutorialMetadataDraft = Field(..., description="教程元数据")


class TutorialResearchNotes(BaseModel):
    """
    教程研究阶段产物

    Args:
        scenario: 场景类型
        used_official_docs: 是否实际使用了官方文档
        tool_budget: 工具调用预算
        trigger_reasons: 触发研究的原因
        research_summary: 研究摘要文本

    Returns:
        None

    Raises:
        ValueError: 当字段不满足约束时
    """

    scenario: Literal["development", "non_development"] = Field(..., description="场景类型")
    used_official_docs: bool = Field(default=False, description="是否使用官方文档")
    tool_budget: int = Field(default=0, ge=0, le=3, description="研究阶段工具调用预算")
    trigger_reasons: list[str] = Field(default_factory=list, description="触发研究的原因")
    research_summary: str = Field(default="", description="研究摘要文本")

    def to_prompt_text(self) -> str:
        """
        将研究产物转换为写作阶段可读文本

        Args:
            无

        Returns:
            适合注入 Prompt 的纯文本摘要

        Raises:
            无
        """

        lines = [
            f"场景类型：{self.scenario}",
            f"是否使用官方文档：{'是' if self.used_official_docs else '否'}",
        ]
        if self.trigger_reasons:
            lines.append(f"触发原因：{'；'.join(self.trigger_reasons)}")
        if self.research_summary.strip():
            lines += ["研究摘要：", self.research_summary.strip()]
        else:
            lines.append("研究摘要：未额外查询官方文档，请基于稳健知识写作。")
        return "\n".join(lines)


class TutorialGeneratorAgent(BaseAgent):
    """
    教程生成器 Agent

    采用“研究阶段 + 结构化写作阶段”两段式流程：
    1. 先用本地规则判断是否属于开发场景，以及是否值得查询官方文档
    2. 只在必要时执行小预算 ReAct 研究
    3. 最终统一进入无工具的结构化写作阶段
    """

    def __init__(
        self,
        agent_id: str = "tutorial_generator",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.GENERATOR_PROVIDER,
            model_name=model_name or settings.GENERATOR_MODEL,
            base_url=base_url or settings.GENERATOR_BASE_URL,
            api_key=api_key or settings.GENERATOR_API_KEY,
            temperature=0.8,
            max_tokens=32768,
        )
        self._langchain_tools: dict[str, Any] = {}

    def _get_required_constraints(self) -> list[str]:
        """
        返回教程生成器依赖的约束集合

        Args:
            无

        Returns:
            约束名称列表

        Raises:
            无
        """

        from app.models.domain import ConstraintNames

        return [
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            ConstraintNames.DIFFICULTY,
            ConstraintNames.CONTENT_FORMAT_PREFERENCE,
            ConstraintNames.KEY_TECHNOLOGIES,
        ]

    async def _get_tools(self, is_dev_scenario: bool = True) -> list[Dict[str, Any]]:
        """
        获取可用工具定义

        Args:
            is_dev_scenario: 是否为开发场景

        Returns:
            OpenAI function calling 格式的工具定义列表

        Raises:
            无
        """

        if not is_dev_scenario:
            logger.info(
                "tutorial_generator_no_tools_needed",
                scenario="non_development",
            )
            return []

        self._langchain_tools = {}
        tools: list[Dict[str, Any]] = []

        try:
            context7_tools = await load_context7_tools()
            for tool in context7_tools:
                self._langchain_tools[tool.name] = tool

                if hasattr(tool, "args_schema") and tool.args_schema:
                    if hasattr(tool.args_schema, "schema"):
                        parameters = tool.args_schema.schema()
                    elif isinstance(tool.args_schema, dict):
                        parameters = tool.args_schema
                    else:
                        parameters = {"type": "object", "properties": {}}
                else:
                    parameters = {"type": "object", "properties": {}}

                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": parameters,
                        },
                    }
                )

            logger.info(
                "tutorial_generator_tools_loaded",
                scenario="development",
                tools_count=len(tools),
                tools=[tool["function"]["name"] for tool in tools],
            )
        except Exception as exc:
            logger.warning(
                "context7_tools_loading_failed",
                error=str(exc),
                message="Continue without tools and rely on model knowledge",
            )

        return tools

    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        执行工具调用

        Args:
            tool_name: 工具名称
            tool_args: 工具参数

        Returns:
            工具执行结果

        Raises:
            ValueError: 当工具不存在时抛出
            Exception: 当工具执行失败时抛出
        """

        if tool_name not in self._langchain_tools:
            raise ValueError(f"Tool '{tool_name}' not found in registered tools")

        tool = self._langchain_tools[tool_name]

        try:
            result = await tool.ainvoke(tool_args)
            logger.debug(
                "tool_executed",
                tool_name=tool_name,
                args=tool_args,
                result_preview=str(result)[:200],
            )
            return result
        except Exception as exc:
            logger.error(
                "tool_execution_failed",
                tool_name=tool_name,
                args=tool_args,
                error=str(exc),
            )
            raise

    def _build_signal_text(self, concept: Concept, context: dict) -> str:
        """
        汇总用于规则判断的信号文本

        Args:
            concept: 概念信息
            context: 上下文信息

        Returns:
            归一化后的文本

        Raises:
            无
        """

        context_fragments = []
        for value in context.values():
            if isinstance(value, str):
                context_fragments.append(value)
            elif isinstance(value, list):
                context_fragments.extend(str(item) for item in value)

        parts = [
            concept.name,
            concept.description or "",
            " ".join(concept.keywords),
            " ".join(context_fragments),
        ]
        return " ".join(parts).lower()

    @staticmethod
    def _contains_any(text: str, keywords: set[str]) -> bool:
        """
        判断文本是否包含任一关键词

        Args:
            text: 待检查文本
            keywords: 关键词集合

        Returns:
            是否命中任一关键词

        Raises:
            无
        """

        return any(keyword in text for keyword in keywords)

    def _is_development_scenario(self, concept: Concept, context: dict) -> bool:
        """
        使用本地规则判断是否为开发场景

        Args:
            concept: 概念信息
            context: 上下文信息

        Returns:
            是否属于开发场景

        Raises:
            无
        """

        signal_text = self._build_signal_text(concept, context)
        is_dev = self._contains_any(signal_text, DEVELOPMENT_SCENARIO_HINTS)

        logger.info(
            "tutorial_scenario_detected_by_rules",
            concept_id=concept.concept_id,
            concept_name=concept.name,
            scenario="development" if is_dev else "non_development",
        )
        return is_dev

    def _should_use_official_docs(
        self,
        concept: Concept,
        context: dict,
        is_dev_scenario: bool,
    ) -> tuple[bool, list[str]]:
        """
        判断是否值得进入官方文档研究阶段

        Args:
            concept: 概念信息
            context: 上下文信息
            is_dev_scenario: 是否为开发场景

        Returns:
            (是否需要研究, 触发原因列表)

        Raises:
            无
        """

        if not is_dev_scenario:
            return False, []

        signal_text = self._build_signal_text(concept, context)
        reasons: list[str] = []

        if self._contains_any(signal_text, VERSION_HINTS):
            reasons.append("概念包含明显的版本或升级信号")

        if self._contains_any(signal_text, OFFICIAL_DOC_HINTS):
            reasons.append("概念与具体框架或 API 细节强相关")

        if concept.difficulty == "hard":
            reasons.append("概念难度较高，需要降低技术细节编造风险")

        if concept.prerequisites and len(concept.prerequisites) > 3:
            reasons.append("前置关系较多，需要更稳健地约束示例与术语")

        if self._contains_any(signal_text, BASIC_DEVELOPMENT_CONCEPT_HINTS) and not self._contains_any(
            signal_text,
            VERSION_HINTS,
        ):
            reasons = [reason for reason in reasons if reason != "概念与具体框架或 API 细节强相关"]

        return bool(reasons), reasons

    def _get_react_iteration_budget(self, concept: Concept, should_research: bool) -> int:
        """
        计算研究阶段的工具调用预算

        Args:
            concept: 概念信息
            should_research: 是否进入研究阶段

        Returns:
            工具调用预算，范围为 0-3

        Raises:
            无
        """

        if not should_research:
            return 0

        budget = 2
        if concept.difficulty == "hard" or (concept.prerequisites and len(concept.prerequisites) > 3):
            budget = 3
        return budget

    def _get_research_prompt(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
        tool_budget: int,
        trigger_reasons: list[str],
    ) -> str:
        """
        构建研究阶段 Prompt

        Args:
            concept: 概念信息
            context: 上下文信息
            user_preferences: 用户偏好
            tool_budget: 工具调用预算
            trigger_reasons: 触发原因

        Returns:
            渲染后的 Prompt 文本

        Raises:
            无
        """

        language_prefs = user_preferences.get_language_preferences()
        return self._load_system_prompt(
            "tutorial_generator_research.j2",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            language_preferences=language_prefs.model_dump() if language_prefs else None,
            tool_budget=tool_budget,
            trigger_reasons=trigger_reasons,
        )

    def _get_write_prompt(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
        research_notes: TutorialResearchNotes,
    ) -> str:
        """
        构建结构化写作阶段 Prompt

        Args:
            concept: 概念信息
            context: 上下文信息
            user_preferences: 用户偏好
            research_notes: 研究阶段产物

        Returns:
            渲染后的 Prompt 文本

        Raises:
            无
        """

        language_prefs = user_preferences.get_language_preferences()
        return self._load_system_prompt(
            "tutorial_generator_write.j2",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            language_preferences=language_prefs.model_dump() if language_prefs else None,
            research_notes_text=research_notes.to_prompt_text(),
            is_dev_scenario=research_notes.scenario == "development",
        )

    async def _run_research_stage(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
    ) -> TutorialResearchNotes:
        """
        执行研究阶段

        Args:
            concept: 概念信息
            context: 上下文信息
            user_preferences: 用户偏好

        Returns:
            研究阶段产物

        Raises:
            无
        """

        is_dev_scenario = self._is_development_scenario(concept, context)
        should_research, trigger_reasons = self._should_use_official_docs(
            concept=concept,
            context=context,
            is_dev_scenario=is_dev_scenario,
        )
        tool_budget = self._get_react_iteration_budget(concept, should_research)
        scenario = "development" if is_dev_scenario else "non_development"

        if not should_research:
            logger.info(
                "tutorial_research_skipped",
                concept_id=concept.concept_id,
                scenario=scenario,
            )
            return TutorialResearchNotes(
                scenario=scenario,
                used_official_docs=False,
                tool_budget=0,
                trigger_reasons=[],
                research_summary="未进入官方文档研究阶段，请基于稳定知识输出教程。",
            )

        tools = await self._get_tools(is_dev_scenario=True)
        if not tools:
            logger.warning(
                "tutorial_research_tools_unavailable",
                concept_id=concept.concept_id,
                concept_name=concept.name,
            )
            return TutorialResearchNotes(
                scenario=scenario,
                used_official_docs=False,
                tool_budget=tool_budget,
                trigger_reasons=trigger_reasons,
                research_summary="官方文档工具不可用，请谨慎使用模型现有知识完成教程。",
            )

        system_prompt = self._get_research_prompt(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            tool_budget=tool_budget,
            trigger_reasons=trigger_reasons,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请开始研究，并在信息充分后直接输出研究摘要。"},
        ]

        try:
            response = await self._call_llm(
                messages=messages,
                tools=tools,
                use_react=True,
                max_iterations=tool_budget,
            )
            content = response.choices[0].message.content or ""
            research_summary = content.strip() or "未返回研究摘要，请在写作阶段谨慎生成。"
            logger.info(
                "tutorial_research_completed",
                concept_id=concept.concept_id,
                tool_budget=tool_budget,
                summary_length=len(research_summary),
            )
            return TutorialResearchNotes(
                scenario=scenario,
                used_official_docs=True,
                tool_budget=tool_budget,
                trigger_reasons=trigger_reasons,
                research_summary=research_summary,
            )
        except Exception as exc:
            logger.warning(
                "tutorial_research_failed_fallback_to_model_knowledge",
                concept_id=concept.concept_id,
                concept_name=concept.name,
                error=str(exc),
            )
            return TutorialResearchNotes(
                scenario=scenario,
                used_official_docs=False,
                tool_budget=tool_budget,
                trigger_reasons=trigger_reasons,
                research_summary="研究阶段失败，请基于已有知识写作，但避免编造不确定版本细节。",
            )

    async def _write_tutorial_draft(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
        research_notes: TutorialResearchNotes,
    ) -> TutorialDraft:
        """
        执行结构化写作阶段

        Args:
            concept: 概念信息
            context: 上下文信息
            user_preferences: 用户偏好
            research_notes: 研究阶段产物

        Returns:
            结构化教程草稿

        Raises:
            Exception: 当单阶段与降级阶段都失败时抛出
        """

        system_prompt = self._get_write_prompt(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            research_notes=research_notes,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "请直接输出结构化教程草稿。"},
        ]

        try:
            draft: TutorialDraft = await self._call_llm(
                messages=messages,
                response_model=TutorialDraft,
                use_two_stage=False,
            )
            logger.info(
                "tutorial_structured_write_completed",
                concept_id=concept.concept_id,
                mode="single_stage_structured",
                markdown_length=len(draft.markdown_content),
            )
            return draft
        except Exception as exc:
            logger.warning(
                "tutorial_structured_write_direct_failed",
                concept_id=concept.concept_id,
                error=str(exc),
                fallback="two_stage_generation",
            )
            draft = await self._call_llm(
                messages=messages,
                response_model=TutorialDraft,
                use_two_stage=True,
            )
            logger.info(
                "tutorial_structured_write_completed",
                concept_id=concept.concept_id,
                mode="two_stage_structured",
                markdown_length=len(draft.markdown_content),
            )
            return draft

    async def generate(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
    ) -> TutorialGenerationOutput:
        """
        生成教程

        Args:
            concept: 要生成教程的概念
            context: 上下文信息
            user_preferences: 用户偏好

        Returns:
            教程生成结果

        Raises:
            Exception: 当写作或上传失败时抛出
        """

        logger.info(
            "tutorial_generation_start",
            concept_id=concept.concept_id,
            concept_name=concept.name,
            difficulty=concept.difficulty,
        )

        research_notes = await self._run_research_stage(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
        )
        draft = await self._write_tutorial_draft(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            research_notes=research_notes,
        )

        title = draft.metadata.title or concept.name
        summary = draft.metadata.summary or (concept.description[:100] if concept.description else "")
        estimated_completion_time = draft.metadata.estimated_completion_time or int(concept.estimated_hours * 60)

        s3_key = await self._upload_to_s3(
            draft.markdown_content,
            concept.concept_id,
            context,
        )

        logger.info(
            "tutorial_generation_completed",
            concept_id=concept.concept_id,
            scenario=research_notes.scenario,
            used_official_docs=research_notes.used_official_docs,
            markdown_length=len(draft.markdown_content),
            s3_key=s3_key,
        )

        return TutorialGenerationOutput(
            concept_id=concept.concept_id,
            tutorial_id=str(uuid.uuid4()),
            title=title,
            summary=summary,
            content_url=s3_key,
            content_status="completed",
            estimated_completion_time=estimated_completion_time,
            created_at=datetime.now(),
            content_version=context.get("content_version", 1),
        )

    async def execute(self, input_data: TutorialGenerationInput) -> TutorialGenerationOutput:
        """
        实现基类抽象方法

        Args:
            input_data: 教程生成输入

        Returns:
            教程生成结果

        Raises:
            Exception: 当生成流程失败时抛出
        """

        return await self.generate(
            concept=input_data.concept,
            context=input_data.context,
            user_preferences=input_data.user_preferences,
        )

    async def _upload_to_s3(
        self,
        markdown: str,
        concept_id: str,
        context: dict,
    ) -> str:
        """
        上传教程到 S3

        Args:
            markdown: Markdown 教程正文
            concept_id: 概念 ID
            context: 上下文信息

        Returns:
            S3 Key

        Raises:
            RuntimeError: 当上传工具未注册时抛出
        """

        from app.tools.tool_helpers import tool_registry

        s3_tool = tool_registry.get("s3_upload")
        if not s3_tool:
            raise RuntimeError("S3 Storage Tool 未注册")

        roadmap_id = context.get("roadmap_id", "unknown")
        content_version = context.get("content_version", 1)
        s3_key = f"{roadmap_id}/concepts/{concept_id}/v{content_version}.md"

        upload_request = S3UploadRequest(
            key=s3_key,
            content=markdown,
            content_type="text/markdown",
        )

        await s3_tool.execute(upload_request)

        logger.info(
            "tutorial_uploaded_to_s3",
            concept_id=concept_id,
            s3_key=s3_key,
        )
        return s3_key
