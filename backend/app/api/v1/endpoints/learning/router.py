"""学习体验路由"""
from fastapi import APIRouter
from . import progress, assessment

router = APIRouter(tags=["Learning Experience"])

router.include_router(progress.router)
router.include_router(assessment.router)

