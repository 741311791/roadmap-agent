# 本地错误日志文件 - 快速开始

## 🚀 一分钟启用

### 1. 在 `.env` 文件中添加配置

```bash
# 启用本地错误日志文件
ENABLE_ERROR_LOG_FILE=true
```

### 2. 启动服务

```bash
cd backend
make dev
```

### 3. 查看错误日志

```bash
# 实时查看
tail -f backend/logs/err.log

# 搜索特定错误
grep "ERROR" backend/logs/err.log

# 查看最近50行
tail -n 50 backend/logs/err.log
```

---

## 🧪 功能测试

运行测试脚本验证功能：

```bash
cd backend
uv run python scripts/test_error_log.py
```

**测试输出示例**：
```
======================================================================
错误日志文件功能测试
======================================================================

配置检查:
  ENABLE_ERROR_LOG_FILE: True
  ERROR_LOG_FILE_PATH: logs/err.log
  ERROR_LOG_FILE_MAX_SIZE: 10.0MB

日志文件:
  路径: logs/err.log
  存在: ✅ 是
  大小: 1234 字节 (1.2KB)

生成测试日志:
  ❌ DEBUG - 不会写入文件
  ❌ INFO - 不会写入文件
  ✅ WARNING - 已写入文件
  ✅ ERROR - 已写入文件
  ✅ CRITICAL - 已写入文件
  ✅ EXCEPTION - 已写入文件（包含堆栈）

======================================================================
✅ 测试完成
======================================================================
```

---

## 📋 日志格式

```log
2026-01-14 15:30:45 | WARNING  | app.agents.base | LLM调用超时，正在重试...
2026-01-14 15:31:02 | ERROR    | app.core.orchestrator.executor | 路线图生成失败
2026-01-14 15:31:02 | CRITICAL | app.db.session | 数据库连接池耗尽
```

**格式说明**：
- `时间戳` | `级别` | `日志来源` | `消息内容`
- 只收集 **WARNING**、**ERROR**、**CRITICAL** 级别
- 自动包含异常堆栈信息

---

## ⚙️ 高级配置

在 `.env` 文件中自定义配置：

```bash
# 是否启用（默认: false）
ENABLE_ERROR_LOG_FILE=true

# 日志文件路径（默认: logs/err.log）
ERROR_LOG_FILE_PATH=logs/err.log

# 单文件最大大小（默认: 10MB）
ERROR_LOG_FILE_MAX_SIZE=10485760
```

---

## 🔍 实用命令

### 实时监控
```bash
# 监控所有错误
tail -f backend/logs/err.log

# 监控特定类型错误
tail -f backend/logs/err.log | grep "database"
```

### 日志分析
```bash
# 统计错误级别分布
cat backend/logs/err.log | awk '{print $4}' | sort | uniq -c

# 查找特定路线图的错误
grep "rdmp_abc123" backend/logs/err.log

# 查看最近的Agent错误
grep "app.agents" backend/logs/err.log | tail -n 20
```

### 日志清理
```bash
# 清空日志文件
> backend/logs/err.log

# 或直接删除
rm backend/logs/err.log
```

---

## ❓ 常见问题

### Q: 日志文件没有生成？
**检查清单**：
1. ✅ `.env` 中设置了 `ENABLE_ERROR_LOG_FILE=true`
2. ✅ 服务已重启
3. ✅ 确实产生了 WARNING 或以上级别的日志

### Q: 日志文件会占用大量磁盘空间吗？
**不会**：单文件最大 10MB，超过自动覆盖，不保留备份。

### Q: 生产环境会启用吗？
**不会**：默认禁用，只有显式设置 `ENABLE_ERROR_LOG_FILE=true` 才会启用。

---

## 📚 详细文档

- **详细使用手册**：`backend/docs/20260114_本地错误日志文件功能.md`
- **总结文档**：`doc/20260114_本地错误日志文件功能完成.md`

---

## ✨ 特点总结

- ✅ **零侵入**：仅修改配置文件，不影响业务逻辑
- ✅ **仅本地**：默认禁用，生产环境零影响
- ✅ **可读性**：纯文本格式，易于查看和分析
- ✅ **自动轮转**：单文件最大 10MB，自动覆盖
- ✅ **多级别**：WARNING、ERROR、CRITICAL 全收集

---

**开发完成**：2026-01-14  
**架构影响**：最小（2个配置文件，73行代码）

