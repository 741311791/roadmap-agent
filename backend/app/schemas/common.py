"""
通用Schemas - 跨模块复用的基础模型
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Generic, TypeVar, Optional
from datetime import datetime

# ===== 通用响应模型 =====

class ErrorDetail(BaseModel):
    """错误详情"""
    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    field: Optional[str] = Field(None, description="错误字段（表单验证时使用）")

class ErrorResponse(BaseModel):
    """统一错误响应"""
    error: ErrorDetail
    request_id: Optional[str] = Field(None, description="请求追踪ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SuccessResponse(BaseModel):
    """通用成功响应"""
    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="提示消息")
    data: Optional[dict] = Field(None, description="返回数据")

# ===== 分页模型 =====

T = TypeVar('T')

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码（从1开始）")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    
    @property
    def skip(self) -> int:
        """计算跳过的记录数"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """返回限制数量"""
        return self.page_size

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数")
    
    model_config = ConfigDict(from_attributes=True)
    
    @classmethod
    def create(cls, items: list[T], total: int, pagination: PaginationParams):
        """工厂方法：创建分页响应"""
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=(total + pagination.page_size - 1) // pagination.page_size,
        )

# ===== 任务状态模型 =====

class TaskStatus(BaseModel):
    """异步任务状态"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending/processing/completed/failed")
    progress: Optional[int] = Field(None, ge=0, le=100, description="进度百分比")
    message: Optional[str] = Field(None, description="状态消息")
    result: Optional[dict] = Field(None, description="任务结果（completed时返回）")
    error: Optional[str] = Field(None, description="错误信息（failed时返回）")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

