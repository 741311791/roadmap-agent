"""
CRUD层统一导出
"""

from app.crud.base import BaseCRUD
from app.crud.crud_roadmap import RoadmapCRUD, get_roadmap_crud
from app.crud.crud_concept import ConceptCRUD, get_concept_crud
from app.crud.crud_tutorial import TutorialCRUD, get_tutorial_crud
from app.crud.crud_resource import ResourceCRUD, get_resource_crud
from app.crud.crud_quiz import QuizCRUD, get_quiz_crud
from app.crud.crud_task import TaskCRUD, get_task_crud
from app.crud.crud_user import UserCRUD, get_user_crud
from app.crud.crud_progress import ProgressCRUD, get_progress_crud

# 技术评估相关
from app.crud.crud_tech_assessment import (
    TechAssessmentCRUD,
    get_tech_assessment_crud,
    UserProfileCRUD,
    get_user_profile_crud,
)

# 工作流相关
from app.crud.crud_workflow import (
    IntentAnalysisCRUD,
    get_intent_analysis_crud,
    ExecutionLogCRUD,
    get_execution_log_crud,
    ValidationCRUD,
    get_validation_crud,
    EditCRUD,
    get_edit_crud,
    EditPlanCRUD,
    get_edit_plan_crud,
)

__all__ = [
    # Base
    "BaseCRUD",
    # Roadmap
    "RoadmapCRUD",
    "get_roadmap_crud",
    # Concept
    "ConceptCRUD",
    "get_concept_crud",
    # Tutorial
    "TutorialCRUD",
    "get_tutorial_crud",
    # Resource
    "ResourceCRUD",
    "get_resource_crud",
    # Quiz
    "QuizCRUD",
    "get_quiz_crud",
    # Task
    "TaskCRUD",
    "get_task_crud",
    # User
    "UserCRUD",
    "get_user_crud",
    # Progress
    "ProgressCRUD",
    "get_progress_crud",
    # 技术评估CRUD
    "TechAssessmentCRUD",
    "get_tech_assessment_crud",
    "UserProfileCRUD",
    "get_user_profile_crud",
    # 工作流CRUD
    "IntentAnalysisCRUD",
    "get_intent_analysis_crud",
    "ExecutionLogCRUD",
    "get_execution_log_crud",
    "ValidationCRUD",
    "get_validation_crud",
    "EditCRUD",
    "get_edit_crud",
    "EditPlanCRUD",
    "get_edit_plan_crud",
]

