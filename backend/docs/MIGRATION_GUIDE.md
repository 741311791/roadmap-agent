# 架构迁移指南

> **目的**: 帮助开发者将旧代码迁移到新架构  
> **适用范围**: 阶段1架构基础建设完成后  
> **更新日期**: 2026-01-05

---

## 概述

本指南介绍如何将旧代码迁移到新架构。新架构包含：
- **Schemas层**: 统一的API请求/响应模型
- **CRUD层**: 泛型数据访问层
- **Session分离**: 读写Session区分
- **依赖注入**: 统一的依赖注入规范

---

## 迁移步骤

### 步骤1: 提取Schemas

#### 问题
旧代码中Schemas分散在各个endpoint文件中，导致重复定义和维护困难。

#### 旧代码（在endpoint文件中定义）
```python
# app/api/v1/endpoints/tutorials.py
from pydantic import BaseModel

class RetryTutorialRequest(BaseModel):
    preferences: dict
    retry_reason: str = None
```

#### 新代码（在schemas/目录中）
```python
# app/schemas/tutorial.py
from pydantic import BaseModel, Field
from typing import Optional
from app.models.domain import LearningPreferences

class TutorialRetryRequest(BaseModel):
    """教程重试请求"""
    preferences: LearningPreferences = Field(..., description="学习偏好")
    retry_reason: Optional[str] = Field(None, description="重试原因")
    
    model_config = {"json_schema_extra": {
        "example": {
            "preferences": {"learning_style": "visual"},
            "retry_reason": "内容太浅"
        }
    }}

# app/api/v1/endpoints/tutorials.py
from app.schemas.tutorial import TutorialRetryRequest
```

#### 迁移清单
- [ ] 找出endpoint文件中的所有Schema定义
- [ ] 将Schema移动到对应的`app/schemas/*.py`文件
- [ ] 添加`Field`描述和验证规则
- [ ] 提供示例数据
- [ ] 更新endpoint中的import语句

---

### 步骤2: 创建CRUD层

#### 问题
旧代码在endpoint中直接查询数据库，导致代码重复和测试困难。

#### 旧代码（在endpoint中直接查询）
```python
from sqlalchemy import select

@router.get("/{id}")
async def get_tutorial(id: str, session: AsyncSession = Depends(get_db)):
    result = await session.execute(
        select(Tutorial).where(Tutorial.id == id)
    )
    tutorial = result.scalar_one_or_none()
    if not tutorial:
        raise HTTPException(status_code=404)
    return tutorial
```

#### 新代码（使用CRUD层）
```python
# 1. 创建CRUD类
# app/crud/crud_tutorial.py
from app.crud.base import BaseCRUD
from app.models.database import TutorialMetadata
from app.schemas.tutorial import TutorialCreate, TutorialUpdate

class TutorialCRUD(BaseCRUD[TutorialMetadata, TutorialCreate, TutorialUpdate]):
    """教程CRUD操作"""
    
    async def get_by_tutorial_id(
        self,
        session: AsyncSession,
        tutorial_id: str,
    ) -> Optional[TutorialMetadata]:
        """根据tutorial_id获取教程"""
        result = await session.execute(
            select(TutorialMetadata).where(
                TutorialMetadata.tutorial_id == tutorial_id
            )
        )
        return result.scalar_one_or_none()

def get_tutorial_crud() -> TutorialCRUD:
    """获取TutorialCRUD实例"""
    return TutorialCRUD(TutorialMetadata)

# 2. 更新endpoint
# app/api/v1/endpoints/tutorials.py
from app.api.v1.deps import CurrentSession, CurrentTutorialCRUD

@router.get("/{tutorial_id}")
async def get_tutorial(
    tutorial_id: str,
    crud: CurrentTutorialCRUD,
    session: CurrentSession,
):
    """获取教程详情"""
    tutorial = await crud.get_by_tutorial_id(session, tutorial_id)
    if not tutorial:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    return tutorial
```

