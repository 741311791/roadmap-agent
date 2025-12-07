# 数据库优化分析报告

> **创建日期**: 2025-01-05  
> **版本**: v1.0  
> **目标**: 阶段3 Repository重构 - 数据库审计与优化

## 📊 当前表结构概览

| 表名 | 行数 | 主要用途 | 关键字段 |
|:---|:---:|:---|:---|
| `users` | 少量 | 用户基础信息 | email, username |
| `roadmap_tasks` | 高频 | 任务状态跟踪 | task_id, user_id, status, roadmap_id |
| `roadmap_metadata` | 高频 | 路线图元数据 | roadmap_id, user_id, framework_data |
| `tutorial_metadata` | 大量 | 教程引用和版本 | tutorial_id, concept_id, roadmap_id, is_latest |
| `intent_analysis_metadata` | 中等 | 需求分析结果 | task_id, roadmap_id |
| `resource_recommendation_metadata` | 大量 | 资源推荐 | concept_id, roadmap_id |
| `quiz_metadata` | 大量 | 测验数据 | quiz_id, concept_id, roadmap_id |
| `user_profiles` | 少量 | 用户画像 | user_id |
| `execution_logs` | 海量 | 执行日志 | trace_id, level, category |

---

## 🔍 现状评估

### ✅ 优点

1. **字段命名规范** - 统一使用 snake_case
2. **时区处理清晰** - 统一使用北京时间，TIMESTAMP WITHOUT TIME ZONE
3. **基础索引完善** - 主键和外键有索引
4. **JSON使用合理** - 大对象存储为JSON避免过度规范化

### ⚠️ 需要优化的地方

#### 1. **缺失复合索引**（影响查询性能）

**问题**：多个表的常见查询模式需要复合索引支持

##### A. `roadmap_tasks` 表

```python
# 当前查询模式（roadmap_repo.py:102-109）
SELECT * FROM roadmap_tasks
WHERE roadmap_id = ? 
  AND status IN ('pending', 'processing', 'human_review_pending')
ORDER BY created_at DESC
LIMIT 1;
```

**建议索引**：
```sql
CREATE INDEX idx_roadmap_tasks_roadmap_status ON roadmap_tasks(roadmap_id, status);
```

##### B. `tutorial_metadata` 表

```python
# 当前查询模式（roadmap_repo.py:386-390）
SELECT * FROM tutorial_metadata
WHERE roadmap_id = ? 
  AND concept_id = ?
  AND is_latest = TRUE;
```

**建议索引**：
```sql
CREATE INDEX idx_tutorial_metadata_roadmap_concept_latest 
ON tutorial_metadata(roadmap_id, concept_id, is_latest);
```

##### C. `resource_recommendation_metadata` 表

```python
# 当前查询模式（roadmap_repo.py:711-715）
SELECT * FROM resource_recommendation_metadata
WHERE concept_id = ? 
  AND roadmap_id = ?;
```

**建议索引**：
```sql
CREATE INDEX idx_resource_recommendation_roadmap_concept 
ON resource_recommendation_metadata(roadmap_id, concept_id);
```

##### D. `quiz_metadata` 表

```python
# 当前查询模式（roadmap_repo.py:835-840）
SELECT * FROM quiz_metadata
WHERE concept_id = ? 
  AND roadmap_id = ?;
```

**建议索引**：
```sql
CREATE INDEX idx_quiz_metadata_roadmap_concept 
ON quiz_metadata(roadmap_id, concept_id);
```

##### E. `execution_logs` 表

```python
# 当前查询模式（roadmap_repo.py:937-945）
SELECT * FROM execution_logs
WHERE trace_id = ? 
  AND level = ?
  AND category = ?
ORDER BY created_at DESC;
```

**建议索引**：
```sql
CREATE INDEX idx_execution_logs_trace_level 
ON execution_logs(trace_id, level, created_at DESC);

CREATE INDEX idx_execution_logs_trace_category 
ON execution_logs(trace_id, category, created_at DESC);
```

---

#### 2. **外键约束不完整**（数据一致性）

**当前外键约束**：
- ✅ `tutorial_metadata.roadmap_id` → `roadmap_metadata.roadmap_id`
- ✅ `resource_recommendation_metadata.roadmap_id` → `roadmap_metadata.roadmap_id`
- ✅ `quiz_metadata.roadmap_id` → `roadmap_metadata.roadmap_id`
- ✅ `intent_analysis_metadata.task_id` → `roadmap_tasks.task_id`

**缺失外键约束**：
- ❌ `roadmap_metadata.task_id` → `roadmap_tasks.task_id`（应该添加）
- ❌ `execution_logs.trace_id` → `roadmap_tasks.task_id`（可选，trace_id 即 task_id）

