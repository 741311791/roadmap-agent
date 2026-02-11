"""
技术栈能力测试 API 端点

提供技术栈能力测验题目获取和评估功能
"""
import random
import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_db_transaction
from app.db.redis_client import redis_client
from app.services.learning.assessment_service import TechAssessmentService, evaluate_answers
from app.agents.tech_assessment_generator import TechAssessmentGenerator
from app.agents.tech_capability_analyzer import TechCapabilityAnalyzer

# ✅ 导入 Schema（符合企业级架构规范）
from app.schemas.tech_assessment import (
    QuestionResponse,
    AssessmentResponse,
    EvaluateRequest,
    EvaluationResult,
    KnowledgeGap,
    ProficiencyVerification,
    ScoreBreakdownItem,
    CapabilityAnalysisResult,
    AnalyzeCapabilityRequest,
    CustomTechAssessmentRequest,
    CustomAssessmentResponse,
    AvailableTechnologiesResponse,
    AnalyzeTaskResponse,
)

router = APIRouter(prefix="/learning/assessment", tags=["assessments"])
logger = structlog.get_logger()

# Redis 缓存配置
ASSESSMENT_CACHE_TTL = 7200  # 2小时过期时间
ASSESSMENT_CACHE_PREFIX = "assessment:session:"

# 根据用户选择的级别，混合抽取各 proficiency_level 的题目（共10题）
PROFICIENCY_DISTRIBUTION = {
    "beginner": {
        "beginner": 7,       # 70% 基础题
        "intermediate": 2,   # 20% 中等题
        "expert": 1,         # 10% 进阶题
    },
    "intermediate": {
        "beginner": 2,       # 20% 基础题
        "intermediate": 6,   # 60% 中等题
        "expert": 2,         # 20% 进阶题
    },
    "expert": {
        "beginner": 1,       # 10% 基础题
        "intermediate": 3,   # 30% 中等题
        "expert": 6,         # 60% 进阶题
    },
}


# ============================================================
# 缓存辅助函数
# ============================================================

async def _save_assessment_to_cache(assessment_id: str, questions: list):
    """
    将测验题目保存到Redis缓存
    
    Args:
        assessment_id: 测验ID
        questions: 题目列表（包含答案）
    """
    cache_key = f"{ASSESSMENT_CACHE_PREFIX}{assessment_id}"
    await redis_client.set_json(cache_key, questions, ex=ASSESSMENT_CACHE_TTL)
    
    logger.debug(
        "assessment_saved_to_cache",
        assessment_id=assessment_id,
        question_count=len(questions),
    )


async def _get_assessment_from_cache(assessment_id: str) -> list | None:
    """
    从Redis缓存获取测验题目
    
    Args:
        assessment_id: 测验ID
        
    Returns:
        题目列表（包含答案），如果不存在或已过期则返回None
    """
    cache_key = f"{ASSESSMENT_CACHE_PREFIX}{assessment_id}"
    questions = await redis_client.get_json(cache_key)
    
    if questions:
        logger.debug(
            "assessment_retrieved_from_cache",
            assessment_id=assessment_id,
            question_count=len(questions),
        )
    else:
        logger.debug(
            "assessment_not_found_in_cache",
            assessment_id=assessment_id,
        )
    
    return questions


# ============================================================
# API Endpoints
# ============================================================

