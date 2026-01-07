# Code Review检查清单

> **目的**: 确保代码质量和架构一致性  
> **适用范围**: 所有后端Python代码  
> **更新日期**: 2026-01-05

---

## API层（Endpoints）

### 基础规范
- [ ] 函数不超过50行
- [ ] 只负责HTTP协议，不包含业务逻辑
- [ ] 使用Pydantic Schema验证输入输出
- [ ] 使用统一的依赖注入（`app/api/v1/deps.py`）
- [ ] 不直接实例化Service或Agent
- [ ] 不直接访问数据库（通过Service/CRUD层）

### Session使用
- [ ] **读操作使用**`CurrentSession`（来自`app/api/v1/deps`）
- [ ] **写操作使用**`CurrentSessionTransaction`（来自`app/api/v1/deps`）
- [ ] 不直接调用`get_db()`（已废弃）

### HTTP规范
- [ ] HTTP状态码使用恰当
  - 200: 成功
  - 201: 创建成功
  - 204: 删除成功
  - 400: 请求参数错误
  - 401: 未认证
  - 403: 权限不足
  - 404: 资源不存在
  - 500: 服务器错误
- [ ] 错误处理规范（使用`HTTPException`）
- [ ] 包含中文文档字符串

### 示例（正确的Endpoint写法）
```python
from app.api.v1.deps import CurrentSession, CurrentRoadmapCRUD
from app.schemas.roadmap import RoadmapDetail

@router.get("/{roadmap_id}", response_model=RoadmapDetail)
async def get_roadmap(
    roadmap_id: str,
    crud: CurrentRoadmapCRUD,  # ✅ 注入CRUD
    session: CurrentSession,    # ✅ 只读Session
):
    """获取路线图详情"""
    roadmap = await crud.get_by_roadmap_id(session, roadmap_id)
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap
```

---

## Schemas层

### 基础规范
- [ ] 所有API输入输出都有对应Schema
- [ ] Schema定义在`app/schemas/`目录
- [ ] 使用`Field`添加描述和验证规则
- [ ] 提供示例（`model_config = {"json_schema_extra": {...}}`）
- [ ] 避免与Model/Domain对象混用
- [ ] 使用Pydantic v2语法（`model_config`而非`Config`）

### 命名规范
- [ ] 请求Schema：`{Resource}Create`, `{Resource}Update`, `{Resource}Request`
- [ ] 响应Schema：`{Resource}Response`, `{Resource}Detail`, `{Resource}Summary`
- [ ] 通用Schema：定义在`app/schemas/common.py`

### 示例（正确的Schema写法）
```python
from pydantic import BaseModel, Field
from typing import Optional

class RoadmapCreate(BaseModel):
    """路线图创建Schema"""
    roadmap_id: str = Field(..., description="路线图ID")
    user_id: str = Field(..., description="用户ID")
    title: Optional[str] = Field(None, description="标题")
    
    model_config = {"json_schema_extra": {
        "example": {
            "roadmap_id": "roadmap-123",
            "user_id": "user-456",
            "title": "Python全栈开发路线图"
        }
    }}
```

---

## Service层

### 基础规范
- [ ] 函数职责单一，不超过100行
- [ ] 包含核心业务逻辑
- [ ] 通过CRUD层访问数据库
- [ ] 可单独测试（不依赖HTTP层）
- [ ] 正确处理事务边界
- [ ] 异常处理完善
- [ ] 包含详细的文档字符串

### 依赖注入
- [ ] Service通过构造函数接收CRUD实例
- [ ] 不直接实例化其他Service（通过依赖注入）
- [ ] 避免循环依赖

### 示例（正确的Service写法）
```python
class RoadmapService:
    """路线图业务逻辑"""
    
    def __init__(
        self,
        roadmap_crud: RoadmapCRUD,
        concept_crud: ConceptCRUD,
    ):
        self.roadmap_crud = roadmap_crud
        self.concept_crud = concept_crud
    
    async def create_roadmap_with_concepts(
        self,
        session: AsyncSession,
        roadmap_data: RoadmapCreate,
        concepts: list[ConceptCreate],
    ) -> RoadmapMetadata:
        """
        创建路线图及其概念
        
        Args:
            session: 数据库会话（事务）
            roadmap_data: 路线图数据
            concepts: 概念列表
            
        Returns:
            创建的路线图元数据
        """
        # 创建路线图
        roadmap = await self.roadmap_crud.create(session, obj_in=roadmap_data)
        
        # 创建概念
        for concept in concepts:
            await self.concept_crud.create(session, obj_in=concept)
        
        # ✅ Session由调用方管理，这里不commit
        return roadmap
```

---

## CRUD层

### 基础规范
- [ ] 只包含数据库CRUD操作
- [ ] 不包含业务逻辑
- [ ] 继承`BaseCRUD`
- [ ] 函数命名清晰（`get_by_*`, `create`, `update`, `delete`）
- [ ] 使用`selectinload`避免N+1查询
- [ ] 支持分页和排序
- [ ] 正确处理软删除（过滤`deleted_at`）

