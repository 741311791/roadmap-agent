# ResourceRecommender 资源推荐问题诊断总结

## 🎯 用户反馈的问题

**问题描述**: 推荐的很多资源链接都是404页面，明显已经过时很久了

## 🔍 诊断结果

### 1. 现有实现确认

✅ **好消息**: 系统**已经集成**了互联网搜索功能！

- **搜索工具位置**: `backend/app/tools/search/web_search.py`
- **支持的搜索引擎**:
  1. **Tavily API** (主要) - 高质量搜索，支持时间筛选
  2. **DuckDuckGo** (备选) - 免费，无需API Key

- **调用方式**: ResourceRecommenderAgent 通过 LLM 的 Function Calling 机制调用 `web_search` 工具

```python
# 工具调用流程
ResourceRecommenderAgent.recommend()
    ↓
LLM 决定调用 web_search 工具
    ↓
WebSearchTool.execute(SearchQuery)
    ↓
优先使用 Tavily API
    ↓ (失败时)
回退到 DuckDuckGo
    ↓
返回搜索结果给 LLM
    ↓
LLM 基于搜索结果生成资源推荐
```

### 2. 发现的关键问题

#### ❌ 问题1: 缺少 URL 有效性验证
- 搜索引擎返回的结果**未经验证**就直接推荐给用户
- LLM 可能"幻觉"生成不存在的URL
- 无法过滤404、失效或重定向的链接

#### ❌ 问题2: 缺少资源时效性筛选
- Tavily API 支持 `days` 参数限制搜索时间范围，**但未使用**
- DuckDuckGo 不提供发布日期，无法判断资源新旧
- LLM Prompt 中缺少明确的"避免推荐过时资源"指令

#### ❌ 问题3: Tavily API 可能未配置
- 默认配置: `TAVILY_API_KEY=None`
- 如果未配置，会回退到 DuckDuckGo（质量可能较低）

#### ⚠️  问题4: 搜索结果质量依赖 LLM 判断
- LLM 只能看到标题和摘要(snippet)，未实际访问URL内容
- 可能误判资源质量

## 🔧 解决方案

### 方案1: 添加URL有效性验证 ⭐ **推荐优先实施**

**实现位置**: `backend/app/agents/resource_recommender.py`

```python
async def _verify_urls(self, resources: List[Resource]) -> List[Resource]:
    """验证资源URL的有效性，过滤404链接"""
    verified_resources = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []
        for resource in resources:
            async def check_url(r: Resource):
                try:
                    response = await client.head(r.url, follow_redirects=True)
                    if response.status_code == 200:
                        r.url = str(response.url)  # 更新为最终URL
                        return r
                except Exception as e:
                    logger.warning("url_invalid", url=r.url, error=str(e))
                return None
            
            tasks.append(check_url(resource))
        
        results = await asyncio.gather(*tasks)
        verified_resources = [r for r in results if r is not None]
    
    return verified_resources

async def recommend(self, concept, context, user_preferences):
    # ... 现有代码 ...
    
    # 构建 Resource 列表
    resources = [...]
    
    # 🆕 验证URL有效性
    resources = await self._verify_urls(resources)
    
    # 构建输出
    result = ResourceRecommendationOutput(...)
    return result
```

**优势**:
- 有效过滤404/失效链接
- 自动处理重定向
- 实现简单，侵入性小

### 方案2: 启用 Tavily 时间筛选

**实现位置**: `backend/app/tools/search/web_search.py`

```python
async def _search_with_tavily(self, input_data: SearchQuery) -> SearchResult:
    response = await client.post(
        f"{self.base_url}/search",
        json={
            "api_key": self.api_key,
            "query": input_data.query,
            "search_depth": "advanced",  # 改为 advanced
            "max_results": input_data.max_results,
            "days": 730,  # 🆕 只搜索最近2年内的内容
        },
        ...
    )
```

**配置检查**:
```bash
# 检查是否配置了 Tavily API Key
grep TAVILY_API_KEY backend/.env

# 如果没有，请注册并配置:
# https://tavily.com/
```

