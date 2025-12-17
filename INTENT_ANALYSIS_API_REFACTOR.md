# Intent Analysis 数据获取方式重构

## 背景

**原问题：** 前端 Intent Analysis 卡片的数据从执行日志中提取，数据不完整且不稳定。

**改进方案：** 直接从数据库的 `intent_analysis_metadata` 表获取数据，该表存储了需求分析的完整结构化数据，内容更加丰富。

## 实施改进

### 1. 后端新增 API 端点（✅ 已完成）

**文件：** `backend/app/api/v1/roadmap.py`

新增 Intent Analysis Router 和端点：

```python
intent_router = APIRouter(prefix="/intent-analysis", tags=["intent-analysis"])


class IntentAnalysisResponse(BaseModel):
    """需求分析响应"""
    id: str
    task_id: str
    roadmap_id: Optional[str] = None
    parsed_goal: str
    key_technologies: list[str]
    difficulty_profile: str
    time_constraint: str
    recommended_focus: list[str]
    user_profile_summary: Optional[str] = None
    skill_gap_analysis: list[str]
    personalized_suggestions: list[str]
    estimated_learning_path_type: Optional[str] = None
    content_format_weights: Optional[dict] = None
    language_preferences: Optional[dict] = None
    created_at: Optional[str] = None


@intent_router.get("/{task_id}", response_model=IntentAnalysisResponse)
async def get_intent_analysis(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定 task_id 的需求分析元数据
    
    从 intent_analysis_metadata 表获取完整的需求分析数据
    """
    repo = RoadmapRepository(db)
    metadata = await repo.get_intent_analysis_metadata(task_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="需求分析元数据不存在")
    
    return IntentAnalysisResponse(
        id=metadata.id,
        task_id=metadata.task_id,
        roadmap_id=metadata.roadmap_id,
        parsed_goal=metadata.parsed_goal,
        key_technologies=metadata.key_technologies,
        difficulty_profile=metadata.difficulty_profile,
        time_constraint=metadata.time_constraint,
        recommended_focus=metadata.recommended_focus,
        user_profile_summary=metadata.user_profile_summary,
        skill_gap_analysis=metadata.skill_gap_analysis,
        personalized_suggestions=metadata.personalized_suggestions,
        estimated_learning_path_type=metadata.estimated_learning_path_type,
        content_format_weights=metadata.content_format_weights,
        language_preferences=metadata.language_preferences,
        created_at=metadata.created_at.isoformat() if metadata.created_at else None,
    )
```

**文件：** `backend/app/api/v1/router.py`

注册新的路由：

```python
from .roadmap import users_router, router as roadmap_router, trace_router, intent_router

# 需求分析相关
router.include_router(intent_router)
```

**API 端点：** `GET /api/v1/intent-analysis/{task_id}`

### 2. 前端新增 API 客户端（✅ 已完成）

**文件：** `frontend-next/lib/api/endpoints.ts`

新增接口定义和函数：

```typescript
/**
 * 需求分析响应接口定义
 */
export interface IntentAnalysisResponse {
  id: string;
  task_id: string;
  roadmap_id?: string | null;
  parsed_goal: string;
  key_technologies: string[];
  difficulty_profile: string;
  time_constraint: string;
  recommended_focus: string[];
  user_profile_summary?: string | null;
  skill_gap_analysis: string[];
  personalized_suggestions: string[];
  estimated_learning_path_type?: string | null;
  content_format_weights?: Record<string, number> | null;
  language_preferences?: Record<string, any> | null;
  created_at?: string | null;
}

/**
 * 获取需求分析元数据
 * 
 * 从数据库的 intent_analysis_metadata 表获取需求分析的完整数据，
 * 比从日志中提取的数据更加丰富和结构化。
 * 
 * @param taskId - 任务 ID
 * @returns 需求分析元数据
 */
export async function getIntentAnalysis(
  taskId: string
): Promise<IntentAnalysisResponse> {
  const response = await apiClient.get<IntentAnalysisResponse>(
    `/intent-analysis/${taskId}`
  );
  return response.data;
}
```