### 示例（正确的CRUD写法）
```python
from app.crud.base import BaseCRUD
from app.models.database import RoadmapMetadata
from app.schemas.roadmap import RoadmapCreate, RoadmapUpdate

class RoadmapCRUD(BaseCRUD[RoadmapMetadata, RoadmapCreate, RoadmapUpdate]):
    """路线图CRUD操作"""
    
    async def get_by_user(
        self,
        session: AsyncSession,
        user_id: str,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[RoadmapMetadata]:
        """获取用户的路线图列表"""
        result = await session.execute(
            select(RoadmapMetadata)
            .where(RoadmapMetadata.user_id == user_id)
            .where(RoadmapMetadata.deleted_at.is_(None))  # ✅ 过滤软删除
            .order_by(RoadmapMetadata.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
```

---

## 通用规范

### 代码风格
- [ ] 所有函数包含类型注解
- [ ] 所有公开函数包含中文文档字符串
- [ ] 使用`structlog`记录关键操作
- [ ] 敏感信息已脱敏（密码、Token等）
- [ ] 没有硬编码的配置（使用`settings`）

### 质量检查
- [ ] 通过`mypy`类型检查
- [ ] 通过`ruff`代码检查
- [ ] 单元测试覆盖率 >80%

### 日志规范
```python
import structlog

logger = structlog.get_logger()

# ✅ 正确的日志写法
logger.info(
    "roadmap_created",
    roadmap_id=roadmap.roadmap_id,
    user_id=roadmap.user_id,
)

# ❌ 错误的日志写法
logger.info(f"Created roadmap {roadmap.roadmap_id}")  # 不要用f-string
```

---

## 依赖注入规范

### 统一导入路径
```python
# ✅ 正确的导入
from app.api.v1.deps import (
    CurrentSession,
    CurrentSessionTransaction,
    CurrentRoadmapCRUD,
    CurrentActiveUser,
)

# ❌ 错误的导入
from app.db.session import get_db  # 已废弃
from app.crud.crud_roadmap import RoadmapCRUD  # 应该从deps导入
```

### Endpoint依赖注入模板
```python
# GET请求（只读）
@router.get("/{id}")
async def get_resource(
    id: str,
    crud: CurrentResourceCRUD,
    session: CurrentSession,
    user: CurrentActiveUser,
):
    ...

# POST请求（写操作）
@router.post("/")
async def create_resource(
    request: ResourceCreate,
    crud: CurrentResourceCRUD,
    session: CurrentSessionTransaction,  # ✅ 注意这里是Transaction
    user: CurrentActiveUser,
):
    ...
```

---

## 常见错误

### ❌ 错误示例1：Endpoint中包含业务逻辑
```python
@router.post("/roadmaps")
async def create_roadmap(...):
    # ❌ 业务逻辑应该在Service中
    roadmap = RoadmapMetadata(...)
    session.add(roadmap)
    
    for concept in concepts:
        concept_obj = ConceptMetadata(...)
        session.add(concept_obj)
    
    await session.commit()
```

### ✅ 正确示例1：Endpoint调用Service
```python
@router.post("/roadmaps")
async def create_roadmap(
    request: RoadmapCreate,
    service: CurrentRoadmapService,  # ✅ 通过Service处理
    user: CurrentActiveUser,
):
    return await service.create_roadmap(request, user)
```

### ❌ 错误示例2：使用旧的get_db()
```python
@router.get("/roadmaps")
async def list_roadmaps(db: AsyncSession = Depends(get_db)):
    # ❌ get_db()已废弃
    ...
```

### ✅ 正确示例2：使用CurrentSession
```python
@router.get("/roadmaps")
async def list_roadmaps(
    session: CurrentSession,  # ✅ 使用新的依赖注入
):
    ...
```

### ❌ 错误示例3：CRUD中包含业务逻辑
```python
class RoadmapCRUD(BaseCRUD[...]):
    async def create_with_notification(self, ...):
        # ❌ 发送通知是业务逻辑，不应该在CRUD中
        roadmap = await self.create(...)
        await send_notification(...)
        return roadmap
```

### ✅ 正确示例3：业务逻辑在Service中
```python
class RoadmapService:
    async def create_roadmap(self, ...):
        # ✅ 业务逻辑在Service中
        roadmap = await self.roadmap_crud.create(...)
        await self.notification_service.send(...)
        return roadmap
```

---

## 检查命令

```bash
# 类型检查
mypy app/ --strict

# 代码风格检查
ruff check app/

# 运行测试
pytest tests/ -v --cov=app --cov-report=term-missing

# 格式化代码
ruff format app/
```

---

**维护说明**: 本清单随架构演进持续更新，如有疑问请咨询架构组。

