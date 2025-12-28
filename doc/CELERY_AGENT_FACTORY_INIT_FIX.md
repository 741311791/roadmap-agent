# Celery AgentFactory 初始化错误修复

**日期**: 2025-12-27  
**状态**: ✅ 已修复  
**问题**: Celery Worker 执行内容生成任务时崩溃：`AgentFactory.__init__() missing 1 required positional argument: 'settings'`

---

## 问题描述

### 错误堆栈

```python
[2025-12-27 20:54:46,750: ERROR/ForkPoolWorker-2] 
Task app.tasks.content_generation_tasks.generate_roadmap_content[...] raised unexpected: 
TypeError("AgentFactory.__init__() missing 1 required positional argument: 'settings'")

Traceback (most recent call last):
  File "/backend/app/tasks/content_generation_tasks.py", line 223, in _async_generate_content
    agent_factory = AgentFactory()
                    ^^^^^^^^^^^^^^
TypeError: AgentFactory.__init__() missing 1 required positional argument: 'settings'
```

### 用户影响

1. ✅ 前端人工审核通过后，Celery 任务被正确发送到队列
2. ❌ Celery Worker 开始执行任务，但在初始化 `AgentFactory` 时崩溃
3. ❌ 任务自动重试 3 次后失败，内容生成阶段完全无法执行
4. ❌ 任务状态停留在 `processing`，用户界面显示"进行中"但永远无法完成

---

## 根本原因

### 问题定位

**文件**: `backend/app/tasks/content_generation_tasks.py` (第 223 行)

#### ❌ 错误的代码（修复前）

```python
# 第 180 行：导入
from app.agents.factory import AgentFactory

# 第 223 行：错误调用
agent_factory = AgentFactory()  # ❌ 缺少必需的 settings 参数
```

### 为什么会出错？

根据 `AgentFactory` 的定义（`backend/app/agents/factory.py`）：

```python
class AgentFactory:
    """Agent 工厂类"""
    
    def __init__(self, settings: Settings):
        """
        初始化工厂
        
        Args:
            settings: 应用配置对象（必需参数）
        """
        self.settings = settings
        logger.info("agent_factory_initialized")
```

**关键点**：
1. `AgentFactory` 构造函数需要 `settings` 参数（不是可选的）
2. `settings` 包含所有 LLM 的配置（API Key、Model、Base URL 等）
3. 如果不传递 `settings`，所有 Agent 都无法正确初始化

---

## 正确的用法

### 方案 1: 使用全局单例函数（✅ 推荐）

`AgentFactory` 提供了全局单例函数，自动注入 `settings`：

```python
from app.agents.factory import get_agent_factory

# ✅ 自动获取 settings，返回单例实例
agent_factory = get_agent_factory()
```

**优势**：
- ✅ 不需要手动传递 `settings`
- ✅ 确保整个应用使用同一个 `AgentFactory` 实例
- ✅ 这是工厂模式的推荐用法

### 方案 2: 手动传递 settings（不推荐）

```python
from app.agents.factory import AgentFactory
from app.config.settings import settings

# ⚠️ 手动传递 settings（不推荐，容易出错）
agent_factory = AgentFactory(settings)
```

**缺点**：
- ❌ 需要额外导入 `settings`
- ❌ 每次调用都创建新实例（浪费资源）
- ❌ 不符合工厂模式的最佳实践

---

## 修复方案

### 修复代码

**文件**: `backend/app/tasks/content_generation_tasks.py`

#### 修改 1: 更新导入（第 180 行）

```python
# ❌ 修复前
from app.agents.factory import AgentFactory

# ✅ 修复后
from app.agents.factory import get_agent_factory
```

#### 修改 2: 使用全局单例（第 223 行）

```python
# ❌ 修复前
agent_factory = AgentFactory()  # TypeError: missing 'settings'

# ✅ 修复后
agent_factory = get_agent_factory()  # 自动注入 settings
```

