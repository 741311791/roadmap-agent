# ResourceRecommender 重构实施方案

**创建时间**: 2025-12-08  
**目标**: 提升资源推荐的有效性和时效性，解决404链接和过时资源问题

---

## 📋 重构目标

1. ✅ 解决 Tavily API 432 错误（请求速率控制）
2. ✅ 实施 URL 有效性验证（过滤404链接）
3. ✅ 启用时间筛选（优先推荐近期资源）
4. ✅ 增强 Prompt（提升LLM判断能力）
5. ✅ 扩展数据模型（支持新字段）

---

## 🎯 实施步骤

### Phase 1: WebSearchTool 优化（请求速率控制 + 时间筛选）

**文件**: `backend/app/tools/search/web_search.py`

**修改内容**:

1. **添加请求速率限制**
   - 使用 `asyncio.Semaphore` 控制并发数
   - 添加请求间隔延迟
   - 避免触发 Tavily API 限流

2. **启用 Tavily 时间筛选**
   - 添加 `days: 730` 参数（最近2年）
   - 将 `search_depth` 改为 `advanced`
   - 提升搜索质量

3. **改进 DuckDuckGo 搜索**
   - 添加语言区域支持
   - 优化结果筛选

**代码清单**:
```python
class WebSearchTool:
    def __init__(self):
        # 🆕 添加速率限制
        self._search_semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 最小请求间隔500ms
    
    async def _rate_limited_request(self, coro):
        """带速率限制的请求"""
        async with self._search_semaphore:
            # 确保请求间隔
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._min_request_interval:
                await asyncio.sleep(self._min_request_interval - elapsed)
            
            result = await coro
            self._last_request_time = time.time()
            return result
    
    async def _search_with_tavily(self, input_data: SearchQuery):
        # 🆕 使用速率限制
        async def do_search():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": input_data.query,
                        "search_depth": "advanced",  # 🆕 改为 advanced
                        "max_results": input_data.max_results,
                        "days": 730,  # 🆕 只搜索最近2年
                        "include_answer": False,
                        "include_raw_content": False,
                        "include_images": False,
                    },
                    timeout=15.0,
                )
                return response
        
        response = await self._rate_limited_request(do_search())
        # ... 处理响应
```

---

### Phase 2: ResourceRecommenderAgent 增强（URL验证）

**文件**: `backend/app/agents/resource_recommender.py`

**修改内容**:

1. **添加 URL 验证方法**
   - 批量并发验证
   - 过滤404链接
   - 处理403/412（可能有效）
   - 更新重定向后的URL

2. **集成到推荐流程**
   - 在返回结果前验证
   - 记录验证日志
   - 保留至少3个有效资源