#### 迁移清单
- [ ] 创建对应的CRUD类，继承`BaseCRUD`
- [ ] 实现特定的查询方法（如`get_by_*`）
- [ ] 创建工厂函数（`get_*_crud()`）
- [ ] 更新endpoint使用CRUD层
- [ ] 删除endpoint中的直接数据库查询代码

---

### 步骤3: 提取Service层

#### 问题
旧代码在endpoint中包含复杂业务逻辑，导致代码难以测试和维护。

#### 旧代码（业务逻辑在endpoint中）
```python
@router.post("/retry")
async def retry_tutorial(
    request: RetryTutorialRequest,
    session: AsyncSession = Depends(get_db),
):
    # ❌ 40行业务逻辑在endpoint中
    # 获取概念
    concept = await session.execute(
        select(Concept).where(Concept.id == request.concept_id)
    )
    concept = concept.scalar_one_or_none()
    
    # 调用Agent生成内容
    agent = TutorialGeneratorAgent()
    result = await agent.execute(concept, request.preferences)
    
    # 保存结果
    tutorial = TutorialMetadata(...)
    session.add(tutorial)
    await session.commit()
    
    return {"success": True, "tutorial": tutorial}
```

#### 新代码（业务逻辑在Service中）
```python
# 1. 创建Service类
# app/services/content_service.py
class ContentService:
    """内容生成服务"""
    
    def __init__(
        self,
        tutorial_crud: TutorialCRUD,
        concept_crud: ConceptCRUD,
        tutorial_agent: TutorialGeneratorAgent,
    ):
        self.tutorial_crud = tutorial_crud
        self.concept_crud = concept_crud
        self.tutorial_agent = tutorial_agent
    
    async def retry_tutorial(
        self,
        session: AsyncSession,
        concept_id: str,
        preferences: LearningPreferences,
    ) -> TutorialMetadata:
        """
        重新生成教程
        
        Args:
            session: 数据库会话（事务）
            concept_id: 概念ID
            preferences: 学习偏好
            
        Returns:
            生成的教程元数据
        """
        # 获取概念
        concept = await self.concept_crud.get_by_concept_id(session, concept_id)
        if not concept:
            raise ValueError(f"Concept not found: {concept_id}")
        
        # 调用Agent生成内容
        result = await self.tutorial_agent.execute(concept, preferences)
        
        # 保存结果
        tutorial_data = TutorialCreate(
            tutorial_id=result["tutorial_id"],
            concept_id=concept_id,
            content=result["content"],
        )
        tutorial = await self.tutorial_crud.create(session, obj_in=tutorial_data)
        
        return tutorial

# 2. 在deps.py中注册Service依赖
# app/api/v1/deps.py
def get_content_service(
    tutorial_crud: CurrentTutorialCRUD,
    concept_crud: CurrentConceptCRUD,
) -> ContentService:
    """获取ContentService实例"""
    return ContentService(
        tutorial_crud=tutorial_crud,
        concept_crud=concept_crud,
        tutorial_agent=TutorialGeneratorAgent(),
    )

CurrentContentService = Annotated[ContentService, Depends(get_content_service)]

# 3. 更新endpoint
# app/api/v1/endpoints/tutorials.py
from app.api.v1.deps import CurrentContentService, CurrentSessionTransaction

@router.post("/retry")
async def retry_tutorial(
    request: TutorialRetryRequest,
    service: CurrentContentService,
    session: CurrentSessionTransaction,  # ✅ 使用事务Session
):
    """重新生成教程"""
    tutorial = await service.retry_tutorial(
        session,
        request.concept_id,
        request.preferences,
    )
    return {"success": True, "tutorial": tutorial}
```

#### 迁移清单
- [ ] 识别endpoint中的业务逻辑（超过20行）
- [ ] 创建对应的Service类
- [ ] 将业务逻辑移到Service方法中
- [ ] 在`app/api/v1/deps.py`中注册Service依赖
- [ ] 更新endpoint使用Service
- [ ] 删除endpoint中的业务逻辑代码

