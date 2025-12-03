# 路线图 ID 轮询架构

## 设计理念

**URL 纯净性第一** - 路线图详情页的 URL 应当简洁、语义化：`/app/roadmap/{roadmap_id}`

**roadmap_id 为中心** - 一个路线图可能关联多个任务（初始生成、修改、重试等），前端应基于 `roadmap_id` 查询当前活跃任务。

## 架构流程

### 1. 路线图生成流程

```
前端 (new page) → 后端 API
  ├─ POST /roadmaps/generate
  │   └─ 返回 task_id (UUID)
  │
  ├─ WebSocket 连接 (监听进度)
  │   ├─ intent_analysis → 生成 roadmap_id (语义化英文ID)
  │   ├─ 发送 roadmap_id 给前端
  │   └─ 前端跳转: /app/roadmap/{roadmap_id}
  │
  └─ 路线图详情页自动检测活跃任务
```

### 2. 路线图详情页加载流程

```
用户打开 /app/roadmap/{roadmap_id}
  │
  ├─ 加载路线图数据
  │   GET /roadmaps/{roadmap_id}
  │
  ├─ 查询活跃任务
  │   GET /roadmaps/{roadmap_id}/active-task
  │   └─ 返回:
  │       • has_active_task: boolean
  │       • task_id: string | null
  │       • status: 'processing' | 'human_review_pending' | ...
  │
  └─ 如果有活跃任务
      ├─ 启动轮询 (2秒间隔)
      │   GET /roadmaps/{task_id}/status
      │
      └─ 或启动 WebSocket (实时更新)
          ws://api/ws/{task_id}
```

### 3. 核心 API 端点

#### `GET /roadmaps/{roadmap_id}/active-task`

**用途**: 查询路线图当前是否有正在进行的任务

**返回**:
```json
{
  "has_active_task": true,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "current_step": "tutorial_generation",
  "created_at": "2025-12-03T10:00:00Z",
  "updated_at": "2025-12-03T10:05:30Z"
}
```

**活跃任务定义**: 状态为 `processing` 或 `human_review_pending` 的任务

#### `GET /roadmaps/{task_id}/status`

**用途**: 轮询任务状态

**返回**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "current_step": "tutorial_generation",
  "roadmap_id": "learn-react-typescript-a1b2c3d4",
  "created_at": "2025-12-03T10:00:00Z",
  "updated_at": "2025-12-03T10:05:30Z"
}
```

## roadmap_id 生成

### 时机

在 `_run_intent_analysis` 需求分析完成后生成

### 格式

`{学习目标关键词}-{技术关键词1}-{技术关键词2}-{8位UUID}`

### 示例

- `learn-react-typescript-a1b2c3d4`
- `master-python-django-postgresql-f5e8d9c2`
- `javascript-vue-nodejs-3a7b9f1e`

### 实现

```python
def _generate_semantic_roadmap_id(self, learning_goal: str, key_technologies: list[str]) -> str:
    goal_keywords = re.findall(r'\b\w+\b', learning_goal.lower())
    tech_keywords = [re.sub(r'[^a-z0-9]', '', tech.lower()) for tech in key_technologies]
    
    # 提取主要学习目标词
    main_goal_word = ""
    if "learn" in goal_keywords:
        main_goal_word = goal_keywords[goal_keywords.index("learn") + 1]
    if not main_goal_word and goal_keywords:
        main_goal_word = goal_keywords[0]
    
    # 组合关键词 (最多3个词)
    parts = []
    if main_goal_word:
        parts.append(main_goal_word)
    if tech_keywords:
        parts.extend(tech_keywords[:2])
    
    base_id = "-".join(parts) if parts else "roadmap"
    unique_suffix = uuid.uuid4().hex[:8]
    
    return f"{base_id}-{unique_suffix}"
```

## 前端状态管理

### 移除的全局状态

- ❌ `activeTaskId` - 不再需要全局追踪任务ID
- ❌ `activeGenerationPhase` - 改为页面级状态
- ❌ `isLiveGenerating` - 改为页面级状态

### 页面级状态 (roadmap/[id]/page.tsx)

```typescript
const [taskId, setTaskId] = useState<string | null>(null);
const [isPolling, setIsPolling] = useState(false);
const [isLiveGenerating, setIsLiveGenerating] = useState(false);
const [currentPhase, setCurrentPhase] = useState<GenerationPhase | null>(null);
```

## 优势

1. **URL 纯净** - 无需 URL 参数，更易分享和收藏
2. **解耦合** - roadmap 和 task 的关系清晰，一对多
3. **容错性强** - 用户刷新页面后自动恢复任务追踪
4. **语义化** - roadmap_id 有意义，便于调试和日志查看
5. **可扩展** - 支持多任务并发（修改、重试等）

## 注意事项

### 同一路线图的多个任务

当前实现中，`active-task` API 只返回最新的活跃任务。如果需要支持同一路线图的多个任务同时进行，需要：

1. 修改 `active-task` 返回任务列表
2. 前端支持多任务显示和切换
3. 数据库添加 `task_priority` 或 `task_type` 字段

### 历史任务查询

如需查询历史任务，可添加新端点：

```
GET /roadmaps/{roadmap_id}/tasks?status=completed&limit=10
```

### WebSocket vs 轮询

- **WebSocket**: 适合实时性要求高的场景（如正在生成）
- **轮询**: 适合检测任务启动和完成（2秒间隔足够）

当前实现：页面加载时用轮询检测，检测到活跃任务后可切换到 WebSocket。

