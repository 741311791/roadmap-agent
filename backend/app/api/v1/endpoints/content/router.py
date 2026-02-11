"""内容管理路由

重构变更：
- ✅ 拆分content.py为query/regenerate
- ✅ 保留modification/concept_status/subgraph
"""
from fastapi import APIRouter
from . import query, regenerate, modification, concept_status, subgraph

router = APIRouter(tags=["Content Management"])

# 内容查询
router.include_router(query.router)

# 内容重新生成
router.include_router(regenerate.router)

# 内容修改
router.include_router(modification.router)

# Concept状态
router.include_router(concept_status.router)

# 子图生成
router.include_router(subgraph.router)

