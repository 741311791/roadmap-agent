"""
测试数据工厂

提供各种测试数据的工厂方法，用于生成一致性的测试数据。
"""
from datetime import datetime, timezone
import uuid
from typing import Dict, Any

from app.models.domain import (
    LearningPreferences,
    UserRequest,
    Concept,
    Module,
    Stage,
    RoadmapFramework,
    IntentAnalysisOutput,
    ValidationOutput,
    ValidationIssue,
    TutorialGenerationOutput,
    ResourceRecommendationOutput,
    QuizGenerationOutput,
    Resource,
    QuizQuestion,
)


class LearningPreferencesFactory:
    """学习偏好数据工厂"""
    
    @staticmethod
    def create_beginner_preferences() -> LearningPreferences:
        """创建初学者学习偏好"""
        return LearningPreferences(
            learning_goal="学习全栈Web开发",
            available_hours_per_week=15,
            motivation="转行进入技术领域",
            current_level="beginner",
            career_background="市场营销 3 年经验",
            content_preference=["text", "hands_on", "visual"],
            target_deadline=None,
        )
    
    @staticmethod
    def create_advanced_preferences() -> LearningPreferences:
        """创建进阶学习者偏好"""
        return LearningPreferences(
            learning_goal="深入学习系统设计和架构",
            available_hours_per_week=20,
            motivation="提升技术能力",
            current_level="advanced",
            career_background="后端开发 5 年经验",
            content_preference=["text", "video", "hands_on"],
            target_deadline=None,
        )


class UserRequestFactory:
    """用户请求数据工厂"""
    
    @staticmethod
    def create_simple_request() -> UserRequest:
        """创建简单用户请求"""
        return UserRequest(
            user_id=f"test-user-{uuid.uuid4().hex[:8]}",
            session_id=f"test-session-{uuid.uuid4().hex[:8]}",
            preferences=LearningPreferencesFactory.create_beginner_preferences(),
            additional_context="希望能在 6 个月内找到初级开发工作",
        )


class ConceptFactory:
    """概念数据工厂"""
    
    @staticmethod
    def create_simple_concept(concept_id: str = None, name: str = None) -> Concept:
        """创建简单概念"""
        concept_id = concept_id or f"c-{uuid.uuid4().hex[:8]}"
        name = name or f"测试概念 {concept_id}"
        
        return Concept(
            concept_id=concept_id,
            name=name,
            description=f"{name}的详细描述",
            estimated_hours=5.0,
            prerequisites=[],
            difficulty="easy",
            keywords=["test", "concept"],
        )
    
    @staticmethod
    def create_concept_with_prerequisites(
        concept_id: str = None,
        prerequisites: list[str] = None
    ) -> Concept:
        """创建带前置概念的概念"""
        concept_id = concept_id or f"c-{uuid.uuid4().hex[:8]}"
        prerequisites = prerequisites or []
        
        return Concept(
            concept_id=concept_id,
            name=f"进阶概念 {concept_id}",
            description="需要前置知识的进阶概念",
            estimated_hours=8.0,
            prerequisites=prerequisites,
            difficulty="medium",
            keywords=["test", "advanced"],
        )


