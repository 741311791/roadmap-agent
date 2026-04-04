"""
产品路书公开页路由汇总
"""
from fastapi import APIRouter

from .public import router as public_router
from .voting import router as voting_router

router = APIRouter()
router.include_router(public_router)
router.include_router(voting_router)
