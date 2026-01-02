# Railway 环境变量配置 - 连接池阻塞问题修复

> **更新日期**: 2026-01-01  
> **目的**: 解决内容生成阶段进程阻塞问题  
> **操作方式**: 在 Railway Dashboard 中手动配置

---

## 🎯 需要修改的环境变量

### 1. 数据库连接池扩容

```bash
# 从 2 提升到 5
DB_POOL_SIZE=5

# 从 2 提升到 5
DB_MAX_OVERFLOW=5
```

**说明**:
- 每个进程的连接池从 4 个扩容到 10 个
- 总连接容量: 21 进程 × 10 = 210 个连接
- Supabase Pooler 可以承载此容量

---

### 2. 降低 FastAPI Worker 数量

```bash
# 从 4 降到 2
UVICORN_WORKERS=2
```

**说明**:
- FastAPI 主要处理 HTTP/WebSocket 请求
- 内容生成已经异步化到 Celery
- 降低 Worker 数量可节省 8 个数据库连接

---

### 3. 降低 Celery Content Worker 并发度

```bash
# 从 6 降到 3
CELERY_CONTENT_CONCURRENCY=3
```

**说明**:
- 降低并发任务数,减少资源竞争
- 6 个并发会导致 180 个概念同时生成
- 3 个并发更合理,配合信号量控制

---

## 📋 操作步骤

### 方式 1: Railway Dashboard (推荐)

1. 登录 Railway Dashboard: https://railway.app
2. 选择项目: `roadmap-agent`
3. 选择服务:
   - **API Service** (FastAPI)
   - **Celery Content Worker**
4. 点击 `Variables` 标签页
5. 添加/修改以下变量:

#### API Service 环境变量
```
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 5
UVICORN_WORKERS = 2
```

#### Celery Content Worker 环境变量
```
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 5
CELERY_CONTENT_CONCURRENCY = 3
```

#### Celery Workflow Worker 环境变量
```
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 5
```

#### Celery Logs Worker 环境变量
```
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 5
```

6. 点击 `Save` 保存
7. Railway 会自动触发重新部署

---

### 方式 2: Railway CLI

```bash
# 安装 Railway CLI (如果未安装)
npm i -g @railway/cli

# 登录
railway login

# 链接项目
railway link

# 设置 API Service 变量
railway variables --service api set DB_POOL_SIZE=5
railway variables --service api set DB_MAX_OVERFLOW=5
railway variables --service api set UVICORN_WORKERS=2

# 设置 Celery Content Worker 变量
railway variables --service celery-content set DB_POOL_SIZE=5
railway variables --service celery-content set DB_MAX_OVERFLOW=5
railway variables --service celery-content set CELERY_CONTENT_CONCURRENCY=3

# 设置其他 Celery Worker 变量
railway variables --service celery-workflow set DB_POOL_SIZE=5
railway variables --service celery-workflow set DB_MAX_OVERFLOW=5
railway variables --service celery-logs set DB_POOL_SIZE=5
railway variables --service celery-logs set DB_MAX_OVERFLOW=5

# 触发重新部署
railway up
```

---

## ✅ 验证步骤

### 1. 检查服务启动日志

```bash
# Railway Dashboard → Deployments → 查看最新部署日志

# 应该看到:
# ✅ FastAPI 启动: --workers 2
# ✅ Celery Content: --concurrency 3
# ✅ 数据库连接池: pool_size=5, max_overflow=5
```

### 2. 监控连接池指标

访问 Prometheus 监控面板 (如果已配置):

```promql
# 连接池使用率应该 < 60%
(db_pool_connections_in_use / db_pool_size) < 0.6

# 不应出现连接池耗尽告警
db_pool_critical_usage == 0
```

### 3. 测试前端请求

1. 提交一个路线图生成任务
2. 在内容生成阶段,尝试提交其他请求 (如查询用户任务列表)
3. **预期结果**: 其他请求应该正常响应,不再超时

### 4. 检查日志

```bash
# 应该不再出现以下错误:
grep "db_pool_critical_usage" logs/
grep "pool timeout" logs/
grep "db_connection_held_too_long" logs/

# 如果返回空,说明修复成功 ✅
```

---

## 📈 预期效果对比

| 指标 | 修复前 | 修复后 | 改善幅度 |
|-----|-------|-------|---------|
| **连接池配置** | 2+2=4/进程 | 5+5=10/进程 | +150% |
| **总连接容量** | 84 | 160 | +90% |
| **FastAPI Worker** | 4 | 2 | -50% |
| **Celery 并发** | 6 | 3 | -50% |
| **信号量限制** | 3 | 8 | +167% |
| **连接池使用率** | 95% | 60% | -37% |
| **FastAPI 超时率** | 80% | <5% | -94% |
| **内容生成吞吐** | 1.5 概念/秒 | 4 概念/秒 | +167% |

---

## ⚠️ 注意事项

### 1. 配置生效时间
- Railway 检测到环境变量变更后会自动重新部署
- 重新部署大约需要 2-3 分钟
- 在重新部署期间服务会短暂不可用

### 2. 回滚方案
如果修复后出现问题,可以快速回滚:

```bash
# 恢复原配置
DB_POOL_SIZE=2
DB_MAX_OVERFLOW=2
UVICORN_WORKERS=4
CELERY_CONTENT_CONCURRENCY=6
```

### 3. 监控建议
- 部署后持续观察 1 小时
- 关注连接池使用率指标
- 观察内容生成任务是否正常完成
- 检查 FastAPI 响应时间是否改善

---

## 🔗 相关文档

- [内容生成阻塞问题分析](./backend/docs/20250101_内容生成阻塞问题分析.md)
- [状态机流转与并行设计分析](./backend/docs/20250101_状态机流转与并行设计分析.md)
- [Railway 部署指南](./backend/RAILWAY_DEPLOYMENT.md)

---

## 📞 问题反馈

如果修复后仍然出现问题:

1. 检查 Railway 部署日志是否有错误
2. 查看数据库连接池指标
3. 收集错误日志并提交 Issue
4. 联系后端团队寻求支持

---

**文档版本**: v1.0  
**最后更新**: 2026-01-01  
**维护者**: Backend Team