class RoadmapFactory:
    """路线图测试数据工厂"""
    
    @staticmethod
    def create_simple_roadmap(roadmap_id: str = None) -> RoadmapFramework:
        """创建简单路线图（1个Stage, 1个Module, 2个Concepts）"""
        roadmap_id = roadmap_id or f"test-roadmap-{uuid.uuid4().hex[:8]}"
        
        concept1 = Concept(
            concept_id="c1",
            name="HTML基础",
            description="学习HTML文档结构和标签",
            estimated_hours=5.0,
            prerequisites=[],
            difficulty="easy",
            keywords=["HTML", "web"],
        )
        
        concept2 = Concept(
            concept_id="c2",
            name="CSS基础",
            description="学习CSS样式和布局",
            estimated_hours=8.0,
            prerequisites=["c1"],
            difficulty="easy",
            keywords=["CSS", "web"],
        )
        
        module = Module(
            module_id="m1",
            name="Web入门",
            description="Web开发基础知识",
            concepts=[concept1, concept2],
        )
        
        stage = Stage(
            stage_id="s1",
            name="前端基础",
            description="学习前端开发基础",
            order=1,
            modules=[module],
        )
        
        return RoadmapFramework(
            roadmap_id=roadmap_id,
            title="Web开发学习路线",
            stages=[stage],
            total_estimated_hours=13.0,
            recommended_completion_weeks=2,
        )
    
    @staticmethod
    def create_complex_roadmap(roadmap_id: str = None) -> RoadmapFramework:
        """创建复杂路线图（2个Stages, 4个Modules, 8个Concepts）"""
        roadmap_id = roadmap_id or f"test-roadmap-{uuid.uuid4().hex[:8]}"
        
        # Stage 1: 前端基础
        concepts_stage1 = [
            Concept(
                concept_id="c1",
                name="HTML基础",
                description="HTML文档结构",
                estimated_hours=5.0,
                prerequisites=[],
                difficulty="easy",
                keywords=["HTML"],
            ),
            Concept(
                concept_id="c2",
                name="CSS基础",
                description="CSS样式",
                estimated_hours=6.0,
                prerequisites=["c1"],
                difficulty="easy",
                keywords=["CSS"],
            ),
            Concept(
                concept_id="c3",
                name="JavaScript基础",
                description="JS语法",
                estimated_hours=10.0,
                prerequisites=["c1", "c2"],
                difficulty="medium",
                keywords=["JavaScript"],
            ),
            Concept(
                concept_id="c4",
                name="DOM操作",
                description="DOM API",
                estimated_hours=8.0,
                prerequisites=["c3"],
                difficulty="medium",
                keywords=["DOM", "JavaScript"],
            ),
        ]
        
        module1 = Module(
            module_id="m1",
            name="Web基础",
            description="HTML和CSS",
            concepts=concepts_stage1[:2],
        )
        
        module2 = Module(
            module_id="m2",
            name="JavaScript入门",
            description="JavaScript编程",
            concepts=concepts_stage1[2:],
        )
        
        stage1 = Stage(
            stage_id="s1",
            name="前端基础",
            description="前端开发基础知识",
            order=1,
            modules=[module1, module2],
        )
        
        # Stage 2: 前端框架
        concepts_stage2 = [
            Concept(
                concept_id="c5",
                name="React基础",
                description="React组件",
                estimated_hours=12.0,
                prerequisites=["c4"],
                difficulty="medium",
                keywords=["React"],
            ),
            Concept(
                concept_id="c6",
                name="React Hooks",
                description="React Hooks API",
                estimated_hours=10.0,
                prerequisites=["c5"],
                difficulty="medium",
                keywords=["React", "Hooks"],
            ),
            Concept(
                concept_id="c7",
                name="状态管理",
                description="Redux/Zustand",
                estimated_hours=8.0,
                prerequisites=["c6"],
                difficulty="hard",
                keywords=["State Management"],
            ),
            Concept(
                concept_id="c8",
                name="路由和导航",
                description="React Router",
                estimated_hours=6.0,
                prerequisites=["c6"],
                difficulty="medium",
                keywords=["Routing"],
            ),
        ]
        
        module3 = Module(
            module_id="m3",
            name="React框架",
            description="React开发",
            concepts=concepts_stage2[:2],
        )
        
        module4 = Module(
            module_id="m4",
            name="React进阶",
            description="状态管理和路由",
            concepts=concepts_stage2[2:],
        )
        
        stage2 = Stage(
            stage_id="s2",
            name="前端框架",
            description="学习React框架",
            order=2,
            modules=[module3, module4],
        )
        
        total_hours = sum(c.estimated_hours for s in [stage1, stage2] for m in s.modules for c in m.concepts)
        
        return RoadmapFramework(
            roadmap_id=roadmap_id,
            title="全栈Web开发学习路线",
            stages=[stage1, stage2],
            total_estimated_hours=total_hours,
            recommended_completion_weeks=8,
        )


class IntentAnalysisFactory:
    """意图分析输出工厂"""
    
    @staticmethod
    def create_simple_intent() -> IntentAnalysisOutput:
        """创建简单意图分析输出"""
        return IntentAnalysisOutput(
            parsed_goal="系统学习全栈Web开发",
            key_technologies=["HTML", "CSS", "JavaScript", "React", "Node.js"],
            difficulty_profile="零基础学习者，需要从基础开始",
            time_constraint="每周15小时，预计6个月",
            recommended_focus=["前端基础", "JavaScript核心", "React框架"],
        )


class ValidationFactory:
    """验证输出工厂"""
    
    @staticmethod
    def create_valid_output() -> ValidationOutput:
        """创建验证通过的输出"""
        return ValidationOutput(
            is_valid=True,
            issues=[],
            overall_score=95.0,
        )
    
    @staticmethod
    def create_invalid_output() -> ValidationOutput:
        """创建验证失败的输出"""
        return ValidationOutput(
            is_valid=False,
            issues=[
                ValidationIssue(
                    severity="critical",
                    location="Stage 1 > Module 1",
                    issue="概念缺少必要的前置关系",
                    suggestion="添加HTML基础作为CSS的前置概念",
                ),
                ValidationIssue(
                    severity="warning",
                    location="Stage 1",
                    issue="阶段内容过于简单",
                    suggestion="增加更多实践项目",
                ),
            ],
            overall_score=65.0,
        )


