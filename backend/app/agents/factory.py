"""
Agent Factory（已集成统一工具框架）

统一创建和管理所有 Agent 实例。

设计模式：
- 工厂模式：封装 Agent 的创建逻辑
- 注册中心模式：管理所有可用工具（ToolRegistry）

职责：
- 封装 Agent 的创建逻辑
- 从配置中读取 LLM 参数
- 初始化并管理 ToolRegistry
- 注册所有可用工具
- 支持依赖注入
- 简化测试（可替换为 Mock Agent）

使用示例：
```python
from app.agents.factory import AgentFactory
from app.config.settings import settings

# 创建工厂（会自动初始化 ToolRegistry）
factory = AgentFactory(settings)

# 创建 Agent
tutorial_generator = factory.create_tutorial_generator()
result = await tutorial_generator.execute(input_data)
```
"""
from typing import Optional
import structlog

from app.config.settings import Settings
from app.tools.registry import ToolRegistry
from app.agents.protocol import (
    IntentAnalyzerProtocol,
    CurriculumArchitectProtocol,
    StructureValidatorProtocol,
    RoadmapEditorProtocol,
    TutorialGeneratorProtocol,
    ResourceRecommenderProtocol,
    QuizGeneratorProtocol,
    QuizModifierProtocol,
)

logger = structlog.get_logger(__name__)