### 方案3: 增强 Prompt

**实现位置**: `backend/prompts/resource_recommender.j2`

添加以下内容:

```jinja2
[3. Constraints & Rules]
工作规范：
...
8. **优先推荐近期发布的资源（最好是最近1-2年内）** 🆕
9. **严格避免推荐以下类型的资源**: 🆕
   - ❌ 2020年之前的技术文章（除非是经典文档）
   - ❌ 已失效的第三方网站
   - ❌ 明显过时的技术栈教程
   - ❌ 内容不完整或质量低下的资源

[4. Output Format]
{
  "resources": [
    {
      "title": "...",
      "url": "...",
      "type": "...",
      "description": "...",
      "relevance_score": 0.95,
      "confidence_score": 0.9,  // 🆕 资源可信度 (0-1)
      "published_date": "2024-01-15",  // 🆕 发布日期 (如有)
      "language": "zh"
    }
  ]
}
```

## 📊 实施优先级

| 方案 | 优先级 | 难度 | 效果 | 依赖 |
|------|--------|------|------|------|
| 方案1: URL验证 | 🔴 最高 | 低 | 显著减少404 | 无 |
| 方案2: Tavily时间筛选 | 🟡 高 | 低 | 减少过时资源 | Tavily API |
| 方案3: 增强Prompt | 🟡 高 | 中 | 提升整体质量 | 无 |

## 🚀 快速修复步骤

### 第1步: 检查 Tavily API 配置 (5分钟)

```bash
cd backend
grep TAVILY_API_KEY .env
```

如果未配置或值为 `your_tavily_api_key_here`:
1. 访问 https://tavily.com/ 注册账号
2. 获取 API Key
3. 更新 `.env` 文件:
   ```
   TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxx
   ```

### 第2步: 测试当前质量 (10分钟)

```bash
cd backend
python scripts/test_resource_quality.py
```

这个脚本会:
- 推荐3个不同概念的资源
- 验证每个URL的有效性
- 生成质量报告

### 第3步: 实施URL验证 (30分钟)

修改 `backend/app/agents/resource_recommender.py`:
1. 添加 `_verify_urls()` 方法
2. 在 `recommend()` 方法中调用验证
3. 记录验证失败的URL到日志

### 第4步: 启用时间筛选 (15分钟)

修改 `backend/app/tools/search/web_search.py`:
1. 在 `_search_with_tavily()` 中添加 `days: 730` 参数
2. 将 `search_depth` 改为 `advanced`

### 第5步: 增强Prompt (20分钟)

修改 `backend/prompts/resource_recommender.j2`:
1. 添加时效性要求
2. 添加"避免推荐的资源类型"清单
3. 添加 `confidence_score` 和 `published_date` 字段

### 第6步: 重新测试 (10分钟)

```bash
python scripts/test_resource_quality.py
```

对比修改前后的URL有效率变化。

## 📈 预期效果

### 修改前 (预估)
- URL有效率: < 70%
- 平均资源发布时间: > 2年前
- 用户满意度: < 70%

### 修改后 (目标)
- URL有效率: > 95%
- 平均资源发布时间: < 1年前
- 用户满意度: > 85%

## 📚 相关文件

1. **详细分析报告**: `RESOURCE_RECOMMENDER_ANALYSIS.md`
2. **测试脚本**: `backend/scripts/test_resource_quality.py`
3. **核心实现**: 
   - `backend/app/agents/resource_recommender.py`
   - `backend/app/tools/search/web_search.py`
   - `backend/prompts/resource_recommender.j2`

## 💡 后续优化建议

1. **添加URL验证缓存** (使用Redis，避免重复验证)
2. **实施资源质量监控** (定期检查推荐资源的有效性)
3. **收集用户反馈** (让用户标记失效资源)
4. **优化搜索查询** (根据概念类型定制搜索策略)

---

**诊断时间**: 2025-12-07  
**分析工具**: Cursor AI Code Analysis  
**项目**: Roadmap Agent