class ContentFactory:
    """内容生成输出工厂"""
    
    @staticmethod
    def create_tutorial_output(concept_id: str = "c1") -> TutorialGenerationOutput:
        """创建教程生成输出"""
        return TutorialGenerationOutput(
            concept_id=concept_id,
            tutorial_id=f"tutorial-{uuid.uuid4().hex[:8]}",
            title=f"{concept_id}基础教程",
            summary="本教程将带你从零开始学习",
            content_url=f"s3://test-bucket/tutorials/{concept_id}.md",
            content_status="completed",
            estimated_completion_time=45,
            generated_at=datetime.now(timezone.utc),
        )
    
    @staticmethod
    def create_resource_output(concept_id: str = "c1") -> ResourceRecommendationOutput:
        """创建资源推荐输出"""
        return ResourceRecommendationOutput(
            concept_id=concept_id,
            resources=[
                Resource(
                    title="官方文档",
                    url="https://example.com/docs",
                    resource_type="documentation",
                    description="官方文档",
                    estimated_time=60,
                ),
                Resource(
                    title="视频教程",
                    url="https://example.com/video",
                    resource_type="video",
                    description="入门视频",
                    estimated_time=120,
                ),
            ],
            search_query=f"{concept_id} learning resources",
            generated_at=datetime.now(timezone.utc),
        )
    
    @staticmethod
    def create_quiz_output(concept_id: str = "c1") -> QuizGenerationOutput:
        """创建测验生成输出"""
        return QuizGenerationOutput(
            concept_id=concept_id,
            quiz_id=f"quiz-{uuid.uuid4().hex[:8]}",
            questions=[
                QuizQuestion(
                    question_id="q1",
                    question_text="什么是HTML?",
                    question_type="multiple_choice",
                    options=["A. 编程语言", "B. 标记语言", "C. 数据库", "D. 框架"],
                    correct_answer="B",
                    explanation="HTML是超文本标记语言",
                    difficulty="easy",
                ),
                QuizQuestion(
                    question_id="q2",
                    question_text="HTML文档的根元素是什么?",
                    question_type="multiple_choice",
                    options=["A. <body>", "B. <head>", "C. <html>", "D. <div>"],
                    correct_answer="C",
                    explanation="<html>是HTML文档的根元素",
                    difficulty="easy",
                ),
            ],
            generated_at=datetime.now(timezone.utc),
        )


class MockResponseFactory:
    """Mock响应数据工厂"""
    
    @staticmethod
    def create_llm_intent_response() -> Dict[str, Any]:
        """创建意图分析LLM响应"""
        return {
            "parsed_goal": "系统学习全栈Web开发，从前端基础到后端API开发",
            "key_technologies": ["HTML", "CSS", "JavaScript", "React", "Node.js", "PostgreSQL"],
            "difficulty_profile": "零基础学习者，需要从基础概念开始，循序渐进",
            "time_constraint": "每周15小时，预计6个月完成基础学习",
            "recommended_focus": ["前端基础", "JavaScript核心", "React框架", "后端入门"],
        }
    
    @staticmethod
    def create_llm_curriculum_response() -> Dict[str, Any]:
        """创建课程设计LLM响应"""
        roadmap = RoadmapFactory.create_simple_roadmap("fullstack-web-dev-abc123")
        return {
            "roadmap_id": roadmap.roadmap_id,
            "title": roadmap.title,
            "stages": [
                {
                    "stage_id": stage.stage_id,
                    "name": stage.name,
                    "description": stage.description,
                    "order": stage.order,
                    "modules": [
                        {
                            "module_id": module.module_id,
                            "name": module.name,
                            "description": module.description,
                            "concepts": [
                                {
                                    "concept_id": concept.concept_id,
                                    "name": concept.name,
                                    "description": concept.description,
                                    "estimated_hours": concept.estimated_hours,
                                    "prerequisites": concept.prerequisites,
                                    "difficulty": concept.difficulty,
                                    "keywords": concept.keywords,
                                }
                                for concept in module.concepts
                            ],
                        }
                        for module in stage.modules
                    ],
                }
                for stage in roadmap.stages
            ],
            "total_estimated_hours": roadmap.total_estimated_hours,
            "recommended_completion_weeks": roadmap.recommended_completion_weeks,
        }
    
    @staticmethod
    def create_llm_validation_response(is_valid: bool = True) -> Dict[str, Any]:
        """创建验证LLM响应"""
        if is_valid:
            return {
                "is_valid": True,
                "issues": [],
                "overall_score": 95.0,
            }
        else:
            return {
                "is_valid": False,
                "issues": [
                    {
                        "severity": "critical",
                        "location": "Stage 1 > Module 1",
                        "issue": "概念缺少必要的前置关系",
                        "suggestion": "添加HTML基础作为CSS的前置概念",
                    }
                ],
                "overall_score": 65.0,
            }

