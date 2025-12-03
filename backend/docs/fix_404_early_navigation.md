# 修复前端早期跳转404问题

## 问题描述

当用户创建新路线图时：
1. 前端调用 `/generate` API，获得 `task_id`
2. 前端通过 WebSocket 接收实时进度
3. 当 `intent_analysis` 完成并生成 `roadmap_id` 后，前端立即跳转到 `/app/roadmap/${roadmap_id}`
4. **问题**：此时后端 `GET /{roadmap_id}` API 返回 404

## 根本原因

在 `intent_analysis` 阶段：
- ✅ 生成了 `roadmap_id`
- ✅ 通过 WebSocket 发送给前端
- ❌ **但没有更新数据库中的 `roadmap_tasks` 表的 `roadmap_id` 字段**

当前端跳转到 `/app/roadmap/${roadmap_id}` 时，`get_roadmap` API 会：
1. 检查 `roadmap_metadata` 表 → 不存在（还在生成中）
2. 检查是否有活跃任务关联该 `roadmap_id` → 找不到（因为 task 记录中 `roadmap_id` 字段为 NULL）
3. 返回 404

## 解决方案

在 `orchestrator.py` 的 `_run_intent_analysis()` 方法中，当 `roadmap_id` 验证完成后，**立即更新 task 记录**：

```python
# 验证并确保唯一性
original_id = result.roadmap_id
unique_id = await ensure_unique_roadmap_id(result.roadmap_id, repo)
result.roadmap_id = unique_id

# 🔧 关键修复：立即更新task记录的roadmap_id字段
# 这样前端跳转时就能通过roadmap_id找到活跃的task
await repo.update_task_status(
    task_id=trace_id,
    status="processing",
    current_step="intent_analysis",
    roadmap_id=unique_id,
)
await session.commit()
```

## 修复后的流程

1. `intent_analysis` 完成 → 生成 `roadmap_id`
2. **更新数据库 task 记录的 `roadmap_id` 字段** ✅
3. 通过 WebSocket 发送 `roadmap_id` 给前端
4. 前端跳转到 `/app/roadmap/${roadmap_id}`
5. `GET /{roadmap_id}` API：
   - 检查 `roadmap_metadata` → 不存在
   - 检查活跃任务 → **找到了！**（通过 `roadmap_id` 匹配）
   - 返回：
     ```json
     {
       "status": "processing",
       "task_id": "xxx",
       "current_step": "curriculum_design",
       "message": "路线图正在生成中"
     }
     ```
6. 前端显示"正在生成中"状态，继续监听 WebSocket 更新 ✅

## 相关代码文件

- `backend/app/core/orchestrator.py` - 修复位置：`_run_intent_analysis()` 方法
- `backend/app/api/v1/roadmap.py` - API端点：`GET /{roadmap_id}`
- `backend/app/db/repositories/roadmap_repo.py` - 数据库操作：`update_task_status()`, `get_active_task_by_roadmap_id()`
- `frontend-next/app/app/new/page.tsx` - 前端跳转逻辑：第254-263行

## 测试建议

1. 创建新路线图
2. 观察前端是否在 `intent_analysis` 完成后立即跳转
3. 确认跳转后的页面显示"正在生成中"而不是404
4. 确认页面能继续接收 WebSocket 更新并显示进度

## 数据库Schema

`roadmap_tasks` 表相关字段：
```sql
CREATE TABLE roadmap_tasks (
    task_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    roadmap_id VARCHAR,  -- 在 intent_analysis 完成后设置
    status VARCHAR,      -- processing, completed, failed, etc.
    current_step VARCHAR,
    ...
);
```

`roadmap_metadata` 表相关字段：
```sql
CREATE TABLE roadmap_metadata (
    roadmap_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    task_id VARCHAR,
    framework JSONB,
    ...
);
```

## 查询逻辑

```python
# backend/app/api/v1/roadmap.py - get_roadmap()

# 1. 尝试获取完整roadmap
roadmap = await service.get_roadmap(roadmap_id)

if not roadmap:
    # 2. 如果不存在，查找关联的活跃任务
    active_task = await repo.get_active_task_by_roadmap_id(roadmap_id)
    
    if active_task:
        # 🎯 修复后：能找到活跃任务！
        return {
            "status": "processing",
            "task_id": active_task.task_id,
            "current_step": active_task.current_step,
            "message": "路线图正在生成中"
        }
    
    # 3. 如果都没有，返回404
    raise HTTPException(status_code=404)
```

## 修改时间

2024-12-04

## 相关问题

- 前端早期跳转策略（在 `curriculum_design` 完成后跳转而非全部完成）
- roadmap_id 的生成和唯一性保证
- WebSocket 实时进度推送

