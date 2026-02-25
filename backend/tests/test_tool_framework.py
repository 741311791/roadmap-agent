"""
统一工具框架单元测试

测试覆盖：
1. BaseTool 基类功能
2. ToolRegistry 注册与执行
3. WebSearchTool 适配
4. AgentFactory 集成
5. QAAgent 工具调用
"""
import pytest
from pydantic import BaseModel, Field
from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry


# ============================================================
# 测试用的 Mock Tool
# ============================================================

class MockToolInput(BaseModel):
    """Mock 工具输入"""
    text: str = Field(..., description="输入文本")
    count: int = Field(1, description="重复次数")


class MockToolOutput(BaseModel):
    """Mock 工具输出"""
    result: str = Field(..., description="处理结果")
    success: bool = Field(True, description="是否成功")


class MockTool(BaseTool[MockToolInput, MockToolOutput]):
    """Mock 工具（用于测试）"""
    
    def __init__(self):
        super().__init__(
            tool_id="mock_tool_v1",
            name="mock_tool",
            description="A mock tool for testing",
            args_schema=MockToolInput,
        )
    
    async def execute(self, input_data: MockToolInput, **kwargs) -> MockToolOutput:
        """执行 Mock 工具"""
        result = input_data.text * input_data.count
        return MockToolOutput(result=result, success=True)


class FailingMockTool(BaseTool[MockToolInput, MockToolOutput]):
    """会失败的 Mock 工具（用于测试错误处理）"""
    
    def __init__(self):
        super().__init__(
            tool_id="failing_mock_tool_v1",
            name="failing_mock_tool",
            description="A mock tool that always fails",
            args_schema=MockToolInput,
        )
    
    async def execute(self, input_data: MockToolInput, **kwargs) -> MockToolOutput:
        """执行失败"""
        raise ValueError("This tool always fails")


# ============================================================
# 测试 BaseTool 基类
# ============================================================

class TestBaseTool:
    """测试 BaseTool 基类功能"""
    
    def test_tool_initialization(self):
        """测试工具初始化"""
        tool = MockTool()
        
        assert tool.tool_id == "mock_tool_v1"
        assert tool.name == "mock_tool"
        assert tool.description == "A mock tool for testing"
        assert tool.args_schema == MockToolInput
    
    def test_to_openai_function_schema(self):
        """测试生成 OpenAI Function Schema"""
        tool = MockTool()
        schema = tool.to_openai_function_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "mock_tool"
        assert schema["function"]["description"] == "A mock tool for testing"
        assert "parameters" in schema["function"]
        
        # 验证参数 Schema
        params = schema["function"]["parameters"]
        assert "properties" in params
        assert "text" in params["properties"]
        assert "count" in params["properties"]
    
    def test_to_mcp_tool_schema(self):
        """测试生成 MCP Tool Schema"""
        tool = MockTool()
        schema = tool.to_mcp_tool_schema()
        
        assert schema["name"] == "mock_tool"
        assert schema["description"] == "A mock tool for testing"
        assert "inputSchema" in schema
    
    @pytest.mark.asyncio
    async def test_tool_execution(self):
        """测试工具执行"""
        tool = MockTool()
        input_data = MockToolInput(text="Hello", count=3)
        
        result = await tool.execute(input_data)
        
        assert isinstance(result, MockToolOutput)
        assert result.result == "HelloHelloHello"
        assert result.success is True


# ============================================================
# 测试 ToolRegistry
# ============================================================

