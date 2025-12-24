# 僵尸状态检测与修复 - 完整报告

> **日期**: 2025-12-12  
> **问题**: concept_id为`rag-enterprise-knowledge-base-d4e2f1c8:c-3-1-2`的学习资源一直显示"Fetching Learning Resources"  
> **状态**: ✅ 已完成

---

## 🔍 问题诊断

### 用户报告的问题
- **路线图 ID**: `rag-enterprise-knowledge-base-d4e2f1c8`
- **概念 ID**: `rag-enterprise-knowledge-base-d4e2f1c8:c-3-1-2`
- **内容类型**: `resources`
- **状态**: `pending`
- **现象**: 前端一直显示"Fetching Learning Resources"，但没有任务在运行

### 根本原因分析

通过后端脚本检查发现：

1. **卡住的任务**：
   ```
   任务 ID: retry-resources-rag-ente-724be140
   类型: retry_resources
   状态: processing
   当前步骤: resource_recommendation
   运行时长: 26分钟
   ```
   
   该任务已运行26分钟，明显超时卡住。

2. **其他僵尸任务**：
   - 2个创建任务运行了5天（`fastapi-asynchronous-web-development-b8c7d6e5`）
   - 81个概念处于僵尸状态（状态为`pending`/`generating`但无活跃任务）

3. **前端问题**：
   - 前端使用的是 `GeneratingContentLoader` 组件
   - 该组件**不包含超时检测**，完全依赖 WebSocket 推送
   - 当任务卡住时，WebSocket 不会推送更新，导致前端永远卡在加载状态

---

## ✅ 解决方案

### 1. 后端修复

#### 1.1 修复卡住的任务

**脚本**: `backend/scripts/fix_stuck_tasks.py`

**功能**:
- 扫描运行时间超过5分钟的任务
- 将任务状态标记为 `failed`
- 更新路线图中对应概念的状态为 `failed`

**执行结果**:
```bash
cd backend
uv run python scripts/fix_stuck_tasks.py --no-dry-run --timeout 300
```

修复了3个卡住的任务：
- `retry-resources-rag-ente-724be140` (26分钟)
- `33b92b00-e983-4cde-902d-3ca1d6461204` (5天)
- `39a065db-7a4e-4e26-b436-6e304f73af36` (5天)

#### 1.2 修复僵尸状态

**脚本**: `backend/scripts/fix_stale_statuses_v2.py`

**功能**:
- 扫描所有路线图
- 检查是否有活跃任务
- 如果没有活跃任务，将 `pending`/`generating` 状态标记为 `failed`

**执行结果**:
```bash
cd backend
uv run python scripts/fix_stale_statuses_v2.py --no-dry-run
```

修复了81个僵尸状态概念（主要在 `fastapi-asynchronous-web-development-b4c5d6e7` 路线图）

#### 1.3 验证 API

**端点**: `GET /api/v1/roadmaps/{roadmap_id}/status-check`

**测试结果**:
```bash
curl "http://localhost:8000/api/v1/roadmaps/rag-enterprise-knowledge-base-d4e2f1c8/status-check"
```

返回：
```json
{
  "roadmap_id": "rag-enterprise-knowledge-base-d4e2f1c8",
  "has_active_task": false,
  "active_tasks": [],
  "stale_concepts": [
    {
      "concept_id": "rag-enterprise-knowledge-base-d4e2f1c8:c-3-1-2",
      "concept_name": "前端界面原型（可选）",
      "content_type": "resources",
      "current_status": "pending"
    }
  ]
}
```

✅ API 正常工作，正确检测到僵尸状态

---

### 2. 前端修复

#### 2.1 重新引入僵尸状态检测器

**文件**: `frontend-next/components/roadmap/immersive/learning-stage.tsx`

**修改内容**:

1. **导入 StaleStatusDetector**:
   ```typescript
   import { StaleStatusDetector } from '@/components/common/stale-status-detector';
   ```

2. **替换 Tutorial 加载状态**:
   ```typescript
   {tutorialGenerating || tutorialPending ? (
     roadmapId && concept && userPreferences ? (
       <StaleStatusDetector
         roadmapId={roadmapId}
         conceptId={concept.concept_id}
         contentType="tutorial"
         status={concept.content_status}
         preferences={userPreferences}
         timeoutSeconds={120}
         onSuccess={() => onRetrySuccess?.()}
       />
     ) : (
       <GeneratingContentLoader contentType="tutorial" />
     )
   ) : ...}
   ```

3. **替换 Resources 加载状态**:
   ```typescript
   {resourcesGenerating || resourcesPending ? (
     roadmapId && concept && userPreferences ? (
       <StaleStatusDetector
         roadmapId={roadmapId}
         conceptId={concept.concept_id}
         contentType="resources"
         status={concept.resources_status}
         preferences={userPreferences}
         timeoutSeconds={120}
         onSuccess={() => onRetrySuccess?.()}
       />
     ) : (
       <GeneratingContentLoader contentType="resources" />
     )
   ) : ...}
   ```

