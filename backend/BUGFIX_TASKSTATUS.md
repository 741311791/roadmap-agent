# TaskStatus 导入错误修复

## 问题描述

生成路线图请求失败，错误信息：
```
ImportError: cannot import name 'TaskStatus' from 'app.models.database'
```

## 根本原因

`TaskStatus` 枚举类从未在代码库中定义，但多个文件尝试从 `app.models.database` 导入它。

## 修复方案

### 1. 创建 TaskStatus 枚举类

创建新文件 `backend/app/models/constants.py`，定义以下枚举：

- `TaskStatus`: 任务状态枚举（与前端完全对齐）
  - PENDING = "pending"
  - PROCESSING = "processing"
  - HUMAN_REVIEW = "human_review"
  - COMPLETED = "completed"
  - PARTIAL_FAILURE = "partial_failure"
  - FAILED = "failed"
  - CANCELLED = "cancelled"

- `ContentStatus`: 内容生成状态枚举
- `WorkflowStep`: 工作流步骤枚举

### 2. 修复导入语句

修改以下文件的导入：
- `backend/app/tasks/roadmap_generation_tasks.py`
- `backend/app/tasks/workflow_resume_tasks.py`

从：
```python
from app.models.database import TaskStatus
```

改为：
```python
from app.models.constants import TaskStatus
```

### 3. 修复函数调用

修复 `update_task_status()` 调用，添加缺失的 `current_step` 参数：

**roadmap_generation_tasks.py:**
```python
# 修复 _mark_task_failed 函数
await task_repo.update_task_status(
    task_id=task_id,
    status=TaskStatus.FAILED.value,
    current_step="failed",  # 添加此参数
    error_message=error_message,
)
```

**workflow_resume_tasks.py:**
```python
# 修复 3 处调用，添加 current_step 参数
await task_repo.update_task_status(
    task_id=task_id,
    status=TaskStatus.PROCESSING.value,
    current_step="resuming",  # 添加此参数
    celery_task_id=celery_task_id,
)
```

## 测试验证

```bash
cd backend
source .venv/bin/activate
python -c "
from app.models.constants import TaskStatus
from app.tasks.roadmap_generation_tasks import generate_roadmap
print('✅ TaskStatus 导入成功')
print('✅ generate_roadmap 任务导入成功')
"
```

## 后续步骤

1. ✅ FastAPI 服务器已自动重新加载（使用 --reload）
2. ⚠️ 需要重启 Celery Workers 以加载新代码：
   ```bash
   # 停止现有 workers（Ctrl+C）
   # 重新启动 logs worker
   uv run celery -A app.core.celery_app worker \
       --loglevel=info \
       --queues=logs \
       --concurrency=4 \
       --pool=prefork \
       --hostname=logs@%h \
       --max-tasks-per-child=500
   
   # 重新启动 content_generation worker
   uv run celery -A app.core.celery_app worker \
       --loglevel=info \
       --queues=content_generation \
       --concurrency=2 \
       --pool=prefork \
       --hostname=content@%h \
       --max-tasks-per-child=50
   ```

## 影响范围

- ✅ 修复了路线图生成任务的导入错误
- ✅ 修复了工作流恢复任务的导入错误
- ✅ 统一了任务状态的定义（与前端对齐）
- ✅ 修复了所有缺失的 `current_step` 参数

## 相关文件

- `backend/app/models/constants.py` (新建)
- `backend/app/tasks/roadmap_generation_tasks.py` (修改)
- `backend/app/tasks/workflow_resume_tasks.py` (修改)

