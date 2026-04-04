"""用户路由"""
from fastapi import APIRouter
from . import feedback, profile

router = APIRouter(tags=["Users"])

# 包含用户画像与反馈管理
router.include_router(profile.router)
router.include_router(feedback.router)

