# 内容生成测试脚本快速指南

## 🚀 快速开始

### 1. 最快测试方式（推荐）

使用 Mock 模式，3个 Concept，约 30-60 秒完成：

```bash
cd backend
uv run python scripts/test_content_generation.py --mock
```

### 2. 测试现有路线图

```bash
# 先获取可用的路线图 ID
uv run python scripts/test_roadmap_generation.py --no-cleanup

# 使用返回的 roadmap_id 进行测试
uv run python scripts/test_content_generation.py --roadmap-id <roadmap_id> --max-concepts 2
```

### 3. 保留数据供查看

```bash
uv run python scripts/test_content_generation.py --mock --no-cleanup
```

## 📋 前置条件

### 1. 环境准备

确保已安装依赖：

```bash
cd backend
uv sync
```

### 2. 环境变量配置

确保 `.env` 文件包含必要的配置：

```bash
# LLM 配置（Tutorial/Quiz 生成）
TUTORIAL_GENERATOR_PROVIDER=openai
TUTORIAL_GENERATOR_MODEL=gpt-4o
TUTORIAL_GENERATOR_API_KEY=sk-xxx

QUIZ_GENERATOR_PROVIDER=openai
QUIZ_GENERATOR_MODEL=gpt-4o
QUIZ_GENERATOR_API_KEY=sk-xxx

# Tavily 配置（Resource 推荐）
RESOURCE_RECOMMENDER_PROVIDER=openai
RESOURCE_RECOMMENDER_MODEL=gpt-4o
RESOURCE_RECOMMENDER_API_KEY=sk-xxx
TAVILY_API_KEY=tvly-xxx

# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/roadmap_agent
POSTGRES_SAVER_CONNECTION_STRING=postgresql://user:password@localhost:5432/roadmap_agent

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3. 服务启动

确保 PostgreSQL 和 Redis 正在运行：

```bash
# 检查 PostgreSQL
pg_isready

# 检查 Redis
redis-cli ping
```

## 🎯 使用场景

### 场景1: 验证内容生成流程是否正常

```bash
# 使用 Mock 模式快速测试
uv run python scripts/test_content_generation.py --mock
```

**预期结果**：
- 3/3 Concepts 生成成功
- Tutorial、Resource、Quiz 全部生成
- 元数据已保存到数据库
- Framework 已更新

### 场景2: 测试真实路线图的内容生成

```bash
# 限制生成 2 个 Concept（加快测试）
uv run python scripts/test_content_generation.py \
  --roadmap-id roadmap_abc123 \
  --max-concepts 2
```

**预期结果**：
- 只生成前 2 个 Concept
- 其他 Concept 保持 pending 状态
- 可用于验证部分生成功能

### 场景3: 调试内容生成问题

```bash
# 保留数据供后续检查
uv run python scripts/test_content_generation.py \
  --mock \
  --no-cleanup

# 查看生成的内容
# 使用返回的 roadmap_id 查询数据库
```

### 场景4: 性能测试

```bash
# 生成完整路线图的内容
uv run python scripts/test_content_generation.py \
  --roadmap-id <roadmap_id>

# 观察总耗时和各阶段耗时
```

## 📊 输出解读

### 成功输出示例

```
✅ 内容生成完成
总耗时: 45.3秒 (0.8分钟)

生成成功统计:
   - Tutorial: 3/3
   - Resource: 3/3
   - Quiz: 3/3
   - 元数据已保存: 3/3
```

**说明**：
- 所有 Concept 的 Tutorial、Resource、Quiz 都成功生成
- 元数据已保存到数据库
- Framework 已更新

### 部分失败输出示例

```
生成成功统计:
   - Tutorial: 2/3
   - Resource: 3/3
   - Quiz: 3/3
   - 元数据已保存: 2/3

详细结果:
   [1] Python 基本语法 (C-1-1-1)
      Tutorial: success
      Resource: success
      Quiz: success
      元数据: ✅ 已保存

   [2] 数据结构基础 (C-1-1-2)
      Tutorial: failed
      Resource: success
      Quiz: success
      元数据: ❌ 未保存
      错误: LLM timeout after 30s
```

**说明**：
- Concept C-1-1-2 的 Tutorial 生成失败
- 即使部分失败，其他成功的内容仍会保存
- 查看错误信息定位问题

## 🔍 故障排查

### 问题1: "模块导入失败"

**错误信息**：
```
ModuleNotFoundError: No module named 'app'
```

**解决方案**：
```bash
# 确保在 backend 目录下执行
cd backend

# 重新安装依赖
uv sync
```

### 问题2: "数据库连接失败"

**错误信息**：
```
Could not connect to PostgreSQL
```

**解决方案**：
```bash
# 检查 PostgreSQL 状态
pg_isready

# 检查 .env 配置
cat .env | grep DATABASE_URL

