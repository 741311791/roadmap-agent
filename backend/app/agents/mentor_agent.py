"""
伴学Agent编排器

作为伴学模式的唯一入口，负责：
1. 接收用户消息和学习上下文
2. 调用IntentRecognizerAgent识别意图
3. 根据意图路由到相应的子Agent
4. 支持流式输出
"""
from typing import AsyncIterator, Optional
from app.agents.base import BaseAgent
from app.agents.intent_recognizer import IntentRecognizerAgent
from app.agents.qa_agent import QAAgent
from app.agents.note_recorder_agent import NoteRecorderAgent
from app.models.domain import MentorAgentInput, MentorAgentOutput
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class MentorAgent(BaseAgent):
    """
    伴学Agent编排器
    
    核心职责：
    1. 意图识别与路由
    2. 上下文管理
    3. 流式输出编排
    
    设计原则：
    - 单入口多路由
    - 流式优先
    - 上下文感知
    """
    
    def __init__(
        self,
        agent_id: str = "mentor_agent",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        # MentorAgent本身不直接调用LLM，而是编排子Agent
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or getattr(settings, 'MENTOR_PROVIDER', None) or settings.GENERATOR_PROVIDER,
            model_name=model_name or getattr(settings, 'MENTOR_MODEL', None) or settings.GENERATOR_MODEL,
            base_url=base_url or getattr(settings, 'MENTOR_BASE_URL', None) or settings.GENERATOR_BASE_URL,
            api_key=api_key or getattr(settings, 'MENTOR_API_KEY', None) or settings.GENERATOR_API_KEY,
            temperature=0.7,
            max_tokens=2048,
        )
        
        # 初始化子Agent
        self.intent_recognizer = IntentRecognizerAgent()
        self.qa_agent = QAAgent()
        self.note_agent = NoteRecorderAgent()
        # QuizGeneratorAgent使用现有的，不需要重新创建
    
    async def execute_stream(
        self,
        input_data: MentorAgentInput,
    ) -> AsyncIterator[str]:
        """
        流式执行伴学对话
        
        流程：
        1. 意图识别
        2. 根据意图路由到子Agent
        3. 流式输出子Agent的响应
        
        Args:
            input_data: 伴学Agent输入
            
        Yields:
            流式文本片段
        """
        logger.info(
            "mentor_agent_started",
            user_id=input_data.user_id,
            roadmap_id=input_data.roadmap_id,
            concept_id=input_data.concept_id,
            message_preview=input_data.user_message[:50] + "..." if len(input_data.user_message) > 50 else input_data.user_message,
        )
        
        # Step 1: 意图识别
        try:
            intent_result = await self.intent_recognizer.execute(input_data)
            intent = intent_result.intent
            confidence = intent_result.confidence
            
            logger.info(
                "mentor_agent_intent_recognized",
                intent=intent,
                confidence=confidence,
            )
        except Exception as e:
            logger.error(
                "mentor_agent_intent_recognition_failed",
                error=str(e),
            )
            intent = "qa"
            confidence = 0.5
        
        # Step 2: 根据意图路由到子Agent
        try:
            if intent == "quiz_request":
                # 测验请求 - 使用现有的QuizGeneratorAgent
                async for chunk in self._handle_quiz_request(input_data):
                    yield chunk
            
            elif intent == "note_record":
                # 笔记记录
                async for chunk in self.note_agent.execute_stream(input_data):
                    yield chunk
            
            else:
                # qa, explanation_request, analogy_request 都用QAAgent处理
                async for chunk in self.qa_agent.execute_stream(input_data):
                    yield chunk
        
        except Exception as e:
            logger.error(
                "mentor_agent_sub_agent_failed",
                intent=intent,
                error=str(e),
            )
            yield f"抱歉，处理你的请求时遇到了问题: {str(e)}"
    
    async def _handle_quiz_request(
        self,
        input_data: MentorAgentInput,
    ) -> AsyncIterator[str]:
        """
        处理测验请求
        
        如果当前概念已有测验，返回测验链接；
        否则提示用户该概念尚无测验。
        
        Args:
            input_data: 伴学Agent输入
            
        Yields:
            流式文本片段
        """
        if not input_data.concept_id:
            yield "请先选择一个学习概念，我才能为你生成测验题目。\n"
            return
        
        yield f"📝 正在为你查找「{input_data.concept_name or '当前概念'}」的测验...\n\n"
        
        # 查询是否已有测验
        try:
            from app.db.repository_factory import get_repository_factory
            
            repo_factory = get_repository_factory()
            async with repo_factory.create_session() as session:
                quiz_repo = repo_factory.create_quiz_repo(session)
                quiz = await quiz_repo.get_by_concept_id(
                    roadmap_id=input_data.roadmap_id,
                    concept_id=input_data.concept_id,
                )
                
                if quiz:
                    yield f"✅ 找到测验！共 {quiz.total_questions} 道题目。\n\n"
                    yield f"你可以在学习页面的「Quiz」标签页中完成测验。\n\n"
                    yield "**难度分布**:\n"
                    yield f"- 简单: {quiz.easy_count} 题\n"
                    yield f"- 中等: {quiz.medium_count} 题\n"
                    yield f"- 困难: {quiz.hard_count} 题\n"
                else:
                    yield "⚠️ 该概念暂时没有测验题目。\n\n"
                    yield "测验会在教程生成后自动创建，请稍后再试。\n"
        
        except Exception as e:
            logger.error(
                "mentor_agent_quiz_query_failed",
                error=str(e),
            )
            yield f"查询测验时出错: {str(e)}\n"
    
    async def execute(self, input_data: MentorAgentInput) -> MentorAgentOutput:
        """
        执行伴学对话（非流式版本）
        
        收集所有流式输出并返回完整响应。
        推荐使用 execute_stream 以获得更好的用户体验。
        
        Args:
            input_data: 伴学Agent输入
            
        Returns:
            完整的响应输出
        """
        # 收集所有流式输出
        full_response = ""
        async for chunk in self.execute_stream(input_data):
            full_response += chunk
        
        # 获取意图类型
        intent = await self.get_intent(input_data)
        
        return MentorAgentOutput(
            response=full_response,
            intent_type=intent,
            tool_calls=[],
            metadata={},
        )
    
    async def get_intent(self, input_data: MentorAgentInput) -> str:
        """
        获取用户消息的意图（供外部调用）
        
        Args:
            input_data: 伴学Agent输入
            
        Returns:
            意图类型
        """
        result = await self.intent_recognizer.execute(input_data)
        return result.intent
