# 真实端到端测试指南

本文档描述如何运行真实的端到端测试，测试完整的路线图生成流程（不使用 Mock）。

## 测试概述

真实端到端测试会：
1. 启动真实的 FastAPI 服务（HTTP API）
2. 启动真实的 Celery Worker（后台任务处理）
3. 发送真实的HTTP请求
4. 调用真实的 LLM（OpenAI/Anthropic）
5. 执行真实的数据库操作
6. 验证完整的工作流

## 前置条件

### 1. 环境变量配置

确保 `.env` 文件包含所有必需的环境变量：

```bash
# 数据库
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/roadmap_test

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Tavily搜索
TAVILY_API_KEY=tvly-...

# JWT密钥
SECRET_KEY=your-secret-key
```

### 2. 依赖服务启动

确保以下服务已启动：

```bash
# PostgreSQL（测试数据库）
docker-compose -f docker-compose.test.yml up -d postgres

# Redis（消息队列）
docker-compose -f docker-compose.test.yml up -d redis
```

验证服务可用：

```bash
# 检查 PostgreSQL
psql postgresql://user:password@localhost:5432/roadmap_test -c "SELECT 1"

# 检查 Redis
redis-cli -h localhost -p 6379 ping
```

## 运行测试

### 方式一：自动化脚本（推荐）

使用提供的脚本一键启动所有服务并运行测试：

```bash
# 1. 启动所有服务（FastAPI + Celery Worker）
cd backend
./scripts/run_e2e_test_services.sh start

# 2. 查看服务状态
./scripts/run_e2e_test_services.sh status

# 3. 运行测试（在新终端）
pytest tests/e2e/test_real_roadmap_generation_e2e.py -v -s

# 4. 查看实时日志（在新终端）
./scripts/run_e2e_test_services.sh logs

# 5. 停止所有服务
./scripts/run_e2e_test_services.sh stop
```

### 方式二：手动启动（调试用）

适用于需要详细控制每个服务的场景。

#### 终端1：启动 FastAPI

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**日志输出示例：**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 终端2：启动 Celery Worker

```bash
cd backend
celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --pool=prefork
```

**日志输出示例：**
```
[2026-01-11 10:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379//
[2026-01-11 10:00:00,001: INFO/MainProcess] celery@hostname ready.
[2026-01-11 10:00:00,002: INFO/MainProcess] Tasks:
  . roadmap_generation.generate_roadmap
  . workflow_resume.resume_workflow
```

#### 终端3：运行测试

```bash
cd backend
pytest tests/e2e/test_real_roadmap_generation_e2e.py -v -s --log-cli-level=INFO
```

## 测试用例说明

### 1. `test_complete_roadmap_generation_flow`

**测试目标：** 完整的路线图生成流程

**测试步骤：**
1. 创建测试用户并登录
2. 提交路线图生成请求
3. 轮询任务状态直到完成
4. 验证生成的路线图数据
5. 清理测试数据

**预期耗时：** 2-5 分钟（取决于 LLM 响应速度）

**验证点：**
- ✅ API 返回正确的 `task_id`
- ✅ Celery 任务成功执行
- ✅ 路线图框架生成正确（包含 Stage > Module > Concept）
- ✅ 数据库状态正确保存
- ✅ 数据可以正确清理

### 2. `test_roadmap_generation_with_cancellation`

**测试目标：** 任务取消功能

**测试步骤：**
1. 创建测试用户并登录
2. 提交路线图生成请求
3. 等待 5 秒后取消任务
4. 验证任务状态变为 `cancelled`
5. 清理测试数据

**预期耗时：** 10-20 秒

**验证点：**
- ✅ 取消请求成功
- ✅ 任务状态正确更新为 `cancelled`
- ✅ Celery 任务被正确终止

### 3. `test_roadmap_generation_status_polling`

**测试目标：** 任务状态轮询和阶段跟踪

**测试步骤：**
1. 创建测试用户并登录
2. 提交路线图生成请求
3. 持续轮询任务状态，记录每个阶段的耗时
4. 输出状态变化汇总
5. 清理测试数据

**预期耗时：** 2-5 分钟

**验证点：**
- ✅ 状态轮询正常
- ✅ 记录所有阶段的状态变化
- ✅ 计算每个阶段的耗时

**示例输出：**
```
📊 状态变化汇总:
   pending:init                   - 耗时: 0.5s (第1次查询)
   processing:intent_analysis     - 耗时: 15.2s (第5次查询)
   processing:curriculum_design   - 耗时: 45.6s (第15次查询)
   processing:validation          - 耗时: 58.3s (第19次查询)
   processing:human_review        - 耗时: 72.1s (第24次查询)
   completed:completed            - 耗时: 85.4s (第28次查询)

   总耗时: 85.4s
   总查询次数: 28
```

## 监控日志

### FastAPI 日志

**位置：** `backend/logs/e2e/fastapi.log`

**关键日志示例：**

```
INFO:     127.0.0.1:54321 - "POST /api/v1/workflows/generation/generate HTTP/1.1" 200 OK
INFO:     roadmap_generation_requested user_id=... learning_goal="成为Python开发者"
INFO:     roadmap_generation_task_created task_id=... celery_task_id=...
```

### Celery Worker 日志

**位置：** `backend/logs/e2e/celery.log`

**关键日志示例：**

