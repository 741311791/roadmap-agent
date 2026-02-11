"""
Quiz Generator Agent（测验生成器）
"""
import uuid
from datetime import datetime
from app.agents.base import BaseAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    QuizGenerationInput,
    QuizGenerationOutput,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class QuizGeneratorAgent(BaseAgent):
    """
    测验生成器 Agent
    
    配置从环境变量加载：
    - QUIZ_PROVIDER: 模型提供商（默认: openai）
    - QUIZ_MODEL: 模型名称（默认: gpt-4o-mini）
    - QUIZ_BASE_URL: 自定义 API 端点（可选）
    - QUIZ_API_KEY: API 密钥（必需）
    
    注意：此 Agent 不使用任何工具，直接基于 LLM 知识生成测验题目。
    """
    
    def __init__(
        self,
        agent_id: str = "quiz_generator",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.QUIZ_PROVIDER,
            model_name=model_name or settings.QUIZ_MODEL,
            base_url=base_url or settings.QUIZ_BASE_URL,
            api_key=api_key or settings.QUIZ_API_KEY,
            temperature=0.7,
            max_tokens=4096,
        )
    
    def _get_required_constraints(self) -> list[str]:
        """测验生成器需要的约束"""
        from app.models.domain import ConstraintNames
        return [
            # 通用约束
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            # 特定约束
            ConstraintNames.DIFFICULTY,
        ]
    
    async def execute(self, input_data: QuizGenerationInput) -> QuizGenerationOutput:
        """
        为给定的 Concept 生成测验题目
        
        Args:
            input_data: 包含概念、上下文和用户偏好
            
        Returns:
            测验生成结果
        """
        concept = input_data.concept
        context = input_data.context
        user_preferences = input_data.user_preferences
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "quiz_generator.j2",
            agent_name="Quiz Generator",
            role_description="专业教育评估专家，擅长设计能够准确评估学习者知识掌握程度的测验题目，题目设计科学、难度适中、解析详尽。",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
        )
        
        # 构建用户消息
        user_message = f"""
请为以下概念生成测验题目：

**概念信息**:
- 名称: {concept.name}
- 描述: {concept.description}
- 难度: {concept.difficulty}
- 预估学习时长: {concept.estimated_hours} 小时
- 前置概念: {", ".join(concept.prerequisites) if concept.prerequisites else "无"}
- 关键词: {", ".join(concept.keywords) if concept.keywords else "无"}

**上下文信息**:
- 所属阶段: {context.get("stage_name", "未知")}
- 所属模块: {context.get("module_name", "未知")}

**用户偏好**:
- 当前水平: {user_preferences.current_level}

请生成 5-8 道测验题目，要求：
1. 题目类型多样化（单选、多选、判断、填空）
2. 题目难度与概念难度和用户水平匹配
3. 每道题必须有详细的答案解析
4. 题目覆盖概念的核心知识点
5. 输出 JSON 格式
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        logger.info(
            "quiz_generator_llm_call",
            concept_id=concept.concept_id,
            concept_name=concept.name,
        )
        
        # 使用 instructor 调用 LLM，自动验证和重试
        result = await self._call_llm(
            messages,
            response_model=QuizGenerationOutput
        )
        
        # 生成 quiz_id（使用完整 UUID 确保全局唯一）
        result.quiz_id = str(uuid.uuid4())
        result.concept_id = concept.concept_id
        # ✅ created_at 有默认值，不需要手动设置
        result.total_questions = len(result.questions)
        
        logger.info(
            "quiz_generator_success",
            concept_id=concept.concept_id,
            quiz_id=result.quiz_id,
            questions_count=len(result.questions),
        )
        
        return result
