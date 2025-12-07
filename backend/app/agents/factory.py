"""
Agent Factory

统一创建和管理所有 Agent 实例。

设计模式：工厂模式
- 封装 Agent 的创建逻辑
- 从配置中读取 LLM 参数
- 支持依赖注入
- 简化测试（可替换为 Mock Agent）

使用示例：
```python
from app.agents.factory import AgentFactory
from app.config.settings import settings

# 创建工厂
factory = AgentFactory(settings)

# 创建 Agent
intent_analyzer = factory.create_intent_analyzer()
result = await intent_analyzer.execute(user_request)
```
"""
from typing import Protocol
import structlog

from app.config.settings import Settings
from app.agents.protocol import (
    IntentAnalyzerProtocol,
    CurriculumArchitectProtocol,
    StructureValidatorProtocol,
    RoadmapEditorProtocol,
    TutorialGeneratorProtocol,
    ResourceRecommenderProtocol,
    QuizGeneratorProtocol,
    ModificationAnalyzerProtocol,
    TutorialModifierProtocol,
    ResourceModifierProtocol,
    QuizModifierProtocol,
)

logger = structlog.get_logger(__name__)


class AgentFactory:
    """
    Agent 工厂类
    
    职责：
    1. 根据配置创建 Agent 实例
    2. 确保所有 Agent 配置正确
    3. 提供统一的 Agent 创建接口
    """
    
    def __init__(self, settings: Settings):
        """
        初始化工厂
        
        Args:
            settings: 应用配置对象
        """
        self.settings = settings
        logger.info("agent_factory_initialized")
    
    def create_intent_analyzer(self) -> IntentAnalyzerProtocol:
        """
        创建意图分析器
        
        从 user_request 中提取：
        - 学习主题
        - 技能水平
        - 学习偏好
        - roadmap_id
        
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
        
        根据验证结果修复路线图框架：
        - 修复 ID 冲突
        - 修复引用错误
        - 补充缺失字段
        
        Returns:
            RoadmapEditorAgent 实例
        """
        from app.agents.roadmap_editor import RoadmapEditorAgent
        
        return RoadmapEditorAgent(
            agent_id="roadmap_editor",
            model_provider=self.settings.EDITOR_PROVIDER,
            model_name=self.settings.EDITOR_MODEL,
            base_url=self.settings.EDITOR_BASE_URL,
            api_key=self.settings.EDITOR_API_KEY,
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
    
    def create_resource_recommender(self) -> ResourceRecommenderProtocol:
        """
        创建资源推荐器
        
        推荐学习资源：
        - 视频教程
        - 技术文章
        - 开发工具
        - 实战项目
        
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
    
    def create_modification_analyzer(self) -> ModificationAnalyzerProtocol:
        """
        创建修改分析器
        
        分析用户的修改请求：
        - 判断修改类型（教程/资源/测验）
        - 提取修改意图
        - 生成修改指令
        
        Returns:
            ModificationAnalyzerAgent 实例
        """
        from app.agents.modification_analyzer import ModificationAnalyzerAgent
        
        # 如果未配置独立 API Key，复用 ANALYZER_API_KEY
        api_key = (
            self.settings.MODIFICATION_ANALYZER_API_KEY 
            or self.settings.ANALYZER_API_KEY
        )
        
        return ModificationAnalyzerAgent(
            agent_id="modification_analyzer",
            model_provider=self.settings.MODIFICATION_ANALYZER_PROVIDER,
            model_name=self.settings.MODIFICATION_ANALYZER_MODEL,
            base_url=self.settings.MODIFICATION_ANALYZER_BASE_URL,
            api_key=api_key,
        )
    
    def create_tutorial_modifier(self) -> TutorialModifierProtocol:
        """
        创建教程修改器
        
        修改现有教程内容：
        - 更新文本内容
        - 修改代码示例
        - 调整难度等级
        
        Returns:
            TutorialModifierAgent 实例
        """
        from app.agents.tutorial_modifier import TutorialModifierAgent
        
        # 如果未配置独立 API Key，复用 GENERATOR_API_KEY
        api_key = (
            self.settings.TUTORIAL_MODIFIER_API_KEY 
            or self.settings.GENERATOR_API_KEY
        )
        
        return TutorialModifierAgent(
            agent_id="tutorial_modifier",
            model_provider=self.settings.TUTORIAL_MODIFIER_PROVIDER,
            model_name=self.settings.TUTORIAL_MODIFIER_MODEL,
            base_url=self.settings.TUTORIAL_MODIFIER_BASE_URL,
            api_key=api_key,
        )
    
    def create_resource_modifier(self) -> ResourceModifierProtocol:
        """
        创建资源修改器
        
        修改资源推荐内容：
        - 更新资源链接
        - 修改推荐理由
        - 调整资源类型
        
        Returns:
            ResourceModifierAgent 实例
        """
        from app.agents.resource_modifier import ResourceModifierAgent
        
        # 如果未配置独立 API Key，复用 RECOMMENDER_API_KEY
        api_key = (
            self.settings.RESOURCE_MODIFIER_API_KEY 
            or self.settings.RECOMMENDER_API_KEY
        )
        
        return ResourceModifierAgent(
            agent_id="resource_modifier",
            model_provider=self.settings.RESOURCE_MODIFIER_PROVIDER,
            model_name=self.settings.RESOURCE_MODIFIER_MODEL,
            base_url=self.settings.RESOURCE_MODIFIER_BASE_URL,
            api_key=api_key,
        )
    
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