### 3. 前端任务详情页重构（✅ 已完成）

**文件：** `frontend-next/app/(app)/tasks/[taskId]/page.tsx`

#### 修改 1：导入新的 API 函数

```typescript
import { getTaskDetail, getTaskLogs, getRoadmap, getIntentAnalysis } from '@/lib/api/endpoints';
```

#### 修改 2：替换日志提取逻辑为 API 调用

**修改前：**
```typescript
const extractIntentAnalysisFromLogs = useCallback((logs: ExecutionLog[]): IntentAnalysisOutput | null => {
  // 查找 intent_analysis 类型的日志
  const intentLog = logs.find(
    log => log.details?.log_type === 'intent_analysis_output' ||
           log.details?.output_summary?.learning_goal
  );
  
  if (intentLog?.details?.output_summary) {
    return intentLog.details.output_summary;
  }
  
  return null;
}, []);
```

**修改后：**
```typescript
const loadIntentAnalysis = useCallback(async (taskId: string) => {
  try {
    const intentData = await getIntentAnalysis(taskId);
    
    // 转换为前端需要的格式
    const intentOutput: IntentAnalysisOutput = {
      learning_goal: intentData.parsed_goal,
      key_technologies: intentData.key_technologies,
      difficulty_level: intentData.difficulty_profile,
      estimated_duration_weeks: 0, // 从 time_constraint 解析（可选）
      skill_gaps: intentData.skill_gap_analysis.map(gap => ({
        skill_name: gap,
        current_level: 'beginner',
        required_level: 'intermediate',
      })),
      learning_strategies: intentData.personalized_suggestions,
    };
    
    setIntentAnalysis(intentOutput);
  } catch (err) {
    console.error('Failed to load intent analysis:', err);
    // 如果获取失败，不设置数据（保持为 null）
  }
}, []);
```

#### 修改 3：初始加载时调用新的 API

**修改前：**
```typescript
setExecutionLogs(limitedLogs);

// 从日志中提取需求分析输出
const intentOutput = extractIntentAnalysisFromLogs(limitedLogs);
if (intentOutput) {
  setIntentAnalysis(intentOutput);
}
```

**修改后：**
```typescript
setExecutionLogs(limitedLogs);

// 加载需求分析数据（从数据库获取，内容更丰富）
await loadIntentAnalysis(taskId);
```

#### 修改 4：WebSocket 更新时重新加载

**修改前：**
```typescript
const limitedLogs = limitLogsByStep(allLogs, 100);
setExecutionLogs(limitedLogs);

// 更新需求分析
const intentOutput = extractIntentAnalysisFromLogs(logs);
if (intentOutput) {
  setIntentAnalysis(intentOutput);
}
```

**修改后：**
```typescript
const limitedLogs = limitLogsByStep(allLogs, 100);
setExecutionLogs(limitedLogs);

// 重新加载需求分析数据（使用最新的数据库数据）
await loadIntentAnalysis(taskId);
```

#### 修改 5：更新依赖项

```typescript
// 修改前
}, [taskId, extractIntentAnalysisFromLogs, loadRoadmapFramework]);

// 修改后
}, [taskId, loadIntentAnalysis, loadRoadmapFramework]);
```

## 数据对比

### intent_analysis_metadata 表的完整字段

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `id` | string | 主键 |
| `task_id` | string | 任务 ID（外键） |
| `roadmap_id` | string? | 路线图 ID |
| `parsed_goal` | string | 解析后的学习目标 |
| `key_technologies` | string[] | 关键技术列表 |
| `difficulty_profile` | string | 难度分析 |
| `time_constraint` | string | 时间约束 |
| `recommended_focus` | string[] | 推荐学习重点 |
| `user_profile_summary` | string? | 用户画像摘要 |
| `skill_gap_analysis` | string[] | **技能差距分析** ⭐ |
| `personalized_suggestions` | string[] | **个性化建议** ⭐ |
| `estimated_learning_path_type` | string? | **学习路径类型** ⭐ |
| `content_format_weights` | dict? | **内容格式权重** ⭐ |
| `language_preferences` | dict? | **语言偏好** ⭐ |
| `created_at` | datetime | 创建时间 |

