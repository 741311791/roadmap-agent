"""
API测试专用数据工厂

提供API测试所需的请求/响应数据。
继承自tests.factories中的通用工厂。
"""
from typing import Dict, Any
import uuid

from tests.factories import (
    LearningPreferencesFactory,
    UserRequestFactory,
    RoadmapFactory,
    ContentFactory,
)


class APIRequestFactory:
    """
    API请求数据工厂
    
    生成符合API Schema的请求数据。
    """
    
    @staticmethod
    def create_generation_request() -> Dict[str, Any]:
        """
        创建路线图生成请求
        
        Returns:
            符合UserRequest schema的字典
        """
        user_request = UserRequestFactory.create_simple_request()
        
        # 转换为API请求格式（UserRequest模型）
        return {
            "user_id": user_request.user_id,
            "session_id": user_request.session_id,
            "preferences": {
                "learning_goal": user_request.preferences.learning_goal,
                "available_hours_per_week": user_request.preferences.available_hours_per_week,
                "motivation": user_request.preferences.motivation,
                "current_level": user_request.preferences.current_level,
                "career_background": user_request.preferences.career_background,
                "content_preference": user_request.preferences.content_preference,
                "target_deadline": user_request.preferences.target_deadline,
            },
            "additional_context": user_request.additional_context
        }
    
    @staticmethod
    def create_approval_request(approved: bool = True, feedback: str = None) -> Dict[str, Any]:
        """
        创建人工审核请求
        
        Args:
            approved: 是否批准
            feedback: 反馈意见
            
        Returns:
            符合ApprovalRequest schema的字典
        """
        return {
            "approved": approved,
            "feedback": feedback,
        }
    
    @staticmethod
    def create_retry_content_request(content_types: list = None) -> Dict[str, Any]:
        """
        创建内容重试请求
        
        Args:
            content_types: 重试的内容类型列表
            
        Returns:
            符合RetryContentRequest schema的字典
        """
        if content_types is None:
            content_types = ["tutorial"]
        
        return {
            "content_types": content_types
        }
    
    @staticmethod
    def create_progress_start_request() -> Dict[str, Any]:
        """
        创建开始学习进度请求
        
        Returns:
            符合StartProgressRequest schema的字典
        """
        return {}
    
    @staticmethod
    def create_concept_complete_request() -> Dict[str, Any]:
        """
        创建完成概念请求
        
        Returns:
            符合CompleteConceptRequest schema的字典
        """
        return {}
    
    @staticmethod
    def create_login_request(email: str = None, password: str = "testpassword123") -> Dict[str, Any]:
        """
        创建登录请求
        
        Args:
            email: 邮箱地址
            password: 密码
            
        Returns:
            登录表单数据
        """
        if email is None:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        return {
            "username": email,  # FastAPI Users使用username字段
            "password": password,
        }
    
    @staticmethod
    def create_register_request(email: str = None, password: str = "testpassword123") -> Dict[str, Any]:
        """
        创建注册请求
        
        Args:
            email: 邮箱地址
            password: 密码
            
        Returns:
            符合UserCreate schema的字典
        """
        if email is None:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        
        return {
            "email": email,
            "password": password,
        }
    
    @staticmethod
    def create_invite_user_request(email: str = None) -> Dict[str, Any]:
        """
        创建邀请用户请求
        
        Args:
            email: 邮箱地址
            
        Returns:
            符合InviteUserRequest schema的字典
        """
        if email is None:
            email = f"invited_{uuid.uuid4().hex[:8]}@example.com"
        
        return {
            "email": email
        }
    
    @staticmethod
    def create_batch_invite_request(emails: list = None) -> Dict[str, Any]:
        """
        创建批量邀请请求
        
        Args:
            emails: 邮箱地址列表
            
        Returns:
            符合BatchSendInviteRequest schema的字典
        """
        if emails is None:
            emails = [
                f"user{i}_{uuid.uuid4().hex[:6]}@example.com"
                for i in range(3)
            ]
        
        return {
            "emails": emails
        }
    
    @staticmethod
    def create_add_tavily_key_request(api_key: str = None) -> Dict[str, Any]:
        """
        创建添加Tavily密钥请求
        
        Args:
            api_key: API密钥
            
        Returns:
            符合AddTavilyAPIKeyRequest schema的字典
        """
        if api_key is None:
            api_key = f"tvly-{uuid.uuid4().hex}"
        
        return {
            "api_key": api_key
        }


class APIResponseFactory:
    """
    API响应数据工厂（用于验证）
    
    生成期望的API响应结构。
    """
    
    @staticmethod
    def create_success_response(data: Any = None) -> Dict[str, Any]:
        """
        创建成功响应
        
        Args:
            data: 响应数据
            
        Returns:
            符合ResponseSchemaModel的字典
        """
        return {
            "code": 200,
            "message": "Success",
            "data": data or {},
        }
    
    @staticmethod
    def create_error_response(code: int, message: str) -> Dict[str, Any]:
        """
        创建错误响应
        
        Args:
            code: 错误码
            message: 错误消息
            
        Returns:
            符合ErrorResponse的字典
        """
        return {
            "code": code,
            "message": message,
        }

