"""
BaseCRUD泛型类 - 提供通用的CRUD操作
"""
from typing import Generic, TypeVar, Type, Optional, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from pydantic import BaseModel

# 定义泛型类型
ModelType = TypeVar("ModelType", bound=DeclarativeBase)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)

class BaseCRUD(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    基础CRUD类（泛型）
    
    功能：
    - 提供通用的增删改查操作
    - 自动处理分页
    - 支持软删除
    - 类型安全（泛型约束）
    
    使用示例：
    ```python
    class RoadmapCRUD(BaseCRUD[RoadmapMetadata, RoadmapCreate, RoadmapUpdate]):
        pass
    
    crud = RoadmapCRUD(RoadmapMetadata)
    roadmap = await crud.get(session, roadmap_id)
    ```
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        初始化CRUD实例
        
        Args:
            model: SQLModel/SQLAlchemy模型类
        """
        self.model = model
    
    # ===== 基础查询 =====
    
    async def get(
        self, 
        session: AsyncSession, 
        id: Any
    ) -> Optional[ModelType]:
        """
        根据ID获取单条记录
        
        Args:
            session: 数据库会话
            id: 主键ID
            
        Returns:
            模型实例或None
        """
        result = await session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        session: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """
        获取多条记录（分页）
        
        Args:
            session: 数据库会话
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            模型实例列表
        """
        result = await session.execute(
            select(self.model)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def count(self, session: AsyncSession) -> int:
        """
        统计记录总数
        
        Args:
            session: 数据库会话
            
        Returns:
            记录总数
        """
        result = await session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar_one()
    
    # ===== 创建操作 =====
    
    async def create(
        self,
        session: AsyncSession,
        *,
        obj_in: CreateSchemaType | dict[str, Any],
    ) -> ModelType:
        """
        创建新记录
        
        Args:
            session: 数据库会话
            obj_in: Pydantic Schema或字典
            
        Returns:
            创建的模型实例
        """
        # 转换为字典
        if isinstance(obj_in, dict):
            create_data = obj_in
        else:
            create_data = obj_in.model_dump(exclude_unset=True)
        
        # 创建实例
        db_obj = self.model(**create_data)
        session.add(db_obj)
        await session.flush()  # 获取自动生成的ID
        await session.refresh(db_obj)
        
        return db_obj
    
    # ===== 更新操作 =====
    
    async def update(
        self,
        session: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """
        更新记录
        
        Args:
            session: 数据库会话
            db_obj: 现有的数据库对象
            obj_in: 更新数据（Pydantic Schema或字典）
            
        Returns:
            更新后的模型实例
        """
        # 转换为字典
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        # 更新字段
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        
        return db_obj
    
    # ===== 删除操作 =====
    
    async def remove(
        self,
        session: AsyncSession,
        *,
        id: Any,
    ) -> Optional[ModelType]:
        """
        硬删除记录
        
        Args:
            session: 数据库会话
            id: 主键ID
            
        Returns:
            被删除的模型实例或None
        """
        obj = await self.get(session, id)
        if obj:
            await session.delete(obj)
            await session.flush()
        return obj
    
    async def soft_delete(
        self,
        session: AsyncSession,
        *,
        id: Any,
    ) -> Optional[ModelType]:
        """
        软删除记录（设置deleted_at字段）
        
        前提：模型必须有deleted_at字段
        
        Args:
            session: 数据库会话
            id: 主键ID
            
        Returns:
            被软删除的模型实例或None
        """
        from datetime import datetime
        
        obj = await self.get(session, id)
        if obj and hasattr(obj, "deleted_at"):
            obj.deleted_at = datetime.utcnow()
            session.add(obj)
            await session.flush()
            await session.refresh(obj)
        return obj