### 完整上下文（第 221-225 行）

```python
# 3. 创建服务和工具
repo_factory = RepositoryFactory()
agent_factory = get_agent_factory()  # ✅ 使用全局单例，自动注入 settings
config = WorkflowConfig()
```

---

## 验证测试

### 测试步骤

1. **确保 Celery Worker 正在运行**：
   ```bash
   cd /Users/louie/Documents/Vibecoding/roadmap-agent/backend
   
   # 重启 content_generation Worker（加载修复后的代码）
   uv run celery -A app.core.celery_app worker \
       --loglevel=info \
       --queues=content_generation \
       --concurrency=2 \
       --pool=prefork \
       --hostname=content@%h
   ```

2. **触发内容生成任务**：
   - 在前端创建新的路线图生成任务
   - 等待到达人工审核节点
   - 点击 "Approve" 按钮

3. **检查 Celery Worker 日志**（应该看到成功执行）：
   ```
   [INFO/MainProcess] Task app.tasks.content_generation_tasks.generate_roadmap_content[xxx] received
   [INFO/ForkPoolWorker-1] celery_content_generation_task_started task_id=xxx roadmap_id=yyy
   [INFO/ForkPoolWorker-1] concepts_extracted task_id=xxx roadmap_id=yyy total_concepts=10
   [INFO/ForkPoolWorker-1] concept_generation_started concept_id=aaa concept_name="Python Basics"
   [INFO/ForkPoolWorker-1] tutorial_generation_started concept_id=aaa
   [INFO/ForkPoolWorker-1] tutorial_generation_completed concept_id=aaa
   [INFO/ForkPoolWorker-1] resource_generation_started concept_id=aaa
   [INFO/ForkPoolWorker-1] resource_generation_completed concept_id=aaa
   [INFO/ForkPoolWorker-1] quiz_generation_started concept_id=aaa
   [INFO/ForkPoolWorker-1] quiz_generation_completed concept_id=aaa
   [INFO/ForkPoolWorker-1] concept_generation_completed concept_id=aaa
   ...
   [INFO/ForkPoolWorker-1] celery_content_generation_task_completed task_id=xxx
   ```

4. **验证最终结果**：
   ```bash
   curl http://localhost:8000/api/v1/roadmaps/{task_id}/status
   ```
   
   **预期响应**：
   ```json
   {
     "task_id": "xxx",
     "status": "completed",
     "current_step": "completed",
     "roadmap_id": "yyy",
     "execution_summary": {
       "tutorial_count": 10,
       "resource_count": 10,
       "quiz_count": 10,
       "failed_count": 0
     }
   }
   ```

### 预期结果

| 测试项 | 修复前 | 修复后 |
|--------|--------|--------|
| AgentFactory 初始化 | ❌ TypeError | ✅ 成功 |
| Celery 任务执行 | ❌ 崩溃并重试 | ✅ 正常执行 |
| 内容生成 | ❌ 0 个内容 | ✅ 90+ 个内容 |
| 任务最终状态 | ❌ 停留在 processing | ✅ completed |
| 前端显示 | ❌ 卡在"进行中" | ✅ 显示"已完成" |

---

## 架构说明

### AgentFactory 的设计模式

```python
# 工厂类定义
class AgentFactory:
    def __init__(self, settings: Settings):
        self.settings = settings
    
    def create_intent_analyzer(self) -> IntentAnalyzerProtocol:
        return IntentAnalyzerAgent(
            model_provider=self.settings.ANALYZER_PROVIDER,
            model_name=self.settings.ANALYZER_MODEL,
            api_key=self.settings.ANALYZER_API_KEY,
        )
    
    # ... 其他 Agent 创建方法

# 全局单例
_agent_factory: AgentFactory | None = None

def get_agent_factory() -> AgentFactory:
    """获取全局 AgentFactory 单例"""
    global _agent_factory
    
    if _agent_factory is None:
        from app.config.settings import settings
        _agent_factory = AgentFactory(settings)
    
    return _agent_factory
```

