# Alembic 迁移修复说明

## 🐛 问题描述

部署到 Railway 后，应用启动时报错：

```
column roadmap_tasks.celery_task_id does not exist
```

## 🔍 根本原因

`railway_entrypoint.sh` 脚本使用了错误的 Alembic 命令：

```bash
# ❌ 错误的命令
alembic stamp head
```

### `alembic stamp` 的作用

`alembic stamp head` 只是**标记**数据库迁移版本为最新，但**不执行实际的迁移操作**。

- ✅ 更新 `alembic_version` 表中的版本号
- ❌ 不运行迁移脚本中的 `upgrade()` 函数
- ❌ 不修改表结构（不添加列、不修改索引等）

### `alembic upgrade` 的作用

`alembic upgrade head` 会**实际执行**所有待运行的迁移：

- ✅ 运行迁移脚本中的 `upgrade()` 函数
- ✅ 执行表结构变更（添加列、修改索引等）
- ✅ 更新 `alembic_version` 表中的版本号

---

## ✅ 解决方案

### 修复后的脚本

```bash
# ✅ 正确的命令
alembic upgrade head
```

### 完整的数据库初始化流程

```bash
# 1. 创建基础表结构（如果是全新数据库）
python scripts/create_tables.py

# 2. 检查并修复迁移状态（自动检测 stamp 导致的问题）
python scripts/check_and_fix_migration.py

# 3. 执行 Alembic 迁移（添加新列、修改结构等）
alembic upgrade head

# 4. 创建管理员账户
python scripts/create_admin_user.py || true
```

### 自动修复脚本

为了处理已经使用 `alembic stamp` 标记但未实际执行迁移的情况，我们添加了 `check_and_fix_migration.py` 脚本：

**功能**：
- 检查关键列是否存在（如 `roadmap_tasks.celery_task_id`）
- 检查 `alembic_version` 表中的版本标记
- 如果版本已标记但列不存在，自动清除版本标记
- 允许 `alembic upgrade head` 重新执行迁移

**使用**：
```bash
# 手动运行
python scripts/check_and_fix_migration.py

# 启动脚本会自动调用
```

---

## 📝 修改的文件

### 1. `backend/scripts/railway_entrypoint.sh`

**修改前：**
```bash
python scripts/create_tables.py
alembic stamp head  # ❌ 只标记，不执行
python scripts/create_admin_user.py || true
```

**修改后：**
```bash
echo "🔧 Creating base tables..."
python scripts/create_tables.py

echo "🔄 Running database migrations..."
alembic upgrade head  # ✅ 实际执行迁移

echo "👤 Creating admin user..."
python scripts/create_admin_user.py || true

echo "✅ Database initialization complete!"
```

### 2. 文档修复

- `backend/CELERY_RAILWAY_DEPLOYMENT_SUMMARY.md`
- `backend/DEPLOYMENT_COMPARISON.md`

---

## 🔄 如何应用修复

### 方式一：重新部署（推荐）

1. 提交并推送代码
2. Railway 会自动触发重新部署
3. 新的部署会执行 `alembic upgrade head`
4. 缺失的列会被自动添加

### 方式二：手动运行迁移

如果无法重新部署，可以手动运行迁移：

```bash
# 连接到 Railway PostgreSQL
railway connect <service-name>

# 在应用容器中运行
railway run alembic upgrade head
```

---

## 🧪 验证修复

部署后，检查日志中是否有：

```
🔧 Creating base tables...
🔄 Running database migrations...
✅ Database initialization complete!
```

如果迁移成功，应该能看到类似以下的输出：

```
INFO  [alembic.runtime.migration] Running upgrade add_waitlist_invite_fields -> c7e9f8b1a2d3, add celery_task_id to roadmap_tasks
```

---

## 📚 相关资源

### Alembic 命令对比

| 命令 | 作用 | 执行迁移 | 更新版本号 | 使用场景 |
|-----|------|---------|----------|---------|
| `alembic upgrade head` | 升级到最新版本 | ✅ 是 | ✅ 是 | **生产部署** |
| `alembic downgrade -1` | 回滚一个版本 | ✅ 是 | ✅ 是 | 回滚错误迁移 |
| `alembic stamp head` | 标记为最新版本 | ❌ 否 | ✅ 是 | 修复版本不一致 |
| `alembic current` | 查看当前版本 | ❌ 否 | ❌ 否 | 检查迁移状态 |
| `alembic history` | 查看迁移历史 | ❌ 否 | ❌ 否 | 查看所有迁移 |

### 何时使用 `stamp`？

`alembic stamp` 只应在特殊情况下使用：

1. **数据库已经是正确状态**，但 `alembic_version` 表中的版本号不对
2. **手动执行了迁移**（直接运行 SQL），需要更新版本号
3. **从非 Alembic 系统迁移**，需要标记初始版本

**在正常部署中，永远不要使用 `stamp`！**

---

## 🚨 注意事项

### 1. 只在 API 服务中运行迁移

```bash
case $SERVICE_TYPE in
  api)
    # ✅ 只在 API 服务中运行
    alembic upgrade head
    ;;
  celery_*)
    # ❌ Worker 不运行迁移
    ;;
esac
```

**原因**：
- 避免多个服务同时运行迁移（竞态条件）
- API 服务通常先启动，确保数据库就绪后再启动 Worker

### 2. 迁移失败后的处理

如果迁移失败（例如语法错误、约束冲突）：

```bash
# 1. 查看当前版本
alembic current

# 2. 查看迁移历史
alembic history

# 3. 回滚到上一个版本
alembic downgrade -1

# 4. 修复迁移脚本后重新升级
alembic upgrade head
```

### 3. 生产环境最佳实践

1. **在暂存环境测试迁移**
   ```bash
   # 测试升级
   alembic upgrade head
   
   # 测试回滚
   alembic downgrade -1
   ```

2. **备份数据库**（生产环境）
   ```bash
   # Railway 自动备份，也可手动备份
   pg_dump $DATABASE_URL > backup.sql
   ```

3. **使用迁移版本号**
   ```bash
   # 升级到特定版本（更可控）
   alembic upgrade c7e9f8b1a2d3
   ```

---

## 📖 参考文档

- [Alembic 官方文档](https://alembic.sqlalchemy.org/)
- [Alembic 命令参考](https://alembic.sqlalchemy.org/en/latest/api/commands.html)
- [Railway 部署指南](../QUICK_START_RAILWAY.md)

