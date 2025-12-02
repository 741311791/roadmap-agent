"""
API v1 路由汇总
"""
from fastapi import APIRouter
from app.api.v1 import roadmap, websocket

api_router_v1 = APIRouter()

# 注册子路由
api_router_v1.include_router(roadmap.router)
api_router_v1.include_router(roadmap.users_router)  # 用户画像 API
api_router_v1.include_router(roadmap.trace_router)  # 执行日志查询 API
api_router_v1.include_router(websocket.router, tags=["websocket"])

