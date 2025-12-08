# Tavily MCP 搜索服务配置指南

## 概述

本系统已重构为支持通过 **OpenAI MCP (Model Context Protocol)** 调用 Tavily 搜索服务，提供更标准化和可扩展的搜索能力。

## 架构说明

### 传统方式（保留）
```
Resource Recommender → WebSearchTool → Tavily API (直接调用)
```

### MCP 方式（推荐）
```
Resource Recommender → WebSearchToolMCP → OpenAI MCP → Tavily MCP Server
```

## 优势

1. **标准化接口**: 使用 OpenAI 标准 MCP 协议
2. **更好的集成**: 与其他 MCP 服务无缝集成
3. **增强的功能**: 利用 OpenAI 的语言理解能力优化搜索
4. **自动回退**: 如果 MCP 不可用，自动回退到传统方式或 DuckDuckGo

## 配置步骤

### 1. 环境变量配置

在 `.env` 文件中添加/更新以下配置：

```bash
# Tavily API 配置（必需）
TAVILY_API_KEY=your_actual_tavily_api_key

# OpenAI API 配置（MCP 需要）
RECOMMENDER_API_KEY=your_actual_openai_api_key

# 备选搜索引擎配置（可选）
USE_DUCKDUCKGO_FALLBACK=true
```

### 2. 获取 API 密钥

