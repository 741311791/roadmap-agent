# Web Search 工具架构分析与重构建议

## 问题概述

当前的 Web Search 工具实现存在两个核心架构问题：

### 问题 1：代码重复和职责不清

**现状**：
- `web_search.py` 和 `web_search_mcp.py` 包含大量重复代码
- DuckDuckGo 实现在两个文件中完全重复（约 80 行代码）
- 速率控制逻辑重复
- 每个工具都实现了完整的回退逻辑

**影响**：
- 维护成本高（修改一处需要同步多处）
- 违反 DRY 原则
- 职责不清晰（工具既负责搜索又负责路由）

### 问题 2：MCP 架构设计不当

**现状**：
- `WebSearchToolMCP` 自己初始化 OpenAI 客户端
- Agent（ResourceRecommender）已经有 LLM，工具又初始化 LLM
- MCP 作为独立工具类实现，而不是 LLM 的工具定义

**根本问题**：
误解了 MCP 的本质。Tavily MCP 不是一个独立的工具，而是 OpenAI LLM 的扩展功能。

## 深度分析

### 问题 1 分析：当前架构

```
WebSearchTool (web_search.py)
├─ Tavily API 调用
├─ DuckDuckGo 调用
├─ 速率控制
└─ 回退逻辑

WebSearchToolMCP (web_search_mcp.py)
├─ OpenAI 客户端初始化 ❌
├─ Tavily MCP 调用
├─ DuckDuckGo 调用 (重复)
├─ 速率控制 (重复)
└─ 回退逻辑 (重复)
```

**代码重复统计**：
- DuckDuckGo 实现：~80 行（100% 重复）
- 速率控制逻辑：~30 行（80% 重复）
- 错误处理：~40 行（70% 重复）
- 总计：约 150 行重复代码

### 问题 2 分析：MCP 调用链

**当前调用链**：
```
ResourceRecommender (OpenAI LLM)
  → 定义 web_search 工具 (type: function)
  → LLM 返回 tool_call: web_search
  → Agent._handle_tool_calls()
  → tool_registry.get("web_search_mcp_v1")
  → WebSearchToolMCP
      → 初始化 OpenAI 客户端 ❌
      → client.responses.create() 调用 MCP
      → 解析 MCP 响应
  → 返回给 Agent
```

**问题所在**：
1. **重复的 LLM 实例**：Agent 用 OpenAI，工具又初始化 OpenAI
2. **架构不对称**：Agent 通过 function calling 调用工具，工具又通过 MCP 调用 Tavily
3. **无法复用**：如果其他 Agent 用 Anthropic LLM，无法使用此工具

**正确的 MCP 调用链应该是**：
```
ResourceRecommender (OpenAI LLM)
  → 定义工具:
      - web_search (type: function) → 普通工具
      - tavily_mcp (type: mcp) → MCP 工具定义
  → LLM 自动调用 Tavily MCP
  → OpenAI 返回 MCP 结果
  → Agent 接收并处理
```

## 重构方案

### 方案概览

```
新架构：
├─ 搜索工具层（独立职责）
│   ├─ TavilyAPISearchTool ─ 直接调用 Tavily REST API
│   └─ DuckDuckGoSearchTool ─ 调用 DuckDuckGo
│
├─ 路由层
│   └─ WebSearchRouter ─ 按优先级路由到具体工具
│
└─ Agent 层
    └─ ResourceRecommender
        ├─ 普通工具定义: web_search → WebSearchRouter
        └─ MCP 工具定义: tavily_mcp → Tavily MCP Server
```

**优先级策略**：
1. **Tavily MCP**（如果 Agent 使用 OpenAI LLM）
2. **Tavily API**（通过 WebSearchRouter → TavilyAPISearchTool）
3. **DuckDuckGo**（通过 WebSearchRouter → DuckDuckGoSearchTool）

### 详细设计

#### 1. TavilyAPISearchTool

```python
class TavilyAPISearchTool(BaseTool[SearchQuery, SearchResult]):
    """
    Tavily API 搜索工具（专注于 API 调用）
    
    职责：
    - 调用 Tavily REST API
    - 速率控制
    - 结果格式化
    
    不负责：
    - 回退逻辑（由 Router 处理）
    - MCP 调用（由 Agent 处理）
    """
    
    def __init__(self):
        super().__init__(tool_id="tavily_api_search")
        self.api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"
        self._search_semaphore = asyncio.Semaphore(3)
        self._last_request_time = 0
        self._min_request_interval = 0.5
    
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """直接调用 Tavily API，不包含回退逻辑"""
        # ... 只负责 Tavily API 调用
```

