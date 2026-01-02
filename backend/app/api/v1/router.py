"""
API v1 路由注册

将所有拆分的端点模块统一注册到主路由
"""
from fastapi import APIRouter

from .endpoints import (
    generation,
    retrieval,
    approval,
    tutorial,
    resource,
    quiz,
    modification,
    retry,
    progress,
    mentor,
    waitlist,
    admin,
    tech_assessment,
    featured,
    validation,
    edit,
    status,
    streaming,
    management,
    users,
    intent,
    trace,
    cover_image,
    celery_monitor,
    concept_status,
)
from app.core.auth import fastapi_users, auth_backend
from app.core.auth.schemas import UserRead, UserCreate, UserUpdate

# 创建v1主路由
router = APIRouter(prefix="/api/v1")

# 注册所有子路由
# 路线图生成相关
router.include_router(generation.router)

# 路线图查询相关
router.include_router(retrieval.router)

# 人工审核相关
router.include_router(approval.router)

# 教程管理相关
router.include_router(tutorial.router)

# 资源管理相关
router.include_router(resource.router)

# 测验管理相关
router.include_router(quiz.router)

# 内容修改相关
router.include_router(modification.router)

# 失败重试相关
router.include_router(retry.router)
router.include_router(retry.tasks_router)

# 学习进度相关
router.include_router(progress.router)

# Concept 状态相关（内容生成进度）
router.include_router(concept_status.router)

# 验证记录相关
router.include_router(validation.router)

# 编辑记录相关
router.include_router(edit.router)

# 伴学Agent相关（聊天、笔记）
router.include_router(mentor.router)

# 技术栈能力测试相关
router.include_router(tech_assessment.router)

# 精选路线图相关
router.include_router(featured.router)

# 路线图状态查询
router.include_router(status.router)

# 流式生成
router.include_router(streaming.router)

# 路线图管理（删除、恢复等）
router.include_router(management.router)

# 用户相关（画像等）
router.include_router(users.router)

# 需求分析相关
router.include_router(intent.router)

# 执行追踪相关（日志、摘要）
router.include_router(trace.router)

# 候补名单相关
router.include_router(waitlist.router)

# 封面图相关
router.include_router(cover_image.router)

# ==================== FastAPI Users 认证路由 ====================
# JWT 认证路由（登录、登出）
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# 用户管理路由（获取/更新当前用户信息）
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# 管理员路由
router.include_router(admin.router)

# Celery 监控路由
router.include_router(celery_monitor.router)