---

### 步骤4: 更新Session使用

#### 问题
旧代码使用`get_db()`，不区分读写操作。

#### 旧代码（不区分读写）
```python
@router.get("/roadmaps")
async def list_roadmaps(db: AsyncSession = Depends(get_db)):
    # ❌ 读操作也会自动commit
    result = await db.execute(select(Roadmap))
    return result.scalars().all()

@router.post("/roadmaps")
async def create_roadmap(
    request: RoadmapCreate,
    db: AsyncSession = Depends(get_db),
):
    # commit在get_db()中自动处理
    roadmap = Roadmap(**request.dict())
    db.add(roadmap)
    return roadmap
```

#### 新代码（读写分离）
```python
from app.api.v1.deps import CurrentSession, CurrentSessionTransaction

# ✅ 读操作使用CurrentSession
@router.get("/roadmaps")
async def list_roadmaps(
    session: CurrentSession,  # 只读Session
    crud: CurrentRoadmapCRUD,
):
    return await crud.get_multi(session, skip=0, limit=20)

# ✅ 写操作使用CurrentSessionTransaction
@router.post("/roadmaps")
async def create_roadmap(
    request: RoadmapCreate,
    session: CurrentSessionTransaction,  # 事务Session
    crud: CurrentRoadmapCRUD,
):
    return await crud.create(session, obj_in=request)
    # ✅ 函数结束时自动commit
```

#### 迁移清单
- [ ] 找出所有使用`get_db()`的地方
- [ ] 将GET请求改为使用`CurrentSession`
- [ ] 将POST/PUT/DELETE请求改为使用`CurrentSessionTransaction`
- [ ] 删除手动的`commit()`调用（由Session管理）
- [ ] 更新导入语句

---

### 步骤5: 统一依赖注入

#### 问题
旧代码依赖注入方式不统一。

#### 旧代码（混乱的依赖注入）
```python
# 方式1：直接注入Session
@router.get("/users/{user_id}")
async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
    repo = UserRepository(db)
    return await repo.get(user_id)

# 方式2：直接实例化
@router.post("/generate")
async def generate(...):
    agent = TutorialGeneratorAgent()  # ❌ 无依赖注入
    result = await agent.execute(...)
```

#### 新代码（统一依赖注入）
```python
from app.api.v1.deps import (
    CurrentSession,
    CurrentUserCRUD,
    CurrentActiveUser,
)

# ✅ 统一的依赖注入
@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    crud: CurrentUserCRUD,
    session: CurrentSession,
    current_user: CurrentActiveUser,
):
    user = await crud.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404)
    return user
```

#### 迁移清单
- [ ] 找出所有直接实例化的地方
- [ ] 在`app/api/v1/deps.py`中定义依赖
- [ ] 更新endpoint使用统一的依赖注入
- [ ] 删除直接实例化的代码

---

## 完整迁移示例

### 旧代码（需要迁移）
```python
# app/api/v1/endpoints/tutorials.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

router = APIRouter()

class RetryRequest(BaseModel):
    concept_id: str
    preferences: dict

@router.post("/retry")
async def retry_tutorial(
    request: RetryRequest,
    db: AsyncSession = Depends(get_db),
):
    # 获取概念
    result = await db.execute(
        select(Concept).where(Concept.id == request.concept_id)
    )
    concept = result.scalar_one_or_none()
    if not concept:
        raise HTTPException(status_code=404)
    
    # 生成教程
    agent = TutorialGeneratorAgent()
    content = await agent.execute(concept, request.preferences)
    
    # 保存
    tutorial = Tutorial(
        concept_id=request.concept_id,
        content=content,
    )
    db.add(tutorial)
    await db.commit()
    
    return {"success": True, "tutorial": tutorial}
```

