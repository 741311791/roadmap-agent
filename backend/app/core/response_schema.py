"""
统一响应格式

提供标准化的API响应封装，确保所有接口返回一致的数据结构。
"""
from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field


# 泛型类型变量
SchemaT = TypeVar("SchemaT")


class ResponseModel(BaseModel):
    """
    通用响应模型
    
    所有API响应都遵循此格式：
    {
        "code": 200,
        "msg": "Success",
        "data": { ... }
    }
    """
    code: int = Field(..., description="HTTP状态码")
    msg: str = Field(..., description="响应消息（用户友好）")
    data: Optional[Any] = Field(None, description="响应数据")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": 200,
                    "msg": "Success",
                    "data": {"example": "value"}
                }
            ]
        }
    }


class ResponseSchemaModel(ResponseModel, Generic[SchemaT]):
    """
    泛型响应模型（带类型提示）
    
    使用泛型参数指定data字段的具体类型，提供更好的类型安全性和文档生成。
    
    使用示例：
    ```python
    from app.schemas.user import UserDetail
    from app.core.response_schema import ResponseSchemaModel
    
    @router.get("/users/{user_id}", response_model=ResponseSchemaModel[UserDetail])
    async def get_user(user_id: str) -> ResponseSchemaModel[UserDetail]:
        user = await user_service.get_user(user_id)
        return response_base.success(data=user)
    ```
    """
    data: SchemaT  # 指定具体的Schema类型


class ResponseCode:
    """
    响应码常量
    
    定义常用的HTTP状态码和对应的中文消息。
    """
    # 成功响应 (2xx)
    OK = 200
    CREATED = 201
    ACCEPTED = 202
    NO_CONTENT = 204
    
    # 客户端错误 (4xx)
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    UNPROCESSABLE_ENTITY = 422
    
    # 服务器错误 (5xx)
    INTERNAL_SERVER_ERROR = 500
    SERVICE_UNAVAILABLE = 503
    
    # 中文消息映射
    MSG = {
        200: "操作成功",
        201: "创建成功",
        202: "请求已接受",
        204: "无内容",
        400: "请求参数错误",
        401: "未授权",
        403: "权限不足",
        404: "资源不存在",
        409: "资源冲突",
        422: "数据验证失败",
        500: "服务器内部错误",
        503: "服务暂时不可用",
    }


class ResponseBase:
    """
    响应构建器
    
    提供便捷的方法构建标准化响应。
    
    使用示例：
    ```python
    from app.core.response_schema import response_base
    
    # 成功响应
    return response_base.success(data={"user_id": "123"})
    
    # 成功响应（自定义消息）
    return response_base.success(data=user, msg="用户创建成功")
    
    # 失败响应
    return response_base.fail(code=404, msg="用户不存在")
    ```
    """
    
    @staticmethod
    def success(
        data: Any = None,
        msg: str = "Success",
        code: int = ResponseCode.OK
    ) -> ResponseModel:
        """
        构建成功响应
        
        Args:
            data: 响应数据（可选）
            msg: 响应消息（默认：Success）
            code: 状态码（默认：200）
            
        Returns:
            ResponseModel: 标准化响应对象
        """
        return ResponseModel(
            code=code,
            msg=msg,
            data=data
        )
    
    @staticmethod
    def fail(
        code: int = ResponseCode.BAD_REQUEST,
        msg: Optional[str] = None,
        data: Any = None
    ) -> ResponseModel:
        """
        构建失败响应
        
        Args:
            code: 错误状态码（默认：400）
            msg: 错误消息（可选，默认根据code自动获取）
            data: 错误详情（可选）
            
        Returns:
            ResponseModel: 标准化响应对象
        """
        if msg is None:
            msg = ResponseCode.MSG.get(code, "操作失败")
        
        return ResponseModel(
            code=code,
            msg=msg,
            data=data
        )
    
    @staticmethod
    def created(data: Any = None, msg: str = "创建成功") -> ResponseModel:
        """
        构建创建成功响应（201）
        
        Args:
            data: 响应数据（可选）
            msg: 响应消息（默认：创建成功）
            
        Returns:
            ResponseModel: 标准化响应对象
        """
        return ResponseModel(
            code=ResponseCode.CREATED,
            msg=msg,
            data=data
        )
    
    @staticmethod
    def accepted(data: Any = None, msg: str = "请求已接受") -> ResponseModel:
        """
        构建请求已接受响应（202）
        
        用于异步操作，任务已提交但尚未完成。
        
        Args:
            data: 响应数据（可选，通常包含任务ID）
            msg: 响应消息（默认：请求已接受）
            
        Returns:
            ResponseModel: 标准化响应对象
        """
        return ResponseModel(
            code=ResponseCode.ACCEPTED,
            msg=msg,
            data=data
        )
    
    @staticmethod
    def no_content(msg: str = "操作成功") -> ResponseModel:
        """
        构建无内容响应（204）
        
        用于删除操作等不需要返回数据的场景。
        
        Args:
            msg: 响应消息（默认：操作成功）
            
        Returns:
            ResponseModel: 标准化响应对象
        """
        return ResponseModel(
            code=ResponseCode.NO_CONTENT,
            msg=msg,
            data=None
        )


# 全局响应构建器实例（单例模式）
response_base = ResponseBase()

