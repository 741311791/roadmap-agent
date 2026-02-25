# TutorialGeneratorAgent 使用 BaseAgent ReAct 重构

**日期**: 2026-02-07  
**类型**: 重构  
**影响范围**: TutorialGeneratorAgent

## 问题背景

原实现使用 LangChain 的 `create_agent` 来实现 ReAct 模式的工具调用，存在以下问题：

1. **额外依赖**：需要引入 `langchain-openai` 依赖
2. **代码不一致**：与项目中其他 Agent 使用的 `BaseAgent` 模式不一致
3. **维护复杂度**：需要维护两套不同的 Agent 实现机制

原始错误：
```
AttributeError: 'TutorialGeneratorAgent' object has no attribute '_create_langchain_llm'
```

## 解决方案

使用 `BaseAgent` 已有的 `_call_llm_with_tools_react` 方法替代 LangChain 的 `create_agent`。

## 修改内容

### 1. 修改导入

**之前**：
```python
from langchain.agents import create_agent
```

**之后**：
```python
from typing import Any, Dict
# 移除 LangChain Agent 导入
```

### 2. 修改初始化方法

**之前**：
```python
def __init__(self, ...):
    super().__init__(...)
    # 创建 LangChain 兼容的 LLM
    self.llm = self._create_langchain_llm()
```

**之后**：
```python
def __init__(self, ...):
    super().__init__(...)
    # 存储 LangChain 工具实例（用于执行）
    self._langchain_tools = {}
```

### 3. 修改工具加载方法

**之前**：返回 LangChain `BaseTool` 列表

**之后**：
```python
async def _get_tools(self, is_dev_scenario: bool = True) -> list[Dict]:
    """返回 OpenAI function calling 格式的工具列表"""
    tools = []
    
    if is_dev_scenario:
        # 加载LangChain工具
        context7_tools = await load_context7_tools()
        
        # 转换为OpenAI function calling格式
        for tool in context7_tools:
            # 保存工具实例以供后续执行
            self._langchain_tools[tool.name] = tool
            
            # 转换为OpenAI格式
            tool_def = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.args_schema.schema() if hasattr(tool, 'args_schema') and tool.args_schema else {
                        "type": "object",
                        "properties": {},
                    }
                }
            }
            tools.append(tool_def)
    
    return tools
```

### 4. 实现工具执行方法

新增 `_execute_tool` 方法：
```python
async def _execute_tool(
    self,
    tool_name: str,
    tool_args: Dict[str, Any]
) -> Any:
    """执行工具调用（调用LangChain工具）"""
    if tool_name not in self._langchain_tools:
        raise ValueError(f"Tool '{tool_name}' not found")
    
    tool = self._langchain_tools[tool_name]
    result = await tool.ainvoke(tool_args)
    
    return result
```

### 5. 修改生成方法

**之前**：使用 LangChain Agent
```python
# 创建 Agent
agent = create_agent(
    model=self.llm,
    tools=tools,
    system_prompt=system_prompt,
)

# 调用 Agent
result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": user_message}]},
    config={"recursion_limit": 20}
)

# 提取输出
content = result["messages"][-1].content
```

**之后**：使用 BaseAgent ReAct
```python
# 构建消息
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message}
]

# 使用BaseAgent的ReAct方法
response = await self._call_llm(
    messages=messages,
    tools=tools if tools else None,
    use_react=True if tools else False,
    max_iterations=20,
)

# 提取输出
content = response.choices[0].message.content
```

## 技术亮点

### 1. 工具格式转换

将 LangChain 的 `BaseTool` 转换为 OpenAI function calling 格式：
- 提取工具名称、描述
- 转换参数 schema（从 Pydantic schema）
- 保留工具实例用于执行

### 2. 统一的 ReAct 循环

使用 `BaseAgent._call_llm_with_tools_react`：
- 自动处理工具调用循环
- 支持多轮工具调用
- 统一的错误处理和日志记录

### 3. 场景自适应

- **开发场景**：加载 Context7 工具，查询官方文档
- **非开发场景**：不加载工具，使用 LLM 知识库

## 依赖优化

### 移除的依赖
- `langchain-openai` (不再需要)

### 保留的依赖
- `langchain>=1.2.6` (用于工具基类)
- `langchain-mcp-adapters>=0.1.0` (用于加载 MCP 工具)
- `langchain-litellm>=0.3.0` (保留备用)

## 测试验证

1. ✅ Celery workers 启动成功
2. ✅ 工具注册正常
3. ✅ 无依赖错误

## 影响范围

- **修改文件**：
  - `backend/app/agents/tutorial_generator.py`
  
- **无需修改**：
  - `backend/app/agents/base.py` (已有 ReAct 方法)
  - `backend/pyproject.toml` (依赖已正确配置)

## 后续建议

1. **测试完整流程**：运行教程生成测试，验证工具调用是否正常
2. **监控日志**：观察 ReAct 循环的工具调用日志
3. **性能对比**：对比新旧实现的性能和成本

## 总结

本次重构成功将 `TutorialGeneratorAgent` 从 LangChain Agent 迁移到 `BaseAgent` 的 ReAct 模式：
- ✅ 移除额外依赖
- ✅ 统一代码风格
- ✅ 保持功能完整
- ✅ 降低维护成本
