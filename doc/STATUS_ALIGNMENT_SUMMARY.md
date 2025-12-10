# 状态枚举值对齐总结

## 问题描述

原问题：路线图刚开始生成 roadmap_id 后数据库中还没有 roadmap_metadata，页面跳转后返回 404 错误。

期望：即使路线图不存在，但检查到对应的 task_id 还在处理中时，不报错，而是展示加载状态（骨架图），并启动轮询。

## 修复内容

### 1. 后端修改

#### 1.1 添加数据库方法 (`backend/app/db/repositories/roadmap_repo.py`)

```python
async def get_active_task_by_roadmap_id(self, roadmap_id: str) -> Optional[RoadmapTask]:
    """
    通过 roadmap_id 获取活跃任务
    
    查询状态为 pending, processing, human_review_pending 的任务
    """
```

#### 1.2 修改 API 端点 (`backend/app/api/v1/roadmap.py`)

`GET /api/v1/roadmaps/{roadmap_id}` 行为变更：

**修改前:**
- roadmap_metadata 不存在 → 直接返回 404

**修改后:**
- roadmap_metadata 存在 → 返回完整路线图数据
- roadmap_metadata 不存在 + 有活跃任务 → 返回 `status: "processing"` 状态
- roadmap_metadata 不存在 + 无活跃任务 → 返回 404

返回格式（生成中状态）:
```json
{
  "status": "processing",
  "task_id": "xxx",
  "current_step": "intent_analysis",
  "message": "路线图正在生成中",
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

### 2. 前端修改 (`frontend-next/app/app/roadmap/[id]/page.tsx`)

#### 2.1 loadRoadmap 函数增强

检测 API 返回的 `status === "processing"` 状态：
- 自动设置轮询和生成状态
- 从 current_step 解析当前生成阶段
- 展示骨架图和阶段指示器

#### 2.2 加载状态展示优化

**生成中状态显示:**
- 阶段指示器（CompactPhaseIndicator）显示当前阶段
- 友好提示："路线图正在生成中，请稍候..."
- 骨架图（RoadmapSkeletonView）
- 加载动画

#### 2.3 轮询逻辑改进

在轮询任务状态时：
- 检测 roadmap_metadata 是否已创建
- 如果检测到已创建，立即加载完整路线图数据
- 自动计算生成统计信息
- 继续通过 WebSocket 接收实时更新

### 3. 状态枚举值统一

#### 3.1 任务状态 (Task Status)

**表:** `roadmap_tasks.status`

| 状态值 | 说明 |
|:---|:---|
| `pending` | 待处理 |
| `processing` | ✅ **处理中（统一使用此值）** |
| `human_review_pending` | 等待人工审核 |
| `completed` | 已完成 |
| `partial_failure` | 部分失败 |
| `failed` | 失败 |

> **注意:** 前后端统一使用 `processing` 而非 `generating`

#### 3.2 内容状态 (Content Status)

**表:** `tutorial_metadata.content_status`, `Concept` 字段

| 状态值 | 说明 |
|:---|:---|
| `pending` | 待生成 |
| `generating` | 生成中（前端实时显示，不存储到数据库） |
| `completed` | 已完成 |
| `failed` | 失败 |

#### 3.3 工作流步骤 (Workflow Steps)

**字段:** `roadmap_tasks.current_step`

| 步骤值 | 说明 | 阶段 |
|:---|:---|:---|
| `init` | 初始化 | 初始化 |
| `queued` | 已入队 | intent_analysis |
| `starting` | 启动中 | intent_analysis |
| `intent_analysis` | 需求分析 | intent_analysis |
| `curriculum_design` | 课程设计 | curriculum_design |
| `framework_generation` | 框架生成 | curriculum_design |
| `structure_validation` | 结构验证 | structure_validation |
| `human_review` | 人工审核 | human_review |
| `roadmap_edit` | 路线图修正 | human_review |
| `content_generation` | 内容生成 | content_generation |
| `tutorial_generation` | 教程生成 | content_generation |
| `resource_recommendation` | 资源推荐 | content_generation |
| `quiz_generation` | 测验生成 | content_generation |
| `finalizing` | 收尾中 | completed |
| `completed` | 已完成 | completed |
| `failed` | 失败 | completed |

#### 3.4 前端生成阶段 (Frontend Phases)

**类型:** `GenerationPhase` (TypeScript)

| 阶段值 | 标签 | 包含的后端步骤 |
|:---|:---|:---|
| `intent_analysis` | 需求分析 | `queued`, `starting`, `intent_analysis` |
| `curriculum_design` | 结构设计 | `curriculum_design`, `framework_generation` |
| `structure_validation` | 结构验证 | `structure_validation` |
| `human_review` | 人工审核 | `human_review`, `roadmap_edit` |
| `content_generation` | 内容生成 | `content_generation`, `tutorial_generation`, `quiz_generation`, `resource_recommendation` |
| `completed` | 完成 | `finalizing`, `completed`, `failed` |

### 4. 文档更新

所有状态和阶段枚举值已整理到 `backend/AGENT.md` 的"状态与阶段枚举定义"章节，包括：
- 任务状态枚举
- 内容状态枚举
- 工作流步骤枚举
- 前端生成阶段枚举
- 人工审核子状态
- 步骤到阶段映射规则
- 状态流转图

## 完整工作流程

1. 用户提交生成请求 → 获得 `roadmap_id` 和 `task_id`
2. 页面跳转到 `/roadmap/{roadmap_id}`
3. 前端调用 `GET /api/v1/roadmaps/{roadmap_id}`
4. **后端检查:**
   - ✅ roadmap_metadata 存在 → 返回完整路线图
   - ✅ 不存在 + 有活跃任务（status=`processing`） → 返回生成中状态
   - ❌ 都不存在 → 返回 404
5. **前端处理:**
   - 收到 `status: "processing"` → 展示骨架图 + 阶段指示器
   - 启动轮询任务状态（每 2 秒）
   - 检测到 roadmap_metadata 创建 → 立即加载并展示路线图
   - 继续通过 WebSocket 接收实时更新

## 关键修改点

✅ 状态值统一：全部使用 `processing` 而非 `generating`
✅ 后端 API 增加生成中状态检测
✅ 前端页面增加骨架图展示
✅ 前端轮询逻辑优化
✅ 文档完善（AGENT.md）

## 影响范围

- ✅ 后端: `roadmap_repo.py`, `roadmap.py`
- ✅ 前端: `app/roadmap/[id]/page.tsx`
- ✅ 文档: `backend/AGENT.md`

## 测试建议

1. 测试场景 1：快速生成
   - 提交请求后立即跳转
   - 验证显示骨架图和阶段指示器
   - 验证自动加载路线图

2. 测试场景 2：慢速生成
   - 提交请求后等待 10 秒再跳转
   - 验证根据当前步骤显示正确阶段
   - 验证实时更新

3. 测试场景 3：路线图不存在
   - 访问不存在的 roadmap_id
   - 验证返回 404 错误

4. 测试场景 4：已完成的路线图
   - 访问已完成的路线图
   - 验证正常显示完整数据

