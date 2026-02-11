"""认证授权路由"""
from fastapi import APIRouter
from . import auth

router = APIRouter(prefix="/auth", tags=["Authentication"])

router.include_router(auth.router)

