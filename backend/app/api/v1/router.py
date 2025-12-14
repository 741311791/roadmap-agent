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
)
from .roadmap import users_router, router as roadmap_router, trace_router

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

# 学习进度相关
router.include_router(progress.router)

# 伴学Agent相关（聊天、笔记）
router.include_router(mentor.router)

# 路线图管理相关（删除、恢复等）
router.include_router(roadmap_router)

# 用户相关（画像等）
router.include_router(users_router)

# 执行追踪相关（日志、摘要）
router.include_router(trace_router)