**代码清单**:
```python
class ResourceRecommenderAgent(BaseAgent):
    
    async def _verify_urls(
        self, 
        resources: List[Resource]
    ) -> List[Resource]:
        """
        批量验证资源URL的有效性
        
        策略:
        - 使用 HEAD 请求检查
        - 模拟浏览器 User-Agent
        - 并发验证提升速度
        - 保留200和403/412状态码的资源
        """
        verified_resources = []
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36"
        }
        
        async def verify_single(resource: Resource) -> Optional[Resource]:
            try:
                async with httpx.AsyncClient(
                    timeout=10.0, 
                    follow_redirects=True
                ) as client:
                    response = await client.head(resource.url, headers=headers)
                    
                    # 200: 完全有效
                    if response.status_code == 200:
                        resource.url = str(response.url)  # 更新为最终URL
                        logger.info(
                            "url_verified_success",
                            url=resource.url,
                            status=200
                        )
                        return resource
                    
                    # 403/412: 可能需要浏览器访问，但资源可能存在
                    elif response.status_code in [403, 412]:
                        logger.info(
                            "url_possibly_valid",
                            url=resource.url,
                            status=response.status_code
                        )
                        return resource  # 保留，但标记
                    
                    # 404/500+: 确认无效
                    else:
                        logger.warning(
                            "url_invalid",
                            url=resource.url,
                            status=response.status_code
                        )
                        return None
                        
            except Exception as e:
                logger.warning(
                    "url_verification_failed",
                    url=resource.url,
                    error=str(e)
                )
                return None
        
        # 并发验证所有URL
        tasks = [verify_single(r) for r in resources]
        results = await asyncio.gather(*tasks)
        
        verified_resources = [r for r in results if r is not None]
        
        logger.info(
            "url_verification_complete",
            total=len(resources),
            verified=len(verified_resources),
            filtered=len(resources) - len(verified_resources)
        )
        
        return verified_resources
    
    async def recommend(self, concept, context, user_preferences):
        # ... 现有代码 ...
        
        # 构建 Resource 列表
        resources = []
        for r in data.get("resources", []):
            resource = Resource(...)
            resources.append(resource)
        
        # 🆕 验证URL有效性
        logger.info(
            "resource_recommender_verifying_urls",
            concept_id=concept.concept_id,
            resources_count=len(resources)
        )
        
        resources = await self._verify_urls(resources)
        
        # 确保至少有3个资源
        if len(resources) < 3:
            logger.warning(
                "resource_recommender_insufficient_resources",
                concept_id=concept.concept_id,
                resources_count=len(resources)
            )
        
        # ... 构建输出 ...
```

---

### Phase 3: 数据模型扩展

**文件**: `backend/app/models/domain.py`

**修改内容**:

1. **扩展 Resource 模型**
   - 添加 `confidence_score` 字段（资源可信度）
   - 添加 `published_date` 字段（发布日期）
   - 添加 `language` 字段（已存在，确认使用）

**代码清单**:
```python
class Resource(BaseModel):
    """学习资源"""
    title: str = Field(..., description="资源标题")
    url: str = Field(..., description="资源链接")
    type: Literal["article", "video", "book", "course", "documentation", "tool"] = Field(
        ..., description="资源类型"
    )
    description: str = Field(..., description="资源简介")
    relevance_score: float = Field(..., ge=0, le=1, description="相关性评分")
    
    # 🆕 新增字段
    confidence_score: Optional[float] = Field(
        None, 
        ge=0, 
        le=1, 
        description="资源可信度评分（0-1）"
    )
    published_date: Optional[str] = Field(
        None, 
        description="资源发布日期（ISO格式）"
    )
    language: Optional[str] = Field(
        None, 
        description="资源语言代码（zh/en/ja等）"
    )
```

---

### Phase 4: Prompt 增强

**文件**: `backend/prompts/resource_recommender.j2`

**修改内容**:

1. **添加时效性要求**
2. **添加"避免推荐的资源类型"清单**
3. **要求输出新字段**
4. **添加资源可信度评估标准**

**修改位置**:

