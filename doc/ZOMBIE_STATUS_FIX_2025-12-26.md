# 僵尸状态检测修复 - 2025-12-26

## 🐛 问题描述

**现象：**
- 用户打开路线图详情页，查看一个应该是僵尸状态的 Concept
- 前端一直显示 "Generating Tutorial..."，但实际上没有活跃任务在运行
- 数据库中对应 Concept 的状态为 `pending`，但没有关联的活跃任务

**期望行为：**
- 前端应该立即检测到僵尸状态，将状态更新为 `failed`，显示重试按钮

---

## 🔍 根本原因

### 后端 API 实现正确 ✅

后端已经实现了僵尸状态检测 API：

```python
# backend/app/api/v1/endpoints/status.py

@router.get("/{roadmap_id}/status-check")
async def check_status_quick(roadmap_id: str, db: AsyncSession):
    """
    快速检查路线图状态，用于检测僵尸状态
    
    返回格式：
    {
        "roadmap_id": str,
        "has_active_task": bool,
        "active_tasks": [...],
        "stale_concepts": [  # 僵尸状态的概念列表
            {
                "concept_id": str,
                "concept_name": str,
                "content_type": "tutorial" | "resources" | "quiz",
                "current_status": "pending" | "generating"
            }
        ]
    }
    """
```

### 前端调用了 API 但未处理 `stale_concepts` ❌

**问题代码位置：**
`frontend-next/components/roadmap/immersive/learning-stage.tsx:999-1048`

```typescript
// 🔴 旧代码：只处理 has_active_task，忽略了 stale_concepts
const result = await checkRoadmapStatusQuick(roadmapId);

if (result.has_active_task && result.active_tasks) {
  // ✅ 处理活跃任务
  currentConceptTasks.forEach((task: any) => {
    // 更新状态为 generating
  });
}
// ❌ 没有处理 result.stale_concepts
```

**问题分析：**
1. 前端调用了 `checkRoadmapStatusQuick` API
2. 后端正确返回了 `stale_concepts` 列表
3. 前端 **仅处理了 `has_active_task = true` 的情况**
4. 前端 **完全忽略了 `stale_concepts` 字段**
5. 导致僵尸状态的 Concept 一直显示 "Generating"，无法自动恢复

---

## ✅ 修复方案

### 修复位置
`frontend-next/components/roadmap/immersive/learning-stage.tsx:997-1071`

### 修复内容

添加对 `stale_concepts` 的处理逻辑：

```typescript
const result = await checkRoadmapStatusQuick(roadmapId);

if (result.has_active_task && result.active_tasks) {
  // ✅ 处理活跃任务
  currentConceptTasks.forEach((task: any) => {
    if (task.content_type === 'tutorial' && task.status === 'processing') {
      updateConceptStatus(concept.concept_id, { content_status: 'generating' });
    }
    // ... resources, quiz 同理
  });
} else if (!result.has_active_task && result.stale_concepts.length > 0) {
  // 🔧 僵尸状态检测：没有活跃任务，但有僵尸状态的概念
  const currentConceptStaleItems = result.stale_concepts.filter(
    (stale: any) => stale.concept_id === concept.concept_id
  );

  if (currentConceptStaleItems.length > 0) {
    console.warn('[LearningStage] 🧟 Detected stale/zombie status for concept:', 
      concept.concept_id, currentConceptStaleItems);

    // 将僵尸状态的内容标记为 failed
    currentConceptStaleItems.forEach((stale: any) => {
      if (stale.content_type === 'tutorial') {
        console.log('[LearningStage] 🧟 Marking tutorial as failed (zombie detected)');
        updateConceptStatus(concept.concept_id, { content_status: 'failed' });
      } else if (stale.content_type === 'resources') {
        console.log('[LearningStage] 🧟 Marking resources as failed (zombie detected)');
        updateConceptStatus(concept.concept_id, { resources_status: 'failed' });
      } else if (stale.content_type === 'quiz') {
        console.log('[LearningStage] 🧟 Marking quiz as failed (zombie detected)');
        updateConceptStatus(concept.concept_id, { quiz_status: 'failed' });
      }
    });
  }
}
```

---

## 🧪 测试步骤

### 1. 创建僵尸状态的 Concept

