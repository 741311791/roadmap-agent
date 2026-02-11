"""
API测试Mock工具

提供统一的Mock策略，用于模拟外部依赖。
"""
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any
import json

from tests.factories import MockResponseFactory, ContentFactory


class APIMocks:
    """
    统一的API Mock工具类
    
    提供常用的Mock方法，确保测试一致性。
    """
    
    @staticmethod
    def mock_llm_success(response_type: str = "intent"):
        """
        Mock LLM成功响应
        
        Args:
            response_type: 响应类型（intent/curriculum/validation）
            
        Returns:
            配置好的patch对象
        """
        async def mock_acompletion(*args, **kwargs):
            if response_type == "intent":
                data = MockResponseFactory.create_llm_intent_response()
            elif response_type == "curriculum":
                data = MockResponseFactory.create_llm_curriculum_response()
            elif response_type == "validation":
                data = MockResponseFactory.create_llm_validation_response(is_valid=True)
            else:
                data = {}
            
            # 创建Mock响应对象
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = json.dumps(data, ensure_ascii=False)
            return mock_response
        
        return patch("litellm.acompletion", side_effect=mock_acompletion)
    
    @staticmethod
    def mock_llm_failure():
        """
        Mock LLM调用失败
        
        Returns:
            配置好的patch对象
        """
        async def mock_acompletion(*args, **kwargs):
            raise Exception("LLM API调用失败")
        
        return patch("litellm.acompletion", side_effect=mock_acompletion)
    
    @staticmethod
    def mock_llm_rate_limit():
        """
        Mock LLM限流错误
        
        Returns:
            配置好的patch对象
        """
        async def mock_acompletion(*args, **kwargs):
            import litellm
            raise litellm.RateLimitError("Rate limit exceeded")
        
        return patch("litellm.acompletion", side_effect=mock_acompletion)
    
    @staticmethod
    def mock_celery_task(task_id: str = "test-task-id"):
        """
        Mock Celery任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            配置好的patch对象
        """
        mock_result = MagicMock()
        mock_result.id = task_id
        
        return patch(
            "app.tasks.roadmap_generation_tasks.generate_roadmap.delay",
            return_value=mock_result
        )
    
    @staticmethod
    def mock_s3_upload_success():
        """
        Mock S3上传成功
        
        Returns:
            配置好的patch对象
        """
        async def mock_upload(*args, **kwargs):
            content = kwargs.get("content", "")
            key = kwargs.get("key", "test-key.md")
            return MagicMock(
                success=True,
                url=f"s3://test-bucket/{key}",
                key=key,
                size_bytes=len(content),
                etag="mock-etag",
            )
        
        return patch(
            "app.tools.s3_storage_tool.S3StorageTool.upload",
            side_effect=mock_upload
        )
    
    @staticmethod
    def mock_tavily_search_success():
        """
        Mock Tavily搜索成功
        
        Returns:
            配置好的patch对象
        """
        async def mock_search(*args, **kwargs):
            return MagicMock(
                results=[
                    {
                        "title": "Mock搜索结果1",
                        "url": "https://example.com/1",
                        "content": "Mock内容1",
                        "score": 0.95,
                    },
                    {
                        "title": "Mock搜索结果2",
                        "url": "https://example.com/2",
                        "content": "Mock内容2",
                        "score": 0.88,
                    },
                ],
                query="test query",
            )
        
        return patch(
            "app.tools.tavily_search_tool.TavilySearchTool.search",
            side_effect=mock_search
        )
    
    @staticmethod
    def mock_redis_pubsub():
        """
        Mock Redis Pub/Sub通知服务
        
        Returns:
            配置好的patch对象
        """
        mock_service = MagicMock()
        mock_service.publish_progress = AsyncMock()
        mock_service.publish_completed = AsyncMock()
        mock_service.publish_failed = AsyncMock()
        mock_service.send_human_review_request = AsyncMock()
        
        return patch(
            "app.services.notification_service.notification_service",
            return_value=mock_service
        )
    
    @staticmethod
    def mock_tutorial_agent_success(concept_id: str = "c1"):
        """
        Mock教程生成Agent成功
        
        Args:
            concept_id: 概念ID
            
        Returns:
            配置好的patch对象
        """
        mock_agent = AsyncMock()
        mock_agent.generate.return_value = ContentFactory.create_tutorial_output(concept_id)
        
        return patch(
            "app.agents.tutorial_generator.TutorialGeneratorAgent",
            return_value=mock_agent
        )
    
    @staticmethod
    def mock_resource_agent_success(concept_id: str = "c1"):
        """
        Mock资源推荐Agent成功
        
        Args:
            concept_id: 概念ID
            
        Returns:
            配置好的patch对象
        """
        mock_agent = AsyncMock()
        mock_agent.recommend.return_value = ContentFactory.create_resource_output(concept_id)
        
        return patch(
            "app.agents.resource_recommender.ResourceRecommenderAgent",
            return_value=mock_agent
        )
    
    @staticmethod
    def mock_quiz_agent_success(concept_id: str = "c1"):
        """
        Mock测验生成Agent成功
        
        Args:
            concept_id: 概念ID
            
        Returns:
            配置好的patch对象
        """
        mock_agent = AsyncMock()
        mock_agent.generate.return_value = ContentFactory.create_quiz_output(concept_id)
        
        return patch(
            "app.agents.quiz_generator.QuizGeneratorAgent",
            return_value=mock_agent
        )
    
    @staticmethod
    def mock_email_service():
        """
        Mock邮件服务
        
        Returns:
            配置好的patch对象
        """
        mock_service = AsyncMock()
        mock_service.send_invitation_email.return_value = True
        
        return patch(
            "app.services.email_service.get_email_service",
            return_value=mock_service
        )

