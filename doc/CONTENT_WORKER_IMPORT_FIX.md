# Content Worker 导入错误修复

**日期**: 2025-12-27  
**状态**: ✅ 已修复  
**错误**: `No module named 'app.core.orchestrator.workflow_config'`

---

## 问题描述

启动 content_generation Worker 后报错：

```
[2025-12-27 20:48:38,750: WARNING/ForkPoolWorker-2] 2025-12-27 20:48:38 [error] 
celery_content_generation_task_failed 
error="No module named 'app.core.orchestrator.workflow_config'" 
error_type=ModuleNotFoundError
```

## 根本原因

**文件**: `backend/app/tasks/content_generation_tasks.py` (第 181 行)

### 错误的导入 ❌

```python
from app.core.orchestrator.workflow_config import WorkflowConfig
```

### 问题

- `workflow_config.py` 模块**不存在**
- `WorkflowConfig` 类实际定义在 `app.core.orchestrator.base` 模块中

---

## 修复方案 ✅

### 修改文件

**文件**: `backend/app/tasks/content_generation_tasks.py` (第 181 行)

**修复前**:
```python
from app.core.orchestrator.workflow_config import WorkflowConfig
```

**修复后**:
```python
from app.core.orchestrator.base import WorkflowConfig
```

### 完整的导入块

```python
from app.agents.factory import AgentFactory
from app.core.orchestrator.base import WorkflowConfig  # ✅ 修复
from app.core.orchestrator.workflow_brain import WorkflowBrain
from app.core.orchestrator.state_manager import StateManager
from app.services.execution_logger import execution_logger
```

---

## 重启 Worker

由于 Celery Worker 使用了 `prefork` 模式（多进程池），修改代码后需要**重启 Worker** 才能加载新代码。

### 步骤 1: 停止当前 Worker

在运行 Worker 的终端（终端 5）中按 `Ctrl+C`：

```
^C
[2025-12-27 20:xx:xx,xxx: WARNING/MainProcess] Warm shutdown (MainProcess)
[2025-12-27 20:xx:xx,xxx: INFO/MainProcess] Stopping...
```

### 步骤 2: 重新启动 Worker

在同一终端中运行：

```bash
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --queues=content_generation \
    --concurrency=2 \
    --pool=prefork \
    --hostname=content@%h \
    --max-tasks-per-child=50
```

### 步骤 3: 验证启动成功

应该看到以下输出：

```
[2025-12-27 20:xx:xx,xxx: INFO/MainProcess] content@louiedeMac-mini.local ready.
```

**关键信息**：
- ✅ `[tasks]` 列表中有 `generate_roadmap_content`
- ✅ `[queues]` 列表中有 `content_generation`
- ✅ 没有 `ModuleNotFoundError` 错误

---

## 验证修复

### 测试 1: 检查 Worker 日志

Worker 启动后，如果有待处理的任务（之前失败的任务），应该会自动重试：

```
[INFO/MainProcess] Task app.tasks.content_generation_tasks.generate_roadmap_content[xxx] received
[INFO/ForkPoolWorker-1] celery_content_generation_task_started task_id=xxx
[INFO/ForkPoolWorker-1] async_content_generation_started task_id=xxx
[INFO/ForkPoolWorker-1] concepts_extracted total_concepts=10
```

### 测试 2: 创建新任务

1. 在前端创建新的路线图生成任务
2. 通过人工审核节点（点击 Approve）
3. 观察 Worker 日志：

```
[INFO/MainProcess] Task received
[INFO/ForkPoolWorker-1] celery_content_generation_task_started
[INFO/ForkPoolWorker-1] async_content_generation_started
[INFO/ForkPoolWorker-1] concepts_extracted total_concepts=XX
[INFO/ForkPoolWorker-1] concept_generation_started concept_id=xxx
[INFO/ForkPoolWorker-1] concept_generation_completed concept_id=xxx
...
[INFO/ForkPoolWorker-1] celery_content_generation_task_completed
```

### 测试 3: 检查前端进度

前端应该显示：
- ✅ 内容生成进度实时更新
- ✅ 每个 Concept 完成后显示进度
- ✅ 最终显示 "completed" 状态

---

## 相关文件

### 修改的文件

1. **`backend/app/tasks/content_generation_tasks.py`** ✅
   - 修复第 181 行导入语句

### 正确的模块位置