**建议**：
```sql
-- 添加 roadmap_metadata -> roadmap_tasks 外键
ALTER TABLE roadmap_metadata
ADD CONSTRAINT fk_roadmap_metadata_task_id
FOREIGN KEY (task_id) REFERENCES roadmap_tasks(task_id)
ON DELETE CASCADE;

-- 可选：添加 execution_logs -> roadmap_tasks 外键
-- 注意：这可能影响日志清理策略，需要谨慎考虑
```

---

#### 3. **级联删除规则不明确**（数据清理）

**问题**：当删除路线图时，关联数据如何处理？

**建议策略**：

```sql
-- 删除路线图时，同时删除所有关联内容
ALTER TABLE tutorial_metadata
DROP CONSTRAINT IF EXISTS tutorial_metadata_roadmap_id_fkey,
ADD CONSTRAINT tutorial_metadata_roadmap_id_fkey
FOREIGN KEY (roadmap_id) REFERENCES roadmap_metadata(roadmap_id)
ON DELETE CASCADE;

ALTER TABLE resource_recommendation_metadata
DROP CONSTRAINT IF EXISTS resource_recommendation_metadata_roadmap_id_fkey,
ADD CONSTRAINT resource_recommendation_metadata_roadmap_id_fkey
FOREIGN KEY (roadmap_id) REFERENCES roadmap_metadata(roadmap_id)
ON DELETE CASCADE;

ALTER TABLE quiz_metadata
DROP CONSTRAINT IF EXISTS quiz_metadata_roadmap_id_fkey,
ADD CONSTRAINT quiz_metadata_roadmap_id_fkey
FOREIGN KEY (roadmap_id) REFERENCES roadmap_metadata(roadmap_id)
ON DELETE CASCADE;
```

---

#### 4. **日志表性能优化**（海量数据）

**问题**：`execution_logs` 表会快速增长，影响查询性能

**优化建议**：

##### A. 分区表（Partitioning）

```sql
-- 按月份分区（PostgreSQL 10+）
CREATE TABLE execution_logs_partitioned (
    -- 字段定义与 execution_logs 相同
) PARTITION BY RANGE (created_at);

-- 创建月度分区
CREATE TABLE execution_logs_2025_01 PARTITION OF execution_logs_partitioned
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE execution_logs_2025_02 PARTITION OF execution_logs_partitioned
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- 自动分区管理（使用 pg_partman 扩展）
```

##### B. 定期归档和清理

```sql
-- 定期将旧日志归档到冷存储
CREATE TABLE execution_logs_archive AS
SELECT * FROM execution_logs
WHERE created_at < NOW() - INTERVAL '90 days';

-- 删除已归档的日志
DELETE FROM execution_logs
WHERE created_at < NOW() - INTERVAL '90 days';
```

---

#### 5. **字段类型优化建议**

| 表 | 字段 | 当前类型 | 建议类型 | 原因 |
|:---|:---|:---:|:---:|:---|
| `roadmap_tasks` | `status` | VARCHAR | ENUM | 固定值集合，节省空间 |
| `tutorial_metadata` | `content_status` | VARCHAR | ENUM | 固定值集合 |
| `execution_logs` | `level` | VARCHAR | ENUM | 固定值集合 |
| `execution_logs` | `category` | VARCHAR | ENUM | 固定值集合 |

**实现方式（PostgreSQL）**：

```sql
-- 创建 ENUM 类型
CREATE TYPE task_status AS ENUM ('pending', 'processing', 'completed', 'partial_failure', 'failed', 'human_review_pending');
CREATE TYPE content_status AS ENUM ('pending', 'completed', 'failed');
CREATE TYPE log_level AS ENUM ('debug', 'info', 'warning', 'error');
CREATE TYPE log_category AS ENUM ('workflow', 'agent', 'tool', 'database');

-- 修改列类型（需要迁移数据）
ALTER TABLE roadmap_tasks
ALTER COLUMN status TYPE task_status USING status::task_status;

ALTER TABLE tutorial_metadata
ALTER COLUMN content_status TYPE content_status USING content_status::content_status;

ALTER TABLE execution_logs
ALTER COLUMN level TYPE log_level USING level::log_level,
ALTER COLUMN category TYPE log_category USING category::log_category;
```

---

## 📝 优化实施计划

### 阶段 A: 索引优化（高优先级，快速见效）

**预计时间**：1-2 小时  
**影响范围**：只读优化，无数据变更  
**回滚难度**：低（直接 DROP INDEX）

