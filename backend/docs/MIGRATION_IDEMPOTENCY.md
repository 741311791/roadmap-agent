# Alembic 迁移幂等性修复

## 🐛 问题描述

部署时出现错误：

```
sqlalchemy.exc.ProgrammingError: (psycopg.errors.DuplicateTable) 
relation "intent_analysis_metadata" already exists
```

## 🔍 根本原因

启动脚本执行顺序：
1. `python scripts/create_tables.py` - 使用 SQLModel 创建所有表
2. `alembic upgrade head` - 执行 Alembic 迁移

**问题**：
- `create_tables.py` 使用 `SQLModel.metadata.create_all()` 创建了所有表（包括 `intent_analysis_metadata` 等）
- Alembic 迁移脚本 `add_agent_metadata_tables.py` 也尝试创建相同的表
- 导致冲突：表已存在

## ✅ 解决方案

### 修改迁移脚本，添加表存在性检查

让 Alembic 迁移脚本变为**幂等的**（可以安全重复执行）：

```python
def upgrade() -> None:
    # 获取数据库连接和 inspector
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # 只在表不存在时创建
    if 'intent_analysis_metadata' not in existing_tables:
        op.create_table(
            'intent_analysis_metadata',
            # ... 表定义
        )
        # 创建索引
        op.create_index(...)
```

### 修改的迁移文件

`backend/alembic/versions/add_agent_metadata_tables.py`
- ✅ 添加表存在性检查
- ✅ 只在表不存在时创建
- ✅ 避免与 `create_tables.py` 冲突

## 📋 幂等性原则

### 什么是幂等迁移？

**幂等迁移**是指可以安全地多次执行而不会出错的迁移脚本。

**好处**：
1. 可以与 `create_tables.py` 和平共存
2. 可以安全地重新运行（如修复失败的迁移）
3. 更健壮，不会因为部分失败而无法恢复

### 迁移脚本最佳实践

#### ✅ 推荐做法

**创建表**：
```python
from sqlalchemy import inspect

def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'my_table' not in existing_tables:
        op.create_table('my_table', ...)
```

**添加列**：
```python
from sqlalchemy import inspect

def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('my_table')]
    
    if 'new_column' not in columns:
        op.add_column('my_table', sa.Column('new_column', sa.String()))
```

**创建索引**：
```python
from sqlalchemy import inspect

def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    indexes = [idx['name'] for idx in inspector.get_indexes('my_table')]
    
    if 'ix_my_table_column' not in indexes:
        op.create_index('ix_my_table_column', 'my_table', ['column'])
```

#### ❌ 应避免的做法

**直接创建表（非幂等）**：
```python
def upgrade():
    # ❌ 如果表已存在会报错
    op.create_table('my_table', ...)
```

**假设表不存在**：
```python
def upgrade():
    # ❌ 可能导致重复执行失败
    op.add_column('my_table', sa.Column('new_column', sa.String()))
```

## 🔄 为什么需要 create_tables.py？

有人可能会问：既然有 Alembic，为什么还需要 `create_tables.py`？

### create_tables.py 的作用

1. **创建基础表结构**
   - 适用于全新数据库
   - 快速创建所有表，无需逐步执行迁移

2. **创建 LangGraph checkpoint 表**
   - 这些表不在 Alembic 管理范围内
   - 由 LangGraph 自己管理

3. **向后兼容**
   - 保持与旧部署脚本的兼容性

### Alembic 的作用

1. **增量变更**
   - 添加新列
   - 修改索引
   - 数据迁移

2. **版本控制**
   - 跟踪数据库 schema 变更历史
   - 支持回滚

3. **团队协作**
   - 确保所有环境的数据库一致
   - 代码审查和变更追踪

## 🎯 最佳实践

### 开发环境

```bash
# 1. 创建基础表
python scripts/create_tables.py

# 2. 执行迁移（幂等，不会报错）
alembic upgrade head
```

### 生产环境

```bash
# 1. 创建基础表（如果是全新数据库）
python scripts/create_tables.py

# 2. 检查迁移状态
python scripts/check_and_fix_migration.py

# 3. 执行迁移（幂等）
alembic upgrade head
```

### CI/CD Pipeline

```yaml
steps:
  - name: Initialize Database
    run: python scripts/create_tables.py
    
  - name: Check Migration State
    run: python scripts/check_and_fix_migration.py
    
  - name: Run Migrations
    run: alembic upgrade head
```

## 📚 相关资源

- [Alembic 官方文档](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Inspector API](https://docs.sqlalchemy.org/en/20/core/reflection.html)
- [幂等性原则](https://en.wikipedia.org/wiki/Idempotence)

## 🔧 故障排除

### 如果迁移仍然失败

1. **检查表是否存在**：
   ```sql
   SELECT table_name FROM information_schema.tables 
   WHERE table_schema = 'public';
   ```

2. **检查 Alembic 版本**：
   ```bash
   alembic current
   alembic history
   ```

3. **手动清理**（谨慎使用）：
   ```sql
   DROP TABLE IF EXISTS intent_analysis_metadata CASCADE;
   DELETE FROM alembic_version;
   ```

4. **重新运行迁移**：
   ```bash
   alembic upgrade head
   ```