```
[INFO/MainProcess] Task roadmap_generation.generate_roadmap[abc-123] received
[INFO/ForkPoolWorker-1] workflow_execution_started task_id=... user_id=...
[INFO/ForkPoolWorker-1] intent_analysis_completed parsed_goal=...
[INFO/ForkPoolWorker-1] curriculum_design_completed stages=3 modules=8 concepts=24
[INFO/ForkPoolWorker-1] validation_passed overall_score=95.0
[INFO/ForkPoolWorker-1] workflow_execution_completed roadmap_id=... elapsed=85.4s
[INFO/MainProcess] Task roadmap_generation.generate_roadmap[abc-123] succeeded in 85.4s
```

### 实时监控

使用脚本查看实时日志：

```bash
# 同时监控 FastAPI 和 Celery Worker 日志
./scripts/run_e2e_test_services.sh logs
```

或手动使用 `tail`：

```bash
# 终端1：FastAPI 日志
tail -f backend/logs/e2e/fastapi.log

# 终端2：Celery Worker 日志
tail -f backend/logs/e2e/celery.log
```

## 故障排查

### 问题1: FastAPI 启动失败

**症状：**
```
ERROR: FastAPI 启动失败，请查看日志
```

**解决方案：**
1. 检查端口 8000 是否被占用：
   ```bash
   lsof -i :8000
   # 如果被占用，杀死进程：
   kill -9 <PID>
   ```

2. 检查环境变量是否正确：
   ```bash
   cd backend
   python -c "from app.config.settings import settings; print(settings.DATABASE_URL)"
   ```

3. 检查数据库连接：
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

### 问题2: Celery Worker 启动失败

**症状：**
```
ERROR: Celery Worker 启动失败
```

**解决方案：**
1. 检查 Redis 连接：
   ```bash
   redis-cli -h localhost -p 6379 ping
   # 应返回: PONG
   ```

2. 检查 Celery 配置：
   ```bash
   cd backend
   python -c "from app.core.celery_app import celery_app; print(celery_app.conf.broker_url)"
   ```

3. 手动测试 Celery：
   ```bash
   cd backend
   celery -A app.core.celery_app inspect ping
   ```

### 问题3: 测试超时

**症状：**
```
TimeoutError: 任务在 600 秒内未完成
```

**解决方案：**
1. 检查 LLM API 是否可用：
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

2. 增加超时时间：
   ```python
   # 在测试文件中修改
   MAX_POLL_ATTEMPTS = 300  # 从 200 增加到 300
   ```

3. 检查 Celery Worker 日志是否有错误：
   ```bash
   tail -n 50 backend/logs/e2e/celery.log
   ```

### 问题4: 数据库连接错误

**症状：**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方案：**
1. 确认数据库服务已启动：
   ```bash
   docker-compose ps postgres
   ```

2. 检查数据库连接字符串：
   ```bash
   psql $DATABASE_URL -c "SELECT version()"
   ```

3. 重置数据库：
   ```bash
   cd backend
   alembic downgrade base
   alembic upgrade head
   ```

## 性能基准

基于实际测试的性能基准：

| 阶段 | 预期耗时 | 说明 |
|-----|---------|------|
| 意图分析 | 10-20秒 | LLM 解析用户需求 |
| 课程设计 | 20-40秒 | LLM 生成路线图框架 |
| 结构验证 | 5-15秒 | LLM 验证路线图质量 |
| 人工审核 | N/A | 等待用户审核（可选） |
| 内容生成 | 1-3分钟 | 并发生成教程、资源、测验 |
| **总耗时** | **2-5分钟** | 完整流程 |

## 清理测试数据

测试会自动清理数据，但如果测试中断，可以手动清理：

```sql
-- 删除测试用户（会级联删除路线图和任务）
DELETE FROM users WHERE email LIKE 'e2e_test_%@example.com';

-- 删除测试路线图
DELETE FROM roadmap_metadata WHERE roadmap_id LIKE 'test-roadmap-%';

-- 删除测试任务
DELETE FROM roadmap_tasks WHERE task_id LIKE 'test-task-%';
```

## 最佳实践

1. **隔离测试环境**
   - 使用独立的测试数据库
   - 避免在生产数据库上运行测试

2. **监控资源使用**
   - 定期检查数据库大小
   - 清理旧的测试数据
   - 监控 Redis 内存使用

3. **并发控制**
   - 避免同时运行多个真实 E2E 测试
   - LLM API 有速率限制

4. **日志管理**
   - 定期清理旧日志文件
   - 保留失败测试的日志以供分析

5. **成本控制**
   - 真实测试会调用付费 LLM API
   - 建议使用便宜的模型进行测试（如 gpt-3.5-turbo）
   - 限制测试频率

## 常见问题（FAQ）

**Q: 为什么测试这么慢？**  
A: 真实测试会调用真实的 LLM API，每次调用需要几秒到几十秒。这是正常的。

**Q: 可以并行运行多个测试吗？**  
A: 不建议。多个测试会同时调用 LLM API，可能超出速率限制。建议串行运行。

**Q: 测试失败后如何调试？**  
A: 查看日志文件 `backend/logs/e2e/*.log`，搜索错误信息和堆栈跟踪。

**Q: 如何加速测试？**  
A: 可以使用更快的 LLM 模型（如 gpt-3.5-turbo），或减少轮询间隔。

**Q: 测试数据会污染生产数据库吗？**  
A: 不会。测试使用独立的测试数据库，并且会自动清理测试数据。

## 技术支持

如果遇到无法解决的问题，请：
1. 查看完整的错误日志
2. 检查所有依赖服务状态
3. 参考本文档的故障排查章节
4. 联系开发团队