class AgentFactory:
    """
    Agent 工厂类（已集成统一工具框架）
    
    职责：
    1. 根据配置创建 Agent 实例
    2. 初始化并管理 ToolRegistry
    3. 注册所有可用工具
    4. 确保所有 Agent 配置正确
    5. 提供统一的 Agent 创建接口
    """
    
    def __init__(self, settings: Settings):
        """
        初始化工厂
        
        Args:
            settings: 应用配置对象
        """
        self.settings = settings
        
        # ✅ 初始化工具注册中心
        self.tool_registry = ToolRegistry()
        
        # ✅ 注册所有可用工具
        self._register_default_tools()
        
        logger.info(
            "agent_factory_initialized",
            tools_count=len(self.tool_registry.list_tools()),
            tools=self.tool_registry.list_tools(),
        )
    
    def _register_default_tools(self):
        """
        注册默认工具
        
        包括：
        - 搜索工具（WebSearchRouter）
        - Mentor 工具（获取教程、用户画像、路线图元数据等）
        - 笔记工具（记录笔记、标记完成）
        """
        # ============================================================
        # 1. 注册搜索工具
        # ============================================================
        from app.tools.search.web_search_router import WebSearchRouter
        
        self.tool_registry.register(WebSearchRouter())
        
        # ============================================================
        # 2. 注册 Mentor 工具
        # ============================================================
        from app.tools.mentor.get_concept_tutorial_tool import GetConceptTutorialTool
        from app.tools.mentor.get_user_profile_tool import GetUserProfileTool
        from app.tools.mentor.get_roadmap_metadata_tool import GetRoadmapMetadataTool
        from app.tools.mentor.mark_content_complete_tool import MarkContentCompleteTool
        
        self.tool_registry.register(GetConceptTutorialTool())
        self.tool_registry.register(GetUserProfileTool())
        self.tool_registry.register(GetRoadmapMetadataTool())
        self.tool_registry.register(MarkContentCompleteTool())
        
        logger.info(
            "default_tools_registered",
            tools_count=len(self.tool_registry.list_tools()),
        )
    
    # ============================================================
    # initialize_mcp_servers 方法已废弃 (2026-01-19)
    # 原因：统一使用官方 langchain-mcp-adapters
    # 现在Agent直接在需要时加载MCP工具，不通过registry统一初始化
    # ============================================================
    
    # async def initialize_mcp_servers(...): 已删除
    # 
    # 如需使用MCP工具，请参考：
    # - app/tools/mcp_loader.py - 官方langchain-mcp-adapters加载器
    # - app/agents/tutorial_generator.py - 使用示例（场景区分加载）
    
    def create_intent_analyzer(self) -> IntentAnalyzerProtocol:
        """
        创建意图分析器
        
        从 user_request 中提取：
        - 学习主题
        - 技能水平
        - 学习偏好
        - roadmap_id
        
        注入 ToolRegistry 后自动启用增强模式：
        - Phase 1：ReAct 循环（LLM 按规则决定是否搜索）
        - 优先使用一阶段直出结果做本地校验
        - 仅在直出结果不可解析时，才回退到第二阶段结构化提取
        
        Returns:
            IntentAnalyzerAgent 实例
        """
        from app.agents.intent_analyzer import IntentAnalyzerAgent
        
        return IntentAnalyzerAgent(
            agent_id="intent_analyzer",
            model_provider=self.settings.ANALYZER_PROVIDER,
            model_name=self.settings.ANALYZER_MODEL,
            base_url=self.settings.ANALYZER_BASE_URL,
            api_key=self.settings.ANALYZER_API_KEY,
            tool_registry=self.tool_registry,
        )
    
    def create_curriculum_architect(self) -> CurriculumArchitectProtocol:
        """
        创建课程架构师
        
        设计路线图框架：
        - 里程碑（Milestones）
        - 阶段（Stages）
        - 任务（Tasks）
        - 知识点（Concepts）
        
        Returns:
            CurriculumArchitectAgent 实例
        """
        from app.agents.curriculum_architect import CurriculumArchitectAgent
        
        return CurriculumArchitectAgent(
            agent_id="curriculum_architect",
            model_provider=self.settings.ARCHITECT_PROVIDER,
            model_name=self.settings.ARCHITECT_MODEL,
            base_url=self.settings.ARCHITECT_BASE_URL,
            api_key=self.settings.ARCHITECT_API_KEY,
        )
    
    def create_structure_validator(self) -> StructureValidatorProtocol:
        """
        创建结构验证器
        
        验证路线图框架的：
        - ID 唯一性
        - 引用完整性
        - 结构合法性
        
        Returns:
            StructureValidatorAgent 实例
        """
        from app.agents.structure_validator import StructureValidatorAgent
        
        return StructureValidatorAgent(
            agent_id="structure_validator",
            model_provider=self.settings.VALIDATOR_PROVIDER,
            model_name=self.settings.VALIDATOR_MODEL,
            base_url=self.settings.VALIDATOR_BASE_URL,
            api_key=self.settings.VALIDATOR_API_KEY,
        )
    
    def create_roadmap_editor(self) -> RoadmapEditorProtocol:
        """
        创建路线图编辑器
        
        路由策略：
        - UPDATE / CREATE：优先走 JSON Patch 局部编辑
        - REGENERATE：走快速全量重建编辑
        - patch 失败：自动回退到传统全量编辑
        
        Returns:
            兼容 RoadmapEditorProtocol 的适配器实例
        """
        from app.agents.json_patch_editor import (
            AdaptiveRoadmapEditorAgent,
            JsonPatchEditorAgent,
        )
        from app.agents.roadmap_regenerate_editor import FastFullRegenerateEditorAgent
        from app.agents.roadmap_editor import RoadmapEditorAgent
        
        legacy_editor = RoadmapEditorAgent(
            agent_id="roadmap_editor",
            model_provider=self.settings.EDITOR_PROVIDER,
            model_name=self.settings.EDITOR_MODEL,
            base_url=self.settings.EDITOR_BASE_URL,
            api_key=self.settings.EDITOR_API_KEY,
        )
        patch_editor = JsonPatchEditorAgent(
            agent_id="json_patch_editor",
            model_provider=self.settings.EDITOR_PROVIDER,
            model_name=self.settings.EDITOR_MODEL,
            base_url=self.settings.EDITOR_BASE_URL,
            api_key=self.settings.EDITOR_API_KEY,
        )
        regenerate_editor = FastFullRegenerateEditorAgent(
            agent_id="fast_full_regenerate_editor",
            model_provider=self.settings.ARCHITECT_PROVIDER,
            model_name=self.settings.ARCHITECT_MODEL,
            base_url=self.settings.ARCHITECT_BASE_URL,
            api_key=self.settings.ARCHITECT_API_KEY,
        )
        return AdaptiveRoadmapEditorAgent(
            patch_editor=patch_editor,
            regenerate_editor=regenerate_editor,
            legacy_editor=legacy_editor,
        )
    
    def create_edit_plan_analyzer(self):
        """
        创建修改计划分析器
        
        将用户的自然语言反馈解析为结构化的修改计划：
        - 识别修改类型（add/remove/modify/reorder/merge/split）
        - 定位修改目标（stage/module/concept）
        - 生成优先级排序的修改意图列表
        - 明确必须保留不变的元素
        
        Returns:
            EditPlanAnalyzerAgent 实例
        """
        from app.agents.edit_plan_analyzer import EditPlanAnalyzerAgent
        
        # 复用 ANALYZER 配置，因为这是轻量级的意图识别任务
        return EditPlanAnalyzerAgent(
            agent_id="edit_plan_analyzer",
            model_provider=self.settings.ANALYZER_PROVIDER,
            model_name=self.settings.ANALYZER_MODEL,
            base_url=self.settings.ANALYZER_BASE_URL,
            api_key=self.settings.ANALYZER_API_KEY,
        )
    
    def create_tutorial_generator(self) -> TutorialGeneratorProtocol:
        """
        创建教程生成器
        
        为知识点生成详细教程：
        - 理论讲解
        - 代码示例
        - 实践练习
        
        Returns:
            TutorialGeneratorAgent 实例
        """
        from app.agents.tutorial_generator import TutorialGeneratorAgent
        
        return TutorialGeneratorAgent(
            agent_id="tutorial_generator",
            model_provider=self.settings.GENERATOR_PROVIDER,
            model_name=self.settings.GENERATOR_MODEL,
            base_url=self.settings.GENERATOR_BASE_URL,
            api_key=self.settings.GENERATOR_API_KEY,
        )
    
    def create_resource_recommender(
        self, 
        tavily_key: Optional[str] = None
    ) -> ResourceRecommenderProtocol:
        """
        创建资源推荐器（已集成统一工具框架）
        
        推荐学习资源：
        - 视频教程
        - 技术文章
        - 开发工具
        - 实战项目
        
        Args:
            tavily_key: 预分配的 Tavily API Key（可选，用于优化性能）
        
        Returns:
            ResourceRecommenderAgent 实例
        """
        from app.agents.resource_recommender import ResourceRecommenderAgent
        
        return ResourceRecommenderAgent(
            agent_id="resource_recommender",
            model_provider=self.settings.RECOMMENDER_PROVIDER,
            model_name=self.settings.RECOMMENDER_MODEL,
            base_url=self.settings.RECOMMENDER_BASE_URL,
            api_key=self.settings.RECOMMENDER_API_KEY,
            tavily_key=tavily_key,
            tool_registry=self.tool_registry,  # ✅ 注入 ToolRegistry
        )
    
    def create_quiz_generator(self) -> QuizGeneratorProtocol:
        """
        创建测验生成器
        
        为知识点生成测验：
        - 多选题
        - 判断题
        - 编程题
        
        Returns:
            QuizGeneratorAgent 实例
        """
        from app.agents.quiz_generator import QuizGeneratorAgent
        
        return QuizGeneratorAgent(
            agent_id="quiz_generator",
            model_provider=self.settings.QUIZ_PROVIDER,
            model_name=self.settings.QUIZ_MODEL,
            base_url=self.settings.QUIZ_BASE_URL,
            api_key=self.settings.QUIZ_API_KEY,
        )
    
    # ============================================================
    # Modifier Agents（内容修改）
    # ============================================================
    
    def create_quiz_modifier(self) -> QuizModifierProtocol:
        """
        创建测验修改器
        
        修改测验题目：
        - 更新题目内容
        - 修改选项
        - 调整正确答案
        
        Returns:
            QuizModifierAgent 实例
        """
        from app.agents.quiz_modifier import QuizModifierAgent
        
        # 如果未配置独立 API Key，复用 QUIZ_API_KEY
        api_key = (
            self.settings.QUIZ_MODIFIER_API_KEY 
            or self.settings.QUIZ_API_KEY
        )
        
        return QuizModifierAgent(
            agent_id="quiz_modifier",
            model_provider=self.settings.QUIZ_MODIFIER_PROVIDER,
            model_name=self.settings.QUIZ_MODIFIER_MODEL,
            base_url=self.settings.QUIZ_MODIFIER_BASE_URL,
            api_key=api_key,
        )
    
    # ============================================================
    # Learning & Mentor Agents（学习与导师）
    # ============================================================

    def create_mentor_agent(
        self,
        *,
        agent_type: str = "tutoring",
        model_name: str | None = None,
    ):
        """
        创建 AI 伴学助手 Agent

        Args:
            agent_type: AI 伴学助手模式
            model_name: 指定模型 ID；为空时使用默认配置

        Returns:
            MentorAgent 实例
        """
        from app.agents.mentor_agent import MentorAgent

        return MentorAgent(
            self.settings,
            agent_type=agent_type,
            model_name=model_name,
        )


# ============================================================
# 全局工厂实例（单例）
# ============================================================

_agent_factory: AgentFactory | None = None


def get_agent_factory() -> AgentFactory:
    """
    获取全局 AgentFactory 单例
    
    Returns:
        AgentFactory 实例
    """
    global _agent_factory
    
    if _agent_factory is None:
        from app.config.settings import settings
        _agent_factory = AgentFactory(settings)
    
    return _agent_factory


# ============================================================
# FastAPI 依赖注入（供 API 层使用）
# ============================================================

async def get_agent_factory_dep() -> AgentFactory:
    """
    FastAPI 依赖注入函数
    
    使用示例：
    ```python
    @router.post("/generate")
    async def generate_roadmap(
        factory: AgentFactory = Depends(get_agent_factory_dep),
    ):
        agent = factory.create_intent_analyzer()
        result = await agent.execute(...)
    ```
    
    Returns:
        AgentFactory 实例
    """
    return get_agent_factory()