### 为什么需要 settings？

`AgentFactory` 需要 `settings` 是因为所有 Agent 都需要配置：

```python
# settings.py 中的 LLM 配置
ANALYZER_PROVIDER = "openai"
ANALYZER_MODEL = "gpt-4o-mini"
ANALYZER_BASE_URL = "https://api.openai.com/v1"
ANALYZER_API_KEY = "sk-xxx..."

ARCHITECT_PROVIDER = "deepseek"
ARCHITECT_MODEL = "deepseek-chat"
ARCHITECT_BASE_URL = "https://api.deepseek.com"
ARCHITECT_API_KEY = "sk-yyy..."

# ... 其他 Agent 的配置
```

**如果缺少 settings**：
- ❌ Agent 无法知道使用哪个 LLM Provider
- ❌ Agent 无法获取 API Key
- ❌ 所有 LLM 调用都会失败

---

## 相关文件

### 修改的文件

1. **`backend/app/tasks/content_generation_tasks.py`** ✅
   - 第 180 行：导入改为 `get_agent_factory`
   - 第 223 行：调用改为 `get_agent_factory()`

### 相关文件（无需修改）

2. **`backend/app/agents/factory.py`**
   - `AgentFactory` 类定义
   - `get_agent_factory()` 全局单例函数

3. **`backend/app/config/settings.py`**
   - 所有 LLM 的配置

---

## 预防措施

### 1. 代码审查检查项

在 Pull Request 中检查：
- ✅ 所有 `AgentFactory` 的使用都通过 `get_agent_factory()`
- ✅ 不要直接调用 `AgentFactory(settings)`（除非在测试中）
- ✅ Celery 任务中的依赖注入正确

### 2. 添加类型检查

在 CI/CD 中运行：
```bash
# 使用 mypy 检查类型错误
mypy backend/app/tasks/
```

这会提前发现类似问题：
```
error: Missing positional argument "settings" in call to "AgentFactory"
```

### 3. 单元测试

为 Celery 任务添加单元测试：

```python
# tests/unit/test_content_generation_tasks.py
import pytest
from app.tasks.content_generation_tasks import _async_generate_content

@pytest.mark.asyncio
async def test_agent_factory_initialization():
    """测试 AgentFactory 初始化正确"""
    # 模拟任务参数
    result = await _async_generate_content(
        task_id="test-task",
        roadmap_id="test-roadmap",
        roadmap_framework_data={...},
        user_preferences_data={...},
    )
    
    # 验证任务执行成功（不抛出 TypeError）
    assert result is not None
```

---

## 总结

### 问题根源

1. ❌ `content_generation_tasks.py` 中错误地调用 `AgentFactory()` 
2. ❌ 缺少必需的 `settings` 参数
3. ❌ 导致 Celery Worker 在初始化 Agent 时崩溃

### 解决方案

1. ✅ 将导入改为 `get_agent_factory`
2. ✅ 使用全局单例函数自动注入 `settings`
3. ✅ 符合工厂模式的最佳实践

### 修复状态

- ✅ **代码修复**: 已完成
- ✅ **Lint 检查**: 通过
- ⏳ **功能测试**: 需要用户执行
- ⏳ **生产验证**: 待部署验证

### 下一步

1. **重启 Celery Worker**（加载修复后的代码）
2. **执行完整的端到端测试**
3. **验证内容生成正常完成**
4. **监控日志确保无错误**

---

**修复者**: AI Assistant  
**审核者**: 待审核  
**版本**: v1.0  
**参考文档**: 
- `doc/WORKFLOW_APPROVAL_SKIP_CONTENT_FIX.md`
- `backend/docs/CELERY_CONTENT_GENERATION_MIGRATION_COMPLETE.md`
- `backend/app/agents/factory.py`

