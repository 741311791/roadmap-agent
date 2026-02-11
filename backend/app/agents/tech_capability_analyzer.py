"""
技术栈能力分析Agent

功能：
- 基于LLM分析用户的答题情况
- 重点分析错题，判断知识薄弱点
- 提供详细的能力剖析报告
"""
from typing import List, Dict, Any
import structlog
from jinja2 import Environment, FileSystemLoader

from app.config.settings import settings
from app.agents.base import BaseAgent

logger = structlog.get_logger()


class TechCapabilityAnalyzer(BaseAgent):
    """
    技术栈能力分析Agent
    
    功能：
    - 基于LLM分析用户的答题情况
    - 重点分析错题，判断知识薄弱点
    - 提供详细的能力剖析报告
    """
    
    def __init__(
        self,
        agent_id: str = "tech_capability_analyzer",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        """初始化能力分析器，使用QUIZ配置"""
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.QUIZ_PROVIDER,
            model_name=model_name or settings.QUIZ_MODEL,
            base_url=base_url or settings.QUIZ_BASE_URL,
            api_key=api_key or settings.QUIZ_API_KEY,
            temperature=0.7,
            max_tokens=4096,
        )
        
        # 初始化Jinja2环境
        self.jinja_env = Environment(
            loader=FileSystemLoader("prompts"),
            autoescape=False,
        )
    
    def _get_required_constraints(self) -> list[str]:
        """技术能力分析器需要的约束"""
        from app.models.domain import ConstraintNames
        return [
            # 通用约束
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            # 特定约束
            ConstraintNames.SKILL_GAP,
            ConstraintNames.KEY_TECHNOLOGIES,
        ]
    
    async def analyze_capability(
        self,
        technology: str,
        proficiency_level: str,
        questions: List[dict],
        user_answers: List[str],
        evaluation_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        分析用户的技术栈能力
        
        Args:
            technology: 技术栈名称
            proficiency_level: 声称的能力级别
            questions: 题目列表（包含题目、正确答案、解析等）
            user_answers: 用户的答案列表
            evaluation_result: 评估结果（分数、正确率等）
            
        Returns:
            {
                "technology": "python",
                "proficiency_level": "intermediate",
                "overall_assessment": "整体评价文本",
                "strengths": ["优势领域1", "优势领域2"],
                "weaknesses": ["薄弱点1", "薄弱点2"],
                "knowledge_gaps": [
                    {
                        "topic": "主题名称",
                        "description": "详细说明",
                        "priority": "high/medium/low",
                        "recommendations": ["建议1", "建议2"]
                    }
                ],
                "learning_suggestions": ["学习建议1", "建议2"],
                "proficiency_verification": {
                    "claimed_level": "intermediate",
                    "verified_level": "beginner/intermediate/expert",
                    "confidence": "high/medium/low",
                    "reasoning": "判定依据"
                },
                "score_breakdown": {
                    "easy": {"correct": 6, "total": 7, "percentage": 85.7},
                    "medium": {"correct": 5, "total": 7, "percentage": 71.4},
                    "hard": {"correct": 2, "total": 6, "percentage": 33.3}
                }
            }
        """
        logger.info(
            "analyzing_tech_capability",
            technology=technology,
            proficiency_level=proficiency_level,
            score_percentage=evaluation_result["percentage"],
        )
        
        # 准备错题详情
        wrong_questions = self._collect_wrong_questions(questions, user_answers)
        
        # 准备正确题目的概况（用于分析优势）
        correct_questions = self._collect_correct_questions(questions, user_answers)
        
        # 计算各级别分数（从 evaluation_result 中获取）
        level_stats = evaluation_result.get("level_stats", {})
        
        # 计算百分比
        for level, stats in level_stats.items():
            if stats["total"] > 0:
                stats["percentage"] = round((stats["correct"] / stats["total"]) * 100, 1)
            else:
                stats["percentage"] = 0.0
        
        # 构建prompt
        prompt = self._build_analysis_prompt(
            technology=technology,
            proficiency_level=proficiency_level,
            evaluation_result=evaluation_result,
            wrong_questions=wrong_questions,
            correct_questions=correct_questions,
            level_stats=level_stats,
        )
        
        # 调用LLM分析
        try:
            analysis_text = await self._call_llm_for_analysis(prompt)
            
            # 解析LLM响应（假设返回JSON格式）
            import json
            analysis_result = self._parse_analysis_response(analysis_text)
            
            # 添加分数细分（使用 level_stats）
            analysis_result["score_breakdown"] = level_stats
            analysis_result["technology"] = technology
            analysis_result["proficiency_level"] = proficiency_level
            
            logger.info(
                "tech_capability_analyzed",
                technology=technology,
                verified_level=analysis_result.get("proficiency_verification", {}).get("verified_level"),
                weakness_count=len(analysis_result.get("weaknesses", [])),
                knowledge_gap_count=len(analysis_result.get("knowledge_gaps", [])),
            )
            
            return analysis_result
            
        except Exception as e:
            logger.error(
                "tech_capability_analysis_failed",
                technology=technology,
                proficiency_level=proficiency_level,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    def _collect_wrong_questions(
        self,
        questions: List[dict],
        user_answers: List[str]
    ) -> List[Dict[str, Any]]:
        """
        收集答错的题目详情
        
        Args:
            questions: 题目列表
            user_answers: 用户答案列表
            
        Returns:
            错题列表，包含题目详情
        """
        wrong_questions = []
        
        for idx, (question, answer) in enumerate(zip(questions, user_answers)):
            correct_answer = question.get("correct_answer")
            
            # 判断是否答错
            is_correct = False
            if isinstance(correct_answer, list):
                if isinstance(answer, list):
                    is_correct = set(answer) == set(correct_answer)
            else:
                is_correct = str(answer) == str(correct_answer)
            
            if not is_correct:
                wrong_questions.append({
                    "question_number": idx + 1,
                    "question": question.get("question"),
                    "proficiency_level": question.get("proficiency_level", "intermediate"),
                    "user_answer": answer,
                    "correct_answer": correct_answer,
                    "explanation": question.get("explanation"),
                    "keywords": question.get("keywords", []),
                })
        
        return wrong_questions
    
    def _collect_correct_questions(
        self,
        questions: List[dict],
        user_answers: List[str]
    ) -> List[Dict[str, Any]]:
        """
        收集答对的题目（用于分析优势）
        
        Args:
            questions: 题目列表
            user_answers: 用户答案列表
            
        Returns:
            正确题目列表
        """
        correct_questions = []
        
        for idx, (question, answer) in enumerate(zip(questions, user_answers)):
            correct_answer = question.get("correct_answer")
            
            # 判断是否答对
            is_correct = False
            if isinstance(correct_answer, list):
                if isinstance(answer, list):
                    is_correct = set(answer) == set(correct_answer)
            else:
                is_correct = str(answer) == str(correct_answer)
            
            if is_correct:
                correct_questions.append({
                    "proficiency_level": question.get("proficiency_level", "intermediate"),
                    "keywords": question.get("keywords", []),
                })
        
        return correct_questions
    
    def _build_analysis_prompt(
        self,
        technology: str,
        proficiency_level: str,
        evaluation_result: Dict[str, Any],
        wrong_questions: List[Dict[str, Any]],
        correct_questions: List[Dict[str, Any]],
        level_stats: Dict[str, Dict[str, Any]],
    ) -> str:
        """
        构建能力分析prompt
        
        Args:
            technology: 技术栈名称
            proficiency_level: 能力级别
            evaluation_result: 评估结果
            wrong_questions: 错题列表
            correct_questions: 正确题目列表
            level_stats: 各级别统计数据
            
        Returns:
            完整的分析prompt
        """
        template = self.jinja_env.get_template("tech_capability_analyzer.j2")
        return template.render(
            technology=technology,
            proficiency_level=proficiency_level,
            evaluation_result=evaluation_result,
            wrong_questions=wrong_questions,
            correct_questions=correct_questions,
            level_stats=level_stats,
        )
    
    async def _call_llm_for_analysis(self, prompt: str) -> str:
        """
        调用LLM进行能力分析
        
        Args:
            prompt: 分析提示词
            
        Returns:
            LLM返回的分析结果文本
        """
        messages = [
            {
                "role": "system",
                "content": "You are a professional technical capability analyzer. Analyze user's technical assessment results and provide detailed insights."
            },
            {"role": "user", "content": prompt},
        ]
        
        # 调用父类的_call_llm方法
        response = await super()._call_llm(messages)
        
        return response.choices[0].message.content
    
    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """
        解析LLM响应
        
        Args:
            response: LLM返回的原始文本
            
        Returns:
            解析后的分析结果字典
            
        Raises:
            ValueError: 如果无法解析JSON
        """
        import json
        
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
                raise ValueError(f"Failed to parse JSON from analysis response: {response[:200]}...")
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        实现基类的抽象方法
        
        Args:
            input_data: {
                "technology": str,
                "proficiency_level": str,
                "questions": List[dict],
                "user_answers": List[str],
                "evaluation_result": Dict[str, Any]
            }
        
        Returns:
            能力分析结果
        """
        return await self.analyze_capability(
            technology=input_data["technology"],
            proficiency_level=input_data["proficiency_level"],
            questions=input_data["questions"],
            user_answers=input_data["user_answers"],
            evaluation_result=input_data["evaluation_result"],
        )

