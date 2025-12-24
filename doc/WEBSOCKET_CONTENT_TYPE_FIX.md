# WebSocket Content Type 修复 + UI 优化

> **日期**: 2025-12-12  
> **问题**: 前端一直显示"Fetching Learning Resources"，即使后端状态已完成  
> **状态**: ✅ 已完成

---

## 🔍 问题诊断

### 用户报告
- 概念 `rag-enterprise-knowledge-base-d4e2f1c8:c-3-1-2` 的学习资源已完成生成
- 前端仍然显示"Fetching Learning Resources"
- StaleStatusDetector UI 设计不美观，语言为中文

### 根本原因

1. **WebSocket 事件缺少 `content_type` 字段**
   - 后端发送的 `concept_start/complete/failed` 事件没有包含 `content_type`
   - 前端无法区分是 tutorial、resources 还是 quiz 的状态更新
   - 导致所有状态更新都被错误地应用到 `content_status`（tutorial）

2. **前端状态更新逻辑错误**
   - WebSocket 处理器硬编码更新 `tutorial_status`
   - resources 和 quiz 的状态更新被忽略

3. **UI 设计问题**
   - StaleStatusDetector 使用中文
   - 配色与主题不搭
   - 缺乏现代感

---

## ✅ 解决方案

### 1. 后端修复

#### 1.1 更新 NotificationService

**文件**: `backend/app/services/notification_service.py`

**修改**: 在所有 concept 事件中添加 `content_type` 参数

```python
async def publish_concept_start(
    self,
    task_id: str,
    concept_id: str,
    concept_name: str,
    current: int,
    total: int,
    content_type: str = "tutorial",  # 新增参数
):
    event = {
        "type": TaskEvent.CONCEPT_START,
        "task_id": task_id,
        "concept_id": concept_id,
        "concept_name": concept_name,
        "content_type": content_type,  # 新增字段
        ...
    }
```

同样的修改应用到：
- `publish_concept_complete()`
- `publish_concept_failed()`

#### 1.2 更新重试端点

**文件**: `backend/app/api/v1/endpoints/generation.py`

**修改**: 在所有重试端点中传递正确的 `content_type`

```python
# Tutorial 重试
await notification_service.publish_concept_start(
    task_id=task_id,
    concept_id=concept_id,
    concept_name=concept.name,
    current=1,
    total=1,
    content_type="tutorial",  # 明确指定
)

# Resources 重试
await notification_service.publish_concept_start(
    task_id=task_id,
    concept_id=concept_id,
    concept_name=concept.name,
    current=1,
    total=1,
    content_type="resources",  # 明确指定
)

# Quiz 重试
await notification_service.publish_concept_start(
    task_id=task_id,
    concept_id=concept_id,
    concept_name=concept.name,
    current=1,
    total=1,
    content_type="quiz",  # 明确指定
)
```

---

### 2. 前端修复

#### 2.1 更新 WebSocket 类型定义

**文件**: `frontend-next/lib/api/websocket.ts`

```typescript
export interface WSConceptStartEvent extends WSEvent {
  type: 'concept_start';
  concept_id: string;
  concept_name: string;
  content_type: 'tutorial' | 'resources' | 'quiz';  // 新增字段
  progress: { ... };
  ...
}

export interface WSConceptCompleteEvent extends WSEvent {
  type: 'concept_complete';
  concept_id: string;
  concept_name: string;
  content_type: 'tutorial' | 'resources' | 'quiz';  // 新增字段
  ...
}

export interface WSConceptFailedEvent extends WSEvent {
  type: 'concept_failed';
  concept_id: string;
  concept_name: string;
  content_type: 'tutorial' | 'resources' | 'quiz';  // 新增字段
  ...
}
```

#### 2.2 更新 WebSocket 处理逻辑

**文件**: `frontend-next/app/(immersive)/roadmap/[id]/page.tsx`

**修改前**:
```typescript
onConceptComplete: (event) => {
  if (event.concept_id) {
    // 错误：硬编码更新 tutorial_status
    updateConceptStatus(event.concept_id, { tutorial_status: 'completed' });
  }
}
```

