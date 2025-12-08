# Tavily API 高级参数集成

**日期**: 2025-12-08  
**状态**: ✅ 已恢复高级参数  
**调用方式**: 按照官方示例使用同步 TavilyClient  

---

## ✅ 最终方案

按照官方示例调用 Tavily API，支持所有高级参数：

```python
from tavily import TavilyClient

client = TavilyClient(api_key=settings.TAVILY_API_KEY)
response = client.search(
    query="langgraph教程",
    search_depth="advanced",  # 高级搜索
    max_results=5,            # 结果数量
    time_range="year",        # 时间筛选
    include_domains=["github.com"],  # 域名筛选
)
```

---

## 📊 支持的参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `query` | string | 搜索查询字符串（必需） |
| `max_results` | int | 最大结果数量（默认 5） |
| `search_depth` | enum | basic/advanced（默认 advanced） |
| `time_range` | enum | day/week/month/year（可选） |
| `include_domains` | array | 优先搜索的域名列表（可选） |
| `exclude_domains` | array | 排除的域名列表（可选） |

---

## 🔧 关键修改

### 1. 使用同步 TavilyClient

**文件**: `backend/app/tools/search/tavily_api_search.py`

```python
from tavily import TavilyClient  # 使用同步客户端

client = TavilyClient(api_key=self.api_key)

# 使用 asyncio.to_thread 包装同步调用
result = await asyncio.to_thread(client.search, **search_kwargs)
```

### 2. 工具定义包含所有高级参数

**文件**: `backend/app/agents/resource_recommender.py`

```python
{
    "name": "web_search",
    "parameters": {
        "properties": {
            "query": {...},
            "max_results": {...},
            "time_range": {...},        # 新增
            "search_depth": {...},      # 新增
            "include_domains": {...},   # 新增
            "exclude_domains": {...},   # 新增
        }
    }
}
```

### 3. SearchQuery 模型支持高级参数

**文件**: `backend/app/models/domain.py`

```python
class SearchQuery(BaseModel):
    query: str
    max_results: int = 5
    search_depth: Literal["basic", "advanced"] = "advanced"
    time_range: Optional[Literal["day", "week", "month", "year"]] = None
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
```

---

## 🧪 测试验证

**运行测试**：
```bash
cd backend
python3 scripts/test_tavily_sdk_integration.py
```

**测试内容**：
1. ✅ Tavily SDK 高级搜索（search_depth=advanced）
2. ✅ 时间筛选功能（time_range=year）
3. ✅ 域名筛选功能（include_domains）
4. ✅ 工具定义检查
5. ✅ ResourceRecommender Function Calling

---

## 📝 使用示例

### 示例 1：搜索最新教程

```json
{
  "name": "web_search",
  "arguments": {
    "query": "React 18 新特性",
    "max_results": 5,
    "search_depth": "advanced",
    "time_range": "year"
  }
}
```

### 示例 2：优先搜索 GitHub

```json
{
  "name": "web_search",
  "arguments": {
    "query": "langgraph教程",
    "include_domains": ["github.com"]
  }
}
```

---

## ✅ 总结

- ✅ 按照官方示例使用同步 TavilyClient
- ✅ 支持所有高级参数（search_depth, time_range, include_domains, exclude_domains）
- ✅ Function Calling 正确实现
- ✅ 已通过测试验证