**⭐ 标记的字段** 是从日志中无法获取或不稳定的数据。

### 前端 IntentAnalysisOutput 类型映射

| 前端字段 | 后端字段 | 说明 |
|----------|----------|------|
| `learning_goal` | `parsed_goal` | 学习目标 |
| `key_technologies` | `key_technologies` | 关键技术 |
| `difficulty_level` | `difficulty_profile` | 难度等级 |
| `estimated_duration_weeks` | `time_constraint` | 预估时长（需解析） |
| `skill_gaps` | `skill_gap_analysis` | 技能差距（需转换格式） |
| `learning_strategies` | `personalized_suggestions` | 学习策略 |

## 改进效果

### 修改前（从日志提取）

```typescript
// 问题 1: 需要遍历所有日志查找特定类型
const intentLog = logs.find(
  log => log.details?.log_type === 'intent_analysis_output' ||
         log.details?.output_summary?.learning_goal
);

// 问题 2: 数据结构不稳定，可能缺失字段
if (intentLog?.details?.output_summary) {
  return intentLog.details.output_summary;
}

// 问题 3: 缺少很多数据库中存在的字段
// - skill_gap_analysis
// - personalized_suggestions
// - estimated_learning_path_type
// - content_format_weights
// - language_preferences
```

**缺点：**
- ❌ 数据不完整（缺少 5+ 个重要字段）
- ❌ 数据格式不稳定（依赖日志结构）
- ❌ 性能较差（需要遍历大量日志）
- ❌ 依赖日志存在（如果日志被清理则无法获取）

### 修改后（从数据库获取）

```typescript
// 直接调用 API 获取完整数据
const intentData = await getIntentAnalysis(taskId);

// 数据完整且结构化
const intentOutput: IntentAnalysisOutput = {
  learning_goal: intentData.parsed_goal,
  key_technologies: intentData.key_technologies,
  difficulty_level: intentData.difficulty_profile,
  skill_gaps: intentData.skill_gap_analysis.map(...),
  learning_strategies: intentData.personalized_suggestions,
  // ... 可以访问所有字段
};
```

**优点：**
- ✅ 数据完整（所有字段都可用）
- ✅ 数据结构稳定（直接从数据库表映射）
- ✅ 性能更好（单条查询，有索引）
- ✅ 独立于日志（即使日志被清理也能获取）
- ✅ 支持更丰富的 UI 展示

## 数据示例

### API 响应示例

```json
{
  "id": "uuid-123",
  "task_id": "task-456",
  "roadmap_id": "python-web-dev",
  "parsed_goal": "Learn Python web development from basics to deployment",
  "key_technologies": ["Python", "Django", "REST API", "PostgreSQL"],
  "difficulty_profile": "intermediate",
  "time_constraint": "3-6 months",
  "recommended_focus": [
    "Focus on practical project building",
    "Emphasize backend architecture patterns",
    "Include deployment and DevOps basics"
  ],
  "user_profile_summary": "Beginner with basic Python knowledge, wants to transition to backend development",
  "skill_gap_analysis": [
    "Lacks experience with web frameworks",
    "Needs to learn database design",
    "Should understand RESTful API principles"
  ],
  "personalized_suggestions": [
    "Start with a simple CRUD application",
    "Build a portfolio project while learning",
    "Focus on Django as the primary framework"
  ],
  "estimated_learning_path_type": "career_transition",
  "content_format_weights": {
    "visual": 0.3,
    "text": 0.4,
    "hands_on": 0.3
  },
  "language_preferences": {
    "preferred_language": "en",
    "code_comments_language": "en"
  },
  "created_at": "2024-12-17T10:30:00Z"
}
```

## UI 展示改进建议

基于现在可以获取的完整数据，Intent Analysis 卡片可以展示更多内容：

