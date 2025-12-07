# Repository 使用指南

> **版本**: v1.0  
> **创建日期**: 2025-01-05  
> **状态**: 阶段3重构 - Repository层拆分完成

## 📚 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [快速开始](#快速开始)
- [使用示例](#使用示例)
- [最佳实践](#最佳实践)
- [迁移指南](#迁移指南)
- [常见问题](#常见问题)

---

## 概述

### 什么是 Repository 模式？

Repository 模式是一个**数据访问抽象层**，它的职责是：

✅ **应该做的**：
- 数据库的 CRUD 操作（增删改查）
- 简单的数据过滤和排序
- 事务管理
- 数据库查询构建

❌ **不应该做的**：
- 业务逻辑计算
- 数据转换和聚合
- 外部服务调用
- 通知发送

---

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────┐
│              API Layer (FastAPI)                │
│  /api/v1/endpoints/*.py                         │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│           Service Layer (Business Logic)        │
│  app/services/roadmap_service.py                │
│  - 业务规则                                      │
│  - 数据聚合                                      │
│  - 跨Repository协调                             │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│       Repository Layer (Data Access)            │
│  app/db/repositories/*.py                       │
│  - CRUD 操作                                     │
│  - 查询构建                                      │
│  - 数据库访问                                    │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│              Database (PostgreSQL)              │
│  - roadmap_tasks                                │
│  - roadmap_metadata                             │
│  - tutorial_metadata                            │
│  - ...                                          │
└─────────────────────────────────────────────────┘
```

### Repository 列表

| Repository | 表 | 职责 | 文件 |
|:---|:---|:---|:---|
| **TaskRepository** | roadmap_tasks | 任务状态管理 | `task_repo.py` |
| **RoadmapMetadataRepository** | roadmap_metadata | 路线图元数据 | `roadmap_meta_repo.py` |
| **TutorialRepository** | tutorial_metadata | 教程版本管理 | `tutorial_repo.py` |
| **ResourceRepository** | resource_recommendation_metadata | 资源推荐 | `resource_repo.py` |
| **QuizRepository** | quiz_metadata | 测验管理 | `quiz_repo.py` |
| **IntentAnalysisRepository** | intent_analysis_metadata | 需求分析 | `intent_analysis_repo.py` |
| **UserProfileRepository** | user_profiles | 用户画像 | `user_profile_repo.py` |
| **ExecutionLogRepository** | execution_logs | 执行日志 | `execution_log_repo.py` |

---

## 快速开始

### 1. 基础使用

```python
from app.db.repository_factory import get_repository_factory

# 获取工厂实例
repo_factory = get_repository_factory()

# 使用上下文管理器（推荐）
async with repo_factory.create_session() as session:
    # 创建 Repository
    task_repo = repo_factory.create_task_repo(session)
    
    # 执行数据库操作
    task = await task_repo.get_by_task_id("task-123")
    
    # 提交事务
    await session.commit()
# 会话自动关闭
```

### 2. 在 FastAPI 中使用

```python
from fastapi import APIRouter, Depends
from app.db.repository_factory import RepositoryFactory, get_repo_factory

router = APIRouter()

@router.post("/tasks")
async def create_task(
    request: CreateTaskRequest,
    repo_factory: RepositoryFactory = Depends(get_repo_factory),
):
    """创建任务"""
    async with repo_factory.create_session() as session:
        # 创建 Repository
        task_repo = repo_factory.create_task_repo(session)
        
        # 执行数据库操作
        task = await task_repo.create_task(
            task_id=request.task_id,
            user_id=request.user_id,
            user_request=request.user_request,
        )
        
        # 提交事务
        await session.commit()
        
        return task
```

### 3. 在 Service 中使用

```python
from app.db.repository_factory import RepositoryFactory

class RoadmapService:
    def __init__(self, repo_factory: RepositoryFactory):
        self.repo_factory = repo_factory
    
    async def get_roadmap_with_content(self, roadmap_id: str) -> dict:
        """获取完整路线图（元数据 + 教程 + 资源 + 测验）"""
        async with self.repo_factory.create_session() as session:
            # 创建多个 Repository
            roadmap_repo = self.repo_factory.create_roadmap_meta_repo(session)
            tutorial_repo = self.repo_factory.create_tutorial_repo(session)
            resource_repo = self.repo_factory.create_resource_repo(session)
            quiz_repo = self.repo_factory.create_quiz_repo(session)
            
            # 查询路线图元数据
            roadmap = await roadmap_repo.get_by_roadmap_id(roadmap_id)
            if not roadmap:
                return None
            
            # 查询关联内容
            tutorials = await tutorial_repo.list_by_roadmap(roadmap_id, latest_only=True)
            resources = await resource_repo.list_by_roadmap(roadmap_id)
            quizzes = await quiz_repo.list_by_roadmap(roadmap_id)
            
            # 聚合数据（业务逻辑）
            return {
                "roadmap": roadmap,
                "tutorials": tutorials,
                "resources": resources,
                "quizzes": quizzes,
                "total_tutorials": len(tutorials),
                "total_resources": sum(r.resources_count for r in resources),
                "total_quizzes": len(quizzes),
            }
```

---

## 使用示例

### 任务操作

```python
# 创建任务
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    
    task = await task_repo.create_task(
        task_id="task-123",
        user_id="user-456",
        user_request={"goal": "Learn Python"},
    )
    
    await session.commit()

# 更新任务状态
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    
    updated = await task_repo.update_task_status(
        task_id="task-123",
        status="processing",
        current_step="intent_analysis",
        roadmap_id="roadmap-789",
    )
    
    await session.commit()

# 查询活跃任务
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    
    active_task = await task_repo.get_active_task_by_roadmap("roadmap-789")
```

### 路线图操作

```python
# 保存路线图元数据
async with repo_factory.create_session() as session:
    roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
    
    roadmap = await roadmap_repo.save_roadmap(
        roadmap_id="roadmap-789",
        user_id="user-456",
        task_id="task-123",
        framework=RoadmapFramework(...),
    )
    
    await session.commit()

# 查询用户的路线图列表
async with repo_factory.create_session() as session:
    roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
    
    roadmaps = await roadmap_repo.list_by_user(
        user_id="user-456",
        limit=20,
        offset=0,
    )
```

### 教程版本管理

```python
# 保存新教程版本
async with repo_factory.create_session() as session:
    tutorial_repo = repo_factory.create_tutorial_repo(session)
    
    # 自动将旧版本标记为 is_latest=False
    tutorial = await tutorial_repo.save_tutorial(
        tutorial_output=TutorialGenerationOutput(...),
        roadmap_id="roadmap-789",
    )
    
    await session.commit()

# 获取最新版本教程
async with repo_factory.create_session() as session:
    tutorial_repo = repo_factory.create_tutorial_repo(session)
    
    latest = await tutorial_repo.get_latest_tutorial(
        roadmap_id="roadmap-789",
        concept_id="python-basics",
    )

# 查询版本历史
async with repo_factory.create_session() as session:
    tutorial_repo = repo_factory.create_tutorial_repo(session)
    
    history = await tutorial_repo.get_tutorial_history(
        roadmap_id="roadmap-789",
        concept_id="python-basics",
    )
```

### 批量操作

```python
# 批量保存教程
async with repo_factory.create_session() as session:
    tutorial_repo = repo_factory.create_tutorial_repo(session)
    
    tutorial_refs = {
        "concept-1": TutorialGenerationOutput(...),
        "concept-2": TutorialGenerationOutput(...),
        "concept-3": TutorialGenerationOutput(...),
    }
    
    tutorials = await tutorial_repo.save_tutorials_batch(
        tutorial_refs=tutorial_refs,
        roadmap_id="roadmap-789",
    )
    
    await session.commit()
```

---

## 最佳实践

### 1. 会话管理

✅ **推荐**: 使用上下文管理器

```python
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    # 执行操作
    await session.commit()
# 会话自动关闭
```

❌ **不推荐**: 手动管理会话

```python
session = await repo_factory.get_session()
try:
    task_repo = repo_factory.create_task_repo(session)
    # 执行操作
    await session.commit()
finally:
    await session.close()  # 容易忘记
```

### 2. 事务管理

✅ **推荐**: 显式提交

```python
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    
    # 执行多个操作
    task = await task_repo.create_task(...)
    await task_repo.update_task_status(...)
    
    # 显式提交
    await session.commit()
```

❌ **不推荐**: 忘记提交

```python
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    
    task = await task_repo.create_task(...)
    # 忘记 commit，数据不会保存！
```

### 3. 业务逻辑位置

✅ **推荐**: 业务逻辑在 Service 层

```python
# Service 层
class RoadmapService:
    async def calculate_roadmap_stats(self, roadmap_id: str) -> dict:
        """计算路线图统计（业务逻辑）"""
        async with self.repo_factory.create_session() as session:
            tutorial_repo = self.repo_factory.create_tutorial_repo(session)
            tutorials = await tutorial_repo.list_by_roadmap(roadmap_id)
            
            # 业务计算
            total_time = sum(t.estimated_completion_time for t in tutorials)
            return {"total_tutorials": len(tutorials), "total_time": total_time}
```

❌ **不推荐**: 业务逻辑在 Repository 层

```python
# Repository 层（错误示例）
class TutorialRepository:
    async def calculate_total_time(self, roadmap_id: str) -> int:
        """❌ 不应该在 Repository 中计算业务指标"""
        tutorials = await self.list_by_roadmap(roadmap_id)
        return sum(t.estimated_completion_time for t in tutorials)
```

### 4. 错误处理

```python
from sqlalchemy.exc import IntegrityError

async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    
    try:
        task = await task_repo.create_task(...)
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        logger.error("task_creation_failed", error=str(e))
        raise HTTPException(status_code=400, detail="Task ID already exists")
```

---

## 迁移指南

### 从旧 RoadmapRepository 迁移

**旧代码**：

```python
from app.db.repositories.roadmap_repo import RoadmapRepository

async def create_task(session: AsyncSession, ...):
    repo = RoadmapRepository(session)
    task = await repo.create_task(...)
    await session.commit()
```

**新代码**：

```python
from app.db.repository_factory import get_repository_factory

async def create_task(...):
    repo_factory = get_repository_factory()
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        task = await task_repo.create_task(...)
        await session.commit()
```

### 映射表

| 旧方法 (RoadmapRepository) | 新 Repository | 新方法 |
|:---|:---|:---|
| `create_task()` | TaskRepository | `create_task()` |
| `get_task()` | TaskRepository | `get_by_task_id()` |
| `update_task_status()` | TaskRepository | `update_task_status()` |
| `get_roadmap_metadata()` | RoadmapMetadataRepository | `get_by_roadmap_id()` |
| `save_roadmap_metadata()` | RoadmapMetadataRepository | `save_roadmap()` |
| `save_tutorial_metadata()` | TutorialRepository | `save_tutorial()` |
| `get_latest_tutorial()` | TutorialRepository | `get_latest_tutorial()` |
| `save_resource_recommendation_metadata()` | ResourceRepository | `save_resource_recommendation()` |
| `save_quiz_metadata()` | QuizRepository | `save_quiz()` |
| `save_user_profile()` | UserProfileRepository | `save_user_profile()` |
| `get_execution_logs_by_trace()` | ExecutionLogRepository | `list_by_trace()` |

---

## 常见问题

### Q1: 为什么要拆分 Repository？

**A**: 原来的 `RoadmapRepository` 有 1040 行，包含了所有表的操作。拆分后：
- 每个 Repository < 250 行，职责清晰
- 易于测试和维护
- 符合单一职责原则

### Q2: 什么时候 commit？

**A**: 
- 读操作：不需要 commit
- 写操作（create、update、delete）：需要 commit
- 推荐在会话结束前统一 commit

### Q3: 如何处理事务？

**A**:

```python
async with repo_factory.create_session() as session:
    task_repo = repo_factory.create_task_repo(session)
    roadmap_repo = repo_factory.create_roadmap_meta_repo(session)
    
    try:
        # 多个操作在同一个事务中
        task = await task_repo.create_task(...)
        roadmap = await roadmap_repo.save_roadmap(...)
        
        # 统一提交
        await session.commit()
    except Exception as e:
        # 自动回滚
        await session.rollback()
        raise
```

### Q4: 可以跨 Repository 调用吗？

**A**: ❌ 不推荐。Repository 之间不应该相互调用，业务协调应该在 Service 层完成。

```python
# ❌ 错误：在 TaskRepository 中调用 RoadmapRepository
class TaskRepository:
    async def create_task_with_roadmap(self, ...):
        roadmap_repo = RoadmapRepository(self.session)  # ❌ 不推荐
        await roadmap_repo.save_roadmap(...)

# ✅ 正确：在 Service 层协调
class RoadmapService:
    async def create_task_with_roadmap(self, ...):
        async with self.repo_factory.create_session() as session:
            task_repo = self.repo_factory.create_task_repo(session)
            roadmap_repo = self.repo_factory.create_roadmap_meta_repo(session)
            
            task = await task_repo.create_task(...)
            roadmap = await roadmap_repo.save_roadmap(...)
            
            await session.commit()
```

---

## 测试

### 运行测试

```bash
# 运行所有 Repository 测试
pytest tests/unit/test_repository_base.py -v

# 运行 Factory 测试
pytest tests/integration/test_repository_factory.py -v
```

---

**文档版本**: v1.0  
**最后更新**: 2025-01-05  
**维护者**: Backend Team  
**相关文档**: `REFACTORING_TASKS.md`, `DATABASE_OPTIMIZATION_ANALYSIS.md`
