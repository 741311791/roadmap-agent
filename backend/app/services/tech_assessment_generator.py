"""
技术栈能力测试题目生成服务

功能：
- 使用 Plan & Execute 模式生成题目
- Phase 1: 规划考察内容（≥20个考点）
- Phase 2: 并发生成题目
- Phase 3: 汇总结果
- 题目类型：单选、多选、判断
"""
import json
import uuid
import asyncio
from typing import Dict, Any, List
from jinja2 import Environment, FileSystemLoader
import structlog

from app.config.settings import settings
from app.agents.base import BaseAgent

logger = structlog.get_logger()


class TechAssessmentGenerator(BaseAgent):
    """
    技术栈能力测试题目生成器
    
    复用quiz_generator的LLM配置和基础设施
    """
    
    def __init__(
        self,
        agent_id: str = "tech_assessment_generator",
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
            max_tokens=8192,  # 需要生成20道题，给足token
        )
        
        # 初始化Jinja2环境
        self.jinja_env = Environment(
            loader=FileSystemLoader("prompts"),
            autoescape=False,
        )
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应，提取JSON"""
        # 尝试直接解析
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果失败，尝试提取代码块中的JSON
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_str = response[start:end].strip()
                return json.loads(json_str)
            else:
                raise ValueError(f"Failed to parse JSON from response: {response[:200]}...")
    
    async def generate_assessment_with_plan(
        self,
        technology: str,
        proficiency_level: str,
    ) -> Dict[str, Any]:
        """
        使用 Plan & Execute 模式生成测评题目
        
        Phase 1: 生成考察内容规划（≥20个考点）
        Phase 2: 并发为每个考点生成题目
        Phase 3: 汇总结果
        
        Args:
            technology: 技术栈名称 (python, react等)
            proficiency_level: 能力级别 (beginner, intermediate, expert)
            
        Returns:
            {
                "assessment_id": "uuid",
                "technology": "python",
                "proficiency_level": "intermediate",
                "questions": [...],
                "total_questions": 20,
                "examination_plan": {...}
            }
        """
        logger.info(
            "generating_tech_assessment_with_plan",
            technology=technology,
            proficiency_level=proficiency_level,
        )
        
        try:
            # Phase 1: Planning - 生成考察内容规划
            examination_plan = await self._generate_examination_plan(
                technology, proficiency_level
            )
            
            logger.info(
                "examination_plan_generated",
                technology=technology,
                proficiency_level=proficiency_level,
                topics_count=len(examination_plan.get("examination_topics", [])),
            )
            
            # Phase 2: Concurrent Execution - 并发生成题目
            topics = examination_plan.get("examination_topics", [])
            tasks = [
                self._generate_question_for_topic(
                    technology, proficiency_level, topic
                )
                for topic in topics
            ]
            
            # 使用 asyncio.gather 并发执行，捕获异常
            questions = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Phase 3: Aggregation - 汇总结果
            valid_questions = []
            failed_count = 0
            
            for i, q in enumerate(questions):
                if isinstance(q, Exception):
                    logger.warning(
                        "question_generation_failed",
                        technology=technology,
                        proficiency_level=proficiency_level,
                        topic_index=i,
                        error=str(q),
                    )
                    failed_count += 1
                else:
                    valid_questions.append(q)
            
            logger.info(
                "tech_assessment_with_plan_generated",
                technology=technology,
                proficiency_level=proficiency_level,
                total_questions=len(valid_questions),
                failed_count=failed_count,
            )
            
            return {
                "assessment_id": str(uuid.uuid4()),
                "technology": technology,
                "proficiency_level": proficiency_level,
                "questions": valid_questions,
                "total_questions": len(valid_questions),
                "examination_plan": examination_plan,
            }
            
        except Exception as e:
            logger.error(
                "tech_assessment_with_plan_generation_failed",
                technology=technology,
                proficiency_level=proficiency_level,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    async def _generate_examination_plan(
        self,
        technology: str,
        proficiency_level: str,
    ) -> Dict[str, Any]:
        """
        Phase 1: 生成考察内容规划
        
        Args:
            technology: 技术栈名称
            proficiency_level: 能力级别
            
        Returns:
            {
                "technology": "python",
                "proficiency_level": "intermediate",
                "examination_topics": [...]
            }
        """
        # 构建规划 prompt
        template = self.jinja_env.get_template("tech_assessment_planner.j2")
        prompt = template.render(
            technology=technology,
            proficiency_level=proficiency_level,
        )
        
        # 调用 LLM
        messages = [
            {"role": "system", "content": "You are a professional technical assessment planning expert."},
            {"role": "user", "content": prompt},
        ]
        
        response = await super()._call_llm(messages)
        response_text = response.choices[0].message.content
        
        # 解析 JSON 响应
        plan = self._parse_response(response_text)
        
        # 验证规划
        if "examination_topics" not in plan:
            raise ValueError("Missing 'examination_topics' in examination plan")
        
        if len(plan["examination_topics"]) < 20:
            logger.warning(
                "insufficient_examination_topics",
                technology=technology,
                proficiency_level=proficiency_level,
                expected=20,
                actual=len(plan["examination_topics"]),
            )
        
        return plan
    
    async def _generate_question_for_topic(
        self,
        technology: str,
        proficiency_level: str,
        topic: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Phase 2: 为单个考点生成题目
        
        Args:
            technology: 技术栈名称
            proficiency_level: 能力级别
            topic: 考点信息 {topic, description, importance, question_count}
            
        Returns:
            题目字典 {question, type, options, correct_answer, explanation}
        """
        # 构建题目生成 prompt
        template = self.jinja_env.get_template("tech_assessment_question_generator.j2")
        prompt = template.render(
            technology=technology,
            proficiency_level=proficiency_level,
            topic=topic,
        )
        
        # 调用 LLM
        messages = [
            {"role": "system", "content": "You are a professional technical assessment question generator."},
            {"role": "user", "content": prompt},
        ]
        
        response = await super()._call_llm(messages)
        response_text = response.choices[0].message.content
        
        # 解析 JSON 响应
        question = self._parse_response(response_text)
        
        # 验证题目字段
        required_fields = ["question", "type", "options", "correct_answer", "explanation"]
        missing_fields = [f for f in required_fields if f not in question]
        if missing_fields:
            raise ValueError(f"Question missing required fields: {missing_fields}")
        
        return question
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        实现基类的抽象方法
        
        Args:
            input_data: {
                "technology": str,
                "proficiency_level": str
            }
        
        Returns:
            生成的测试题目数据
        """
        # 使用新的 Plan & Execute 模式
        return await self.generate_assessment_with_plan(
            technology=input_data["technology"],
            proficiency_level=input_data["proficiency_level"],
        )