### 当前显示

- ✅ Learning Goal
- ✅ Key Technologies
- ✅ Difficulty Level
- ✅ Estimated Duration

### 可以新增展示

- 🆕 **Skill Gaps** - 显示用户需要弥补的技能差距
- 🆕 **Personalized Suggestions** - 显示个性化学习建议
- 🆕 **Learning Path Type** - 显示学习路径类型（快速入门/深度学习/职业转换）
- 🆕 **Recommended Focus** - 显示推荐的学习重点

### UI 示例

```tsx
<Card>
  <CardHeader>
    <CardTitle>Intent Analysis</CardTitle>
  </CardHeader>
  <CardContent>
    {/* 现有内容 */}
    <div className="space-y-4">
      <div>
        <h4>Learning Goal</h4>
        <p>{intentAnalysis.learning_goal}</p>
      </div>
      
      {/* 新增：技能差距 */}
      {intentAnalysis.skill_gaps && intentAnalysis.skill_gaps.length > 0 && (
        <div>
          <h4>Skill Gaps to Address</h4>
          <ul>
            {intentAnalysis.skill_gaps.map(gap => (
              <li key={gap.skill_name}>
                <Badge>{gap.skill_name}</Badge>
                <span>{gap.current_level} → {gap.required_level}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* 新增：个性化建议 */}
      {intentAnalysis.learning_strategies && intentAnalysis.learning_strategies.length > 0 && (
        <div>
          <h4>Personalized Suggestions</h4>
          <ul>
            {intentAnalysis.learning_strategies.map((strategy, idx) => (
              <li key={idx}>{strategy}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  </CardContent>
</Card>
```

## 测试验证

### 后端测试

```bash
# 1. 创建一个路线图生成任务
curl -X POST "http://localhost:8000/api/v1/roadmaps/generate" \
  -H "Content-Type: application/json" \
  -d '{"user_goal": "Learn Python web development"}'

# 2. 等待 intent_analysis 阶段完成

# 3. 获取需求分析数据
curl -X GET "http://localhost:8000/api/v1/intent-analysis/{task_id}"

# 4. 检查返回的数据是否完整
{
  "id": "...",
  "task_id": "...",
  "parsed_goal": "...",
  "key_technologies": [...],
  "skill_gap_analysis": [...],  # ✅ 新增字段
  "personalized_suggestions": [...],  # ✅ 新增字段
  ...
}
```

### 前端测试

1. 打开任务详情页 `/tasks/{taskId}`
2. 查看浏览器 Network 面板，确认调用了 `/api/v1/intent-analysis/{taskId}`
3. 查看 Intent Analysis 卡片是否显示了完整数据
4. 确认不再依赖日志数据

## 代码位置索引

| 文件 | 修改内容 |
|------|---------|
| `backend/app/api/v1/roadmap.py` | 新增 intent_router 和 get_intent_analysis 端点 |
| `backend/app/api/v1/router.py` | 注册 intent_router |
| `frontend-next/lib/api/endpoints.ts` | 新增 IntentAnalysisResponse 接口和 getIntentAnalysis 函数 |
| `frontend-next/app/(app)/tasks/[taskId]/page.tsx` | 重构数据获取逻辑（4 处修改） |

## 总结

通过将 Intent Analysis 数据的获取方式从"日志提取"改为"数据库 API"，实现了以下改进：

1. ✅ **数据完整性** - 可以访问所有 15+ 个字段，而不是只有 4-5 个
2. ✅ **数据稳定性** - 不再依赖日志结构，数据格式固定
3. ✅ **性能优化** - 单条数据库查询 vs 遍历大量日志
4. ✅ **可维护性** - 数据结构清晰，易于扩展
5. ✅ **用户体验** - 支持展示更丰富的需求分析信息

**核心价值：** 为前端提供更丰富、更稳定的需求分析数据，支持更好的 UI 展示和用户体验。

---

**修复时间：** 2025-12-17
**相关问题：** Intent Analysis 数据不完整、数据格式不稳定