**特点**：
- 单一职责：只负责 Tavily API 调用
- 从 `web_search.py` 提取核心逻辑
- 移除回退逻辑（由 Router 处理）

#### 2. DuckDuckGoSearchTool

```python
class DuckDuckGoSearchTool(BaseTool[SearchQuery, SearchResult]):
    """
    DuckDuckGo 搜索工具
    
    职责：
    - 调用 DuckDuckGo API
    - 区域和语言配置
    - 结果格式化
    """
    
    def __init__(self):
        super().__init__(tool_id="duckduckgo_search")
    
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """调用 DuckDuckGo，使用 asyncio.to_thread"""
        # ... 只负责 DuckDuckGo 调用
```

**特点**：
- 单一职责：只负责 DuckDuckGo 调用
- 从重复代码中提取
- 可被多个工具复用

#### 3. WebSearchRouter

```python
class WebSearchRouter(BaseTool[SearchQuery, SearchResult]):
    """
    Web 搜索路由工具
    
    职责：
    - 按优先级选择搜索引擎
    - 处理回退逻辑
    - 统一错误处理
    
    优先级：
    1. Tavily API（如果配置了 API Key）
    2. DuckDuckGo（如果启用了 fallback）
    """
    
    def __init__(self):
        super().__init__(tool_id="web_search_v1")
        self.tavily_tool = TavilyAPISearchTool()
        self.duckduckgo_tool = DuckDuckGoSearchTool()
        self.use_duckduckgo_fallback = settings.USE_DUCKDUCKGO_FALLBACK
    
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """按优先级路由到具体搜索工具"""
        # 尝试 Tavily API
        if self.tavily_tool.api_key:
            try:
                return await self.tavily_tool.execute(input_data)
            except Exception as e:
                logger.warning("tavily_api_failed", error=str(e))
                # 回退到 DuckDuckGo
        
        # 使用 DuckDuckGo
        if self.use_duckduckgo_fallback:
            return await self.duckduckgo_tool.execute(input_data)
        
        raise ValueError("所有搜索引擎都不可用")
```

**特点**：
- 集中管理路由逻辑
- 清晰的优先级策略
- 易于扩展新的搜索引擎

#### 4. ResourceRecommender MCP 集成

```python
class ResourceRecommenderAgent(BaseAgent):
    """资源推荐师 Agent"""
    
    def _get_tools_definition(self) -> List[Dict[str, Any]]:
        """
        获取工具定义
        
        包含两类工具：
        1. 普通 function calling 工具（web_search）
        2. MCP 工具（tavily_mcp）- 仅当使用 OpenAI LLM 时
        """
        tools = [
            # 普通搜索工具（通过 Router 路由）
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "执行网络搜索（Tavily API 或 DuckDuckGo）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "max_results": {"type": "integer", "default": 5},
                        },
                        "required": ["query"],
                    },
                },
            }
        ]
        
        # 如果使用 OpenAI LLM，添加 MCP 工具定义
        if self.model_provider == "openai" and settings.TAVILY_API_KEY:
            tools.append({
                "type": "mcp",
                "server_label": "tavily",
                "server_url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={settings.TAVILY_API_KEY}",
                "require_approval": "never",
            })
        
        return tools
    
    async def _handle_tool_calls(self, tool_calls: List[Any]) -> List[Dict]:
        """处理工具调用"""
        tool_messages = []
        
        for tool_call in tool_calls:
            # 处理普通 function calling
            if tool_call.type == "function":
                if tool_call.function.name == "web_search":
                    # 调用 WebSearchRouter
                    search_tool = tool_registry.get("web_search_v1")
                    result = await search_tool.execute(...)
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": format_result(result),
                    })
            
            # MCP 工具调用由 OpenAI 自动处理
            # Agent 只需要接收结果，不需要手动调用
            elif tool_call.type == "mcp":
                # OpenAI LLM 已经自动调用了 MCP
                # 结果会在下一次 LLM 响应中返回
                pass
        
        return tool_messages
```

**关键改进**：
1. **MCP 作为工具定义**：不是独立的工具类
2. **LLM 自动处理**：Agent 不需要初始化 OpenAI 客户端
3. **条件性启用**：只有 OpenAI LLM 才添加 MCP 工具

## 实现步骤

### 阶段 1：拆分工具（解决代码重复）

**步骤 1.1**：创建 `TavilyAPISearchTool`
- 从 `web_search.py` 提取 Tavily API 调用逻辑
- 移除 DuckDuckGo 和回退逻辑
- 保留速率控制

**步骤 1.2**：创建 `DuckDuckGoSearchTool`
- 提取 DuckDuckGo 调用逻辑
- 使其可独立使用

