"""
基础 Repository

提供泛型 CRUD 操作，所有具体 Repository 继承此类。

设计原则：
- Repository 只负责数据访问，不包含业务逻辑
- 使用泛型支持类型安全
- 异步操作，支持高并发
- 使用 SQLAlchemy 2.0 新语法
"""
from typing import TypeVar, Generic, Type, Optional, List, Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import DeclarativeMeta
from sqlmodel import SQLModel
import structlog

logger = structlog.get_logger(__name__)

# 泛型类型变量（必须是 SQLModel 子类）
T = TypeVar('T', bound=SQLModel)


class BaseRepository(Generic[T]):
    """
    基础仓储类，提供通用 CRUD 操作
    
    使用示例：
    ```python
    class UserRepository(BaseRepository[User]):
        def __init__(self, session: AsyncSession):
            super().__init__(session, User)
        
        # 添加特定于 User 的查询方法
        async def get_by_email(self, email: str) -> Optional[User]:
            result = await self.session.execute(
                select(User).where(User.email == email)
            )
            return result.scalar_one_or_none()
    ```
    """
    
    def __init__(self, session: AsyncSession, model: Type[T]):
        """
        初始化仓储
        
        Args:
            session: 异步数据库会话
            model: SQLModel 模型类
        """
        self.session = session
        self.model = model
        self._model_name = model.__name__
    
    # ============================================================
    # 基础查询方法
    # ============================================================
    
    async def get_by_id(self, id_value: Any) -> Optional[T]:
        """
        根据主键 ID 查询单条记录
        
        Args:
            id_value: 主键值
            
        Returns:
            实体对象，如果不存在则返回 None
        """
        result = await self.session.execute(
            select(self.model).where(self._get_id_column() == id_value)
        )
        entity = result.scalar_one_or_none()
        
        if entity:
            logger.debug(
                "entity_found",
                model=self._model_name,
                id=id_value,
            )
        else:
            logger.debug(
                "entity_not_found",
                model=self._model_name,
                id=id_value,
            )
        
        return entity
    
    async def get_by_ids(self, id_values: List[Any]) -> List[T]:
        """
        根据多个主键 ID 批量查询
        
        Args:
            id_values: 主键值列表
            
        Returns:
            实体对象列表
        """
        if not id_values:
            return []
        
        result = await self.session.execute(
            select(self.model).where(self._get_id_column().in_(id_values))
        )
        entities = list(result.scalars().all())
        
        logger.debug(
            "entities_found_by_ids",
            model=self._model_name,
            requested_count=len(id_values),
            found_count=len(entities),
        )
        
        return entities
    
    async def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[Any] = None,
    ) -> List[T]:
        """
        查询所有记录（分页）
        
        Args:
            limit: 返回数量限制（默认 100）
            offset: 分页偏移（默认 0）
            order_by: 排序字段（可选，如 Model.created_at.desc()）
            
        Returns:
            实体对象列表
        """
        query = select(self.model)
        
        if order_by is not None:
            query = query.order_by(order_by)
        
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        entities = list(result.scalars().all())
        
        logger.debug(
            "entities_listed",
            model=self._model_name,
            count=len(entities),
            limit=limit,
            offset=offset,
        )
        
        return entities
    
    async def count(self, **filters) -> int:
        """
        统计记录数量
        
        Args:
            **filters: 过滤条件（键值对）
            
        Returns:
            记录数量
        """
        query = select(func.count()).select_from(self.model)
        
        if filters:
            query = self._apply_filters(query, filters)
        
        result = await self.session.execute(query)
        count = result.scalar_one()
        
        logger.debug(
            "entities_counted",
            model=self._model_name,
            count=count,
            filters=filters,
        )
        
        return count
    
    async def exists(self, **filters) -> bool:
        """
        检查记录是否存在
        
        Args:
            **filters: 过滤条件（键值对）
            
        Returns:
            True 如果存在，False 如果不存在
        """
        query = select(self.model).limit(1)
        query = self._apply_filters(query, filters)
        
        result = await self.session.execute(query)
        exists = result.scalar_one_or_none() is not None
        
        logger.debug(
            "entity_exists_check",
            model=self._model_name,
            exists=exists,
            filters=filters,
        )
        
        return exists
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def create(self, entity: T, *, flush: bool = False) -> T:
        """
        创建新记录
        
        Args:
            entity: 实体对象
            flush: 是否立即刷新到数据库（默认 False）
            
        Returns:
            创建后的实体对象（包含自动生成的字段，如 ID）
            
        注意：
        - 默认情况下，只将实体添加到会话，不会立即刷新到数据库
        - 调用者负责在适当的时候 commit 事务
        - 如果需要立即获取数据库生成的字段（如自增ID），设置 flush=True
        """
        self.session.add(entity)
        
        if flush:
            await self.session.flush()
            await self.session.refresh(entity)
        
        logger.info(
            "entity_created",
            model=self._model_name,
            id=self._get_entity_id(entity),
            flushed=flush,
        )
        
        return entity
    
    async def create_batch(self, entities: List[T], *, flush: bool = False) -> List[T]:
        """
        批量创建记录
        
        Args:
            entities: 实体对象列表
            flush: 是否立即刷新到数据库（默认 False）
            
        Returns:
            创建后的实体对象列表
        """
        if not entities:
            return []
        
        self.session.add_all(entities)
        
        if flush:
            await self.session.flush()
            for entity in entities:
                await self.session.refresh(entity)
        
        logger.info(
            "entities_created_batch",
            model=self._model_name,
            count=len(entities),
            flushed=flush,
        )
        
        return entities
    
    async def update_by_id(
        self,
        id_value: Any,
        **fields: Any,
    ) -> bool:
        """
        根据主键 ID 更新记录的指定字段
        
        Args:
            id_value: 主键值
            **fields: 要更新的字段（键值对）
            
        Returns:
            True 如果更新成功，False 如果记录不存在
        """
        if not fields:
            logger.warning(
                "update_called_without_fields",
                model=self._model_name,
                id=id_value,
            )
            return False
        
        result = await self.session.execute(
            update(self.model)
            .where(self._get_id_column() == id_value)
            .values(**fields)
        )
        
        updated = result.rowcount > 0
        
        if updated:
            logger.info(
                "entity_updated",
                model=self._model_name,
                id=id_value,
                updated_fields=list(fields.keys()),
            )
        else:
            logger.warning(
                "entity_update_failed_not_found",
                model=self._model_name,
                id=id_value,
            )
        
        return updated
    
    async def update(self, entity: T, *, flush: bool = False) -> T:
        """
        更新实体对象
        
        Args:
            entity: 已修改的实体对象
            flush: 是否立即刷新到数据库（默认 False）
            
        Returns:
            更新后的实体对象
            
        注意：
        - 实体必须已经被会话跟踪（通过 get_by_id 或 create 获取）
        - 调用者负责在适当的时候 commit 事务
        """
        if flush:
            await self.session.flush()
            await self.session.refresh(entity)
        
        logger.info(
            "entity_updated_by_object",
            model=self._model_name,
            id=self._get_entity_id(entity),
            flushed=flush,
        )
        
        return entity
    
    # ============================================================
    # 删除方法
    # ============================================================
    
    async def delete_by_id(self, id_value: Any) -> bool:
        """
        根据主键 ID 删除记录
        
        Args:
            id_value: 主键值
            
        Returns:
            True 如果删除成功，False 如果记录不存在
        """
        result = await self.session.execute(
            delete(self.model).where(self._get_id_column() == id_value)
        )
        
        deleted = result.rowcount > 0
        
        if deleted:
            logger.info(
                "entity_deleted",
                model=self._model_name,
                id=id_value,
            )
        else:
            logger.warning(
                "entity_delete_failed_not_found",
                model=self._model_name,
                id=id_value,
            )
        
        return deleted
    
    async def delete(self, entity: T) -> bool:
        """
        删除实体对象
        
        Args:
            entity: 要删除的实体对象
            
        Returns:
            True（如果实体在会话中）
            
        注意：
        - 实体必须已经被会话跟踪
        """
        await self.session.delete(entity)
        
        logger.info(
            "entity_deleted_by_object",
            model=self._model_name,
            id=self._get_entity_id(entity),
        )
        
        return True
    
    # ============================================================
    # 辅助方法
    # ============================================================
    
    def _get_id_column(self) -> Any:
        """
        获取模型的主键列
        
        Returns:
            主键列对象
        """
        # SQLModel/SQLAlchemy 主键获取
        # 假设主键字段名为 'id' 或通过 __table__.primary_key 获取
        if hasattr(self.model, 'id'):
            return self.model.id
        
        # 通过 SQLAlchemy 元数据获取主键
        primary_keys = list(self.model.__table__.primary_key.columns)
        if primary_keys:
            return primary_keys[0]
        
        raise ValueError(f"Model {self._model_name} has no primary key defined")
    
    def _get_entity_id(self, entity: T) -> Any:
        """
        获取实体的主键值
        
        Args:
            entity: 实体对象
            
        Returns:
            主键值
        """
        if hasattr(entity, 'id'):
            return entity.id
        
        # 通过主键列名获取值
        primary_keys = list(self.model.__table__.primary_key.columns)
        if primary_keys:
            pk_name = primary_keys[0].name
            return getattr(entity, pk_name, None)
        
        return None
    
    def _apply_filters(self, query: Any, filters: Dict[str, Any]) -> Any:
        """
        应用过滤条件到查询
        
        Args:
            query: SQLAlchemy 查询对象
            filters: 过滤条件字典
            
        Returns:
            应用过滤后的查询对象
        """
        for field, value in filters.items():
            if hasattr(self.model, field):
                column = getattr(self.model, field)
                if isinstance(value, list):
                    query = query.where(column.in_(value))
                else:
                    query = query.where(column == value)
        
        return query
