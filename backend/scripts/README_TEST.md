# 路线图生成服务测试脚本使用说明

## 概述

`test_roadmap_service.py` 是一个用于测试路线图生成服务的命令行工具，支持多种测试场景。

## 前置要求

1. **后端服务运行中**: 确保后端服务在 `http://localhost:8000` 运行
2. **Python 环境**: Python 3.12+
3. **依赖安装**: 
   ```bash
   uv sync --extra dev
   # 或
   poetry install
   ```

## 使用方法

### 基本用法

```bash
# 运行默认场景（场景 1: 全栈 Web 开发）
uv run python scripts/test_roadmap_service.py

# 或直接执行（如果已安装依赖）
python scripts/test_roadmap_service.py
```

### 运行指定场景

```bash
# 场景 1: 全栈 Web 开发学习路线
uv run python scripts/test_roadmap_service.py --scenario 1

# 场景 2: Python 数据分析学习路线
uv run python scripts/test_roadmap_service.py --scenario 2

# 场景 3: 人工审核流程测试
uv run python scripts/test_roadmap_service.py --scenario 3

# 场景 4: 快速测试（跳过验证和审核）
uv run python scripts/test_roadmap_service.py --scenario 4
```

### 运行所有场景

```bash
uv run python scripts/test_roadmap_service.py --all
```

### 指定 API 基础 URL

```bash
# 如果后端服务运行在其他地址
uv run python scripts/test_roadmap_service.py --base-url http://localhost:8001
```

## 测试场景说明

### 场景 1: 全栈 Web 开发
- **目标**: 测试完整的路线图生成流程
- **用户背景**: 零基础，希望转行成为全栈工程师
- **预期**: 生成包含前端、后端、数据库的完整学习路线

### 场景 2: Python 数据分析
- **目标**: 测试中级用户的学习路线生成
- **用户背景**: 有 Excel 和 SQL 基础，希望学习数据分析
- **预期**: 生成针对性的 Python 数据分析路线

### 场景 3: 人工审核流程
- **目标**: 测试 Human-in-the-Loop 功能
- **流程**: 
  1. 生成路线图
  2. 等待到人工审核阶段
  3. 模拟批准操作
  4. 继续完成后续流程

### 场景 4: 快速测试
- **目标**: 快速验证服务可用性
- **注意**: 需要设置环境变量 `SKIP_STRUCTURE_VALIDATION=true` 和 `SKIP_HUMAN_REVIEW=true`
- **预期**: 快速生成路线图（跳过验证和审核步骤）

## 输出说明

脚本会显示：
- ✅ 服务健康状态
- 📝 任务创建信息
- ⏳ 任务执行进度（实时更新）
- 📊 任务状态详情
- 📚 生成的路线图摘要（如果成功）

## 示例输出

```
🚀 路线图生成服务测试脚本

============================================================
测试场景 1: 全栈 Web 开发学习路线
============================================================
✅ 服务健康: {'status': 'healthy', 'version': '1.0.0'}

✅ 路线图生成任务已创建
   任务 ID: abc123-def456-...
   状态: processing

等待任务完成 (ID: abc123...)
状态: processing | 步骤: intent_analysis | 已等待: 5s
...

=== 任务状态 ===
  status: completed
  roadmap_id: roadmap-001
  ...

📚 路线图: 全栈 Web 开发学习路线
   ID: roadmap-001
   总时长: 120.0 小时
   推荐周期: 8 周
   阶段数: 3
```

## 故障排查

### 问题 1: 无法连接到服务

```
❌ 无法连接到服务: Connection refused
```

**解决方案**:
- 确保后端服务正在运行: `uv run uvicorn app.main:app --reload`
- 检查端口是否正确: `--base-url http://localhost:8000`

### 问题 2: 任务超时

```
⏱️  超时: 等待超过 300 秒
```

**解决方案**:
- 检查后端日志，查看是否有错误
- 增加超时时间（修改脚本中的 `max_wait_seconds` 参数）
- 检查 LLM API 是否正常

### 问题 3: 任务失败

```
状态: failed
```

**解决方案**:
- 查看任务状态详情中的错误信息
- 检查后端日志
- 验证环境变量配置（API Keys 等）

## 高级用法

### 自定义测试请求

修改脚本中的 `test_scenario_*` 函数，自定义用户请求：

```python
request = {
    "user_id": "your-user-id",
    "session_id": "your-session-id",
    "preferences": {
        "learning_goal": "你的学习目标",
        "available_hours_per_week": 10,
        "motivation": "学习动机",
        "current_level": "beginner",  # beginner/intermediate/advanced
        "career_background": "你的背景",
        "content_preference": ["text", "video"],
        "target_deadline": None
    },
    "additional_context": "额外信息"
}
```

### 集成到 CI/CD

```bash
# 在 CI 中运行测试
uv run python scripts/test_roadmap_service.py --scenario 4 --base-url $API_URL
```

## 注意事项

1. **API 调用成本**: 每个测试场景会调用 LLM API，请注意成本
2. **执行时间**: 完整流程可能需要几分钟，请耐心等待
3. **数据库状态**: 测试会在数据库中创建记录，测试后可能需要清理
4. **并发限制**: 不要同时运行多个测试，避免资源竞争

## 相关文档

- [API 文档](../README.md#api-文档)
- [架构说明](../README.md#架构说明)
- [开发工作流](../README.md#开发工作流)

