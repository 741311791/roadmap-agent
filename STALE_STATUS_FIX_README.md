# 僵尸状态修复总结

## 🎯 问题

路线图中的概念状态停留在 `pending` 或 `generating`，但实际上没有任务在运行，导致前端一直显示"正在生成中"，用户无法操作。

## ✅ 解决方案

我们提供了**双层防护**机制：

### 1. 前端：智能超时检测 ⏰

**新增组件**：`frontend-next/components/common/stale-status-detector.tsx`

**功能**：
- ✅ 实时计时，显示已等待时间
- ✅ 默认 120 秒后自动提示超时
- ✅ 提供一键重试按钮
- ✅ 显示详细诊断信息
- ✅ 优雅的 UI 过渡

**效果预览**：
```
正常状态（0-120秒）         超时状态（120+秒）
┌──────────────────┐      ┌──────────────────┐
│  🔄 正在生成中   │  →   │  ⚠️ 生成超时     │
│  ⏱️ 已等待 1:35  │      │  ⏱️ 已等待 2:47  │
│  ▓▓▓▓▓░░ 79%    │      │  [重新生成]      │
└──────────────────┘      └──────────────────┘
```

### 2. 后端：自动状态恢复 🔧

**新增脚本**：`backend/scripts/fix_stale_statuses.py`

**功能**：
- ✅ 扫描所有僵尸状态
- ✅ 自动标记为 `failed`
- ✅ 生成诊断报告
- ✅ 支持预览和修复两种模式

**使用方式**：
```bash
# 预览模式（推荐先运行）
uv run python scripts/fix_stale_statuses.py --dry-run

# 实际修复
uv run python scripts/fix_stale_statuses.py --no-dry-run

# 定时任务（建议每天运行）
0 3 * * * cd /path/to/backend && uv run python scripts/fix_stale_statuses.py --no-dry-run
```

## 🚀 立即行动

### Step 1: 修复现有数据（后端）

```bash
cd backend
uv run python scripts/fix_stale_statuses.py --no-dry-run
```

### Step 2: 部署新代码（前端）

已自动集成到 `learning-stage.tsx`，无需额外配置。

### Step 3: 验证

1. 打开一个状态为 `pending` 的概念
2. 等待 2 分钟
3. 应该看到超时提示和重试按钮

## 📚 详细文档

- **问题分析**：`backend/docs/BUG_ANALYSIS_RESOURCES_ID.md`
- **完整方案**：`backend/docs/STALE_STATUS_SOLUTION.md`

## 🔥 快速参考

### 前端超时配置

```typescript
<StaleStatusDetector
  roadmapId={roadmapId}
  conceptId={conceptId}
  contentType="resources"
  status={concept.resources_status}
  preferences={userPreferences}
  timeoutSeconds={120}  // ← 可调整
  onSuccess={() => refetch()}
/>
```

### 后端脚本参数

```bash
--dry-run          # 预览模式（默认）
--no-dry-run       # 实际修复模式
--timeout 3600     # 超时阈值（秒）
```

## 🎨 用户体验

### 之前（问题状态）
```
用户：点击"学习资源" tab
系统：显示"正在获取中..."
用户：等待...
系统：永远加载中 ❌
用户：无法操作，感到困惑
```

### 现在（修复后）
```
用户：点击"学习资源" tab
系统：显示"正在获取中..."
用户：等待 2 分钟
系统：显示"获取超时"警告 ⚠️
系统：提供"重新获取"按钮 ✅
用户：点击重试
系统：重新生成成功 🎉
```

## 🛡️ 预防措施

### 监控建议

1. **定时检查**：每天自动运行修复脚本
2. **告警阈值**：僵尸状态数量 > 10 时发送告警
3. **日志记录**：记录所有超时和重试事件

### 最佳实践

1. **优雅停机**：服务器关闭前将 `generating` 改为 `pending`
2. **任务监控**：添加任务执行心跳机制
3. **快速失败**：任务超时后立即标记为失败

## 📊 影响评估

### 修复前
- ❌ 用户体验差：无限等待，无提示
- ❌ 数据不一致：僵尸状态积累
- ❌ 运维困难：需要手动排查

### 修复后
- ✅ 用户体验好：2 分钟后自动提示
- ✅ 数据一致：自动恢复机制
- ✅ 运维简单：一键修复脚本

## 🎯 总结

| 问题 | 解决方案 | 状态 |
|------|---------|------|
| 僵尸状态卡住 | 前端超时检测 | ✅ 已实现 |
| 无法重试 | 一键重试按钮 | ✅ 已实现 |
| 数据不一致 | 自动恢复脚本 | ✅ 已实现 |
| 缺少诊断信息 | 详细诊断面板 | ✅ 已实现 |
| 运维困难 | 定时任务支持 | ✅ 已实现 |

---

**需要帮助？** 查看完整文档：`backend/docs/STALE_STATUS_SOLUTION.md`
