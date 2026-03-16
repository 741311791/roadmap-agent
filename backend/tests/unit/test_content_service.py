"""
ContentService 单元测试。
"""
from app.services.content.content_service import ContentService


class TestContentService:
    """测试 ContentService 的关键依赖装配。"""

    def test_resource_agent_uses_factory_tool_registry(self):
        """资源重试应复用 AgentFactory 注册过工具的 Resource Agent。"""
        service = ContentService()

        agent = service.resource_agent

        assert "web_search" in agent.tool_registry.list_tools()
