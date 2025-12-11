# 僵尸状态（Stale Status）解决方案

## 问题描述

**问题现象**：
- 概念的状态（`content_status`、`resources_status`、`quiz_status`）停留在 `pending` 或 `generating`
- 实际上没有正在运行的任务（任务已异常中断）
- 前端一直显示"正在生成中"，用户无法操作

**根本原因**：
1. 后台任务异常中断（服务器崩溃、手动停止、异常退出等）
2. 任务状态未能正确更新到 `completed` 或 `failed`
3. 概念状态停留在中间状态，形成"僵尸状态"
4. 没有自动恢复机制，状态会一直卡住

---

## 解决方案架构

```
┌─────────────────────────────────────────────────────────────┐
│                     前端检测层                               │
│  - 超时检测（2分钟）                                         │
│  - 自动提示用户                                             │
│  - 提供重试按钮                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     后端恢复层                               │
│  - 定期扫描僵尸状态                                         │
│  - 自动标记为 failed                                        │
│  - 生成诊断报告                                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     人工介入层                               │
│  - 手动修复脚本                                             │
│  - 状态恢复工具                                             │
│  - 数据一致性检查                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. 前端解决方案：超时检测组件

### 1.1 核心组件：StaleStatusDetector

**位置**：`frontend-next/components/common/stale-status-detector.tsx`

**功能**：
- ✅ 实时计时，显示已等待时间
- ✅ 超时后自动提示用户（默认 120 秒）
- ✅ 提供重试按钮，允许用户手动重新生成
- ✅ 显示诊断信息，帮助排查问题
- ✅ 优雅的 UI 过渡（正常加载 → 超时警告）

**使用示例**：

```typescript
import { StaleStatusDetector } from '@/components/common/stale-status-detector';

// 在 learning-stage.tsx 中使用
{resourcesGenerating || resourcesPending ? (
  <StaleStatusDetector
    roadmapId={roadmapId}
    conceptId={concept.concept_id}
    contentType="resources"
    status={concept.resources_status} // 'pending' | 'generating'
    preferences={userPreferences}
    timeoutSeconds={120} // 2 分钟超时
    onSuccess={() => onRetrySuccess?.()}
  />
) : (
  // 正常内容显示
)}
```

### 1.2 工作流程

```
1. 用户打开学习资源 tab
   └─ 检测 resources_status = 'pending' 或 'generating'
      └─ 显示 StaleStatusDetector 组件
         ├─ 显示加载动画
         ├─ 显示实时计时
         └─ 显示进度条（0-95%）

2. 时间流逝...
   └─ 每秒更新计时器
      └─ 检查是否超时（默认 120 秒）

3. 超时触发
   └─ UI 自动切换为警告状态
      ├─ 显示警告图标（黄色）
      ├─ 提示"生成超时"
      ├─ 显示已等待时间
      └─ 显示重试按钮

4. 用户点击重试
   └─ 调用重试 API
      └─ 订阅 WebSocket
         └─ 实时更新状态
            ├─ generating → completed ✅
            └─ generating → failed ❌
```

### 1.3 UI 状态

#### 正常加载状态（0-120 秒）
```
┌─────────────────────────────────────┐
│         🔄 [旋转动画]                │
│                                     │
│    学习资源正在获取中                 │
│   这可能需要几分钟时间，请稍候...     │
│                                     │
│    ⏱️ 已等待 1:35                   │
│                                     │
│   ▓▓▓▓▓▓▓▓▓▓▓░░░░  79%             │
└─────────────────────────────────────┘
```

#### 超时警告状态（120+ 秒）
```
┌─────────────────────────────────────┐
│         ⚠️ [警告图标]                │
│                                     │
│      学习资源获取超时                 │
│   已处于"生成中"状态超过 2 分钟       │
│  这可能是由于后台任务异常中断         │
│                                     │
│    ⏱️ 已等待 2:47                   │
│                                     │
│  [重新获取资源]  [查看详情]          │
└─────────────────────────────────────┘
```

#### 诊断详情（展开后）
```
┌─────────────────────────────────────┐
│ 诊断信息                             │
│ ─────────────────────────────────── │
│ • 路线图 ID: rag-enterprise-...     │
│ • 概念 ID: c-1-1-1                  │
│ • 当前状态: generating              │
│ • 等待时间: 2:47 (167 秒)           │
│ • 超时阈值: 2:00 (120 秒)           │
│                                     │
│ 可能原因：                           │
│ • 后台生成任务被异常中断              │
│ • 服务器在生成过程中重启              │
│ • WebSocket 连接断开导致状态未更新    │
│ • 任务队列处理异常                    │
└─────────────────────────────────────┘
```

---

## 2. 后端解决方案：状态恢复脚本

### 2.1 核心脚本：fix_stale_statuses.py

**位置**：`backend/scripts/fix_stale_statuses.py`

**功能**：
- ✅ 扫描所有路线图的概念状态
- ✅ 识别僵尸状态（pending/generating 但任务已中断）
- ✅ 自动修复为 failed 状态
- ✅ 生成详细的诊断报告
- ✅ 支持预览模式（dry-run）

**运行方式**：

```bash
# 预览模式（不修改数据库）
uv run python scripts/fix_stale_statuses.py --dry-run --timeout 3600

