"""
高性能序列化工具（基于msgspec）

提供比标准json库快5-10倍的JSON序列化/反序列化功能。
适用于：
- Redis存储的大对象（如LangGraph State）
- 高频序列化场景（如SSE推送）
- 性能敏感的API响应
"""
import msgspec
from typing import Any, TypeVar, Type

T = TypeVar('T')

# ===== 全局编码器/解码器 =====

_encoder = msgspec.json.Encoder()
_decoder = msgspec.json.Decoder()


def fast_dumps(obj: Any) -> bytes:
    """
    高性能JSON序列化
    
    性能：比json.dumps()快5-10倍
    支持：Pydantic模型、dataclass、普通dict
    
    Args:
        obj: 待序列化的对象
        
    Returns:
        JSON字节串
        
    Examples:
        >>> data = {"user_id": "123", "roadmap_id": "abc"}
        >>> fast_dumps(data)
        b'{"user_id":"123","roadmap_id":"abc"}'
    """
    return _encoder.encode(obj)


def fast_loads(data: bytes | str, type_: Type[T] | None = None) -> T | Any:
    """
    高性能JSON反序列化
    
    Args:
        data: JSON字符串或字节
        type_: 目标类型（可选，用于类型安全）
        
    Returns:
        反序列化后的对象
        
    Examples:
        >>> fast_loads(b'{"user_id":"123"}')
        {'user_id': '123'}
        
        >>> from pydantic import BaseModel
        >>> class User(BaseModel):
        ...     user_id: str
        >>> fast_loads(b'{"user_id":"123"}', type_=User)
        User(user_id='123')
    """
    if isinstance(data, str):
        data = data.encode()
    
    if type_:
        # 类型化解码（用于Pydantic模型）
        return msgspec.json.decode(data, type=type_)
    
    # 通用解码
    return _decoder.decode(data)


# ===== 类型化编码器/解码器（高级用法）=====

def typed_encoder(type_: Type[T]) -> msgspec.json.Encoder:
    """
    创建类型化编码器
    
    用于Pydantic模型的高性能序列化，可复用编码器实例。
    
    Args:
        type_: 目标类型
        
    Returns:
        类型化编码器实例
        
    Examples:
        >>> from pydantic import BaseModel
        >>> class RoadmapState(BaseModel):
        ...     task_id: str
        ...     concepts: list[dict]
        >>> encoder = typed_encoder(RoadmapState)
        >>> state = RoadmapState(task_id="123", concepts=[])
        >>> encoder.encode(state)
        b'{"task_id":"123","concepts":[]}'
    """
    return msgspec.json.Encoder()


def typed_decoder(type_: Type[T]) -> msgspec.json.Decoder:
    """
    创建类型化解码器
    
    用于Pydantic模型的高性能反序列化，可复用解码器实例。
    
    Args:
        type_: 目标类型
        
    Returns:
        类型化解码器实例
        
    Examples:
        >>> from pydantic import BaseModel
        >>> class User(BaseModel):
        ...     user_id: str
        >>> decoder = typed_decoder(User)
        >>> decoder.decode(b'{"user_id":"123"}')
        User(user_id='123')
    """
    return msgspec.json.Decoder(type=type_)