@router.get("/available-technologies", response_model=AvailableTechnologiesResponse)
async def get_available_technologies(
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    获取所有有测验题目的技术栈列表
    
    Returns:
        所有可用技术栈的列表（去重并排序）
        
    Example:
        GET /api/v1/tech-assessments/available-technologies
        Response: {
            "technologies": ["angular", "aws", "docker", "python", "react", ...],
            "count": 20
        }
    """
    logger.info("get_available_technologies_requested")
    
    service = TechAssessmentService()
    technologies = await service.get_available_technologies(db)
    
    logger.info(
        "available_technologies_retrieved",
        count=len(technologies),
    )
    
    return AvailableTechnologiesResponse(
        technologies=technologies,
        count=len(technologies),
    )


@router.get("/{technology}/{proficiency}", response_model=AssessmentResponse)
async def get_tech_assessment(
    technology: str,
    proficiency: str,
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    获取技术栈能力测验题目（混合级别抽选10题）
    
    根据用户能力级别，从3个级别的题库中按不同比例随机抽选题目：
    - Beginner: 7道beginner, 2道intermediate, 1道expert（侧重基础）
    - Intermediate: 2道beginner, 6道intermediate, 2道expert（均衡分布）
    - Expert: 1道beginner, 3道intermediate, 6道expert（侧重进阶）
    
    Args:
        technology: 技术栈名称 (python, react, java等)
        proficiency: 能力级别 (beginner, intermediate, expert)
        
    Returns:
        包含10道题目的测验数据（不包含答案和解析）
        
    Raises:
        HTTPException: 404 - 测验不存在
        HTTPException: 400 - 题库题目不足
        
    Example:
        GET /api/v1/tech-assessments/python/intermediate
    """
    logger.info(
        "get_tech_assessment_requested",
        technology=technology,
        proficiency_level=proficiency,
    )
    
    service = TechAssessmentService()
    
    # 获取三个级别的题库
    try:
        assessments_dict = await service.get_assessments_by_levels(db, technology)
        assessments = {level: obj.questions for level, obj in assessments_dict.items()}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    # 获取目标分布比例
    distribution = PROFICIENCY_DISTRIBUTION.get(proficiency, PROFICIENCY_DISTRIBUTION["intermediate"])
    
    # 按分布比例抽取题目
    selected_questions = []
    
    for level, count in distribution.items():
        available = assessments[level]
        
        if len(available) < count:
            logger.warning(
                "insufficient_questions_for_level",
                technology=technology,
                proficiency_level=proficiency,
                target_level=level,
                required=count,
                available=len(available),
            )
            # 如果题目不足，全部选上
            selected = available.copy()
        else:
            # 随机抽选指定数量的题目
            selected = random.sample(available, count)
        
        # 为每道题打上来源级别的标签
        for q in selected:
            q["proficiency_level"] = level
        
        selected_questions.extend(selected)
    
    # 验证题目总数
    if len(selected_questions) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient questions in pool. Required: 10, Available: {len(selected_questions)}"
        )
    
    # 随机打乱题目顺序
    random.shuffle(selected_questions)
    
    # 生成 assessment_id
    assessment_id = str(uuid.uuid4())
    
    # 将完整题目（包含答案）存储到 Redis 缓存中，供评估时使用
    await _save_assessment_to_cache(assessment_id, selected_questions)
    
    # 过滤题目，移除答案和解析，防止作弊
    filtered_questions = []
    for q in selected_questions:
        filtered_questions.append(QuestionResponse(
            question=q["question"],
            type=q["type"],
            options=q["options"],
            proficiency_level=q.get("proficiency_level"),
        ))
    
    logger.info(
        "tech_assessment_questions_selected",
        technology=technology,
        proficiency_level=proficiency,
        assessment_id=assessment_id,
        total_questions=len(filtered_questions),
    )
    
    return AssessmentResponse(
        assessment_id=assessment_id,
        technology=technology,
        proficiency_level=proficiency,
        questions=filtered_questions,
        total_questions=len(filtered_questions),
    )


