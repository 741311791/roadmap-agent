"""平台管理路由

重构变更：
- ✅ 拆分admin.py为users/waitlist/tavily
- ✅ trace模块移到tasks/
- ✅ waitlist公开接口独立注册
"""
from fastapi import APIRouter
from . import users, monitoring, customer_emails
from .waitlist import router_admin as waitlist_admin_router, router_public as waitlist_public_router
from . import tavily

router = APIRouter(prefix="/admin", tags=["Platform Admin"])

# 管理员功能
router.include_router(users.router)
router.include_router(waitlist_admin_router)
router.include_router(tavily.router)
router.include_router(monitoring.router)
router.include_router(customer_emails.router)

# Waitlist公开接口（无需admin prefix）
waitlist_router_public = APIRouter()
waitlist_router_public.include_router(waitlist_public_router)