**方式一：模拟任务中断**
```bash
# 1. 启动一个内容生成任务
curl -X POST "http://localhost:8000/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/retry-tutorial"

# 2. 立即停止后端服务（模拟崩溃）
kill -9 <backend_pid>

# 3. 重启后端
cd backend && poetry run uvicorn app.main:app --reload

# 4. 此时 Concept 的状态仍为 generating，但没有活跃任务 → 僵尸状态
```

**方式二：直接修改数据库**
```sql
-- 将某个 Concept 的状态改为 generating，但删除其对应的任务
UPDATE roadmaps
SET framework = jsonb_set(
  framework,
  '{stages,0,modules,0,concepts,0,content_status}',
  '"generating"'
)
WHERE roadmap_id = 'your-roadmap-id';

-- 确保没有活跃任务
SELECT * FROM tasks WHERE roadmap_id = 'your-roadmap-id' AND status = 'processing';
-- 应该返回空结果
```

### 2. 测试前端检测

**步骤：**
1. 打开浏览器开发者工具 Console
2. 访问路线图详情页：`http://localhost:3000/roadmap/{roadmap_id}?concept={zombie_concept_id}`
3. 观察 Console 输出

**期望输出：**
```
[LearningStage] 🧟 Detected stale/zombie status for concept: c-1-1-1 [...]
[LearningStage] 🧟 Marking tutorial as failed (zombie detected)
```

**期望界面：**
- ❌ 不再显示 "Generating Tutorial..."
- ✅ 显示 "Generation Failed" 和 "Retry" 按钮

### 3. 测试重试功能

**步骤：**
1. 点击 "Retry" 按钮
2. 观察任务是否正常启动
3. WebSocket 是否正确连接并接收更新
4. 内容生成完成后，状态是否正确更新为 `completed`

---

## 📊 影响范围

### 修改的文件
- ✅ `frontend-next/components/roadmap/immersive/learning-stage.tsx`（核心修复）

### 未修改的文件（无需修改）
- ✅ `backend/app/api/v1/endpoints/status.py`（后端 API 已正确实现）
- ✅ `frontend-next/lib/api/endpoints.ts`（API 客户端已正确定义）
- ✅ `frontend-next/components/roadmap/immersive/knowledge-rail.tsx`（仅导航显示，无需检测）

### 影响的用户场景
1. **路线图详情页**：用户查看僵尸状态的 Concept 时，立即检测并更新为 failed
2. **Tab 切换**：切换到 Resources 或 Quiz 时，也会触发检测
3. **Concept 切换**：在不同 Concept 之间切换时，会为每个 Concept 检测僵尸状态

---

## 🔄 工作流程

### 修复前
```
用户打开 Concept
    ↓
前端调用 checkRoadmapStatusQuick()
    ↓
后端返回 { has_active_task: false, stale_concepts: [...] }
    ↓
前端忽略 stale_concepts ❌
    ↓
UI 一直显示 "Generating..." 🧟
```

### 修复后
```
用户打开 Concept
    ↓
前端调用 checkRoadmapStatusQuick()
    ↓
后端返回 { has_active_task: false, stale_concepts: [...] }
    ↓
前端检测到 stale_concepts ✅
    ↓
更新状态为 failed
    ↓
UI 显示 "Failed" + "Retry" 按钮 ✅
```

---

## 📝 相关文档

- `doc/STALE_STATUS_SOLUTION.md` - 僵尸状态解决方案架构
- `doc/QUICK_STATUS_CHECK_IMPLEMENTATION.md` - 快速状态检查实现
- `backend/docs/STALE_STATUS_SOLUTION.md` - 后端僵尸状态文档

---

## ✨ 总结

### 问题原因
前端虽然调用了僵尸状态检测 API，但只处理了"有活跃任务"的分支，忽略了"没有活跃任务但有僵尸状态"的分支。

### 修复方式
在 `LearningStage` 组件的 `checkActiveRetryTasks` 函数中，添加对 `stale_concepts` 的处理逻辑，将检测到的僵尸状态内容标记为 `failed`。

### 修复效果
- ✅ 僵尸状态的 Concept 立即显示为 Failed
- ✅ 用户可以立即点击 Retry 重新生成
- ✅ 不再需要等待超时或手动刷新页面
- ✅ 提升用户体验，减少困惑

---

**修复完成时间：** 2025-12-26  
**修复作者：** AI Assistant  
**测试状态：** ⏳ 待测试