@router.post("/{technology}/{proficiency}/evaluate", response_model=EvaluationResult)
async def evaluate_assessment(
    technology: str,
    proficiency: str,
    request: EvaluateRequest,
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    评估测验结果（支持混合级别题目）
    
    从缓存中获取用户的测验题目（包含答案），进行评估。
    
    计算加权分数：
    - Beginner题: 1分
    - Intermediate题: 2分
    - Expert题: 3分
    
    判定逻辑：
    - ≥80%: confirmed - 确认当前级别
    - 60-79%: adjust - 建议保持当前级别
    - <60%: downgrade - 建议降低级别
    
    Args:
        technology: 技术栈名称
        proficiency: 能力级别
        request: 包含测验ID和用户答案的请求
        
    Returns:
        评估结果，包括得分、正确率和建议
        
    Raises:
        HTTPException: 404 - 测验会话不存在或已过期
        HTTPException: 400 - 答案数量与题目数量不匹配
        
    Example:
        POST /api/v1/tech-assessments/python/intermediate/evaluate
        {
            "assessment_id": "uuid",
            "answers": ["选项A", "选项B", ...]
        }
    """
    logger.info(
        "evaluate_tech_assessment_requested",
        technology=technology,
        proficiency_level=proficiency,
        assessment_id=request.assessment_id,
        answer_count=len(request.answers),
    )
    
    # 从 Redis 缓存中获取完整的题目列表（包含答案）
    questions = await _get_assessment_from_cache(request.assessment_id)
    if not questions:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment session not found or expired. Please restart the assessment."
        )
    
    # 验证答案数量与题目数量是否匹配
    if len(request.answers) != len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"Expected {len(questions)} answers, got {len(request.answers)}"
        )
    
    # 评估答案
    result = evaluate_answers(questions, request.answers)
    
    logger.info(
        "tech_assessment_evaluated",
        technology=technology,
        proficiency_level=proficiency,
        assessment_id=request.assessment_id,
        score=result["score"],
        percentage=result["percentage"],
        recommendation=result["recommendation"],
    )
    
    return EvaluationResult(**result)


@router.post(
    "/{technology}/{proficiency}/analyze",
    response_model=AnalyzeTaskResponse,
)
async def analyze_capability(
    technology: str,
    proficiency: str,
    request: AnalyzeCapabilityRequest,
):
    """
    分析用户的技术栈能力（异步任务）
    
    触发异步分析任务，立即返回任务ID。
    用户可以通过查询接口获取分析结果。
    
    基于LLM深度分析用户的答题情况，重点关注错题，提供：
    - 整体能力评价
    - 优势和薄弱点分析
    - 知识缺口识别
    - 个性化学习建议
    - 能力级别验证
    
    Args:
        technology: 技术栈名称
        proficiency: 能力级别
        request: 包含测验ID、用户ID、答案列表和是否保存到画像的标志
        
    Returns:
        任务触发状态和任务ID
        
    Raises:
        HTTPException: 404 - 测验会话不存在或已过期
        HTTPException: 400 - 答案数量不匹配
        
    Example:
        POST /api/v1/learning/assessment/python/intermediate/analyze
        {
            "user_id": "user123",
            "assessment_id": "uuid",
            "answers": ["选项A", "选项B", ...],
            "save_to_profile": true
        }
        
        Response:
        {
            "status": "processing",
            "task_id": "task-uuid",
            "message": "分析任务已启动，请稍后查看结果"
        }
    """
    logger.info(
        "analyze_capability_requested",
        technology=technology,
        proficiency_level=proficiency,
        user_id=request.user_id,
        assessment_id=request.assessment_id,
        answer_count=len(request.answers),
        save_to_profile=request.save_to_profile,
    )
    
    # 从 Redis 缓存中获取完整的题目列表（包含答案）- 快速验证
    questions = await _get_assessment_from_cache(request.assessment_id)
    if not questions:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment session not found or expired. Please restart the assessment."
        )
    
    # 验证答案数量与题目数量是否匹配
    if len(request.answers) != len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"Expected {len(questions)} answers, got {len(request.answers)}"
        )
    
    # 触发异步分析任务
    from app.tasks.capability_analysis_tasks import analyze_tech_capability_task
    
    task = analyze_tech_capability_task.apply_async(
        kwargs={
            "technology": technology,
            "proficiency": proficiency,
            "user_id": request.user_id,
            "assessment_id": request.assessment_id,
            "answers": request.answers,
            "save_to_profile": request.save_to_profile,
        }
    )
    
    logger.info(
        "capability_analysis_task_triggered",
        technology=technology,
        proficiency_level=proficiency,
        user_id=request.user_id,
        assessment_id=request.assessment_id,
        task_id=task.id,
    )
    
    return AnalyzeTaskResponse(
        status="processing",
        task_id=task.id,
        message="能力分析任务已启动，请稍后查看结果",
        technology=technology,
        proficiency=proficiency,
    )


@router.get(
    "/{technology}/{proficiency}/analyze-result",
    response_model=CapabilityAnalysisResult | None,
)
async def get_analyze_result(
    technology: str,
    proficiency: str,
    user_id: str,
):
    """
    查询技术能力分析结果
    
    从Redis缓存中获取最近的分析结果（24小时内有效）
    
    Args:
        technology: 技术栈名称
        proficiency: 能力级别
        user_id: 用户ID（查询参数）
        
    Returns:
        - CapabilityAnalysisResult: 分析完成时返回完整结果
        - None: 任务还在处理中时返回None（前端应定期轮询）
        
    Raises:
        HTTPException: 404 - 分析结果不存在或已过期
        
    Example:
        GET /api/v1/learning/assessment/python/intermediate/analyze-result?user_id=user123
    """
    logger.info(
        "get_analyze_result_requested",
        technology=technology,
        proficiency=proficiency,
        user_id=user_id,
    )
    
    from app.tasks.capability_analysis_tasks import get_analysis_result
    
    result = await get_analysis_result(
        user_id=user_id,
        technology=technology,
        proficiency=proficiency,
    )
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail="Analysis result not found or expired"
        )
    
    # 检查任务状态
    if result.get("status") != "completed":
        # 任务还在处理中，返回 None（符合 response_model 类型定义）
        logger.info(
            "analysis_task_still_processing",
            technology=technology,
            proficiency=proficiency,
            user_id=user_id,
            task_id=result.get("task_id"),
            status=result.get("status", "processing"),
        )
        return None
    
    analysis_result = result.get("analysis_result", {})
    
    logger.info(
        "analyze_result_retrieved",
        technology=technology,
        proficiency=proficiency,
        user_id=user_id,
    )
    
    return CapabilityAnalysisResult(**analysis_result)


async def _save_capability_analysis_to_profile(
    db: AsyncSession,
    user_id: str,
    technology: str,
    proficiency: str,
    analysis_result: dict,
):
    """
    将能力分析结果保存到用户画像的tech_stack字段
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        technology: 技术栈名称
        proficiency: 能力级别
        analysis_result: 能力分析结果
    """
    from datetime import datetime
    from app.models.database import beijing_now
    
    service = TechAssessmentService()
    
    # 保存能力分析到用户画像
    await service.save_capability_analysis_to_profile(
        session=db,
        user_id=user_id,
        technology=technology,
        proficiency=proficiency,
        analysis_result=analysis_result,
    )
    
    logger.info(
        "capability_analysis_saved",
        user_id=user_id,
        technology=technology,
        proficiency=proficiency,
    )


@router.post("/custom", response_model=CustomAssessmentResponse)
async def get_custom_tech_assessment(
    request: CustomTechAssessmentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    获取自定义技术栈测验
    
    - 检查数据库是否已存在该技术栈的所有级别题库
    - 如果不存在，后台生成题库（3个级别）
    - 如果已存在，直接返回题目
    
    Args:
        request: 包含技术栈名称和能力级别
        background_tasks: FastAPI 后台任务
        db: 数据库会话
        
    Returns:
        生成状态或测验题目
        
    Example:
        POST /api/v1/tech-assessments/custom
        {
            "technology": "hive",
            "proficiency": "intermediate"
        }
    """
    logger.info(
        "custom_tech_assessment_requested",
        technology=request.technology,
        proficiency=request.proficiency,
    )
    
    service = TechAssessmentService()
    
    # 检查是否已存在该技术栈的题库（至少一个级别）
    tech_exists = await service.technology_exists(db, request.technology)
    
    if tech_exists:
        # 已存在，检查所需级别是否齐全
        assessments = {}
        all_levels_exist = True
        
        for level in ["beginner", "intermediate", "expert"]:
            assessment = await service.get_assessment(db, request.technology, level)
            if assessment:
                assessments[level] = assessment.questions
            else:
                all_levels_exist = False
                break
        
        if all_levels_exist:
            # 所有级别都存在，直接返回题目（使用现有的抽题逻辑）
            distribution = PROFICIENCY_DISTRIBUTION.get(
                request.proficiency, 
                PROFICIENCY_DISTRIBUTION["intermediate"]
            )
            
            selected_questions = []
            
            for level, count in distribution.items():
                available = assessments[level]
                
                if len(available) < count:
                    selected = available.copy()
                else:
                    selected = random.sample(available, count)
                
                # 为每道题打上来源级别的标签
                for q in selected:
                    q["proficiency_level"] = level
                
                selected_questions.extend(selected)
            
            # 随机打乱题目顺序
            random.shuffle(selected_questions)
            
            # 生成 assessment_id
            assessment_id = str(uuid.uuid4())
            
            # 将完整题目（包含答案）存储到 Redis 缓存中，供评估时使用
            await _save_assessment_to_cache(assessment_id, selected_questions)
            
            # 过滤题目，移除答案和解析
            filtered_questions = []
            for q in selected_questions:
                filtered_questions.append(QuestionResponse(
                    question=q["question"],
                    type=q["type"],
                    options=q["options"],
                    proficiency_level=q.get("proficiency_level"),
                ))
            
            assessment_response = AssessmentResponse(
                assessment_id=assessment_id,
                technology=request.technology,
                proficiency_level=request.proficiency,
                questions=filtered_questions,
                total_questions=len(filtered_questions),
            )
            
            logger.info(
                "custom_tech_assessment_ready",
                technology=request.technology,
                proficiency=request.proficiency,
            )
            
            return CustomAssessmentResponse(
                status="ready",
                message=f"Assessment ready for {request.technology}",
                assessment=assessment_response,
            )
    
    # 不存在或级别不全，触发后台生成
    background_tasks.add_task(
        _generate_custom_assessment_pool,
        request.technology,
    )
    
    logger.info(
        "custom_tech_assessment_generation_started",
        technology=request.technology,
    )
    
    return CustomAssessmentResponse(
        status="generation_started",
        message=f"正在为 {request.technology} 生成测验题库，预计需要1-2分钟...",
    )


async def _generate_custom_assessment_pool(
    technology: str,
):
    """
    后台任务：为自定义技术栈生成3个级别的题库
    
    Args:
        technology: 技术栈名称
    """
    from app.db.session import get_db_transaction as get_db
    import asyncio
    
    logger.info(
        "custom_assessment_pool_generation_started",
        technology=technology,
    )
    
    # 获取数据库会话
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        generator = TechAssessmentGenerator()
        service = TechAssessmentService()
        
        for level in ["beginner", "intermediate", "expert"]:
            try:
                # 检查是否已存在（避免重复生成）
                existing_assessment = await service.get_assessment(db, technology, level)
                if existing_assessment:
                    logger.info(
                        "custom_assessment_already_exists",
                        technology=technology,
                        level=level,
                    )
                    continue
                
                logger.info(
                    "generating_custom_assessment",
                    technology=technology,
                    level=level,
                )
                
                # 使用 Plan & Execute 模式生成
                assessment_data = await generator.generate_assessment_with_plan(
                    technology=technology,
                    proficiency_level=level,
                )
                
                # 保存到数据库
                await service.create_assessment(
                    session=db,
                    technology=technology,
                    proficiency=level,
                    questions=assessment_data["questions"],
                )
                
                logger.info(
                    "custom_assessment_generated",
                    technology=technology,
                    level=level,
                    total_questions=assessment_data["total_questions"],
                )
                
                # 避免API限流
                await asyncio.sleep(1)
                
            except Exception as e:
                # 回滚当前事务，避免影响后续操作
                await db.rollback()
                
                logger.error(
                    "custom_assessment_generation_failed",
                    technology=technology,
                    level=level,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                # 继续处理下一个级别
                continue
        
        logger.info(
            "custom_assessment_pool_generation_completed",
            technology=technology,
        )
        
    finally:
        # 关闭数据库会话
        await db.close()


# ============================================================
# 测验题初始化进度查询端点
# ============================================================
@router.get(
    "/initialization-progress",
    summary="查询测验题初始化进度",
    description="查询技术栈测验题的初始化进度（用于空白数据库初始化后的进度监控）",
)
async def get_assessment_initialization_progress():
    """
    获取测验题初始化进度
    
    Returns:
        进度信息（完成数量、百分比等）
    """
    try:
        from app.tasks.assessment_initialization_tasks import get_initialization_progress
        
        # 触发Celery任务查询进度
        task = get_initialization_progress.apply_async()
        result = task.get(timeout=10)  # 等待10秒获取结果
        
        logger.info(
            "assessment_initialization_progress_queried",
            result=result,
        )
        
        return result
    
    except Exception as e:
        logger.error(
            "assessment_initialization_progress_query_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to query initialization progress: {str(e)}"
        )


@router.post(
    "/trigger-initialization",
    summary="手动触发测验题初始化",
    description="手动触发技术栈测验题的异步生成任务（用于补全缺失的题目）",
)
async def trigger_assessment_initialization():
    """
    手动触发测验题初始化任务
    
    适用场景：
    - 启动时初始化失败
    - 需要补全缺失的题目
    - 管理员手动触发重新生成
    
    Returns:
        任务触发状态
    """
    try:
        from app.tasks.assessment_initialization_tasks import (
            check_and_trigger_assessment_generation
        )
        
        # 触发异步任务
        task = check_and_trigger_assessment_generation.apply_async()
        
        logger.info(
            "assessment_initialization_manually_triggered",
            task_id=task.id,
        )
        
        return {
            "status": "triggered",
            "task_id": task.id,
            "message": "Assessment initialization triggered successfully",
        }
    
    except Exception as e:
        logger.error(
            "assessment_initialization_trigger_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger initialization: {str(e)}"
        )