**步骤 1.3**：创建 `WebSearchRouter`
- 实现路由和回退逻辑
- 注册为 `web_search_v1`

**步骤 1.4**：更新 `tool_registry`
- 注册三个新工具
- 保持向后兼容（`web_search_v1` 仍然可用）

**验证**：
```bash
# 运行现有测试，确保功能不变
pytest tests/integration/test_resource_recommender.py
```

### 阶段 2：优化 MCP 架构（解决 LLM 初始化问题）

**步骤 2.1**：修改 `ResourceRecommender._get_tools_definition()`
- 添加 MCP 工具定义
- 条件性启用（仅 OpenAI LLM）

**步骤 2.2**：更新 `ResourceRecommender._handle_tool_calls()`
- 识别 MCP 工具调用
- 正确处理 MCP 响应

**步骤 2.3**：删除 `web_search_mcp.py`
- 不再需要独立的 MCP 工具类
- 从 `tool_registry` 移除

**步骤 2.4**：更新配置和文档
- 更新 `TAVILY_MCP_SETUP.md`
- 说明新的架构

**验证**：
```bash
# 测试 MCP 功能
python scripts/test_tavily_mcp.py

# 完整集成测试
pytest tests/e2e/
```

### 阶段 3：清理和优化

**步骤 3.1**：代码审查
- 确保没有遗漏的重复代码
- 检查错误处理

**步骤 3.2**：性能测试
- 对比新旧架构的性能
- 确保没有性能退化

**步骤 3.3**：文档更新
- 更新架构文档
- 更新 API 文档

## 优势对比

### 当前架构 vs. 新架构

| 维度 | 当前架构 | 新架构 | 改进 |
|------|---------|--------|------|
| 代码重复 | ~150 行重复代码 | 0 行重复 | ✅ 消除重复 |
| 职责分离 | 工具混合了搜索+路由 | 单一职责 | ✅ 清晰职责 |
| LLM 初始化 | 工具初始化 LLM ❌ | Agent 的 LLM 处理 | ✅ 正确架构 |
| MCP 使用 | 工具封装 MCP | LLM 原生支持 | ✅ 充分利用 |
| 可维护性 | 修改需同步多处 | 单点修改 | ✅ 易维护 |
| 可扩展性 | 难以添加新引擎 | 只需添加工具 | ✅ 易扩展 |
| 性能 | 多余的 LLM 调用 | 优化的调用链 | ✅ 更高效 |

### 代码量对比

```
当前：
- web_search.py: 261 行
- web_search_mcp.py: 435 行
- 总计: 696 行（含 ~150 行重复）

新架构：
- tavily_api_search_tool.py: 120 行
- duckduckgo_search_tool.py: 80 行
- web_search_router.py: 100 行
- resource_recommender.py: +50 行（MCP 定义）
- 总计: 350 行（无重复）

减少: 346 行 (49.7%)
```

## 风险和缓解

### 风险 1：MCP 响应格式不确定

**风险描述**：
OpenAI MCP 返回的响应格式可能与预期不同

**缓解措施**：
1. 先在测试脚本中验证 MCP 响应格式
2. 实现健壮的响应解析逻辑
3. 保留 fallback 到 Tavily API 的能力

### 风险 2：破坏现有功能

**风险描述**：
重构可能影响现有的资源推荐功能

**缓解措施**：
1. 渐进式重构（两个阶段）
2. 保持向后兼容
3. 完整的测试覆盖
4. 可以回滚到旧版本

### 风险 3：性能退化

**风险描述**：
新架构可能引入额外开销

**缓解措施**：
1. 性能基准测试
2. 路由逻辑优化
3. 保留速率控制机制

## 总结

### 核心问题

1. **代码重复**：违反 DRY 原则，维护成本高
2. **架构不当**：MCP 应该是 LLM 的工具定义，而不是独立工具类

### 解决方案

1. **拆分工具**：单一职责，消除重复
2. **路由模式**：集中管理优先级和回退
3. **正确使用 MCP**：在 Agent 层定义，让 LLM 处理

### 预期效果

- ✅ 减少 50% 代码量
- ✅ 消除所有重复代码
- ✅ 架构更清晰、更易维护
- ✅ 正确使用 OpenAI MCP 功能
- ✅ 易于扩展新的搜索引擎

### 下一步

建议按照阶段 1 → 阶段 2 → 阶段 3 的顺序实施重构，每个阶段都要进行充分测试。

---

**文档版本**: v1.0  
**创建日期**: 2024-12-08  
**作者**: AI Assistant  
**审核状态**: 待审核