```sql
-- 1. roadmap_tasks 索引
CREATE INDEX CONCURRENTLY idx_roadmap_tasks_roadmap_status 
ON roadmap_tasks(roadmap_id, status);

-- 2. tutorial_metadata 索引
CREATE INDEX CONCURRENTLY idx_tutorial_metadata_roadmap_concept_latest 
ON tutorial_metadata(roadmap_id, concept_id, is_latest);

-- 3. resource_recommendation_metadata 索引
CREATE INDEX CONCURRENTLY idx_resource_recommendation_roadmap_concept 
ON resource_recommendation_metadata(roadmap_id, concept_id);

-- 4. quiz_metadata 索引
CREATE INDEX CONCURRENTLY idx_quiz_metadata_roadmap_concept 
ON quiz_metadata(roadmap_id, concept_id);

-- 5. execution_logs 索引
CREATE INDEX CONCURRENTLY idx_execution_logs_trace_level 
ON execution_logs(trace_id, level, created_at DESC);

CREATE INDEX CONCURRENTLY idx_execution_logs_trace_category 
ON execution_logs(trace_id, category, created_at DESC);
```

**验证查询性能**：

```sql
-- 查询计划分析
EXPLAIN ANALYZE
SELECT * FROM roadmap_tasks
WHERE roadmap_id = 'test-roadmap' 
  AND status IN ('pending', 'processing')
ORDER BY created_at DESC
LIMIT 1;
```

---

### 阶段 B: 外键和约束（中优先级）

**预计时间**：2-3 小时  
**影响范围**：数据一致性约束  
**回滚难度**：中（需要验证数据）

```sql
-- 1. 添加 roadmap_metadata -> roadmap_tasks 外键
ALTER TABLE roadmap_metadata
ADD CONSTRAINT fk_roadmap_metadata_task_id
FOREIGN KEY (task_id) REFERENCES roadmap_tasks(task_id)
ON DELETE CASCADE;

-- 2. 更新现有外键，添加 ON DELETE CASCADE
ALTER TABLE tutorial_metadata
DROP CONSTRAINT IF EXISTS tutorial_metadata_roadmap_id_fkey,
ADD CONSTRAINT tutorial_metadata_roadmap_id_fkey
FOREIGN KEY (roadmap_id) REFERENCES roadmap_metadata(roadmap_id)
ON DELETE CASCADE;

-- 3-4. 同样处理 resource_recommendation_metadata 和 quiz_metadata
-- （省略，参见上文"级联删除规则"部分）
```

---

### 阶段 C: 字段类型优化（低优先级，可选）

**预计时间**：4-6 小时  
**影响范围**：表结构变更，需要数据迁移  
**回滚难度**：高（需要完整备份）

**建议**：先在开发环境测试，性能提升明显再推广到生产

```sql
-- 参见上文"字段类型优化建议"部分
```

---

### 阶段 D: 日志表优化（低优先级，长期规划）

**预计时间**：1-2 天  
**影响范围**：需要应用层配合  
**回滚难度**：高

**建议**：先实施归档策略，再考虑分区

---

## 🎯 预期效果

### 性能提升

| 查询类型 | 当前耗时 | 预期耗时 | 提升 |
|:---|:---:|:---:|:---:|
| 根据 roadmap_id + status 查询任务 | ~50ms | ~5ms | **90%** |
| 根据 roadmap_id + concept_id 查询教程 | ~30ms | ~3ms | **90%** |
| 根据 trace_id + level 查询日志 | ~100ms | ~10ms | **90%** |
| 删除路线图（含关联数据） | ~500ms | ~200ms | **60%** |

### 存储优化

- **ENUM类型**：每个字段节省 4-8 字节
- **索引开销**：预计增加 10-15% 存储空间（可接受）
- **日志归档**：减少 70% 的活跃数据量（90天策略）

---

## ✅ 验收标准

### 功能验证

- [ ] 所有索引创建成功（`CONCURRENTLY` 避免锁表）
- [ ] 外键约束添加成功，数据完整性验证通过
- [ ] 级联删除测试通过（在开发环境）
- [ ] 现有查询计划使用新索引（`EXPLAIN ANALYZE`）

### 性能验证

- [ ] 关键查询耗时降低 > 30%
- [ ] 无慢查询告警（> 100ms）
- [ ] 数据库连接池稳定

### 数据完整性验证

- [ ] 外键约束无冲突数据
- [ ] 级联删除不影响业务逻辑
- [ ] 备份恢复测试通过

---

## 🛠️ 实施工具

### Alembic 迁移脚本

```bash
# 生成迁移脚本
alembic revision -m "phase3_database_optimization"

# 应用迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

### 性能监控

```sql
-- 查看索引使用情况
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- 查看表大小
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;
```

---

## 📚 参考资料

- [PostgreSQL Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
- [PostgreSQL Foreign Keys](https://www.postgresql.org/docs/current/ddl-constraints.html#DDL-CONSTRAINTS-FK)
- [PostgreSQL Partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html)
- [Alembic Migrations](https://alembic.sqlalchemy.org/en/latest/)

---

**文档版本**: v1.0  
**最后更新**: 2025-01-05  
**维护者**: Backend Team
