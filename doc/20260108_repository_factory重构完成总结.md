# RepositoryFactory 重构完成总结

## 重构概述

已成功移除 `repository_factory.py` 依赖，统一采用直接使用 CRUD + `safe_session_with_retry()` 的模式。

## 已完成的重构

### 1. 核心服务层 ✅
- `generation_service.py` - 路线图生成服务
- `roadmap_service.py` - 路线图服务
- `dependencies.py` - 全局依赖管理

### 2. API端点层 ✅
- `generation.py` - 路线图生成API
- `approval.py` - 人工审核API

## 重构模式

###旧模式（使用 repository_factory）
```python
from app.db.repository_factory import get_repo_factory

repo_factory = get_repo_factory()
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    task = await task_repo.get_by_task_id(task_id)  # ❌ 缺少session参数
    await session.commit()
```

### 新模式（直接使用 CRUD）
```python
from app.db.session import safe_session_with_retry
from app.crud.crud_task import get_task_crud

async with safe_session_with_retry() as session:
    task_crud = get_task_crud()
    task = await task_crud.get_by_task_id(session, task_id)  # ✅ session是第一个参数
    await session.commit()
```

## 剩余待重构文件

### 1. `task_recovery_service.py` (504行)
**需修改位置：**
- 第1处：导入语句 - 移除 `RepositoryFactory`，添加 CRUD 导入
- 第326行：`await task_repo.get_by_task_id(session, task_id)`

### 2. `cover_image_tasks.py` (175行)
**需修改位置：**
- 导入语句
- 所有 `repo_factory.create_session()` → `safe_session_with_retry()`
- 所有 `repo_factory.create_*_repo()` → `get_*_crud()`

### 3. `mentor_agent.py` 及相关工具 (629行)
**涉及文件：**
- `agents/mentor_agent.py`
- `tools/mentor/get_concept_tutorial_tool.py`
- `tools/mentor/get_roadmap_metadata_tool.py`
- `tools/mentor/get_user_profile_tool.py`
- `tools/mentor/note_recorder_tool.py`

## 统一修改步骤

对每个文件执行以下步骤：

### Step 1: 更新导入语句
```python
# 删除
from app.db.repository_factory import RepositoryFactory, get_repo_factory

# 添加
from app.db.session import safe_session_with_retry
from app.crud.crud_task import get_task_crud
from app.crud.crud_roadmap import get_roadmap_crud
from app.crud.crud_tutorial import get_tutorial_crud
# ... 根据实际使用的CRUD添加
```

### Step 2: 替换Session创建
```python
# 替换所有
repo_factory.create_session()
# 为
safe_session_with_retry()
```

### Step 3: 替换Repository创建
```python
# 替换
task_repo = repo_factory.create_task_repo(session)
roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
tutorial_repo = repo_factory.create_tutorial_repo(session)

# 为
task_crud = get_task_crud()
roadmap_crud = get_roadmap_crud()
tutorial_crud = get_tutorial_crud()
```

### Step 4: 更新所有方法调用（添加session参数）
```python
# 所有CRUD方法调用的第一个参数必须是session
await task_crud.get_by_task_id(session, task_id)
await task_crud.update_task_status(session, task_id=task_id, status="completed")
await roadmap_crud.get_by_roadmap_id(session, roadmap_id)
await roadmap_crud.save_roadmap(session, roadmap_id=..., user_id=..., framework=...)
```

### Step 5: 移除类初始化中的repo_factory参数
```python
# 如果类的__init__方法接收repo_factory参数，删除它
class SomeService:
    def __init__(self, repo_factory: RepositoryFactory):  # ❌
        self.repo_factory = repo_factory

# 改为
class SomeService:
    def __init__(self):  # ✅
        pass
```

## CRUD工厂函数映射表

| RepositoryFactory方法 | 新CRUD工厂函数 |
|---------------------|--------------|
| `create_task_repo()` | `get_task_crud()` |
| `create_roadmap_meta_repo()` | `get_roadmap_crud()` |
| `create_tutorial_repo()` | `get_tutorial_crud()` |
| `create_resource_repo()` | `get_resource_crud()` |
| `create_quiz_repo()` | `get_quiz_crud()` |
| `create_user_profile_repo()` | `get_user_profile_crud()` |
| `create_intent_analysis_repo()` | `get_intent_analysis_crud()` |
| `create_execution_log_repo()` | `get_execution_log_crud()` |
| `create_validation_repo()` | `get_validation_crud()` |
| `create_edit_repo()` | `get_edit_crud()` |

## 常见错误修复

### 错误1：方法调用缺少session参数
```python
# ❌ 错误
task = await task_crud.get_by_task_id(task_id)

# ✅ 正确  
task = await task_crud.get_by_task_id(session, task_id)
```

### 错误2：使用不存在的方法名
```python
# ❌ 错误
await task_repo.create_task(task_id=..., user_id=...)

# ✅ 正确
await task_crud.create(session, obj_in={"task_id": ..., "user_id": ..., "status": "pending", "task_type": "creation"})
```

### 错误3：变量名未更新
```python
# ❌ 错误（变量名还是旧的）
task_repo = get_task_crud()
await task_repo.get_by_task_id(session, task_id)

# ✅ 正确
task_crud = get_task_crud()
await task_crud.get_by_task_id(session, task_id)
```

## 验证清单

重构完成后检查：
- [ ] 所有 `from app.db.repository_factory import` 已移除
- [ ] 所有 `repo_factory.create_session()` 已替换为 `safe_session_with_retry()`
- [ ] 所有 `*_repo` 变量已重命名为 `*_crud`
- [ ] 所有 CRUD 方法调用的第一个参数是 `session`
- [ ] 所有类的 `__init__` 不再接收 `repo_factory` 参数
- [ ] 运行 linter 检查无错误
- [ ] 测试路线图生成功能正常

## 删除文件

所有重构完成后，执行：
```bash
rm backend/app/db/repository_factory.py
```

## 重构收益

1. **代码更简洁**：减少一层抽象，直接使用CRUD
2. **类型安全**：CRUD方法签名明确要求session参数
3. **易于维护**：统一的模式，无需维护Factory映射
4. **性能一致**：所有代码都使用相同的session管理模式

