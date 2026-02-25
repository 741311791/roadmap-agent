
import asyncio
import os
import sys
from datetime import datetime

# Add backend directory to sys.path to allow imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.models.domain import (
    CurriculumDesignInput,
    IntentAnalysisOutput,
    LearningPreferences,
    UserRequest,
    LanguagePreferences
)
import structlog

# Configure structlog for better output
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)

async def main():
    print("--- Testing Curriculum Architect Agent ---")
    
    # Check API Key
    if not os.environ.get("ARCHITECT_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("Warning: ARCHITECT_API_KEY or ANTHROPIC_API_KEY not found in environment.")
        # We might want to exit or let it fail naturally
    
    # 1. Construct Mock Data
    
    # Learning Preferences
    preferences = LearningPreferences(
        learning_goal="Learn Python for Data Science",
        available_hours_per_week=10,
        motivation="Career transition",
        current_level="beginner",
        career_background="Marketing Analyst with Excel experience",
        content_preference=["visual", "hands_on"],
        primary_language="en",
        secondary_language="zh"
    )
    
    # User Request
    user_request = UserRequest(
        user_id="test_user_123",
        session_id="test_session_456",
        preferences=preferences
    )
    
    # Intent Analysis Output (Mocking the output of A1)
    intent_analysis = IntentAnalysisOutput(
        parsed_goal="Master Python programming and data analysis libraries (Pandas, NumPy) for data science applications.",
        key_technologies=["Python", "Pandas", "NumPy", "Matplotlib", "Jupyter Notebook"],
        difficulty_profile="Beginner to Intermediate",
        time_constraint="Flexible, approx 3-4 months at 10h/week",
        recommended_focus=["Python Syntax", "Data Structures", "Data Cleaning", "Visualization"],
        user_profile_summary="Marketing background, familiar with data concepts via Excel, no coding experience.",
        skill_gap_analysis=["Programming logic", "Python syntax", "Dataframe manipulation"],
        personalized_suggestions=["Focus on pandas-excel comparisons", "Use real marketing datasets"],
        estimated_learning_path_type="career_transition",
        language_preferences=LanguagePreferences(primary_language="en", secondary_language="zh"),
        roadmap_id="python-data-science-roadmap-001",
        full_analysis_data={
            "生成语言约束": "English (primary), Chinese (secondary resources)",
            "用户目标约束": "Learn Python for Data Science",
            "用户画像约束": "Marketing Analyst, Excel user, Beginner coder"
        }
    )
    
    # Curriculum Design Input
    input_data = CurriculumDesignInput(
        intent_analysis=intent_analysis,
        user_preferences=preferences
    )
    
    # 2. Instantiate Agent
    # Note: It will pick up config from environment variables
    agent = CurriculumArchitectAgent()
    
    print(f"Agent initialized: {agent.agent_id}")
    print(f"Model: {agent.model_name} ({agent.model_provider})")
    
    # 3. Execute
    try:
        print("\nExecuting curriculum design... (this may take a minute)")
        result = await agent.execute(input_data)
        
        print("\n--- Execution Successful ---")
        print(f"Roadmap ID: {result.framework.roadmap_id}")
        print(f"Roadmap Title: {result.framework.title}")
        print(f"Total Hours: {result.framework.total_estimated_hours}")
        print(f"Completion Weeks: {result.framework.recommended_completion_weeks}")
        print(f"Stages: {len(result.framework.stages)}")
        
        # 统计信息
        total_modules = sum(len(s.modules) for s in result.framework.stages)
        total_concepts = sum(
            len(m.concepts) for s in result.framework.stages for m in s.modules
        )
        print(f"Total Modules: {total_modules}")
        print(f"Total Concepts: {total_concepts}")
        
        print("\n--- Roadmap Structure ---")
        for stage in result.framework.stages:
            print(f"\nStage {stage.order}: {stage.name} ({stage.total_hours}h)")
            for module in stage.modules:
                print(f"  - Module: {module.name} ({module.total_hours}h)")
                for concept in module.concepts:
                    prereqs = ", ".join(concept.prerequisites) if concept.prerequisites else "None"
                    print(f"    * [{concept.difficulty}] {concept.name} ({concept.estimated_hours}h) - prereqs: {prereqs}")
        
    except Exception as e:
        print(f"\n--- Execution Failed ---")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
