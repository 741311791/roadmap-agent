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
from app.services.tech_assessment_service import TechAssessmentService, evaluate_answers
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
)

router = APIRouter(prefix="/tech-assessments", tags=["tech-assessments"])
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
    response_model=CapabilityAnalysisResult
)
async def analyze_capability(
    technology: str,
    proficiency: str,
    request: AnalyzeCapabilityRequest,
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    分析用户的技术栈能力（支持混合级别题目）
    
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
        详细的能力分析结果
        
    Raises:
        HTTPException: 404 - 测验会话不存在或已过期
        HTTPException: 400 - 答案数量不匹配
        HTTPException: 500 - 分析失败
        
    Example:
        POST /api/v1/tech-assessments/python/intermediate/analyze
        {
            "user_id": "user123",
            "assessment_id": "uuid",
            "answers": ["选项A", "选项B", ...],
            "save_to_profile": true
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
    
    # 先评估答案
    evaluation_result = evaluate_answers(questions, request.answers)
    
    # 使用LLM进行能力分析
    try:
        analyzer = TechCapabilityAnalyzer()
        analysis_result = await analyzer.analyze_capability(
            technology=technology,
            proficiency_level=proficiency,
            questions=questions,
            user_answers=request.answers,
            evaluation_result=evaluation_result,
        )
        
        # 如果需要保存到用户画像
        if request.save_to_profile:
            await _save_capability_analysis_to_profile(
                db=db,
                user_id=request.user_id,
                technology=technology,
                proficiency=proficiency,
                analysis_result=analysis_result,
            )
        
        logger.info(
            "capability_analysis_completed",
            technology=technology,
            proficiency_level=proficiency,
            user_id=request.user_id,
            assessment_id=request.assessment_id,
            verified_level=analysis_result.get("proficiency_verification", {}).get("verified_level"),
        )
        
        return CapabilityAnalysisResult(**analysis_result)
        
    except Exception as e:
        logger.error(
            "capability_analysis_failed",
            technology=technology,
            proficiency_level=proficiency,
            user_id=request.user_id,
            assessment_id=request.assessment_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Capability analysis failed: {str(e)}"
        )


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

