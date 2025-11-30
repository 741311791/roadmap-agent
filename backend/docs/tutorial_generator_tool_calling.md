# TutorialGeneratorAgent 工具调用功能

## 修改概述

为 `TutorialGeneratorAgent` 添加了对 `web_search` 工具的支持，使其能够在生成教程时主动搜索最新的技术资源、文档和示例。

## 修改内容

### 1. 导入更新

```python
from typing import AsyncIterator, List, Dict, Any
from app.models.domain import SearchQuery
```

添加了 `List`, `Dict`, `Any` 类型以及 `SearchQuery` 模型。

### 2. 新增方法：`_get_tools_definition()`

为 LLM 提供工具定义（Function Calling 格式）：

```python
def _get_tools_definition(self) -> List[Dict[str, Any]]:
    """获取工具定义（符合 OpenAI Function Calling 格式）"""
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "执行网络搜索以获取最新的学习资源、技术文档和教程信息...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "..."},
                        "max_results": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
            },
        }
    ]
```

### 3. 新增方法：`_handle_tool_calls()`

处理 LLM 返回的工具调用请求：

- 解析工具调用参数
- 执行 `web_search_v1` 工具
- 格式化搜索结果
- 返回工具响应消息

```python
async def _handle_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
    """处理 LLM 返回的工具调用请求"""
    # 1. 获取 web_search 工具
    # 2. 构建 SearchQuery
    # 3. 执行搜索
    # 4. 格式化结果并返回
```

### 4. 修改方法：`generate()`

支持工具调用的迭代式对话流程：

```python
# 1. 获取工具定义
tools = self._get_tools_definition()

# 2. 迭代式调用 LLM
max_iterations = 5
while iteration < max_iterations:
    response = await self._call_llm(messages, tools=tools)
    
    # 3. 检查是否有工具调用
    if hasattr(message, 'tool_calls') and message.tool_calls:
        # 将 assistant 消息添加到历史
        messages.append({...})
        
        # 处理工具调用
        tool_messages = await self._handle_tool_calls(message.tool_calls)
        messages.extend(tool_messages)
        
        iteration += 1
        continue
    
    # 4. 没有工具调用，获取最终内容
    content = message.content
    break
```

### 5. 修改方法：`generate_stream()`

流式生成时支持工具调用：

- **工具调用阶段**（非流式）：先处理所有工具调用
- **内容生成阶段**（流式）：然后流式生成最终教程内容

推送的事件类型：

```python
{"type": "tool_call", "tool_name": "...", "tool_args": {...}}
{"type": "tool_result", "results_count": N}
{"type": "tutorial_chunk", "content": "..."}
{"type": "tutorial_complete", "data": {...}}
{"type": "tutorial_error", "error": "..."}
```

## 工作流程

```
用户请求
    ↓
加载 System Prompt（包含工具使用指南）
    ↓
调用 LLM（传递工具定义）
    ↓
LLM 决定是否调用工具
    ↓
如果调用 web_search：
    1. 执行搜索
    2. 返回搜索结果
    3. LLM 再次生成（融合搜索结果）
    ↓
生成教程内容
    ↓
上传到 S3
    ↓
返回结果
```

## 测试

运行测试脚本：

```bash
cd backend
python scripts/test_tutorial_tool_calling.py
```

测试内容：

1. **非流式生成测试**：验证工具调用和教程生成
2. **流式生成测试**：验证工具调用事件推送和流式内容生成

## 注意事项

1. **最大迭代次数**：设置为 5 次，防止无限循环
2. **工具调用是可选的**：LLM 会根据需要决定是否使用工具
3. **流式处理策略**：先完成所有工具调用（非流式），再流式生成内容
4. **错误处理**：工具调用失败时会将错误信息返回给 LLM

## 依赖

- `web_search_v1` 工具必须在 `tool_registry` 中注册
- 需要配置 `TAVILY_API_KEY` 环境变量（用于网络搜索）

## Prompt 模板更新

`prompts/tutorial_generator.j2` 中已包含工具使用指南：

```jinja2
[5. Tool Usage Guide]
可用工具：
- web_search_v1: 执行网络搜索以获取最新的学习资源、技术文档和教程（可选）

工具使用流程：
1. （可选）使用 web_search_v1 搜索相关学习资源获取最新信息
2. 生成完整的教程内容，包含在 JSON 的 tutorial_content 字段中
3. 系统会自动将教程内容上传到 S3 存储
```

## 示例日志

```
[INFO] tool_call_received: tool_name=web_search, tool_args={'query': 'React Hooks 最佳实践', 'max_results': 5}
[INFO] web_search_success: query="React Hooks 最佳实践", results_count=5, provider=tavily
[INFO] tool_call_success: tool_name=web_search, results_count=5
[INFO] tutorial_generation_success: concept_id=react-hooks-001, tutorial_id=..., content_url=...
```

## 性能影响

- **非流式调用**：增加 1-3 次额外的 LLM 调用（如果使用工具）
- **流式调用**：工具调用阶段是非流式的，完成后才开始流式生成
- **搜索延迟**：每次 web_search 调用约 1-3 秒

## 后续优化建议

1. **缓存搜索结果**：相同查询可以复用结果
2. **并行工具调用**：如果 LLM 请求多个独立的工具调用，可以并行执行
3. **完全流式支持**：探索在流式模式下处理工具调用的方案（更复杂）

