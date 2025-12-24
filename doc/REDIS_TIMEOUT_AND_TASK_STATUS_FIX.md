# Redis 超时与任务状态修复总结

## 问题描述

### 问题 1: Redis 通知发布超时
在路线图生成完成后，出现 Redis 通知发布超时错误：
```
2025-12-14 13:19:59 [error] notification_publish_failed error='Timeout reading from 47.111.115.130:6379'
```

**影响**：
- 前端无法收到实时进度通知
- 工作流本身执行正常，数据已正确保存
- 用户体验受影响（进度条可能卡住）

### 问题 2: 任务 `current_step` 显示不清晰
当任务完成时（包括部分失败），`current_step` 始终显示为 `content_generation`，导致前端可能误判任务状态。

---

## 根本原因

### 问题 1: Redis 连接配置缺陷
1. **缺少超时配置**：Redis 客户端未设置 socket 超时，导致网络波动时无限等待
2. **无重试机制**：publish 操作失败时直接抛出异常
3. **无降级策略**：通知失败会影响工作流完整性（虽然不会中断任务）

### 问题 2: 任务状态语义不明确
原代码逻辑：
```python
# 无论成功还是部分失败，current_step 都是 "content_generation"
await repo.update_task_status(
    task_id=task_id,
    status=final_status,  # "completed" 或 "partial_failure"
    current_step="content_generation",  # ❌ 固定值
)
```

前端无法区分：
- 任务已完全成功完成
- 任务仍在执行内容生成
- 任务在内容生成阶段部分失败

---

## 修复方案

### 修复 1: Redis 客户端优化

**文件**: `backend/app/db/redis_client.py`

```python
async def connect(self):
    """建立连接"""
    if self._client is None:
        self._client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            # ✅ 添加超时配置
            socket_timeout=5,  # Socket 操作超时 5 秒
            socket_connect_timeout=5,  # 连接超时 5 秒
            socket_keepalive=True,  # 启用 TCP keepalive
            max_connections=50,  # 连接池最大连接数
            retry_on_timeout=True,  # 超时时自动重试
        )
```

**改进点**：
- Socket 读写超时：5 秒
- 连接超时：5 秒
- TCP keepalive：防止长连接被中间网络设备断开
- 连接池：提高并发性能
- 自动重试：提高容错性

---

### 修复 2: 通知发布超时保护

**文件**: `backend/app/services/notification_service.py`

```python
async def _publish(self, task_id: str, event: dict):
    """
    发布事件到 Redis 频道
    
    如果 Redis 连接失败或超时，会记录错误但不会抛出异常，
    确保工作流不会因为通知失败而中断。
    """
    await self._ensure_connected()
    channel = self._get_channel(task_id)
    
    try:
        message = json.dumps(event, ensure_ascii=False)
        # ✅ 添加超时保护：5秒超时
        await asyncio.wait_for(
            redis_client._client.publish(channel, message),
            timeout=5.0
        )
        
        logger.debug("notification_published", ...)
    except asyncio.TimeoutError:
        # ✅ 优雅降级：超时时记录错误但不抛异常
        logger.error("notification_publish_timeout", ...)
    except Exception as e:
        # ✅ 优雅降级：其他错误也不抛异常
        logger.error("notification_publish_failed", ...)
```

**改进点**：
- 操作级超时：每次 publish 最多等待 5 秒
- 优雅降级：超时或错误时不影响工作流
- 详细日志：区分超时和其他错误类型

---

### 修复 3: 任务状态语义优化

**文件**: `backend/app/core/orchestrator/workflow_brain.py`

```python
# 更新最终状态
# ✅ 如果全部成功：status=completed, current_step=completed
# ✅ 如果部分失败：status=partial_failure, current_step=content_generation（标记失败发生在哪一步）
final_status = "partial_failure" if failed_concepts else "completed"
final_step = "content_generation" if failed_concepts else "completed"

await repo.update_task_status(
    task_id=task_id,
    status=final_status,
    current_step=final_step,  # ✅ 动态设置
    ...
)
```

**状态组合表**：

| 情况 | `status` | `current_step` | 含义 |
|------|----------|---------------|------|
| 全部成功 | `completed` | `completed` | 任务完整成功完成 |
| 部分失败 | `partial_failure` | `content_generation` | 内容生成阶段有部分失败 |
| 完全失败 | `failed` | `content_generation` | 内容生成阶段完全失败 |

