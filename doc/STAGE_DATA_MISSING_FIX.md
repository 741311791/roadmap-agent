# Stage 数据缺失问题修复

## 问题描述

**日期**: 2025-12-22

**症状**: My Learning Journeys 模块的卡片背面没有显示 Stage 信息，而是显示默认描述文本：
```
"A comprehensive learning path to master your skills step by step."
```

**根本原因**: **后端 API 没有返回 `stages` 字段**

## 问题根源分析

### 数据流路径

```
API: getUserRoadmaps(userId) [❌ 问题根源在这里 - 后端没有返回 stages]
  ↓
Home Page: fetchRoadmaps()
  ↓
Zustand Store: setHistory()
  ↓
Home Page: allRoadmaps mapping
  ↓
Component: MyLearningCard
```

### 具体问题

1. **后端 API 缺少 stages 字段** ⭐ 根本原因
   - **位置**: `backend/app/api/v1/endpoints/users.py`
   - **问题**: `RoadmapHistoryItem` 模型没有 `stages` 字段
   - **问题**: `get_user_roadmaps` API 创建响应时没有包含 stages 数据
   - **结果**: API 响应中根本没有 stages 数据

2. **前端类型定义不完整**
   - **位置**: `frontend-next/types/custom/store.ts` Line 17-25
   - **问题**: `RoadmapHistory` 接口缺少 `stages` 等字段
   - **结果**: TypeScript 没有提示缺少字段的错误

3. **Home Page 数据映射缺失**
   - **位置**: `frontend-next/app/(app)/home/page.tsx` Line 96-111
   - **问题**: 从 API 响应映射数据到 Store 时，遗漏了 `stages` 字段
   - **结果**: 即使后端返回了 stages，也会在前端丢失

## 修复方案

### 1. 后端：添加 StageSummary 模型和更新 RoadmapHistoryItem ⭐

**文件**: `backend/app/api/v1/endpoints/users.py`

```python
class StageSummary(BaseModel):
    """Stage 摘要信息，用于卡片展示"""
    name: str
    description: Optional[str] = None
    order: int


class RoadmapHistoryItem(BaseModel):
    """路线图历史项"""
    roadmap_id: str
    title: str
    created_at: str
    total_concepts: int
    completed_concepts: int
    topic: Optional[str] = None
    status: Optional[str] = None
    stages: Optional[list[StageSummary]] = None  # ✅ 新增
    # ... 其他字段
```

### 2. 后端：修改 get_user_roadmaps API 返回 stages 数据 ⭐

**文件**: `backend/app/api/v1/endpoints/users.py`

```python
# 提取 Stage 摘要信息
stage_summaries = []
for stage in stages_data:
    stage_summaries.append(StageSummary(
        name=stage.get("name", ""),
        description=stage.get("description"),
        order=stage.get("order", 0),
    ))

roadmap_items.append(RoadmapHistoryItem(
    # ... 其他字段
    stages=stage_summaries if stage_summaries else None,  # ✅ 传递 stages
))
```

### 3. 前端：更新 RoadmapHistory 类型定义

**文件**: `frontend-next/types/custom/store.ts`

```typescript
export interface RoadmapHistory {
  roadmap_id: string;
  title: string;
  created_at: string;
  status: 'draft' | 'completed' | 'archived' | 'generating' | 'failed' | 'learning';
  total_concepts: number;
  completed_concepts: number;
  topic?: string;
  // 新增字段：支持未完成路线图的恢复
  task_id?: string | null;
  task_status?: string | null;
  current_step?: string | null;
  // Stages 信息
  stages?: Array<{
    name: string;
    description?: string;
    order: number;
  }> | null;
}
```

### 4. 前端：修复 Home Page 数据映射

**文件**: `frontend-next/app/(app)/home/page.tsx`

```typescript
const historyData = response.roadmaps.map((item) => {
  return {
    // ... 其他字段
    stages: item.stages || null, // ✅ 保留 stages 数据
  };
});
```

## 修复验证

### 1. 类型检查
```bash
✅ No TypeScript errors
✅ No linter errors
```

### 2. 数据流验证

完整的数据流现在应该是：

```
API Response (with stages)
  ↓
Home Page fetchRoadmaps() ✅ 保留 stages
  ↓
Zustand Store setHistory() ✅ 包含 stages
  ↓
Home Page allRoadmaps ✅ 传递 stages
  ↓
MyLearningCard ✅ 显示 stages
```

### 3. UI 验证

卡片背面现在应该显示：
- ✅ Stage 列表（如果有数据）
- ✅ 每个 Stage 带 Tooltip
- ✅ 最多显示 5 个 Stages
- ✅ 超过 5 个显示 "+X more stages"

## 文件修改清单

| 文件 | 修改内容 |
|-----|---------|
| `backend/app/api/v1/endpoints/users.py` | ⭐ 添加 StageSummary 模型；更新 RoadmapHistoryItem 添加 stages 字段；修改 get_user_roadmaps 返回 stages 数据 |
| `frontend-next/types/custom/store.ts` | 更新 RoadmapHistory 接口，添加 stages 等字段 |
| `frontend-next/app/(app)/home/page.tsx` | 添加 stages 字段映射 |

## 相关文档

- [Learning Card Stage Tooltip Optimization](./LEARNING_CARD_STAGE_TOOLTIP_OPTIMIZATION.md)
- [My Learning Journeys 3D Flip Implementation](./MY_LEARNING_JOURNEYS_3D_FLIP_IMPLEMENTATION.md)

## 经验教训

### 1. 数据流完整性
- ⚠️ 在多层数据映射时，要确保关键字段不会丢失
- ✅ 使用 TypeScript 类型确保数据结构完整性

### 2. 类型定义先行
- ⚠️ 先更新类型定义，让 TypeScript 帮助发现问题
- ✅ 完整的类型定义可以避免运行时数据丢失

### 3. 数据映射检查清单
- [ ] API 响应包含该字段？
- [ ] 第一次映射保留该字段？
- [ ] Store 类型定义包含该字段？
- [ ] 后续映射传递该字段？
- [ ] 组件接收该字段？

## 状态

**修复状态**: ✅ 已完成  
**测试状态**: ⏳ 待测试  
**部署状态**: ⏳ 待部署

## 测试建议

### 手动测试
1. [ ] 刷新 Home 页面
2. [ ] 悬停 My Learning Journeys 卡片
3. [ ] 验证背面显示 Stage 列表
4. [ ] 悬停 Stage 项查看 Tooltip
5. [ ] 验证所有卡片的 Stages 数据正确

### 数据验证
1. [ ] 打开浏览器开发者工具
2. [ ] 查看网络请求：`/users/{userId}/roadmaps`
3. [ ] 确认响应包含 `stages` 字段
4. [ ] 检查 Zustand Store 状态
5. [ ] 确认 `history` 数组中包含 `stages`

## 总结

这次修复解决了 My Learning Journeys 卡片背面 Stage 数据缺失的问题。问题的根源在于数据流的第一层映射遗漏了关键字段，通过完善类型定义和数据映射，确保了数据的完整性。