class TestToolRegistry:
    """测试 ToolRegistry 功能"""
    
    def test_registry_initialization(self):
        """测试注册中心初始化"""
        registry = ToolRegistry()
        
        assert len(registry.list_tools()) == 0
        assert registry._tools == {}
    
    def test_register_tool(self):
        """测试注册工具"""
        registry = ToolRegistry()
        tool = MockTool()
        
        registry.register(tool)
        
        assert len(registry.list_tools()) == 1
        assert "mock_tool" in registry.list_tools()
        assert registry.get_tool("mock_tool") == tool
    
    def test_register_duplicate_tool(self):
        """测试注册重复工具（应该覆盖）"""
        registry = ToolRegistry()
        tool1 = MockTool()
        tool2 = MockTool()
        
        registry.register(tool1)
        registry.register(tool2)  # 覆盖
        
        assert len(registry.list_tools()) == 1
        assert registry.get_tool("mock_tool") == tool2
    
    def test_unregister_tool(self):
        """测试取消注册工具"""
        registry = ToolRegistry()
        tool = MockTool()
        
        registry.register(tool)
        assert len(registry.list_tools()) == 1
        
        success = registry.unregister("mock_tool")
        assert success is True
        assert len(registry.list_tools()) == 0
        
        # 取消不存在的工具
        success = registry.unregister("non_existent")
        assert success is False
    
    def test_get_all_schemas_openai(self):
        """测试获取所有工具的 OpenAI Schema"""
        registry = ToolRegistry()
        registry.register(MockTool())
        
        schemas = registry.get_all_schemas(format="openai")
        
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "mock_tool"
    
    def test_get_all_schemas_mcp(self):
        """测试获取所有工具的 MCP Schema"""
        registry = ToolRegistry()
        registry.register(MockTool())
        
        schemas = registry.get_all_schemas(format="mcp")
        
        assert len(schemas) == 1
        assert schemas[0]["name"] == "mock_tool"
        assert "inputSchema" in schemas[0]
    
    def test_get_all_schemas_invalid_format(self):
        """测试使用无效格式"""
        registry = ToolRegistry()
        
        with pytest.raises(ValueError, match="不支持的 Schema 格式"):
            registry.get_all_schemas(format="invalid")
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """测试成功执行工具"""
        registry = ToolRegistry()
        registry.register(MockTool())
        
        result = await registry.execute_tool(
            name="mock_tool",
            arguments={"text": "Test", "count": 2},
        )
        
        assert isinstance(result, MockToolOutput)
        assert result.result == "TestTest"
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """测试执行不存在的工具（返回错误描述）"""
        registry = ToolRegistry()
        
        result = await registry.execute_tool(
            name="non_existent_tool",
            arguments={},
        )
        
        # 应该返回错误字符串，而不是抛出异常
        assert isinstance(result, str)
        assert "Error" in result
        assert "non_existent_tool" in result
    
    @pytest.mark.asyncio
    async def test_execute_tool_invalid_arguments(self):
        """测试使用无效参数执行工具（返回错误描述）"""
        registry = ToolRegistry()
        registry.register(MockTool())
        
        # 缺少必填参数 'text'
        result = await registry.execute_tool(
            name="mock_tool",
            arguments={"count": 2},  # 缺少 'text'
        )
        
        # 应该返回错误字符串
        assert isinstance(result, str)
        assert "Error" in result
    
    @pytest.mark.asyncio
    async def test_execute_tool_execution_failure(self):
        """测试工具执行失败（返回错误描述）"""
        registry = ToolRegistry()
        registry.register(FailingMockTool())
        
        result = await registry.execute_tool(
            name="failing_mock_tool",
            arguments={"text": "Test", "count": 1},
        )
        
        # 应该返回错误字符串
        assert isinstance(result, str)
        assert "Error" in result
        assert "always fails" in result


# ============================================================
# 测试 WebSearchTool 适配
# ============================================================

class TestWebSearchToolAdapter:
    """测试 WebSearchTool 适配新框架"""
    
    def test_web_search_tool_initialization(self):
        """测试 WebSearchTool 初始化"""
        from app.tools.search.web_search_router import WebSearchRouter
        
        tool = WebSearchRouter()
        
        assert tool.tool_id == "web_search_v2"
        assert tool.name == "web_search"
        assert "search" in tool.description.lower()
    
    def test_web_search_tool_schema_generation(self):
        """测试 WebSearchTool Schema 生成"""
        from app.tools.search.web_search_router import WebSearchRouter
        
        tool = WebSearchRouter()
        schema = tool.to_openai_function_schema()
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "web_search"
        assert "parameters" in schema["function"]


# ============================================================
# 测试 AgentFactory 集成
# ============================================================

class TestAgentFactoryIntegration:
    """测试 AgentFactory 集成 ToolRegistry"""
    
    def test_agent_factory_initialization(self):
        """测试 AgentFactory 初始化（会自动创建 ToolRegistry）"""
        from app.agents.factory import AgentFactory
        from app.config.settings import settings
        
        factory = AgentFactory(settings)
        
        assert factory.tool_registry is not None
        assert isinstance(factory.tool_registry, ToolRegistry)
        
        # 验证默认工具已注册
        tools = factory.tool_registry.list_tools()
        assert "web_search" in tools
        assert "get_concept_tutorial" in tools
    
    def test_create_qa_agent_with_tool_registry(self):
        """测试创建 QAAgent（会自动注入 ToolRegistry）"""
        from app.agents.factory import AgentFactory
        from app.config.settings import settings
        
        factory = AgentFactory(settings)
        qa_agent = factory.create_qa_agent()
        
        assert qa_agent.tool_registry is not None
        assert qa_agent.tool_registry == factory.tool_registry


# ============================================================
# 集成测试
# ============================================================

@pytest.mark.asyncio
async def test_end_to_end_tool_execution():
    """端到端测试：从注册到执行"""
    # 1. 创建 Registry
    registry = ToolRegistry()
    
    # 2. 注册工具
    registry.register(MockTool())
    
    # 3. 获取 Schema（模拟 Agent 使用）
    schemas = registry.get_all_schemas(format="openai")
    assert len(schemas) == 1
    
    # 4. 执行工具（模拟 LLM 调用）
    result = await registry.execute_tool(
        name="mock_tool",
        arguments={"text": "Hello", "count": 3},
    )
    
    # 5. 验证结果
    assert result.result == "HelloHelloHello"


@pytest.mark.asyncio
async def test_error_handling_flow():
    """测试错误处理流程"""
    registry = ToolRegistry()
    registry.register(FailingMockTool())
    
    # 执行会失败的工具
    result = await registry.execute_tool(
        name="failing_mock_tool",
        arguments={"text": "Test", "count": 1},
    )
    
    # 应该返回错误描述（让 LLM 看到并可能重试）
    assert isinstance(result, str)
    assert "Error" in result
    assert "always fails" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

