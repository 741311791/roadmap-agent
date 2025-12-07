"""
Agent Protocol 接口定义

定义统一的 Agent 协议接口，用于类型检查和依赖注入。

设计原则：
- 使用 typing.Protocol 定义接口（鸭子类型）
- 泛型支持不同的输入输出类型
- 统一使用 execute 方法
- 支持类型安全的依赖注入
"""
from typing import Protocol, TypeVar, Generic, Any
from abc import abstractmethod

# 输入输出泛型类型变量
InputT = TypeVar('InputT', contravariant=True)
OutputT = TypeVar('OutputT', covariant=True)


class Agent(Protocol[InputT, OutputT]):
    """
    Agent 协议接口
    
    所有 Agent 必须实现此接口：
    - agent_id: 唯一标识符
    - execute: 执行 Agent 任务
    
    使用示例：
    ```python
    def process_with_agent(agent: Agent[UserRequest, IntentAnalysisOutput]):
        result = await agent.execute(request)
        return result
    ```
    """
    
    @property
    def agent_id(self) -> str:
        """Agent 唯一标识符"""
        ...
    
    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """
        执行 Agent 任务
        
        Args:
            input_data: 输入数据（类型由泛型 InputT 定义）
            
        Returns:
            输出数据（类型由泛型 OutputT 定义）
        """
        ...


# ============================================================
# 具体 Agent 类型（用于类型注解和依赖注入）
# ============================================================

class IntentAnalyzerProtocol(Protocol):
    """
    意图分析器协议
    
    职责：分析用户学习需求，提取关键信息
    输入：UserRequest
    输出：IntentAnalysisOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行意图分析"""
        ...


class CurriculumArchitectProtocol(Protocol):
    """
    课程架构师协议
    
    职责：设计学习路线图框架和知识点结构
    输入：CurriculumDesignInput
    输出：CurriculumDesignOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行课程设计"""
        ...


class StructureValidatorProtocol(Protocol):
    """
    结构验证器协议
    
    职责：验证路线图框架的结构完整性
    输入：ValidationInput
    输出：ValidationOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行结构验证"""
        ...


class RoadmapEditorProtocol(Protocol):
    """
    路线图编辑器协议
    
    职责：根据验证结果修复路线图框架
    输入：RoadmapEditInput
    输出：RoadmapEditOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行路线图编辑"""
        ...


class TutorialGeneratorProtocol(Protocol):
    """
    教程生成器协议
    
    职责：为知识点生成详细的学习教程
    输入：TutorialGenerationInput
    输出：TutorialGenerationOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行教程生成"""
        ...


class ResourceRecommenderProtocol(Protocol):
    """
    资源推荐器协议
    
    职责：推荐学习资源（视频、文章、工具等）
    输入：ResourceRecommendationInput
    输出：ResourceRecommendationOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行资源推荐"""
        ...


class QuizGeneratorProtocol(Protocol):
    """
    测验生成器协议
    
    职责：为知识点生成测验题目
    输入：QuizGenerationInput
    输出：QuizGenerationOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行测验生成"""
        ...


class ModificationAnalyzerProtocol(Protocol):
    """
    修改分析器协议
    
    职责：分析用户的修改请求并确定修改类型
    输入：ModificationAnalysisInput
    输出：ModificationAnalysisOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行修改分析"""
        ...


class TutorialModifierProtocol(Protocol):
    """
    教程修改器协议
    
    职责：修改现有教程内容
    输入：TutorialModificationInput
    输出：TutorialModificationOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行教程修改"""
        ...


class ResourceModifierProtocol(Protocol):
    """
    资源修改器协议
    
    职责：修改资源推荐内容
    输入：ResourceModificationInput
    输出：ResourceModificationOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行资源修改"""
        ...


class QuizModifierProtocol(Protocol):
    """
    测验修改器协议
    
    职责：修改测验题目
    输入：QuizModificationInput
    输出：QuizModificationOutput
    """
    
    @property
    def agent_id(self) -> str: ...
    
    async def execute(self, input_data: Any) -> Any:
        """执行测验修改"""
        ...


# ============================================================
# 工厂接口（供依赖注入使用）
# ============================================================

class AgentFactoryProtocol(Protocol):
    """
    Agent 工厂协议接口
    
    定义 Agent 工厂必须实现的方法
    """
    
    def create_intent_analyzer(self) -> IntentAnalyzerProtocol:
        """创建意图分析器"""
        ...
    
    def create_curriculum_architect(self) -> CurriculumArchitectProtocol:
        """创建课程架构师"""
        ...
    
    def create_structure_validator(self) -> StructureValidatorProtocol:
        """创建结构验证器"""
        ...
    
    def create_roadmap_editor(self) -> RoadmapEditorProtocol:
        """创建路线图编辑器"""
        ...
    
    def create_tutorial_generator(self) -> TutorialGeneratorProtocol:
        """创建教程生成器"""
        ...
    
    def create_resource_recommender(self) -> ResourceRecommenderProtocol:
        """创建资源推荐器"""
        ...
    
    def create_quiz_generator(self) -> QuizGeneratorProtocol:
        """创建测验生成器"""
        ...
    
    def create_modification_analyzer(self) -> ModificationAnalyzerProtocol:
        """创建修改分析器"""
        ...
    
    def create_tutorial_modifier(self) -> TutorialModifierProtocol:
        """创建教程修改器"""
        ...
    
    def create_resource_modifier(self) -> ResourceModifierProtocol:
        """创建资源修改器"""
        ...
    
    def create_quiz_modifier(self) -> QuizModifierProtocol:
        """创建测验修改器"""
        ...
