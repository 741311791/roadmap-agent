"""
Quiz Modifier Agent（测验修改师）

负责根据用户修改要求调整现有测验题目。
支持调整难度、增删改题目、修改题目内容和选项。
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from app.agents.base import BaseAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    QuizQuestion,
    QuizModificationInput,
    QuizModificationOutput,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class QuizModifierAgent(BaseAgent):
    """
    测验修改师 Agent
    
    配置从环境变量加载：
    - QUIZ_MODIFIER_PROVIDER: 模型提供商（默认: openai）
    - QUIZ_MODIFIER_MODEL: 模型名称（默认: gpt-4o-mini）
    - QUIZ_MODIFIER_BASE_URL: 自定义 API 端点（可选）
    - QUIZ_MODIFIER_API_KEY: API 密钥（默认复用 QUIZ_API_KEY）
    """
    
    def __init__(
        self,
        agent_id: str = "quiz_modifier",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.QUIZ_MODIFIER_PROVIDER,
            model_name=model_name or settings.QUIZ_MODIFIER_MODEL,
            base_url=base_url or settings.QUIZ_MODIFIER_BASE_URL,
            api_key=api_key or settings.get_quiz_modifier_api_key,
            temperature=0.7,
            max_tokens=4096,
        )
    
    async def modify(
        self,
        input_data: QuizModificationInput,
    ) -> QuizModificationOutput:
        """
        修改测验题目
        
        Args:
            input_data: 测验修改输入
            
        Returns:
            测验修改输出
        """
        concept = input_data.concept
        context = input_data.context
        user_preferences = input_data.user_preferences
        existing_questions = input_data.existing_questions
        modification_requirements = input_data.modification_requirements
        
        import time
        start_time = time.time()
        
        logger.info(
            "quiz_modification_started",
            agent="quiz_modifier",
            concept_id=concept.concept_id,
            concept_name=concept.name,
            existing_count=len(existing_questions),
            requirements_count=len(modification_requirements),
            requirements=modification_requirements,
        )
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "quiz_modifier.j2",
            agent_name="Quiz Modifier",
            role_description="专业的教育评估编辑师，擅长根据用户反馈调整测验题目，优化难度分布，改进题目质量。",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            existing_questions=existing_questions,
            modification_requirements=modification_requirements,
        )
        
        # 构建现有题目列表
        existing_questions_text = self._format_existing_questions(existing_questions)
        requirements_text = "\n".join([f"- {req}" for req in modification_requirements])
        
        user_message = f"""
请根据以下修改要求调整测验题目：

**概念**: {concept.name}
**描述**: {concept.description}
**难度**: {concept.difficulty}

**现有题目** ({len(existing_questions)} 道):
{existing_questions_text}

**修改要求**:
{requirements_text}

**用户水平**: {user_preferences.current_level}

请输出 JSON 格式的修改后测验题目列表。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 调用 LLM
        logger.info(
            "quiz_modifier_calling_llm",
            agent="quiz_modifier",
            concept_id=concept.concept_id,
            model=self.model_name,
        )
        
        llm_start = time.time()
        response = await self._call_llm(messages)
        llm_duration = time.time() - llm_start
        content = response.choices[0].message.content
        
        logger.info(
            "quiz_modifier_llm_completed",
            agent="quiz_modifier",
            concept_id=concept.concept_id,
            response_length=len(content) if content else 0,
            llm_duration_seconds=llm_duration,
        )
        
        # 解析输出
        if not content:
            raise ValueError("LLM 未返回任何内容")
        
        result = self._parse_modification_output(
            content, 
            concept, 
            modification_requirements,
        )
        
        total_duration = time.time() - start_time
        logger.info(
            "quiz_modification_completed",
            agent="quiz_modifier",
            concept_id=concept.concept_id,
            new_questions_count=result.total_questions,
            changes_count=len(result.changes_made),
            modification_summary=result.modification_summary[:100] if result.modification_summary else "",
            total_duration_seconds=total_duration,
        )
        
        return result
    
    def _format_existing_questions(self, questions: List[QuizQuestion]) -> str:
        """格式化现有题目列表"""
        lines = []
        for i, q in enumerate(questions, 1):
            lines.append(f"\n题目 {i} (ID: {q.question_id}, 类型: {q.question_type}, 难度: {q.difficulty}):")
            lines.append(f"  问题: {q.question}")
            if q.options:
                for j, opt in enumerate(q.options):
                    is_correct = j in q.correct_answer
                    marker = "✓" if is_correct else " "
                    lines.append(f"    [{marker}] {chr(65+j)}. {opt}")
            lines.append(f"  解析: {q.explanation}")
        return "\n".join(lines)
    
    def _parse_modification_output(
        self,
        llm_output: str,
        concept: Concept,
        requirements: List[str],
    ) -> QuizModificationOutput:
        """解析 LLM 输出"""
        try:
            # 提取 JSON
            json_content = llm_output.strip()
            
            if "```json" in json_content:
                json_start = json_content.find("```json") + 7
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
            elif "```" in json_content:
                json_start = json_content.find("```") + 3
                json_end = json_content.find("```", json_start)
                if json_end > json_start:
                    json_content = json_content[json_start:json_end].strip()
            
            # 找到 JSON 对象
            start = json_content.find("{")
            end = json_content.rfind("}") + 1
            if start >= 0 and end > start:
                json_content = json_content[start:end]
            
            data = json.loads(json_content)
            
            # 构建 QuizQuestion 列表
            questions = []
            for i, q in enumerate(data.get("questions", [])):
                try:
                    question = QuizQuestion(
                        question_id=q.get("question_id", f"q{i+1}"),
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
                        "quiz_modifier_parse_question_failed",
                        error=str(e),
                        question_data=q,
                    )
            
            # 构建输出
            return QuizModificationOutput(
                concept_id=concept.concept_id,
                quiz_id=str(uuid.uuid4()),
                questions=questions,
                total_questions=len(questions),
                modification_summary=data.get("modification_summary", "测验已按要求修改"),
                changes_made=data.get("changes_made", requirements),
                generated_at=datetime.now(),
            )
            
        except json.JSONDecodeError as e:
            logger.error(
                "quiz_modifier_json_parse_error",
                error=str(e),
                content=llm_output[:500],
            )
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
    
    async def execute(self, input_data: QuizModificationInput) -> QuizModificationOutput:
        """实现基类的抽象方法"""
        return await self.modify(input_data)

