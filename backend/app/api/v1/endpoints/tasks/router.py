"""任务管理路由"""
from fastapi import APIRouter
from . import generation, query, retry, approval, trace

router = APIRouter()

# 所有子路由已经包含 /tasks prefix，这里不再重复添加
router.include_router(generation.router)
router.include_router(query.router)
router.include_router(retry.router)
router.include_router(approval.router)
router.include_router(trace.router)