**修改后**:
```typescript
onConceptComplete: (event) => {
  if (event.concept_id) {
    // 正确：根据 content_type 动态更新对应的状态
    const contentType = event.content_type;
    const statusKey = contentType === 'resources' 
      ? 'resources_status' 
      : contentType === 'quiz' 
        ? 'quiz_status' 
        : 'content_status';
    updateConceptStatus(event.concept_id, { [statusKey]: 'completed' });
    refetchRoadmap();  // 刷新路线图获取最新数据
  }
}
```

同样的逻辑应用到 `onConceptStart` 和 `onConceptFailed`。

---

### 3. UI 优化

#### 3.1 重新设计 StaleStatusDetector

**文件**: `frontend-next/components/common/stale-status-detector.tsx`

**改进**:

1. **全英文界面**
   - 所有文本改为英文
   - 保持专业和一致性

2. **现代化设计**
   - 使用渐变背景 (`bg-gradient-to-br`)
   - 添加阴影和模糊效果 (`shadow-lg`, `blur-xl`)
   - 更大的图标和间距
   - 圆角更柔和 (`rounded-2xl`)

3. **配色优化**
   - 正常状态：sage 绿色系（与主题一致）
   - 超时状态：红色/橙色渐变（更醒目）
   - 使用半透明背景增加层次感

4. **交互改进**
   - 更大的按钮
   - 更清晰的视觉层次
   - 折叠式详情面板

**对比**:

| 特性 | 修改前 | 修改后 |
|------|--------|--------|
| 语言 | 中文 | 英文 |
| 配色 | amber（琥珀色） | sage（正常）/ red-orange（超时） |
| 圆角 | `rounded-xl` | `rounded-2xl` |
| 图标大小 | `w-8 h-8` | `w-10 h-10` |
| 背景 | 纯色 | 渐变 + 模糊效果 |
| 间距 | `gap-4 py-12` | `gap-6 py-16` |

---

## 📊 修复效果

### 修复前
```
用户点击重试 → 后端生成完成 → 前端仍显示"Fetching..."
原因：WebSocket 更新了 tutorial_status，但前端检查的是 resources_status
```

### 修复后
```
用户点击重试 → 后端生成完成 → WebSocket 推送 content_type="resources"
→ 前端更新 resources_status="completed" → 显示资源列表 ✅
```

---

## 🧪 测试验证

### 1. 测试 WebSocket 事件

```bash
# 监听 WebSocket 事件
wscat -c "ws://localhost:8000/api/v1/ws/retry-resources-xxx"

# 预期收到的事件应包含 content_type
{
  "type": "concept_complete",
  "concept_id": "xxx",
  "content_type": "resources",  # ✅ 包含此字段
  ...
}
```

### 2. 测试前端状态更新

1. 打开路线图
2. 点击重试资源推荐
3. 打开浏览器控制台
4. 查看日志：
   ```
   [WS] Concept complete: { content_type: "resources", ... }
   [Store] Updating concept status: { resources_status: "completed" }
   ```

### 3. 测试 UI

1. 打开一个 pending 状态的概念
2. 等待 3-5 秒（快速检查）
3. 如果检测到僵尸状态，应显示新的 UI：
   - 红色/橙色渐变背景
   - 英文文本
   - 现代化设计

---

## 📝 相关文件

### 后端
- `backend/app/services/notification_service.py` - WebSocket 事件发布
- `backend/app/api/v1/endpoints/generation.py` - 重试端点

### 前端
- `frontend-next/lib/api/websocket.ts` - WebSocket 类型定义
- `frontend-next/app/(immersive)/roadmap/[id]/page.tsx` - WebSocket 处理逻辑
- `frontend-next/components/common/stale-status-detector.tsx` - UI 组件

---

## ✅ 总结

### 问题
1. WebSocket 事件缺少 `content_type` 字段
2. 前端状态更新逻辑错误
3. UI 设计不美观，使用中文

### 解决
1. ✅ 后端所有 concept 事件添加 `content_type` 字段
2. ✅ 前端根据 `content_type` 动态更新对应状态
3. ✅ 重新设计 UI，全英文，现代化设计

### 效果
- 🚀 状态更新准确无误
- 🎨 UI 美观大方，与主题一致
- 🌍 全英文界面，专业统一