# 实际修复模式
uv run python scripts/fix_stale_statuses.py --no-dry-run --timeout 3600
```

### 2.2 检测逻辑

```python
def is_stale(concept, task_id, active_task_ids, timeout_seconds):
    """
    判断概念状态是否为僵尸状态
    
    条件：
    1. 状态为 pending 或 generating
    2. 关联的任务不在活跃任务列表中
    3. 距离上次更新超过 timeout_seconds
    """
    status = concept.get('resources_status')
    
    if status not in ['pending', 'generating']:
        return False
    
    if task_id in active_task_ids:
        return False
    
    if time_since_update < timeout_seconds:
        return False
    
    return True  # 是僵尸状态
```

### 2.3 修复策略

| 状态 | 超时时间 | 修复策略 |
|------|---------|---------|
| `pending` | > 1 小时 | 标记为 `failed` |
| `generating` | > 30 分钟 | 标记为 `failed` |
| `completed` | - | 不修复 |
| `failed` | - | 不修复 |

### 2.4 输出示例

```
======================================================================
僵尸状态修复工具
======================================================================
模式: 预览模式（不会修改数据库）
超时阈值: 3600 秒 (60.0 分钟)

步骤 1/4: 获取活跃任务...
  ✓ 找到 2 个活跃任务

步骤 2/4: 扫描僵尸状态...
  ⚠️  发现 3 个僵尸状态概念

步骤 3/4: 僵尸状态详情
----------------------------------------------------------------------

路线图: 企业级 RAG 知识库构建完整指南
  ID: rag-enterprise-knowledge-base-d4e2f1c8
  任务 ID: task-abc123
  创建时间: 2024-12-10 10:30:00
  距今: 2:15:30
  僵尸概念数: 3

    • RAG 系统架构设计 (resources)
      状态: pending
    • 向量数据库选型与配置 (resources)
      状态: generating
    • Embedding 模型对比 (quiz)
      状态: pending

步骤 4/4: 修复僵尸状态
----------------------------------------------------------------------
  ℹ️  预览模式，不会修改数据库
  将修复 3 个概念的状态

  如需实际修复，请运行:
    uv run python scripts/fix_stale_statuses.py --timeout 3600