#### Tavily API Key
1. 访问 [Tavily.com](https://tavily.com/)
2. 注册账号
3. 在控制台中创建 API 密钥
4. 复制密钥到 `.env` 文件的 `TAVILY_API_KEY`

#### OpenAI API Key
1. 访问 [OpenAI Platform](https://platform.openai.com/)
2. 登录账号
3. 访问 [API Keys 页面](https://platform.openai.com/account/api-keys)
4. 创建新的 API 密钥
5. 复制密钥到 `.env` 文件的 `RECOMMENDER_API_KEY`

**注意**: MCP 功能需要使用支持 `gpt-4.1` 模型的 API 密钥。

### 3. 验证配置

运行测试脚本验证连通性：

```bash
cd backend
uv run python scripts/test_tavily_mcp.py
```

成功的输出示例：
```
============================================================
Tavily MCP 连通性测试
============================================================

步骤 1: 检查配置
------------------------------------------------------------
✓ Tavily API Key: tvly-***
✓ OpenAI API Key: sk-***

步骤 2: 初始化 OpenAI 客户端
------------------------------------------------------------
✓ OpenAI 客户端初始化成功

步骤 3: 配置 Tavily MCP 工具
------------------------------------------------------------
MCP 服务 URL: https://mcp.tavily.com/mcp/...

步骤 4: 发送测试查询
------------------------------------------------------------
查询: 'Python 官方文档'

步骤 5: 验证响应
------------------------------------------------------------
✓ 响应成功

============================================================
✅ Tavily MCP 连通性测试成功！
============================================================
```

## 使用方式

### 自动选择（推荐）

系统会自动选择最佳搜索方式：

1. **优先**: 使用 Tavily MCP（如果配置了 OpenAI 和 Tavily API Key）
2. **备选**: 使用传统 Tavily API（如果只配置了 Tavily API Key）
3. **降级**: 使用 DuckDuckGo（如果启用了备选搜索）

无需修改代码，系统会自动处理。

### 手动选择工具

如果需要手动指定搜索工具：

```python
from app.core.tool_registry import tool_registry

# 使用 MCP 版本
search_tool = tool_registry.get("web_search_mcp_v1")

# 使用传统版本
search_tool = tool_registry.get("web_search_v1")

# 执行搜索
result = await search_tool.execute(search_query)
```

## 故障排查

### 问题 1: 连接超时

**症状**: `APITimeoutError: Request timed out`

**解决方案**:
1. 检查网络连接
2. 如果在国内，配置代理：
   ```bash
   export HTTPS_PROXY=http://your-proxy:port
   export HTTP_PROXY=http://your-proxy:port
   ```
3. 增加超时时间（已在代码中设置为 60 秒）

### 问题 2: 认证失败

**症状**: `AuthenticationError: Incorrect API key provided`

**解决方案**:
1. 检查 `.env` 文件中的 `RECOMMENDER_API_KEY` 是否正确
2. 确保 API 密钥有效且未过期
3. 访问 [OpenAI API Keys](https://platform.openai.com/account/api-keys) 验证密钥

### 问题 3: MCP 工具不可用

**症状**: 日志显示 "MCP 搜索工具不可用，使用传统搜索工具"

**影响**: 系统会自动回退到传统搜索方式，功能正常但可能搜索质量略有差异

**解决方案**:
1. 检查 OpenAI API Key 配置
2. 确保使用的是支持 MCP 的 API 密钥
3. 如果问题持续，传统搜索方式仍然可用

### 问题 4: Tavily API Key 无效

**症状**: `ValueError: Tavily API Key 未配置` 或搜索返回 401 错误

**解决方案**:
1. 检查 `.env` 文件中的 `TAVILY_API_KEY`
2. 确保密钥不是默认值 `your_tavily_api_key_here`
3. 访问 [Tavily Dashboard](https://tavily.com/dashboard) 验证密钥

## 性能优化

### 速率限制

系统内置速率限制机制：
- **并发限制**: 最多 3 个并发搜索请求
- **请求间隔**: 最少 500ms 间隔
- **自动重试**: 失败时自动重试 2 次

### 缓存建议

对于频繁搜索的内容，建议在应用层实现缓存：

```python
# 示例：使用 Redis 缓存搜索结果
import hashlib
from app.core.cache import redis_client

async def cached_search(query: str) -> SearchResult:
    cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
    
    # 尝试从缓存获取
    cached = await redis_client.get(cache_key)
    if cached:
        return SearchResult.model_validate_json(cached)
    
    # 执行搜索
    result = await search_tool.execute(SearchQuery(query=query))
    
    # 缓存结果（24小时）
    await redis_client.setex(
        cache_key,
        86400,  # 24 hours
        result.model_dump_json()
    )
    
    return result
```

## 监控和日志

### 关键日志事件

- `web_search_mcp_start`: MCP 搜索开始
- `web_search_mcp_success`: MCP 搜索成功
- `web_search_mcp_failed`: MCP 搜索失败
- `web_search_fallback_to_duckduckgo`: 回退到 DuckDuckGo
- `resource_recommender_fallback_to_traditional_search`: 回退到传统搜索

### 查看日志

```bash
# 实时查看日志
tail -f logs/app.log | grep "web_search"

# 查看 MCP 相关日志
tail -f logs/app.log | grep "mcp"
```

## 参考资料

- [Tavily 官方文档](https://docs.tavily.com/)
- [Tavily MCP 服务器文档](https://docs.tavily.com/documentation/mcp)
- [OpenAI MCP 集成指南](https://platform.openai.com/docs/)
- [项目架构文档](../architecture.md)

## 常见问题

### Q: MCP 和传统方式有什么区别？

**A**: 
- **MCP 方式**: 通过 OpenAI 的 MCP 协议调用 Tavily，可以利用 LLM 的语言理解能力优化搜索查询和结果解析
- **传统方式**: 直接调用 Tavily API，速度更快但功能相对简单

### Q: 如果我只配置了 Tavily API Key，系统还能工作吗？

**A**: 可以！系统会自动使用传统搜索方式。MCP 是可选的增强功能。

### Q: DuckDuckGo 备选什么时候会被使用？

**A**: 
1. Tavily API 不可用时
2. 配置了 `USE_DUCKDUCKGO_FALLBACK=true`
3. 主搜索方式失败时

### Q: 如何禁用 MCP 搜索？

**A**: 不配置 `RECOMMENDER_API_KEY` 即可。系统会自动回退到传统搜索方式。

## 更新日志

### v1.0.0 (2024-12-08)
- ✅ 实现 Tavily MCP 集成
- ✅ 创建连通性测试脚本
- ✅ 添加自动回退机制
- ✅ 完善错误处理和日志
- ✅ 编写配置文档

## 支持

如有问题，请：
1. 查看本文档的故障排查部分
2. 运行测试脚本诊断问题
3. 查看应用日志
4. 提交 Issue 到项目仓库

