# 修复总结：TutorialGeneratorAgent 工具调用功能

## 问题描述

`TutorialGeneratorAgent` 在生成教程时没有调用 `web_search` 工具，即使 prompt 模板中提到了可以使用该工具。

## 根本原因

1. **没有传递工具定义**：调用 LLM 时没有传递 `tools` 参数
2. **没有处理工具调用**：LLM 返回工具调用请求后，代码没有处理这些请求
3. **缺少迭代机制**：没有实现"LLM 调用 → 工具执行 → LLM 再次调用"的循环流程

## 解决方案

### 修改文件

- `backend/app/agents/tutorial_generator.py`

### 核心改动

#### 1. 添加工具定义方法

```python
def _get_tools_definition(self) -> List[Dict[str, Any]]:
    """返回符合 OpenAI Function Calling 格式的工具定义"""
    return [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "执行网络搜索...",
                "parameters": {...},
            },
        }
    ]
```

#### 2. 添加工具调用处理方法

```python
async def _handle_tool_calls(self, tool_calls: List[Any]) -> List[Dict[str, Any]]:
    """
    处理 LLM 返回的工具调用请求：
    1. 解析工具调用参数
    2. 执行 web_search_v1 工具
    3. 格式化搜索结果
    4. 返回工具响应消息
    """
```

#### 3. 修改 generate() 方法

添加迭代式工具调用逻辑：

```python
# 获取工具定义
tools = self._get_tools_definition()

# 迭代调用（最多5次）
while iteration < max_iterations:
    response = await self._call_llm(messages, tools=tools)
    
    # 检查工具调用
    if message.tool_calls:
        # 处理工具调用
        tool_messages = await self._handle_tool_calls(message.tool_calls)
        messages.extend(tool_messages)
        continue
    
    # 获取最终内容
    content = message.content
    break
```

#### 4. 修改 generate_stream() 方法

采用两阶段策略：

1. **工具调用阶段**（非流式）：先完成所有工具调用
2. **内容生成阶段**（流式）：然后流式生成最终内容

推送新的事件类型：

- `tool_call`：工具调用开始
- `tool_result`：工具调用完成

## 工作流程图

```
┌─────────────────┐
│  用户请求教程    │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ 加载 System Prompt   │
│ (包含工具使用指南)   │
└────────┬────────────┘
         │
         ▼
┌──────────────────────────┐
│ 调用 LLM (传递工具定义)   │
└────────┬─────────────────┘
         │
         ▼
    ┌────────────┐
    │ LLM 决策   │
    └─┬────────┬─┘
      │        │
   调用工具   直接生成
      │        │
      ▼        │
┌──────────────┐│
│ 执行搜索工具  ││
└──────┬───────┘│
       │        │
       ▼        │
┌──────────────┐│
│ 返回搜索结果  ││
└──────┬───────┘│
       │        │
       ▼        ▼
┌─────────────────────┐
│ LLM 生成教程内容     │
│ (融合搜索结果)       │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ 上传到 S3 存储       │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│ 返回结果             │
└─────────────────────┘
```

## 测试方法

运行测试脚本：

```bash
cd backend
python scripts/test_tutorial_tool_calling.py
```

## 预期效果

1. **LLM 自主决策**：根据概念内容，LLM 会自主决定是否需要搜索
2. **搜索最新资源**：如果搜索，会获取最新的技术文档、教程和示例
3. **更优质教程**：融合搜索结果后，生成的教程内容更丰富、更准确
4. **透明性**：日志和事件流会清楚显示工具调用过程

## 日志示例

```
[INFO] tutorial_generation_llm_call: concept_id=react-hooks-001, iteration=0
[INFO] tutorial_generation_tool_calls_detected: concept_id=react-hooks-001, tool_calls_count=1
[INFO] tool_call_received: tool_name=web_search, tool_args={'query': 'React Hooks 最新最佳实践 2024'}
[INFO] web_search_success: query="React Hooks 最新最佳实践 2024", results_count=5
[INFO] tool_call_success: tool_name=web_search, results_count=5
[INFO] tutorial_generation_llm_call: concept_id=react-hooks-001, iteration=1
[INFO] tutorial_generation_success: concept_id=react-hooks-001, tutorial_id=...
```

## 性能考虑

- **额外延迟**：每次工具调用增加 1-3 秒
- **额外 LLM 调用**：每次工具调用需要额外 1 次 LLM 调用
- **成本增加**：约增加 20-30% 的 token 使用量

## 配置要求

确保 `.env` 文件中配置了：

```env
# Tavily API (用于网络搜索)
TAVILY_API_KEY=your_tavily_api_key_here
```

## 相关文档

- [工具调用详细文档](./tutorial_generator_tool_calling.md)
- [测试脚本](../scripts/test_tutorial_tool_calling.py)
- [Prompt 模板](../prompts/tutorial_generator.j2)

## 版本信息

- 修改日期：2024-11-29
- 修改内容：添加工具调用支持
- 影响范围：`TutorialGeneratorAgent.generate()` 和 `generate_stream()`

