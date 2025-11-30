"""
Quiz Generator Agent（测验生成器）
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from app.agents.base import BaseAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    QuizGenerationInput,
    QuizGenerationOutput,
    QuizQuestion,
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
    
    def __init__(self):
        super().__init__(
            agent_id="quiz_generator",
            model_provider=settings.QUIZ_PROVIDER,
            model_name=settings.QUIZ_MODEL,
            base_url=settings.QUIZ_BASE_URL,
            api_key=settings.QUIZ_API_KEY,
            temperature=0.7,
            max_tokens=4096,
        )
    
    async def generate(
        self,
        concept: Concept,
        context: dict,
        user_preferences: LearningPreferences,
    ) -> QuizGenerationOutput:
        """
        为给定的 Concept 生成测验题目
        
        Args:
            concept: 要生成测验的概念
            context: 上下文信息（所属阶段、模块等）
            user_preferences: 用户偏好
            
        Returns:
            测验生成结果
        """
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
        
        # 调用 LLM（不使用工具）
        response = await self._call_llm(messages)
        content = response.choices[0].message.content
        
        # 解析输出
        if not content:
            raise ValueError("LLM 未返回任何内容")
        
        try:
            # 提取 JSON 内容
            json_content = content.strip()
            
            # 如果包含 ```json 代码块，提取其中的内容
            if "```json" in json_content:
                json_start = json_content.find("```json") + 7
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
            elif json_content.startswith("```") and "```" in json_content[3:]:
                json_start = 3
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
            
            # 解析 JSON
            data = json.loads(json_content)
            
            # 构建 QuizQuestion 列表
            questions = []
            for q in data.get("questions", []):
                try:
                    question = QuizQuestion(
                        question_id=q.get("question_id", f"q{len(questions) + 1}"),
                        question_type=q.get("question_type", "single_choice"),
                        question=q.get("question", ""),
                        options=q.get("options", []),
                        correct_answer=q.get("correct_answer", [0]),
                        explanation=q.get("explanation", ""),
                        difficulty=q.get("difficulty", "medium"),
                    )
                    questions.append(question)
                except Exception as e:
                    logger.warning(
                        "quiz_generator_parse_question_failed",
                        error=str(e),
                        question_data=q,
                    )
            
            # 生成 quiz_id（使用完整 UUID 确保全局唯一，避免重复运行时主键冲突）
            quiz_id = str(uuid.uuid4())
            
            # 构建输出
            result = QuizGenerationOutput(
                concept_id=concept.concept_id,
                quiz_id=quiz_id,
                questions=questions,
                total_questions=len(questions),
                generated_at=datetime.now(),
            )
            
            logger.info(
                "quiz_generator_success",
                concept_id=concept.concept_id,
                quiz_id=quiz_id,
                questions_count=len(questions),
            )
            return result
            
        except json.JSONDecodeError as e:
            logger.error(
                "quiz_generator_json_parse_error",
                error=str(e),
                content=content[:500],
            )
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error(
                "quiz_generator_failed",
                concept_id=concept.concept_id,
                error=str(e),
            )
            raise ValueError(f"测验生成失败: {e}")
    
    async def execute(self, input_data: QuizGenerationInput) -> QuizGenerationOutput:
        """实现基类的抽象方法"""
        return await self.generate(
            concept=input_data.concept,
            context=input_data.context,
            user_preferences=input_data.user_preferences,
        )