### 新代码（迁移后）
```python
# 1. 定义Schema
# app/schemas/tutorial.py
from pydantic import BaseModel, Field
from app.models.domain import LearningPreferences

class TutorialRetryRequest(BaseModel):
    """教程重试请求"""
    concept_id: str = Field(..., description="概念ID")
    preferences: LearningPreferences = Field(..., description="学习偏好")

# 2. 创建Service
# app/services/content_service.py
class ContentService:
    def __init__(
        self,
        tutorial_crud: TutorialCRUD,
        concept_crud: ConceptCRUD,
    ):
        self.tutorial_crud = tutorial_crud
        self.concept_crud = concept_crud
        self.agent = TutorialGeneratorAgent()
    
    async def retry_tutorial(
        self,
        session: AsyncSession,
        concept_id: str,
        preferences: LearningPreferences,
    ) -> TutorialMetadata:
        """重新生成教程"""
        # 获取概念
        concept = await self.concept_crud.get_by_concept_id(session, concept_id)
        if not concept:
            raise ValueError(f"Concept not found: {concept_id}")
        
        # 生成内容
        content = await self.agent.execute(concept, preferences)
        
        # 保存
        tutorial_data = TutorialCreate(
            concept_id=concept_id,
            content=content,
        )
        return await self.tutorial_crud.create(session, obj_in=tutorial_data)

# 3. 更新Endpoint
# app/api/v1/endpoints/tutorials.py
from app.api.v1.deps import CurrentSessionTransaction, CurrentContentService
from app.schemas.tutorial import TutorialRetryRequest

@router.post("/retry")
async def retry_tutorial(
    request: TutorialRetryRequest,
    service: CurrentContentService,
    session: CurrentSessionTransaction,
):
    """重新生成教程"""
    try:
        tutorial = await service.retry_tutorial(
            session,
            request.concept_id,
            request.preferences,
        )
        return {"success": True, "tutorial": tutorial}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

---

## 常见问题

### Q: 旧代码何时删除？
**A**: 迁移完成并测试通过后，立即删除旧代码。不保留"备份代码"。

### Q: 如何处理复杂的Repository？
**A**: 拆分为多个CRUD类，按实体划分。例如：
- `RoadmapRepository` → `RoadmapCRUD` + `ConceptCRUD`

### Q: Service之间如何调用？
**A**: 通过依赖注入，避免循环依赖。例如：
```python
class ContentService:
    def __init__(
        self,
        tutorial_crud: TutorialCRUD,
        notification_service: NotificationService,  # 注入其他Service
    ):
        ...
```

### Q: 如何测试新代码？
**A**: 
1. CRUD层：直接测试数据库操作
2. Service层：Mock CRUD层
3. Endpoint层：Mock Service层

示例：
```python
# 测试Service
async def test_retry_tutorial():
    # Mock CRUD
    mock_crud = MagicMock(spec=TutorialCRUD)
    mock_crud.create.return_value = TutorialMetadata(...)
    
    # 测试Service
    service = ContentService(tutorial_crud=mock_crud, ...)
    result = await service.retry_tutorial(...)
    
    assert result.tutorial_id == "..."
```

### Q: 迁移过程中如何保证系统稳定？
**A**:
1. 一次只迁移一个endpoint
2. 每次迁移后立即测试
3. 使用feature flag控制新旧代码切换
4. 保留充分的日志

---

## 迁移检查清单

### 代码层面
- [ ] 所有Schema已移到`app/schemas/`
- [ ] 所有CRUD类已创建并继承`BaseCRUD`
- [ ] 复杂业务逻辑已提取到Service层
- [ ] 所有endpoint使用统一依赖注入
- [ ] 读操作使用`CurrentSession`
- [ ] 写操作使用`CurrentSessionTransaction`
- [ ] 旧代码已删除

### 测试层面
- [ ] 单元测试已更新
- [ ] 集成测试已通过
- [ ] 手动测试已完成
- [ ] 性能测试无明显下降

### 文档层面
- [ ] API文档已更新
- [ ] 代码注释已添加
- [ ] 迁移日志已记录

---

**维护说明**: 本指南随架构演进持续更新，如有疑问请咨询架构组。

