# 数据库连接池优化 - 快速部署指南

## 修改摘要

优化了数据库连接池配置，解决了线上连接池耗尽的问题。

### 修改的文件

1. `backend/app/db/session.py` - SQLAlchemy 连接池配置
2. `backend/app/core/orchestrator_factory.py` - Checkpointer 连接池配置

---

## 部署步骤

### 1. 提交代码
```bash
cd /Users/louie/Documents/Vibecoding/roadmap-agent

git add backend/app/db/session.py
git add backend/app/core/orchestrator_factory.py
git add doc/DATABASE_CONNECTION_POOL_EXHAUSTION_FIX.md

git commit -m "fix: 优化数据库连接池配置，解决连接池耗尽问题

- 降低 SQLAlchemy 连接池大小：pool_size=10, max_overflow=20
- 缩短连接回收时间：pool_recycle=1800 (30分钟)
- 使用 LIFO 模式优先复用热连接
- 改进 get_db() 使用 context manager 确保连接释放
- 降低 Checkpointer 连接池：min_size=1, max_size=5
- 总连接数从 ~70 降至 ~35，优化 50%"

git push origin main
```

### 2. 等待自动部署
Railway 会自动检测代码更新并重新部署：
- 预计时间：3-5 分钟
- 无需手动重启服务

### 3. 验证部署
部署完成后，检查日志：

```bash
# 在 Railway Dashboard 查看日志，应该看到：
# orchestrator_factory_initialized pool_min_size=1 pool_max_size=5
```

---

## 回滚计划

如果部署后出现问题，可以快速回滚：

```bash
git revert HEAD
git push origin main
```

---

## 监控指标

### 部署后 1 小时内监控：

1. **错误率**：应降为 0
   - ❌ 修复前：频繁出现 `QueuePool limit reached`
   - ✅ 修复后：无连接池错误

2. **响应时间**：应保持稳定
   - `/api/v1/featured` 端点 < 500ms

3. **数据库连接数**：
   ```sql
   SELECT count(*) FROM pg_stat_activity 
   WHERE datname = 'roadmap_db' AND application_name = 'roadmap_agent';
   ```
   - 预期：10~35 个连接

---

## 常见问题

### Q1: 降低连接数会影响性能吗？
**A**: 不会。原配置过大导致连接泄漏，降低后反而更稳定。

### Q2: 如果还是出现连接超时怎么办？
**A**: 
1. 检查是否有长时间运行的查询（可能需要优化）
2. 考虑增加 `pool_size` 到 15（但不建议超过 20）
3. 考虑引入 PgBouncer 连接池代理

### Q3: 为什么使用 LIFO 模式？
**A**: LIFO 优先使用最近的连接，减少冷连接数量，提高性能。

---

## 联系人

如有问题，请查看详细文档：
- `doc/DATABASE_CONNECTION_POOL_EXHAUSTION_FIX.md`