```jinja2
[3. Constraints & Rules]
工作规范：
1. 为给定的 Concept 搜索并推荐高质量的学习资源
2. 推荐资源应覆盖多种类型：文章、视频、书籍、在线课程、官方文档、工具
3. 根据用户的学习偏好（{{ user_preferences.content_preference | join(", ") }}）优先推荐对应类型的资源
4. 考虑用户当前水平（{{ user_preferences.current_level }}），确保资源难度适中
5. 每个资源必须包含：标题、URL、类型、简介、相关性评分
6. 相关性评分基于资源与概念的匹配程度（0-1，1 为最相关）
7. 推荐 5-10 个高质量资源，按相关性排序

🆕 8. **优先推荐近期发布的资源（最好是最近1-2年内）**
🆕 9. **为每个资源评估可信度（confidence_score: 0-1）**
🆕 10. **严格避免以下类型的资源**：
   - ❌ 2020年之前的技术文章（除非是经典文档如MDN）
   - ❌ 明显过时的教程（使用已弃用的API/方法）
   - ❌ 个人博客上质量低下或不完整的内容
   - ❌ 失效的第三方网站
   - ❌ 非官方的API文档（优先推荐官方文档）

🆕 **资源可信度评估标准**：
- 0.9-1.0: 官方文档、知名技术网站（MDN、React官网）、经过验证的教程
- 0.7-0.9: 高质量社区内容（掘金精华、知名博主）、知名教育平台课程
- 0.5-0.7: 一般质量的文章/视频
- <0.5: 不应推荐

[4. Output Format]
输出必须严格遵循以下 JSON 格式：

```json
{
  "concept_id": "{{ concept.concept_id }}",
  "resources": [
    {
      "title": "资源标题",
      "url": "https://example.com/resource",
      "type": "article|video|book|course|documentation|tool",
      "description": "资源简介（50-100字）",
      "relevance_score": 0.95,
      🆕 "confidence_score": 0.9,
      🆕 "published_date": "2024-01-15",
      "language": "zh|en"
    }
  ],
  "search_queries_used": ["查询1", "查询2"]
}
```

**字段说明**:
- `confidence_score`: 🆕 资源可信度（0-1），基于来源权威性、内容质量评估
- `published_date`: 🆕 资源发布日期（ISO格式，如 "2024-01-15"）。如果无法确定，填 null
- `language`: 资源内容的语言代码
```

---

## 📊 预期效果

### 改进前（当前状态）

| 指标 | 当前值 | 说明 |
|------|--------|------|
| URL有效率 | 37.5% | 仅200状态码 |
| 可能有效率 | 75% | 包含403/412 |
| 404失效率 | 25% | 确认无效 |
| 搜索引擎 | DuckDuckGo | Tavily失败回退 |
| 时间筛选 | ❌ 无 | 可能推荐过时资源 |

### 改进后（目标）

| 指标 | 目标值 | 改进措施 |
|------|--------|----------|
| URL有效率 | >95% | URL验证过滤 |
| 可能有效率 | 100% | 保留403/412 |
| 404失效率 | 0% | URL验证过滤 |
| 搜索引擎 | Tavily | 速率控制 |
| 时间筛选 | ✅ 2年内 | days参数 |
| 资源可信度 | >0.7 | Prompt增强 |

---

## 🚀 实施顺序

### Step 1: WebSearchTool 优化 ⏰ 30分钟
- 文件: `backend/app/tools/search/web_search.py`
- 添加速率控制
- 启用时间筛选
- 测试 Tavily API

### Step 2: 数据模型扩展 ⏰ 10分钟
- 文件: `backend/app/models/domain.py`
- 添加新字段到 Resource 模型
- 确保向后兼容

### Step 3: Prompt 增强 ⏰ 20分钟
- 文件: `backend/prompts/resource_recommender.j2`
- 添加时效性要求
- 添加可信度评估标准
- 更新输出格式

### Step 4: ResourceRecommenderAgent 增强 ⏰ 40分钟
- 文件: `backend/app/agents/resource_recommender.py`
- 添加 URL 验证方法
- 集成到推荐流程
- 处理新字段

### Step 5: 测试验证 ⏰ 20分钟
- 运行测试脚本
- 验证所有改进
- 检查日志输出

**总预计时间**: 2小时

---

## 📝 实施检查清单

- [ ] Step 1: WebSearchTool 速率控制
- [ ] Step 1: WebSearchTool 时间筛选
- [ ] Step 2: Resource 模型扩展
- [ ] Step 3: Prompt 时效性要求
- [ ] Step 3: Prompt 可信度评估
- [ ] Step 4: URL 验证方法
- [ ] Step 4: 集成验证流程
- [ ] Step 5: 运行测试脚本
- [ ] Step 5: 验证改进效果

---

**创建人**: Cursor AI  
**项目**: Roadmap Agent - ResourceRecommender Refactor

