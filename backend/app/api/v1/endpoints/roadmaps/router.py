"""路线图资源路由

重构变更：
- ✅ 整合list/crud/metadata替代原有的分散文件
- ✅ 移除streaming（已废弃流式输出）
- ✅ 保留cover_image
"""
from fastapi import APIRouter
from . import list as list_module, crud, metadata, cover_image

router = APIRouter(tags=["Roadmap Resources"])

# 列表查询
router.include_router(list_module.router)

# 核心CRUD
router.include_router(crud.router)

# 元数据查询
router.include_router(metadata.router)

# 封面图
router.include_router(cover_image.router)

