# Intent Analysis 显示问题修复

## 问题描述

**症状**：
- 后端 `intent_analysis` 已完成并成功入库（日志显示 `intent_id=5fb77816-6b69-4aff-ad41-db7efc76d9c5`）
- 前端任务详情页的 "Learning Path Overview" 模块没有渲染 Intent Analysis 内容
- 页面显示为空白，用户无法看到需求分析结果

**影响**：
- 用户体验差：无法查看AI对学习目标的理解
- 数据已存在但未展示，造成信息孤岛

## 根因分析

### 1. 数据库层面（✅ 正常）

**验证**：直接调用后端 API 测试
```bash
curl "http://localhost:8000/api/v1/roadmaps/learn-python-basics-5bcc7f49/intent-analysis"
```

**结果**：
```json
{
  "code": 200,
  "data": {
    "available": true,
    "intent_id": "5fb77816-6b69-4aff-ad41-db7efc76d9c5",
    "roadmap_id": "learn-python-basics-5bcc7f49",
    "parsed_goal": "学习Python编程语言的基础知识...",
    "key_technologies": ["Python", "Basic Syntax", ...]
  }
}
```

**结论**：✅ 后端数据已正确保存且可查询

### 2. 事务提交（✅ 正常）

**验证**：检查 `get_celery_session()` 实现

```python
# backend/app/db/celery_session.py:164
@asynccontextmanager
async def get_celery_session() -> AsyncGenerator[AsyncSession, None]:
    async with celery_session_maker.begin() as session:
        yield session
        # ✅ SQLAlchemy 自动处理 commit/rollback/close
```

**结论**：✅ 使用 `.begin()` 方法，事务会自动 commit

### 3. 前端数据加载（❌ 问题所在）

**问题代码**：
```typescript
// frontend-next/app/(app)/tasks/[taskId]/page.tsx:570-584
const handleStatus = (event: any) => {
  console.log('[TaskDetail] Status update:', event);
  if (event.roadmap_id) {
    setTaskInfo((prev) => prev ? { ...prev, roadmap_id: event.roadmap_id } : null);
    roadmapIdRef.current = event.roadmap_id;
    // ❌ 没有立即加载 intent_analysis 数据
  }
};
```

**问题原因**：
1. 在 `intent_analysis` 完成后，后端通过 WebSocket 发送 `status` 事件（包含 `roadmap_id`）
2. 前端 `handleStatus` 回调更新了 `roadmapIdRef.current`
3. **但没有立即调用 `loadIntentAnalysis`**，导致数据未加载
4. 虽然 `handleProgress` 回调（第 634-638 行）会在节点完成时重新加载数据，但可能存在时序问题

## 解决方案

### 修复内容

**1. 在 `handleStatus` 回调中添加立即加载逻辑**

```typescript
const handleStatus = (event: any) => {
  console.log('[TaskDetail] Status update:', event);
  if (event.current_step) {
    const displayStep = mapToDisplayStep(event.current_step);
    setTaskInfo((prev) => prev ? { ...prev, current_step: displayStep } : null);
  }
  if (event.status) {
    setTaskInfo((prev) => prev ? { ...prev, status: event.status } : null);
  }
  if (event.roadmap_id) {
    setTaskInfo((prev) => prev ? { ...prev, roadmap_id: event.roadmap_id } : null);
    roadmapIdRef.current = event.roadmap_id;
    
    // ✅ 修复：当收到 roadmap_id 时，立即加载 intent_analysis 数据
    // 这确保在 intent_analysis 完成后能立即显示数据
    loadIntentAnalysis(event.roadmap_id).catch((err) => {
      console.error('[TaskDetail] Failed to load intent analysis after roadmap_id update:', err);
    });
  }
};
```

**2. 添加调试日志**

```typescript
// 重新加载需求分析数据（使用最新的数据库数据）
const currentRoadmapId = roadmapIdRef.current;
if (currentRoadmapId) {
  console.log('[TaskDetail] Reloading intent analysis after node completion:', {
    step: event.step,
    roadmap_id: currentRoadmapId,
  });
  await loadIntentAnalysis(currentRoadmapId);
} else {
  console.warn('[TaskDetail] Cannot reload intent analysis: roadmap_id is null', {
    step: event.step,
  });
}
```

### 修复原理

**执行流程**：
1. 后端 `intent_analysis` 节点完成
2. 后端保存数据到数据库（事务自动 commit）
3. 后端通过 WebSocket 发送 `status` 事件（包含 `roadmap_id`）
4. 前端 `handleStatus` 回调接收事件
5. **✅ 立即调用 `loadIntentAnalysis(roadmap_id)`**
6. 前端调用 API `/roadmaps/{roadmap_id}/intent-analysis`
7. 后端返回完整的 intent_analysis 数据
8. 前端设置 `intentAnalysis` 状态
9. UI 组件 `CoreDisplayArea` 检测到数据变化，渲染 "Learning Path Overview"

**关键改进**：
- **时机提前**：从"节点完成时重新加载"改为"收到 roadmap_id 时立即加载"
- **避免时序问题**：确保在数据可用时第一时间获取

## 验证步骤

### 1. 启动前端开发服务器
```bash
cd frontend-next
npm run dev
```

### 2. 创建新任务并观察日志

**预期日志输出**：
```
[TaskDetail] Status update: { roadmap_id: "learn-python-basics-xxxx", ... }
[TaskDetail] Intent analysis loaded successfully: { roadmap_id: "...", has_data: true, ... }
[TaskDetail] Reloading intent analysis after node completion: { step: "intent_analysis", ... }
```

### 3. 检查 UI 是否正常显示

**预期效果**：
- ✅ "Learning Path Overview" 标题下显示 Intent Analysis 卡片
- ✅ 卡片包含：学习目标、关键技术栈、预计时长、难度等级
- ✅ 不再出现空白区域

## 影响范围

**修改文件**：
- `frontend-next/app/(app)/tasks/[taskId]/page.tsx`（2处修改）

**涉及组件**：
- `TaskDetailPage`（主页面组件）
- `CoreDisplayArea`（展示区域组件）
- `IntentAnalysisCardInline`（需求分析卡片）

**后向兼容性**：
- ✅ 不影响其他功能
- ✅ 保留原有的重新加载逻辑（第 634-638 行）
- ✅ 添加错误处理，确保异常不影响其他事件

## 总结

**问题根本原因**：前端在收到 `roadmap_id` 更新时，没有立即加载 intent_analysis 数据

**解决方案**：在 WebSocket 的 `handleStatus` 回调中，当收到 `roadmap_id` 时立即调用 `loadIntentAnalysis`

**修复结果**：
- ✅ Intent Analysis 数据能在完成后立即显示
- ✅ 用户体验提升：无需等待或刷新页面
- ✅ 代码健壮性提升：添加了调试日志和错误处理

**相关文档**：
- API 文档：`/api/v1/roadmaps/{roadmap_id}/intent-analysis`
- 后端 Handler：`backend/app/core/orchestrator/handlers/intent_handler.py`
- 前端组件：`frontend-next/components/task/core-display-area.tsx`