======================================================================
完成
======================================================================
```

---

## 3. 后端 API 增强（可选）

### 3.1 新增状态检查端点

```python
@router.get("/{roadmap_id}/status-check")
async def check_roadmap_status(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    检查路线图的状态一致性
    
    Returns:
        {
            "roadmap_id": "xxx",
            "has_stale_statuses": true,
            "stale_concepts": [
                {
                    "concept_id": "c-1-1-1",
                    "content_type": "resources",
                    "status": "generating",
                    "time_since_update": 7200
                }
            ],
            "recommendations": [
                "建议重新生成 c-1-1-1 的学习资源"
            ]
        }
    """
    # 实现逻辑
    pass
```

### 3.2 自动恢复中间件（未来优化）

```python
@app.middleware("http")
async def auto_recovery_middleware(request: Request, call_next):
    """
    每次请求路线图时，自动检测并修复僵尸状态
    
    优点：
    - 用户无感知
    - 自动恢复
    - 无需手动运行脚本
    
    缺点：
    - 增加请求延迟
    - 需要缓存机制避免重复检查
    """
    response = await call_next(request)
    
    # 如果是获取路线图的请求
    if request.url.path.startswith("/api/v1/roadmaps/"):
        roadmap_id = extract_roadmap_id(request.url.path)
        await auto_fix_stale_statuses(roadmap_id)
    
    return response
```

---

## 4. 最佳实践

### 4.1 预防措施

1. **任务监控**：
   - 使用健康检查（health check）监控任务队列
   - 任务超时自动标记为失败
   - 记录任务执行日志

2. **优雅停机**：
   ```python
   # 在服务器关闭前，将所有 generating 状态标记为 pending
   @app.on_event("shutdown")
   async def on_shutdown():
       await mark_generating_as_pending()
   ```

3. **心跳机制**：
   - 任务执行时定期更新心跳时间
   - 后台定期检查心跳超时的任务

### 4.2 运维建议

1. **定期检查**：
   ```bash
   # 每天凌晨 3 点运行一次
   0 3 * * * cd /path/to/backend && uv run python scripts/fix_stale_statuses.py --no-dry-run
   ```

2. **监控告警**：
   - 监控僵尸状态数量
   - 超过阈值时发送告警
   - 记录异常任务的日志

3. **用户通知**：
   - 如果检测到僵尸状态，主动通知用户
   - 提供一键恢复功能

### 4.3 数据恢复流程

```
1. 发现问题
   └─ 用户报告或监控告警

2. 诊断
   └─ 运行 fix_stale_statuses.py --dry-run
      └─ 查看诊断报告
         └─ 确认僵尸状态的范围

3. 修复
   └─ 运行 fix_stale_statuses.py --no-dry-run
      └─ 验证修复结果
         └─ 通知受影响的用户

4. 预防
   └─ 分析根本原因
      └─ 修复导致任务中断的 bug
         └─ 加强监控和告警
```

---

## 5. 用户体验优化

### 5.1 超时时间配置

不同内容类型的推荐超时时间：

| 内容类型 | 预期生成时间 | 推荐超时 | 原因 |
|---------|------------|---------|------|
| Tutorial | 30-60 秒 | 120 秒 | 需要生成长文本 |
| Resources | 10-20 秒 | 60 秒 | 只需搜索和排序 |
| Quiz | 20-30 秒 | 90 秒 | 需要生成题目和答案 |

### 5.2 用户反馈

超时提示中应包含：
- ✅ 清晰的问题描述
- ✅ 可能的原因
- ✅ 明确的操作指引
- ✅ 预计恢复时间
- ✅ 联系支持的方式（如果需要）

### 5.3 错误追踪

```typescript
// 在超时时记录错误日志
if (isStale) {
  console.error('[StaleStatusDetector] 检测到僵尸状态', {
    roadmapId,
    conceptId,
    contentType,
    status,
    elapsedTime,
    timestamp: new Date().toISOString(),
  });
  
  // 可选：发送到错误追踪服务（如 Sentry）
  Sentry.captureMessage('Stale status detected', {
    level: 'warning',
    tags: { component: 'StaleStatusDetector' },
    extra: { roadmapId, conceptId, contentType, status, elapsedTime },
  });
}
```

---

## 6. 测试场景

### 6.1 前端测试

1. **正常生成流程**：
   - 触发资源生成
   - 等待完成
   - 验证状态正确更新

2. **超时场景**：
   - 手动设置超时时间为 10 秒
   - 触发生成但不完成
   - 验证 10 秒后显示超时提示

3. **重试功能**：
   - 触发超时
   - 点击重试按钮
   - 验证重新生成成功

### 6.2 后端测试

1. **僵尸状态检测**：
   - 手动创建僵尸状态的概念
   - 运行修复脚本
   - 验证状态已修复

2. **任务中断模拟**：
   - 启动生成任务
   - 中途停止服务器
   - 重启后运行修复脚本
   - 验证状态已恢复

---

## 7. 总结

### 7.1 解决方案优势

| 层次 | 优势 |
|------|------|
| **前端** | ✅ 实时检测，用户无需等待<br>✅ 友好的超时提示和重试功能<br>✅ 透明的诊断信息 |
| **后端** | ✅ 自动化修复脚本<br>✅ 支持预览和实际修复两种模式<br>✅ 详细的诊断报告 |
| **运维** | ✅ 定时任务自动检查<br>✅ 监控告警及时发现问题<br>✅ 灵活的配置参数 |

### 7.2 改进方向

1. **短期**（已实现）：
   - ✅ 前端超时检测和重试
   - ✅ 后端手动修复脚本
   - ✅ 完善的文档和使用指南

2. **中期**（计划中）：
   - ⏳ 后端自动恢复中间件
   - ⏳ 任务心跳监控机制
   - ⏳ 状态检查 API 端点

3. **长期**（优化）：
   - 💡 分布式任务调度（避免单点故障）
   - 💡 任务重试队列（自动重试失败任务）
   - 💡 实时监控仪表盘（可视化任务状态）

### 7.3 使用建议

1. **立即使用**：
   - 前端：部署 StaleStatusDetector 组件（已集成）
   - 后端：运行一次修复脚本清理历史数据
   ```bash
   uv run python scripts/fix_stale_statuses.py --no-dry-run
   ```

2. **定期维护**：
   - 设置 cron job 每天自动检查
   - 监控僵尸状态数量
   - 分析异常任务的原因

3. **持续改进**：
   - 收集用户反馈
   - 优化超时阈值
   - 完善错误提示文案