```python
# ✅ WorkflowConfig 定义位置
# backend/app/core/orchestrator/base.py

class WorkflowConfig(BaseModel):
    """
    工作流配置
    
    支持通过环境变量跳过特定节点：
    - skip_structure_validation: 跳过结构验证和编辑循环
    - skip_human_review: 跳过人工审核
    - skip_tutorial_generation: 跳过教程生成
    - skip_resource_recommendation: 跳过资源推荐
    - skip_quiz_generation: 跳过测验生成
    """
    skip_structure_validation: bool = False
    skip_human_review: bool = False
    skip_tutorial_generation: bool = False
    skip_resource_recommendation: bool = False
    skip_quiz_generation: bool = False
    
    max_framework_retry: int = 3
    parallel_tutorial_limit: int = 5
```

---

## 技术细节

### Celery Worker 进程模型

#### prefork 模式

```
MainProcess
├── ForkPoolWorker-1 (进程)
└── ForkPoolWorker-2 (进程)
```

**特点**：
- 每个 Worker 是独立的进程
- 代码修改后需要重启才能生效
- 进程间隔离，稳定性更好

#### 为什么不会自动重载？

- FastAPI (`--reload`) 使用文件监听，代码改变时自动重启
- Celery Worker **不支持** `--reload` 模式（prefork 进程无法热重载）
- 必须手动重启 Worker 进程

### 最佳实践

#### 开发环境

使用脚本自动重启 Worker（可选）：

```bash
# backend/scripts/watch_celery_worker.sh
#!/bin/bash

while true; do
    uv run celery -A app.core.celery_app worker \
        --loglevel=info \
        --queues=content_generation \
        --concurrency=2 \
        --pool=prefork \
        --hostname=content@%h \
        --max-tasks-per-child=50
    
    echo "Worker stopped, restarting in 3 seconds..."
    sleep 3
done
```

#### 生产环境

使用进程管理器（如 systemd、supervisor）：

```ini
; supervisor 配置示例
[program:celery_content_worker]
command=/path/to/uv run celery -A app.core.celery_app worker --queues=content_generation
directory=/path/to/backend
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
```

---

## 故障排查

### 问题 1: Worker 启动后仍然报错

**症状**: 重启后仍然看到 `ModuleNotFoundError`

**原因**: 可能使用了缓存的字节码文件 (`.pyc`)

**解决方案**:
```bash
# 清理 Python 缓存
find backend -type d -name "__pycache__" -exec rm -rf {} +
find backend -name "*.pyc" -delete

# 重新启动 Worker
uv run celery -A app.core.celery_app worker ...
```

### 问题 2: 任务一直在重试

**症状**: Worker 日志显示任务不断重试

**原因**: 之前失败的任务仍在队列中

**解决方案**:
```bash
# 清空所有待处理任务
celery -A app.core.celery_app purge

# 或只清空 content_generation 队列
celery -A app.core.celery_app purge -Q content_generation
```

### 问题 3: Worker 无法连接 Redis

**症状**: `Error: Consumer: Connection to broker lost`

**原因**: Redis SSL 连接问题（已在之前修复）

**解决方案**: 参考 `doc/REDIS_SSL_FIX_2025-12-27.md`

---

## 监控命令

### 检查 Worker 状态

```bash
# 查看所有活跃的 Worker
celery -A app.core.celery_app inspect active

# 查看 Worker 统计信息
celery -A app.core.celery_app inspect stats

# 查看待处理任务
celery -A app.core.celery_app inspect reserved
```

### Flower 监控面板

访问 http://localhost:5555

- **Workers**: 查看 Worker 状态
- **Tasks**: 查看任务执行历史
- **Broker**: 查看队列状态

---

## 总结

### 问题根源
- ❌ 错误的导入路径：`app.core.orchestrator.workflow_config`

### 解决方案
- ✅ 修正导入路径：`app.core.orchestrator.base`
- ✅ 重启 Celery Worker

### 修复状态
- ✅ **代码修复**: 已完成
- ⏳ **Worker 重启**: 需要用户执行
- ✅ **验证测试**: 待用户确认

### 下一步
1. 按 `Ctrl+C` 停止当前 Worker
2. 重新启动 Worker
3. 测试内容生成功能
4. 观察任务执行日志

---

**修复者**: AI Assistant  
**审核者**: 待审核  
**版本**: v1.0  
**参考文档**:
- `doc/WORKFLOW_APPROVAL_SKIP_CONTENT_FIX.md`
- `backend/docs/CELERY_CONTENT_GENERATION_MIGRATION_COMPLETE.md`