# 启动 PostgreSQL（macOS）
brew services start postgresql@14
```

### 问题3: "LLM 调用失败"

**错误信息**：
```
OpenAI API error: Invalid API key
```

**解决方案**：
```bash
# 检查 API Key 配置
cat .env | grep API_KEY

# 验证 API Key 有效性
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $TUTORIAL_GENERATOR_API_KEY"
```

### 问题4: "Tavily 搜索失败"

**错误信息**：
```
Tavily search failed: API key invalid
```

**解决方案**：
```bash
# 检查 Tavily API Key
cat .env | grep TAVILY_API_KEY

# 或临时禁用 Tavily（使用 Mock 数据）
# 修改 app/agents/resource_recommender.py
```

## 📝 日志查看

### 应用日志

```bash
# 查看最新日志
tail -f backend/logs/app.log

# 查看错误日志
tail -f backend/logs/err.log

# 搜索特定 task_id 的日志
grep "task_abc123" backend/logs/app.log
```

### 数据库查询

```sql
-- 查看任务状态
SELECT task_id, status, current_step, created_at 
FROM tasks 
ORDER BY created_at DESC 
LIMIT 10;

-- 查看生成的 Tutorial
SELECT concept_id, title, difficulty_level, created_at 
FROM tutorials 
WHERE roadmap_id = 'roadmap_abc123';

-- 查看生成的 Resource
SELECT concept_id, total_resources, created_at 
FROM resources 
WHERE roadmap_id = 'roadmap_abc123';

-- 查看生成的 Quiz
SELECT concept_id, total_questions, created_at 
FROM quizzes 
WHERE roadmap_id = 'roadmap_abc123';
```

## 🔧 高级用法

### 自定义用户偏好

修改脚本中的 `LearningPreferences`：

```python
user_preferences = LearningPreferences(
    learning_goal="深入学习 Python",
    available_hours_per_week=20,
    current_level="intermediate",  # 修改为中级
    content_preference=["text", "video"],  # 偏好文本和视频
    motivation="准备面试",
)
```

### 只生成特定类型的内容

修改 `single_concept_content_generation.py` 中的 `inner_fan_out` 函数：

```python
# 只生成 Tutorial
sends = [
    Send("generate_tutorial", {...}),
    # 注释掉其他内容
    # Send("generate_resource", {...}),
    # Send("generate_quiz", {...}),
]
```

### 调整并发数

修改 LangGraph 的并发配置：

```python
config = {
    "configurable": {
        "thread_id": task_id,
        "checkpoint_ns": "child_graph",
        "runtime_context": runtime_context,
    },
    "recursion_limit": 100,  # 增加递归限制
    "max_concurrency": 5,  # 调整并发数
}
```

## 📚 相关脚本

| 脚本 | 用途 | 适用场景 |
|------|------|----------|
| `test_content_generation.py` | 测试内容生成流程 | 验证内容生成功能 |
| `test_roadmap_generation.py` | 测试完整路线图生成 | 端到端测试 |
| `test_single_concept_generation.py` | 测试单个 Concept 生成 | 细粒度测试 |
| `test_curriculum_architect.py` | 测试课程设计 | 验证课程架构 |
| `test_tutorial_generator_standalone.py` | 测试 Tutorial 生成 | Agent 独立测试 |

## 💡 最佳实践

### 1. 开发阶段

```bash
# 使用 Mock 模式快速迭代
uv run python scripts/test_content_generation.py --mock --no-cleanup
```

### 2. 功能验证

```bash
# 使用真实路线图，限制数量
uv run python scripts/test_content_generation.py \
  --roadmap-id <roadmap_id> \
  --max-concepts 2
```

### 3. 性能测试

```bash
# 生成完整路线图，测量总耗时
time uv run python scripts/test_content_generation.py \
  --roadmap-id <roadmap_id>
```

### 4. 回归测试

```bash
# 保留数据供后续验证
uv run python scripts/test_content_generation.py \
  --mock \
  --no-cleanup

# 使用 API 验证生成的内容质量
```

## 🎉 成功标志

测试成功的标志：

1. ✅ 所有 Concept 的元数据已保存
2. ✅ Tutorial、Resource、Quiz 生成成功率 > 90%
3. ✅ Framework 中 Concept 的 `content_status` 已更新为 `completed`
4. ✅ 数据库中能查询到对应的记录
5. ✅ 无异常或错误日志
6. ✅ 总耗时在合理范围内（3个 Concept 约 30-60 秒）

## 📞 获取帮助

如果遇到问题：

1. 查看详细文档：`backend/docs/20260208_内容生成测试脚本说明.md`
2. 检查错误日志：`backend/logs/err.log`
3. 查看代码注释：`backend/scripts/test_content_generation.py`
4. 参考相关测试脚本：`backend/scripts/test_*.py`