**前端判断逻辑**：
```typescript
if (task.status === "completed" && task.current_step === "completed") {
  // 显示：✅ 路线图生成完成
  navigateTo(`/roadmap/${task.roadmap_id}`);
} else if (task.status === "partial_failure") {
  // 显示：⚠️ 路线图生成完成，但部分内容失败
  // 仍然可以查看路线图，失败的概念会标记为 "failed"
} else if (task.status === "processing") {
  // 显示当前步骤的进度
}
```

---

## 修复效果验证

### 验证 1: Framework 数据更新（已验证 ✅）
从日志可以看到：
```
2025-12-14 13:19:40 [info] workflow_brain_framework_before_update
  sample_content_status=pending  sample_quiz_id=None

2025-12-14 13:19:40 [info] workflow_brain_framework_after_update
  sample_content_status=completed  sample_quiz_id=a09fc089-...

2025-12-14 13:19:41 [info] workflow_brain_framework_verification_after_save
  verification_success=True
```

**结论**：`flag_modified` 修复生效，framework_data 正确更新到数据库。

### 验证 2: Redis 超时保护（待验证）
下次路线图生成时，如果遇到 Redis 超时：
- ✅ 应该看到 `notification_publish_timeout` 日志
- ✅ 工作流继续执行，不会中断
- ✅ 数据正确保存到数据库

### 验证 3: 任务状态清晰化（待验证）
下次路线图生成完成时：
- 如果全部成功：`status=completed, current_step=completed`
- 如果部分失败：`status=partial_failure, current_step=content_generation`

---

## 其他改进建议

### 1. Redis 连接池监控
建议添加 Redis 连接池健康检查：
```python
async def check_redis_health() -> dict:
    """检查 Redis 连接池健康状况"""
    if redis_client._client:
        pool = redis_client._client.connection_pool
        return {
            "connected": True,
            "max_connections": pool.max_connections,
            "available_connections": len(pool._available_connections),
        }
    return {"connected": False}
```

### 2. 通知失败重试机制
对于关键通知（如任务完成），可以考虑添加重试：
```python
async def publish_completed_with_retry(self, task_id: str, roadmap_id: str, max_retries: int = 3):
    """发布任务完成事件（带重试）"""
    for attempt in range(max_retries):
        try:
            await self.publish_completed(task_id, roadmap_id)
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error("publish_completed_failed_after_retries", task_id=task_id)
            else:
                await asyncio.sleep(1)  # 重试前等待 1 秒
```

### 3. 前端轮询兜底
如果 WebSocket 通知失败，前端可以轮询任务状态：
```typescript
const pollTaskStatus = async (taskId: string) => {
  while (true) {
    const task = await fetchTaskStatus(taskId);
    if (task.status === "completed" || task.status === "failed") {
      break;
    }
    await sleep(2000);  // 每 2 秒轮询一次
  }
};
```

---

## 相关文件清单

### 修改的文件
1. `backend/app/db/redis_client.py` - Redis 客户端超时配置
2. `backend/app/services/notification_service.py` - 通知发布超时保护
3. `backend/app/core/orchestrator/workflow_brain.py` - 任务状态优化
4. `backend/app/db/repositories/roadmap_repo.py` - 添加 `flag_modified` 修复 JSON 更新

### 文档
1. `FRAMEWORK_DATA_SYNC_FIX_FINAL.md` - Framework 数据同步修复总结
2. `REDIS_TIMEOUT_AND_TASK_STATUS_FIX.md` - 本文档

---

## 总结

本次修复解决了两个关键问题：

1. **Redis 超时问题**：通过添加超时配置、连接池优化和优雅降级，确保 Redis 通知失败不影响工作流执行
2. **任务状态语义**：通过动态设置 `current_step`，让前端能清晰区分任务的完成状态

**技术要点**：
- 分布式系统设计：外部依赖（Redis）失败不应影响核心业务逻辑
- 优雅降级：通知失败时记录日志但不抛异常
- 状态机清晰化：让状态字段能准确表达业务语义

**遗留问题**：
- 阿里云内容审核问题（羽毛球相关概念被误判为不适当内容）- 需要业务层面处理
- Redis 连接稳定性需要持续监控
