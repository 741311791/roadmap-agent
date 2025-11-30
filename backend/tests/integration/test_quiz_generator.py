"""
A6: 测验生成器 (QuizGeneratorAgent) 集成测试
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from app.agents.quiz_generator import QuizGeneratorAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    QuizGenerationInput,
    QuizGenerationOutput,
    QuizQuestion,
)


class TestQuizGeneratorAgent:
    """测验生成器 Agent 集成测试"""
    
    @pytest.fixture
    def mock_llm_quiz_response(self):
        """Mock LLM 返回的测验生成结果"""
        response_data = {
            "concept_id": "c1",
            "quiz_id": "quiz_c1_001",
            "questions": [
                {
                    "question_id": "q1",
                    "question_type": "single_choice",
                    "question": "HTML 的全称是什么？",
                    "options": [
                        "Hyper Text Markup Language",
                        "High Tech Modern Language",
                        "Hyper Transfer Markup Language",
                        "Home Tool Markup Language"
                    ],
                    "correct_answer": [0],
                    "explanation": "HTML 的全称是 Hyper Text Markup Language（超文本标记语言）。",
                    "difficulty": "easy"
                },
                {
                    "question_id": "q2",
                    "question_type": "multiple_choice",
                    "question": "以下哪些是 HTML5 新增的语义化标签？（多选）",
                    "options": ["<header>", "<div>", "<article>", "<span>"],
                    "correct_answer": [0, 2],
                    "explanation": "<header> 和 <article> 是 HTML5 新增的语义化标签，<div> 和 <span> 是早期 HTML 就有的标签。",
                    "difficulty": "medium"
                },
                {
                    "question_id": "q3",
                    "question_type": "true_false",
                    "question": "HTML 是一种编程语言。",
                    "options": ["正确", "错误"],
                    "correct_answer": [1],
                    "explanation": "HTML 是标记语言（Markup Language），不是编程语言。它用于描述文档结构，而非执行逻辑运算。",
                    "difficulty": "easy"
                },
                {
                    "question_id": "q4",
                    "question_type": "fill_blank",
                    "question": "HTML 文档的根元素是 ______。",
                    "options": [],
                    "correct_answer": [0],
                    "explanation": "答案是 <html>。HTML 文档的根元素是 <html>，所有其他元素都是它的后代。",
                    "difficulty": "easy"
                },
                {
                    "question_id": "q5",
                    "question_type": "single_choice",
                    "question": "哪个标签用于定义 HTML 文档的标题？",
                    "options": ["<head>", "<title>", "<header>", "<h1>"],
                    "correct_answer": [1],
                    "explanation": "<title> 标签用于定义文档的标题，显示在浏览器标签页上。<head> 是头部容器，<header> 是页面头部区域，<h1> 是一级标题。",
                    "difficulty": "easy"
                }
            ],
            "total_questions": 5
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = json.dumps(response_data, ensure_ascii=False)
        return response
    
    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_quiz_response,
    ):
        """测试成功生成测验"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_quiz_response
            
            agent = QuizGeneratorAgent()
            
            context = {
                "roadmap_id": "roadmap-001",
                "stage_id": "s1",
                "stage_name": "前端基础",
                "module_id": "m1",
                "module_name": "Web 基础",
            }
            
            result = await agent.generate(
                concept=sample_concept,
                context=context,
                user_preferences=sample_learning_preferences,
            )
            
            # 验证返回类型
            assert isinstance(result, QuizGenerationOutput)
            
            # 验证内容
            assert result.concept_id == sample_concept.concept_id
            assert result.quiz_id is not None
            assert len(result.questions) > 0
            assert result.total_questions == len(result.questions)
    
    @pytest.mark.asyncio
    async def test_generate_returns_diverse_question_types(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_quiz_response,
    ):
        """测试生成的测验包含多种题目类型"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_quiz_response
            
            agent = QuizGeneratorAgent()
            
            result = await agent.generate(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证题目类型多样性
            question_types = set(q.question_type for q in result.questions)
            assert len(question_types) >= 2  # 至少有两种不同类型的题目
    
    @pytest.mark.asyncio
    async def test_generate_questions_have_explanations(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_quiz_response,
    ):
        """测试每道题都有答案解析"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_quiz_response
            
            agent = QuizGeneratorAgent()
            
            result = await agent.generate(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证每道题都有解析
            for question in result.questions:
                assert question.explanation is not None
                assert len(question.explanation) > 0
    
    @pytest.mark.asyncio
    async def test_generate_questions_have_valid_answers(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_quiz_response,
    ):
        """测试每道题的答案都有效"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_quiz_response
            
            agent = QuizGeneratorAgent()
            
            result = await agent.generate(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证答案有效性
            for question in result.questions:
                assert len(question.correct_answer) > 0
                
                # 对于选择题，答案索引应该在选项范围内
                if question.question_type in ["single_choice", "multiple_choice", "true_false"]:
                    assert len(question.options) > 0
                    for answer_idx in question.correct_answer:
                        assert 0 <= answer_idx < len(question.options)
    
    @pytest.mark.asyncio
    async def test_execute_interface(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_quiz_response,
    ):
        """测试 execute 接口"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_quiz_response
            
            agent = QuizGeneratorAgent()
            
            input_data = QuizGenerationInput(
                concept=sample_concept,
                context={"roadmap_id": "roadmap-001"},
                user_preferences=sample_learning_preferences,
            )
            
            result = await agent.execute(input_data)
            
            assert isinstance(result, QuizGenerationOutput)
    
    @pytest.mark.asyncio
    async def test_generate_questions_have_difficulty(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_quiz_response,
    ):
        """测试每道题都有难度标签"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_quiz_response
            
            agent = QuizGeneratorAgent()
            
            result = await agent.generate(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证难度标签
            valid_difficulties = {"easy", "medium", "hard"}
            for question in result.questions:
                assert question.difficulty in valid_difficulties
    
    @pytest.mark.asyncio
    async def test_generate_single_choice_has_one_answer(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_quiz_response,
    ):
        """测试单选题只有一个正确答案"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_quiz_response
            
            agent = QuizGeneratorAgent()
            
            result = await agent.generate(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证单选题只有一个答案
            for question in result.questions:
                if question.question_type == "single_choice":
                    assert len(question.correct_answer) == 1
    
    @pytest.mark.asyncio
    async def test_generate_true_false_has_two_options(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_quiz_response,
    ):
        """测试判断题有两个选项"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_quiz_response
            
            agent = QuizGeneratorAgent()
            
            result = await agent.generate(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证判断题有两个选项
            for question in result.questions:
                if question.question_type == "true_false":
                    assert len(question.options) == 2

