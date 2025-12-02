# Concept详情页 Quiz & Resources 实现文档

## 概述

本文档描述了如何实现concept详情页面展示quiz（测验）和resources（学习资源）的功能。

## 数据流

```
数据库 (PostgreSQL)
  ├── roadmap_metadata.framework_data (包含 concept.quiz_id 和 concept.resources_id)
  ├── quiz_metadata (测验数据)
  └── resource_recommendation_metadata (资源推荐数据)
        ↓
后端 API (FastAPI)
  ├── GET /roadmaps/{roadmap_id}/concepts/{concept_id}/quiz
  └── GET /roadmaps/{roadmap_id}/concepts/{concept_id}/resources
        ↓
前端 (Next.js)
  └── /app/roadmap/[id]/learn/[conceptId]/page.tsx
```

## 后端实现

### 1. 数据库模型

位置：`backend/app/models/database.py`

#### QuizMetadata 表
```python
class QuizMetadata(SQLModel, table=True):
    quiz_id: str              # 主键，UUID格式
    concept_id: str           # 概念ID（索引）
    roadmap_id: str           # 路线图ID（外键）
    questions: list           # JSON格式的题目列表
    total_questions: int      # 总题数
    easy_count: int          # 简单题数量
    medium_count: int        # 中等题数量
    hard_count: int          # 困难题数量
    generated_at: datetime   # 生成时间
```

#### ResourceRecommendationMetadata 表
```python
class ResourceRecommendationMetadata(SQLModel, table=True):
    id: str                   # 主键，UUID格式
    concept_id: str           # 概念ID（索引）
    roadmap_id: str           # 路线图ID（外键）
    resources: list           # JSON格式的资源列表
    resources_count: int      # 资源数量
    search_queries_used: list # 搜索查询记录
    generated_at: datetime    # 生成时间
```

### 2. Repository方法

位置：`backend/app/db/repositories/roadmap_repo.py`

```python
async def get_quiz_by_concept(
    self,
    concept_id: str,
    roadmap_id: str,
) -> Optional[QuizMetadata]:
    """获取指定概念的测验"""

async def get_resources_by_concept(
    self,
    concept_id: str,
    roadmap_id: str,
) -> Optional[ResourceRecommendationMetadata]:
    """获取指定概念的资源推荐"""
```

### 3. API端点

位置：`backend/app/api/v1/roadmap.py`

#### 获取Quiz
```python
@router.get("/{roadmap_id}/concepts/{concept_id}/quiz")
async def get_concept_quiz(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的测验
    
    返回格式：
    {
        "roadmap_id": "rm-xxx",
        "concept_id": "c1",
        "quiz_id": "quiz-xxx",
        "questions": [
            {
                "question_id": "q1",
                "question_type": "single_choice",
                "question": "题目内容",
                "options": ["选项A", "选项B", "选项C"],
                "correct_answer": [1],
                "explanation": "答案解析",
                "difficulty": "medium"
            }
        ],
        "total_questions": 5,
        "easy_count": 1,
        "medium_count": 3,
        "hard_count": 1,
        "generated_at": "2024-01-01T00:00:00"
    }
    """
```

#### 获取Resources
```python
@router.get("/{roadmap_id}/concepts/{concept_id}/resources")
async def get_concept_resources(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的学习资源
    
    返回格式：
    {
        "roadmap_id": "rm-xxx",
        "concept_id": "c1",
        "resources_id": "res-xxx",
        "resources": [
            {
                "title": "资源标题",
                "url": "https://example.com",
                "type": "article",
                "description": "资源描述",
                "relevance_score": 0.95
            }
        ],
        "resources_count": 3,
        "search_queries_used": ["React hooks", "useState tutorial"],
        "generated_at": "2024-01-01T00:00:00"
    }
    """
```

## 前端实现

### 1. API客户端

位置：`frontend-next/lib/api/endpoints.ts`

```typescript
// 获取Quiz
export async function getConceptQuiz(
  roadmapId: string,
  conceptId: string
): Promise<QuizResponse>

// 获取Resources
export async function getConceptResources(
  roadmapId: string,
  conceptId: string
): Promise<ResourcesResponse>
```

### 2. 页面组件

位置：`frontend-next/app/app/roadmap/[id]/learn/[conceptId]/page.tsx`

#### 主要功能

1. **数据获取**：在`useEffect`中并行获取tutorial、quiz和resources数据
2. **加载状态**：显示加载动画
3. **错误处理**：处理API错误并显示友好提示
4. **空状态**：当quiz或resources不存在时显示占位提示

#### 关键代码片段

```typescript
// 数据状态
const [quiz, setQuiz] = useState<QuizResponse | null>(null);
const [resources, setResources] = useState<ResourcesResponse | null>(null);
const [loading, setLoading] = useState(true);

// 数据获取
useEffect(() => {
  const fetchData = async () => {
    try {
      // 获取路线图找到concept
      const roadmapData = await getRoadmap(roadmapId);
      
      // 获取quiz
      const quizData = await getConceptQuiz(roadmapId, conceptId);
      setQuiz(quizData);
      
      // 获取resources
      const resourcesData = await getConceptResources(roadmapId, conceptId);
      setResources(resourcesData);
    } catch (err) {
      console.error('Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  };
  
  fetchData();
}, [roadmapId, conceptId]);
```

