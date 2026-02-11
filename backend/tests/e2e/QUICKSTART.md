# 快速开始 - 真实E2E测试

## 一键运行（推荐）

```bash
# 在backend目录下执行
cd backend

# 一键启动所有服务并运行测试
python scripts/run_e2e_test.py
```

这个脚本会自动：
1. ✅ 检查依赖服务（PostgreSQL、Redis）
2. ✅ 启动 FastAPI（端口 8000）
3. ✅ 启动 Celery Worker（2个并发）
4. ✅ 运行测试
5. ✅ 实时显示日志
6. ✅ 自动清理服务

## 手动运行（调试用）

### 第一步：启动依赖服务

```bash
# 启动 PostgreSQL 和 Redis
docker-compose -f docker-compose.test.yml up -d postgres redis

# 验证服务
psql $DATABASE_URL -c "SELECT 1"
redis-cli ping
```

### 第二步：启动应用服务

使用提供的脚本：

```bash
cd backend

# 启动 FastAPI 和 Celery Worker
./scripts/run_e2e_test_services.sh start

# 查看服务状态
./scripts/run_e2e_test_services.sh status

# 查看实时日志（可选）
./scripts/run_e2e_test_services.sh logs
```

或者手动启动（在不同终端）：

```bash
# 终端1：FastAPI
cd backend
uvicorn app.main:app --port 8000

# 终端2：Celery Worker  
cd backend
celery -A app.core.celery_app worker --loglevel=info --concurrency=2
```

### 第三步：运行测试

```bash
cd backend

# 运行所有真实E2E测试
pytest tests/e2e/test_real_roadmap_generation_e2e.py -v -s

# 运行单个测试用例
pytest tests/e2e/test_real_roadmap_generation_e2e.py::test_complete_roadmap_generation_flow -v -s
```

### 第四步：停止服务

```bash
# 使用脚本停止
./scripts/run_e2e_test_services.sh stop

# 或手动停止（Ctrl+C 每个终端）
```

## 测试用例说明

### 1. 完整流程测试
```bash
pytest tests/e2e/test_real_roadmap_generation_e2e.py::test_complete_roadmap_generation_flow -v -s
```
**耗时：** 2-5分钟  
**说明：** 测试从用户请求到路线图生成完成的完整流程

### 2. 任务取消测试
```bash
pytest tests/e2e/test_real_roadmap_generation_e2e.py::test_roadmap_generation_with_cancellation -v -s
```
**耗时：** 10-20秒  
**说明：** 测试任务取消功能

### 3. 状态轮询测试
```bash
pytest tests/e2e/test_real_roadmap_generation_e2e.py::test_roadmap_generation_status_polling -v -s
```
**耗时：** 2-5分钟  
**说明：** 测试任务状态轮询和阶段跟踪

## 监控日志

### 方式一：使用脚本（推荐）
```bash
./scripts/run_e2e_test_services.sh logs
```

### 方式二：手动查看
```bash
# FastAPI 日志
tail -f backend/logs/e2e/fastapi.log

# Celery Worker 日志
tail -f backend/logs/e2e/celery.log
```

### 日志示例

**FastAPI 日志：**
```
INFO: 127.0.0.1:54321 - "POST /api/v1/workflows/generation/generate HTTP/1.1" 200 OK
roadmap_generation_requested user_id=... learning_goal="成为Python开发者"
roadmap_generation_task_created task_id=abc-123 celery_task_id=xyz-789
```

**Celery Worker 日志：**
```
[INFO] Task roadmap_generation.generate_roadmap[abc-123] received
[INFO] workflow_execution_started task_id=abc-123
[INFO] intent_analysis_completed parsed_goal=...
[INFO] curriculum_design_completed stages=3 modules=8
[INFO] validation_passed overall_score=95.0
[INFO] Task succeeded in 85.4s
```

## 常见问题

### Q1: 端口 8000 被占用
```bash
# 查看占用进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

### Q2: 数据库连接失败
```bash
# 检查数据库是否启动
docker-compose ps postgres

# 测试连接
psql $DATABASE_URL -c "SELECT version()"
```

### Q3: Redis 连接失败
```bash
# 检查Redis是否启动
docker-compose ps redis

# 测试连接
redis-cli -h localhost -p 6379 ping
```

### Q4: 测试超时
- 检查LLM API密钥是否正确
- 检查网络连接
- 增加 `MAX_POLL_ATTEMPTS` 配置

### Q5: Celery Worker 无法启动
```bash
# 检查日志
cat backend/logs/e2e/celery.log

# 测试Celery配置
cd backend
celery -A app.core.celery_app inspect ping
```

## 性能基准

| 阶段 | 预期耗时 |
|-----|---------|
| 意图分析 | 10-20秒 |
| 课程设计 | 20-40秒 |
| 结构验证 | 5-15秒 |
| 内容生成 | 1-3分钟 |
| **总计** | **2-5分钟** |

## 成本提示

⚠️ **注意：** 真实E2E测试会调用真实的LLM API（OpenAI/Anthropic），会产生费用。

建议：
- 使用便宜的模型（如 `gpt-3.5-turbo`）
- 限制测试频率
- 仅在关键变更后运行

## 下一步

详细文档请参考：[README_E2E_REAL.md](./README_E2E_REAL.md)