4. **替换 Quiz 加载状态**:
   ```typescript
   {quizGenerating || quizPending ? (
     roadmapId && concept && userPreferences ? (
       <StaleStatusDetector
         roadmapId={roadmapId}
         conceptId={concept.concept_id}
         contentType="quiz"
         status={concept.quiz_status}
         preferences={userPreferences}
         timeoutSeconds={120}
         onSuccess={() => onRetrySuccess?.()}
       />
     ) : (
       <GeneratingContentLoader contentType="quiz" />
     )
   ) : ...}
   ```

#### 2.2 StaleStatusDetector 工作原理

**组件**: `frontend-next/components/common/stale-status-detector.tsx`

**双层检测机制**:

1. **主动检测（0-5秒）**:
   - 组件加载时立即调用 `checkRoadmapStatusQuick(roadmapId)` API
   - 检查当前概念是否在僵尸状态列表中
   - 如果是，立即显示超时警告和重试按钮

2. **兜底检测（120秒）**:
   - 如果主动检测未发现问题，启动计时器
   - 120秒后仍未完成，显示超时警告

**优势**:
- ✅ 快速响应（3-5秒内检测到僵尸状态）
- ✅ 双重保障（API检测 + 超时兜底）
- ✅ 用户友好（显示已等待时间、提供重试按钮）

---

## 📊 修复统计

### 后端
- ✅ 修复卡住的任务: **3个**
- ✅ 修复僵尸状态概念: **81个**
- ✅ 验证 API 正常工作: **通过**

### 前端
- ✅ 重新引入僵尸状态检测器: **3个位置** (tutorial, resources, quiz)
- ✅ 代码检查: **无错误**

---

## 🚀 验证步骤

### 1. 后端验证

```bash
# 检查是否还有卡住的任务
cd backend
uv run python scripts/check_task_status.py --list

# 检查特定路线图的僵尸状态
curl "http://localhost:8000/api/v1/roadmaps/rag-enterprise-knowledge-base-d4e2f1c8/status-check" | python3 -m json.tool
```

### 2. 前端验证

1. 打开路线图: `rag-enterprise-knowledge-base-d4e2f1c8`
2. 导航到概念: `c-3-1-2` (前端界面原型)
3. 切换到 "Learning Resources" tab
4. **预期行为**:
   - 立即调用 status-check API
   - 3-5秒内检测到僵尸状态
   - 显示超时警告和重试按钮

### 3. 重试验证

1. 点击"重新获取资源"按钮
2. 后端创建新的重试任务
3. WebSocket 订阅任务状态
4. **预期行为**:
   - 显示"Fetching Learning Resources"
   - 如果任务正常完成，显示资源列表
   - 如果任务再次卡住，120秒后显示超时警告

---

## 🔧 维护建议

### 1. 定期清理僵尸状态

**建议**: 设置定时任务，每天凌晨3点运行

```bash
# crontab
0 3 * * * cd /path/to/backend && uv run python scripts/fix_stale_statuses_v2.py --no-dry-run
```

### 2. 监控卡住的任务

**建议**: 设置告警，当任务运行超过10分钟时发送通知

```bash
# 检查脚本
uv run python scripts/check_task_status.py --list
```

### 3. 优化任务超时设置

**当前设置**:
- 后端任务超时: 5分钟
- 前端检测超时: 120秒

**建议**:
- 根据实际运行情况调整超时阈值
- 对于资源推荐任务，可以设置为3分钟
- 对于教程生成任务，可以设置为5分钟

---

## 📝 相关文件

### 后端脚本
- `backend/scripts/fix_stuck_tasks.py` - 修复卡住的任务
- `backend/scripts/fix_stale_statuses_v2.py` - 修复僵尸状态
- `backend/scripts/check_task_status.py` - 检查任务状态

### 前端组件
- `frontend-next/components/common/stale-status-detector.tsx` - 僵尸状态检测器
- `frontend-next/components/common/generating-content-loader.tsx` - 简单加载指示器
- `frontend-next/components/roadmap/immersive/learning-stage.tsx` - 学习页面（已更新）

### API 端点
- `GET /api/v1/roadmaps/{roadmap_id}/status-check` - 快速状态检查
- `GET /api/v1/roadmaps/{roadmap_id}/active-task` - 获取活跃任务

---

## ✅ 总结

### 问题
- 用户报告的概念一直卡在"Fetching Learning Resources"
- 后端任务已卡住26分钟
- 前端没有超时检测机制

### 解决
1. ✅ 修复了3个卡住的任务
2. ✅ 修复了81个僵尸状态概念
3. ✅ 在前端重新引入僵尸状态检测器
4. ✅ 验证了 status-check API 正常工作

### 效果
- 🚀 快速检测（3-5秒）
- 🛡️ 双重保障（API + 超时）
- 👍 用户友好（显示进度、提供重试）

### 下一步
- 用户刷新页面，应该看到重试按钮
- 点击重试后，任务应该正常完成
- 如果再次卡住，120秒后会自动提示

