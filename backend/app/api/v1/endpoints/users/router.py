"""用户路由"""
from fastapi import APIRouter
from . import profile

router = APIRouter(tags=["Users"])

# 只包含用户画像管理
router.include_router(profile.router)

