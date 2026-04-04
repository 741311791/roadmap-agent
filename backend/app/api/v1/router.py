"""
API v1 主路由（业务领域驱动架构）

重构后按7大业务领域组织：
- auth: 认证授权
- users: 用户画像管理
- roadmaps: 路线图资源管理
- tasks: 任务执行与追踪
- content: 内容管理
- learning: 学习体验
- admin: 平台管理

重构变更(2026-01-14)：
- ✅ 废弃workflows目录，改为tasks
- ✅ 认证模块独立到auth/
- ✅ Waitlist公开接口独立注册
- ✅ 所有模块按业务功能重新归类
"""
from fastapi import APIRouter

# 导入各业务领域的路由
from .endpoints import auth, users, roadmaps, roadmap, tasks, content, learning, admin
from .endpoints.deerflow.router import router as deerflow_router
from .endpoints.admin.waitlist import router_public as waitlist_public_router

# FastAPI Users认证
from app.core.auth import fastapi_users, auth_backend
from app.core.auth.schemas import UserRead, UserUpdate

# 创建v1主路由
router = APIRouter(prefix="/api/v1")

# ==================== 认证授权 ====================
router.include_router(auth.router)

# ==================== 用户管理 ====================
router.include_router(users.router)

# ==================== 路线图管理 ====================
router.include_router(roadmaps.router)
router.include_router(roadmap.router)

# ==================== 任务管理 ====================
router.include_router(tasks.router)

# ==================== 内容管理 ====================
router.include_router(content.router)

# ==================== 学习体验 ====================
router.include_router(learning.router)

# ==================== Deer-Flow 独立实验室 ====================
router.include_router(deerflow_router)

# ==================== 平台管理 ====================
router.include_router(admin.router)

# ==================== Waitlist公开接口 ====================
router.include_router(waitlist_public_router)

# ==================== FastAPI Users 认证路由 ====================
# JWT 认证路由（登录）
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
