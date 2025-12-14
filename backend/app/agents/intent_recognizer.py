"""
意图识别Agent

负责分析用户在学习过程中的消息，识别其真实意图。
支持的意图类型：qa、quiz_request、note_record、explanation_request、analogy_request
"""
import json
from typing import Optional
from app.agents.base import BaseAgent
from app.models.domain import MentorAgentInput, IntentRecognitionResult
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class IntentRecognizerAgent(BaseAgent):
    """
    意图识别Agent
    
    快速分析用户消息，判断意图类型，以便路由到合适的子Agent。
    
    配置从环境变量加载：
    - MENTOR_PROVIDER: 模型提供商（默认: openai）
    - MENTOR_MODEL: 模型名称（默认: gpt-4o-mini）
    """
    
    def __init__(
        self,
        agent_id: str = "intent_recognizer",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        # 使用MENTOR配置，如果没有则使用ANALYZER配置
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or getattr(settings, 'MENTOR_PROVIDER', None) or settings.ANALYZER_PROVIDER,
            model_name=model_name or getattr(settings, 'MENTOR_MODEL', None) or settings.ANALYZER_MODEL,
            base_url=base_url or getattr(settings, 'MENTOR_BASE_URL', None) or settings.ANALYZER_BASE_URL,
            api_key=api_key or getattr(settings, 'MENTOR_API_KEY', None) or settings.ANALYZER_API_KEY,
            temperature=0.1,  # 低温度确保稳定的意图识别
            max_tokens=256,   # 意图识别只需要少量token
        )
    
    async def execute(self, input_data: MentorAgentInput) -> IntentRecognitionResult:
        """
        执行意图识别
        
        Args:
            input_data: 伴学Agent输入
            
        Returns:
            意图识别结果
        """
        logger.info(
            "intent_recognition_started",
            user_id=input_data.user_id,
            message_preview=input_data.user_message[:50] + "..." if len(input_data.user_message) > 50 else input_data.user_message,
        )
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "intent_recognizer.j2",
            user_message=input_data.user_message,
            roadmap_title=input_data.roadmap_title,
            concept_name=input_data.concept_name,
            concept_description=input_data.concept_description,
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_data.user_message},
        ]
        
        try:
            response = await self._call_llm(messages)
            content = response.choices[0].message.content.strip()
            
            # 解析JSON响应
            result = self._parse_result(content)
            
            logger.info(
                "intent_recognition_completed",
                intent=result.intent,
                confidence=result.confidence,
                reason=result.reason,
            )
            
            return result
        
        except Exception as e:
            logger.error(
                "intent_recognition_failed",
                error=str(e),
                user_id=input_data.user_id,
            )
            
            # 默认返回qa意图
            return IntentRecognitionResult(
                intent="qa",
                confidence=0.5,
                reason=f"意图识别失败，默认使用qa: {str(e)}",
            )
    
    def _parse_result(self, content: str) -> IntentRecognitionResult:
        """
        解析LLM返回的JSON结果
        
        Args:
            content: LLM返回的内容
            
        Returns:
            意图识别结果
        """
        # 尝试从可能的代码块中提取JSON
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()
        
        try:
            data = json.loads(content)
            
            # 验证意图类型
            valid_intents = ["qa", "quiz_request", "note_record", "explanation_request", "analogy_request"]
            intent = data.get("intent", "qa")
            if intent not in valid_intents:
                intent = "qa"
            
            return IntentRecognitionResult(
                intent=intent,
                confidence=float(data.get("confidence", 0.5)),
                reason=data.get("reason", ""),
            )
        
        except json.JSONDecodeError:
            logger.warning(
                "intent_recognition_json_parse_failed",
                content=content[:100],
            )
            return IntentRecognitionResult(
                intent="qa",
                confidence=0.5,
                reason="JSON解析失败，默认使用qa意图",
            )
