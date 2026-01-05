# 阿里云数据库配置快速参考

## 📊 连接数分配

| 环境 | 总连接数 | SQLAlchemy | LangGraph | 预留 | 余量 |
|------|---------|-----------|-----------|------|------|
| **研发** | 120 | 88 (峰值) | 10 | 10 | 12 ✅ |
| **生产** | 280 | 210 (峰值) | 20 | 20 | 30 ✅ |

---

## ⚙️ 研发环境配置

```bash
# backend/.env

# 环境标识
ENVIRONMENT=development

# 数据库连接池
DB_POOL_SIZE=4
DB_MAX_OVERFLOW=3

# FastAPI
UVICORN_WORKERS=4

# Celery Workers
CELERY_LOGS_CONCURRENCY=4
CELERY_CONTENT_CONCURRENCY=6
CELERY_WORKFLOW_CONCURRENCY=4
```

**进程计算**：
- FastAPI: 4 进程
- Celery: 5 + 7 + 5 = 17 进程
- 总计: 21 进程 × 7 连接 = **147 连接**（峰值 88）

---

## 🚀 生产环境配置

```bash
# backend/.env

# 环境标识
ENVIRONMENT=production

# 数据库连接池（可省略，使用默认值）
DB_POOL_SIZE=6
DB_MAX_OVERFLOW=4

# FastAPI（可省略，使用默认值）
UVICORN_WORKERS=8

# Celery Workers（可省略，使用默认值）
CELERY_LOGS_CONCURRENCY=8
CELERY_CONTENT_CONCURRENCY=10
CELERY_WORKFLOW_CONCURRENCY=6
```

**进程计算**：
- FastAPI: 8 进程
- Celery: 9 + 11 + 7 = 27 进程
- 总计: 35 进程 × 10 连接 = **350 连接**（峰值 210）

---

## 🔧 Railway 部署配置

### 1. API 服务

```bash
SERVICE_TYPE=api
ENVIRONMENT=production  # 或 development
# 其他环境变量（数据库、Redis、LLM Keys 等）
```

### 2. Celery Workers（三个服务）

| Worker | SERVICE_TYPE | 研发并发 | 生产并发 |
|--------|--------------|---------|---------|
| Logs | `celery_logs` | 4 | 8 |
| Content | `celery_content` | 6 | 10 |
| Workflow | `celery_workflow` | 4 | 6 |

**环境变量**：
- 生产环境：使用默认值（`railway_entrypoint.sh` 已配置）
- 研发环境：需要设置 `CELERY_*_CONCURRENCY` 覆盖默认值

---

## 📈 监控指标

### 数据库连接数查询

```sql
-- PostgreSQL 查询当前连接数
SELECT COUNT(*) AS total_connections
FROM pg_stat_activity
WHERE datname = 'roadmap_prod';  -- 或 roadmap_dev
```

### 应用健康检查

```bash
curl http://your-api-host/health
```

### Prometheus 告警

```promql
# 连接池使用率 > 80%
(db_pool_connections_in_use / db_pool_size) > 0.8

# 连接池超时
rate(db_pool_connection_timeouts_total[5m]) > 0
```

---

## ✅ 部署检查清单

### 研发环境

- [ ] 更新 `.env` 文件（`ENVIRONMENT=development`, `DB_POOL_SIZE=4` 等）
- [ ] 重启所有服务
- [ ] 验证日志：`langgraph_connection_pool_configured environment=development max_size=10`
- [ ] 检查连接池使用率 < 80%

### 生产环境

- [ ] 更新 Railway 环境变量（`ENVIRONMENT=production`）
- [ ] 确认默认并发配置正确（可省略显式设置）
- [ ] 重新部署所有服务
- [ ] 验证日志：`langgraph_connection_pool_configured environment=production max_size=20`
- [ ] 监控连接数（应该 < 250）
- [ ] 压力测试，确认无连接池耗尽错误

---

## 📚 详细文档

- **配置详情**: `backend/docs/20260104_阿里云数据库连接池配置.md`
- **问题修复**: `backend/docs/20260104_内容生成连接池耗尽修复.md`
- **部署脚本**: `backend/scripts/railway_entrypoint.sh`

---

## 🆘 故障排查

### 问题：连接池使用率 > 80%

**解决方案**：
1. 降低 Celery 并发数
2. 检查慢查询（添加索引）
3. 检查连接泄漏（代码 bug）

### 问题：仍然出现连接池超时

**解决方案**：
1. 确认 `ENVIRONMENT` 环境变量正确
2. 重启所有服务
3. 检查数据库实际连接数（SQL 查询）
4. 查看日志中的 `langgraph_connection_pool_configured`

---

**最后更新**: 2026-01-04  
**维护者**: Backend Team