#### UI展示

**Quiz Tab**：
- 显示题目列表，每题包含：难度标签、选项、答案解析
- 支持答题、提交、查看结果
- 空状态提示"暂无测验"

**Resources Tab**：
- 显示资源卡片列表
- 每个资源包含：标题、类型、描述、相关度、外部链接
- 空状态提示"暂无学习资源"

## 测试指南

### 1. 后端API测试

使用提供的测试脚本：

```bash
cd backend

# 测试指定concept的quiz和resources
uv run python scripts/test_concept_details_api.py <roadmap_id> <concept_id>

# 例如：
uv run python scripts/test_concept_details_api.py rm-abc123 concept-html-basics
```

### 2. 前端测试

1. 启动后端服务：
```bash
cd backend
./scripts/start_dev.sh
```

2. 启动前端服务：
```bash
cd frontend-next
npm run dev
```

3. 访问concept详情页：
```
http://localhost:3000/app/roadmap/{roadmap_id}/learn/{concept_id}
```

4. 测试场景：
   - ✅ 有quiz和resources的concept
   - ✅ 只有quiz的concept
   - ✅ 只有resources的concept
   - ✅ 都没有的concept（显示空状态）

### 3. 数据准备

如果数据库中没有quiz和resources数据，可以通过以下方式生成：

```python
# 使用完整流式生成（包含tutorial、quiz、resources）
cd backend
uv run python -c "
import asyncio
from app.api.v1.roadmap import generate_full_roadmap_stream
# ... 调用API生成数据
"
```

或者使用提供的生成脚本：
```bash
cd backend
uv run python scripts/generate_tutorials_for_roadmap.py <roadmap_id>
```

## 数据关系说明

### Concept在framework_data中的结构

```json
{
  "concept_id": "c1",
  "name": "HTML Structure",
  "quiz_id": "quiz-xxx",           // 指向 quiz_metadata 表
  "quiz_status": "completed",
  "resources_id": "res-xxx",       // 指向 resource_recommendation_metadata 表
  "resources_status": "completed",
  "resources_count": 3
}
```

### Quiz数据结构

```json
{
  "quiz_id": "quiz-xxx",
  "concept_id": "c1",
  "questions": [
    {
      "question_id": "q1",
      "question_type": "single_choice",
      "question": "What is HTML?",
      "options": ["A", "B", "C", "D"],
      "correct_answer": [0],
      "explanation": "HTML stands for...",
      "difficulty": "easy"
    }
  ],
  "total_questions": 5,
  "easy_count": 2,
  "medium_count": 2,
  "hard_count": 1
}
```

### Resources数据结构

```json
{
  "id": "res-xxx",
  "concept_id": "c1",
  "resources": [
    {
      "title": "MDN Web Docs",
      "url": "https://developer.mozilla.org/",
      "type": "documentation",
      "description": "Complete HTML reference",
      "relevance_score": 0.98
    }
  ],
  "resources_count": 3,
  "search_queries_used": ["HTML tutorial", "HTML basics"]
}
```

## API错误处理

### 常见错误

1. **404 Not Found**
   - 原因：concept没有生成quiz或resources
   - 前端处理：显示空状态提示

2. **500 Internal Server Error**
   - 原因：数据库查询失败或数据格式错误
   - 前端处理：显示错误提示，建议刷新

3. **Network Error**
   - 原因：后端服务未启动或网络问题
   - 前端处理：显示连接失败提示

## 性能优化建议

1. **并行请求**：tutorial、quiz、resources使用`Promise.all`并行获取
2. **缓存策略**：考虑使用SWR或React Query缓存数据
3. **分页加载**：如果resources很多，考虑分页或虚拟滚动
4. **预加载**：在roadmap概览页预加载常用concept数据

## 未来扩展

1. **Quiz功能增强**
   - 保存答题记录
   - 显示历史成绩
   - 支持多种题型（填空题、简答题等）

2. **Resources功能增强**
   - 用户评分和评论
   - 个性化推荐
   - 资源收藏功能

3. **实时更新**
   - WebSocket推送新生成的quiz和resources
   - 实时显示生成进度

## 故障排查

### 问题：前端显示"暂无测验"

1. 检查后端API是否正常：
```bash
curl http://localhost:8000/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz
```

2. 检查数据库是否有数据：
```sql
SELECT * FROM quiz_metadata WHERE concept_id = 'xxx' AND roadmap_id = 'xxx';
```

3. 检查浏览器控制台是否有错误

### 问题：Resources显示不完整

1. 检查返回的JSON格式是否正确
2. 检查resources数组是否为空
3. 检查相关度分数是否在0-1之间

## 总结

本次实现完成了以下功能：

✅ 后端API端点（已存在，验证可用）
✅ 前端数据获取和展示
✅ 错误处理和空状态展示
✅ 测试脚本和文档

现在concept详情页可以完整展示tutorial、quiz和resources三部分内容，为用户提供完整的学习体验。

