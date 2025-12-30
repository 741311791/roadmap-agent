# Celery Worker 启动指南

## 队列架构

重构后的系统使用 **3 个队列**：

### 1. `roadmap_workflow` 队列（新增，重量级）
**用途**：路线图生成和恢复的工作流任务
- `roadmap_generation.generate_roadmap` - 生成路线图
- `workflow_resume.resume_after_review` - 人工审核后恢复
- `workflow_resume.resume_from_checkpoint` - 从 checkpoint 恢复

**特点**：
- 执行完整的 LangGraph 工作流
- 包含所有 LLM 调用（Intent、Curriculum、Validation、Edit）
- 使用 AsyncPostgresSaver 保存 checkpoint
- 在 Human Review 处会暂停

### 2. `content_generation` 队列（现有，重量级）
**用途**：内容生成任务
- `generate_roadmap_content` - 批量生成内容
- `retry_tutorial_task` - 重试教程生成
- `retry_resources_task` - 重试资源推荐
- `retry_quiz_task` - 重试测验生成

**特点**：
- 并行生成 Tutorial、Resource、Quiz
- 支持断点续传（跳过已完成的 Concept）
- 包含大量 LLM 调用

### 3. `logs` 队列（现有，轻量级）
**用途**：日志批量写入
- `batch_write_logs` - 批量写入日志到数据库

**特点**：
- 轻量级任务
- 纯数据库写入，无 LLM 调用

---

## 启动方式

### 方式 1：启动所有队列（推荐用于开发环境）

```bash
cd backend

# 监听所有队列（logs, content_generation, roadmap_workflow）
celery -A app.core.celery_app worker \
  --loglevel=info \
  --concurrency=4 \
  -n worker@%h
```

**适用场景**：
- 开发环境
- 单机部署
- 资源充足的服务器

---

### 方式 2：分队列启动（推荐用于生产环境）

#### Worker 1: 路线图工作流（高优先级，低并发）
```bash
celery -A app.core.celery_app worker \
  --loglevel=info \
  --queues=roadmap_workflow \
  --concurrency=2 \
  -n workflow_worker@%h
```

**推荐配置**：
- 并发数：2-4
- 原因：LangGraph 工作流是顺序执行，但每个任务很重

#### Worker 2: 内容生成（高并发）
```bash
celery -A app.core.celery_app worker \
  --loglevel=info \
  --queues=content_generation \
  --concurrency=8 \
  -n content_worker@%h
```

**推荐配置**：
- 并发数：8-16
- 原因：内容生成是并行的，可以充分利用多核

#### Worker 3: 日志写入（低优先级）
```bash
celery -A app.core.celery_app worker \
  --loglevel=info \
  --queues=logs \
  --concurrency=2 \
  -n logs_worker@%h
```

**推荐配置**：
- 并发数：2
- 原因：日志任务轻量，避免抢占资源

---

### 方式 3：Railway/云部署配置

在 Railway 或其他云平台上，使用环境变量控制：

```bash
# Procfile 或启动命令
worker: celery -A app.core.celery_app worker --loglevel=info --concurrency=4 -n worker@%h

# 或分多个服务：
workflow_worker: celery -A app.core.celery_app worker --queues=roadmap_workflow --concurrency=2 -n workflow@%h
content_worker: celery -A app.core.celery_app worker --queues=content_generation --concurrency=8 -n content@%h
logs_worker: celery -A app.core.celery_app worker --queues=logs --concurrency=2 -n logs@%h
```

---

## 监控和管理

### 查看活动任务
```bash
celery -A app.core.celery_app inspect active
```

### 查看注册的任务
```bash
celery -A app.core.celery_app inspect registered
```

### 查看队列状态
```bash
celery -A app.core.celery_app inspect stats
```

### 使用 Flower 监控（可选）
```bash
# 安装 Flower
pip install flower

# 启动 Flower Web UI
celery -A app.core.celery_app flower --port=5555

# 访问 http://localhost:5555
```

---

## 常见问题

### Q1: 任务卡在队列中不执行？
**原因**：Worker 没有监听对应的队列
**解决**：检查 Worker 启动命令中的 `--queues` 参数

### Q2: Worker 内存占用过高？
**原因**：LangGraph 工作流和 LLM 调用占用大量内存
**解决**：
1. 降低 `--concurrency` 参数
2. 添加 `--max-tasks-per-child=100`（每 100 个任务重启进程）

### Q3: 任务执行超时？
**原因**：默认超时时间为 5 分钟
**解决**：在 `celery_app.py` 中调整：
```python
task_time_limit=600,  # 10 分钟硬超时
task_soft_time_limit=540,  # 9 分钟软超时
```

### Q4: 如何优雅停止 Worker？
```bash
# 等待当前任务完成后停止
celery -A app.core.celery_app control shutdown

# 或使用信号（推荐）
kill -TERM <worker_pid>
```

---

## 完整启动流程（开发环境）

```bash
# 1. 确保 Redis 正在运行
redis-cli ping  # 应该返回 PONG

# 2. 确保 PostgreSQL 正在运行
psql -U postgres -c "SELECT 1"

# 3. 启动 Celery Worker
cd backend
celery -A app.core.celery_app worker --loglevel=info

# 4. （新终端）启动 FastAPI
cd backend
uvicorn app.main:app --reload --port=8000

# 5. （可选）启动 Flower 监控
celery -A app.core.celery_app flower --port=5555
```

---

## 生产环境建议

1. **使用进程管理器**：Supervisor 或 systemd
2. **分离队列**：workflow、content、logs 分别启动
3. **监控告警**：集成 Sentry、Prometheus
4. **日志收集**：ELK Stack 或 Loki
5. **自动重启**：设置 `--max-tasks-per-child` 避免内存泄漏
6. **资源限制**：使用 Docker 容器限制 CPU 和内存

---

## 队列变更总结

| 队列 | 用途 | 任务数 | 并发建议 | 备注 |
|------|------|--------|----------|------|
| `roadmap_workflow` | 路线图生成和恢复 | 3 | 2-4 | 新增，重量级 |
| `content_generation` | 内容生成 | 4 | 8-16 | 现有，重量级 |
| `logs` | 日志写入 | 1 | 2 | 现有，轻量级 |

**总结**：原来只有 `content_generation` 队列用于内容生成，现在新增 `roadmap_workflow` 队列用于路线图生成和恢复任务。

