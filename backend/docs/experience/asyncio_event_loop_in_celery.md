# AsyncIO Event Loop在Celery中的使用规范

> **经验等级**: 🔥 极高危陷阱  
> **首次遇到**: 2026-02-08（前期也遇到过，2026-01-30曾修复过类似问题）  
> **影响范围**: Celery + AsyncIO + LangGraph  
> **典型错误**: `RuntimeError: Lock object is bound to a different event loop`

---

## 🎯 核心原则

**在Celery Worker中，必须使用持久的Event Loop，禁止在任务中使用`asyncio.run()`创建新loop**

---

## 🧪 底层原理

### 公理1: Event Loop的线程局部性
- 每个线程只能有一个活跃的Event Loop
- AsyncIO原语（Lock、Event、Condition等）在创建时绑定到当前Event Loop
- 在不同Event Loop中使用同一个asyncio原语会触发`RuntimeError`

### 公理2: Celery Worker的进程模型
```
主进程 (Celery Master)
  └─ fork() 子进程1 (Worker Process 1)
      └─ 继承父进程内存空间
      └─ worker_process_init signal触发
          └─ setup_event_loop() 创建持久Loop
          
  └─ fork() 子进程2 (Worker Process 2)
      └─ 继承父进程内存空间
      └─ worker_process_init signal触发
          └─ setup_event_loop() 创建持久Loop
```

### 公理3: LangGraph Checkpointer的状态绑定
- `AsyncPostgresSaver`在初始化时创建内部Lock对象
- Lock对象绑定到创建时的Event Loop
- 如果在新的Event Loop中使用，会触发RuntimeError

---

## ⚠️ 错误模式分析

### 错误模式1: 在Celery任务中使用asyncio.run()

```python
# ❌ 错误：创建新的Event Loop
@celery_app.task
def my_task():
    result = asyncio.run(my_async_function())  # ❌ 创建新loop
    return result
```

**问题链条**:
```
Worker启动
  └─ setup_event_loop() 创建持久Loop A
    └─ OrchestratorFactory.initialize()
      └─ AsyncPostgresSaver创建Lock (绑定到Loop A)

Task执行
  └─ asyncio.run() 创建临时Loop B ❌
    └─ 尝试使用AsyncPostgresSaver
      └─ Lock.acquire() 在Loop B中执行
        └─ Lock检测到当前loop != 创建时的loop
          └─ RuntimeError: bound to a different event loop ❌
```

### 错误模式2: 多次创建新loop导致资源泄漏

```python
# ❌ 错误：每个任务都创建新loop
@celery_app.task
def task1():
    asyncio.run(func1())  # 创建Loop 1

@celery_app.task  
def task2():
    asyncio.run(func2())  # 创建Loop 2

@celery_app.task
def task3():
    asyncio.run(func3())  # 创建Loop 3
```

**问题**:
- 每次创建新loop有性能开销（~10ms）
- Loop关闭时可能残留未清理的资源
- 违反asyncio最佳实践（长期运行应用应该只有一个loop）

---

## ✅ 正确架构

### 1. Worker启动时创建持久Event Loop

**Worker初始化**（`backend/app/core/celery_app.py`）:
```python
from celery.signals import worker_process_init
from app.tasks.event_loop_manager import setup_event_loop

@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """Worker子进程初始化"""
    # ✅ 创建持久的Event Loop
    setup_event_loop()
    
    # ✅ 在持久loop中初始化OrchestratorFactory
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(OrchestratorFactory.initialize())
```

**Event Loop Manager**（`backend/app/tasks/event_loop_manager.py`）:
```python
# 全局变量：Worker进程的持久Event Loop
_worker_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None

def setup_event_loop() -> None:
    """创建持久的Event Loop（在后台线程中运行）"""
    global _worker_loop, _loop_thread
    
    def run_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _worker_loop = loop
        
        # 通知主线程循环已就绪
        _loop_ready.set()
        
        # 持续运行直到被停止
        loop.run_forever()
    
    # 启动后台线程
    _loop_thread = threading.Thread(target=run_loop, daemon=True)
    _loop_thread.start()
    
    # 等待循环就绪
    _loop_ready.wait(timeout=5)
```

### 2. 任务中使用持久Event Loop

```python
# ✅ 正确：使用Worker的持久Event Loop
from app.tasks.event_loop_manager import run_async_in_worker_loop

@celery_app.task
def my_task():
    # 在持久loop中执行异步代码
    result = run_async_in_worker_loop(my_async_function())
    return result


async def my_async_function():
    """异步业务逻辑"""
    # 可以安全使用所有asyncio特性
    async with some_lock:  # ✅ Lock绑定到持久loop
        await do_something()
    return result
```

### 3. run_async_in_worker_loop实现

```python
def run_async_in_worker_loop(coro: Coroutine) -> T:
    """
    在Worker的持久Event Loop中运行协程
    
    替代 asyncio.run()，避免创建新loop。
    """
    global _worker_loop
    
    if _worker_loop is None:
        raise RuntimeError("Worker事件循环未初始化")
    
    # 使用run_coroutine_threadsafe在事件循环线程中执行
    future = asyncio.run_coroutine_threadsafe(coro, _worker_loop)
    
    # 阻塞等待结果（让Celery的time_limit处理超时）
    return future.result()
```

---

## 🚨 历史案例

### 案例1: 内容生成子图Event Loop错误（2026-02-08）

**问题**:
```
RuntimeError: <asyncio.locks.Lock object at 0x160123470 [locked]> 
is bound to a different event loop
```

**调用栈**:
```
generate_all_content_task
  → asyncio.run(_execute_content_generation_subgraph)  ❌ 创建新loop
    → subgraph.ainvoke()
      → AsyncPostgresSaver.aget_tuple()
        → self.lock.acquire()  ❌ Lock绑定到不同loop
```

**根因**:
- Worker初始化时创建了持久Loop A
- OrchestratorFactory的AsyncPostgresSaver绑定到Loop A
- 任务中使用`asyncio.run()`创建了临时Loop B
- Lock对象在Loop B中无法使用

**修复**:
```python
# ❌ 修复前
result = asyncio.run(_execute_content_generation_subgraph(...))

# ✅ 修复后  
from app.tasks.event_loop_manager import run_async_in_worker_loop

result = run_async_in_worker_loop(_execute_content_generation_subgraph(...))
```

**影响文件**:
- `app/tasks/content_generation_tasks.py` (2处)
- `app/tasks/maintenance_tasks.py` (2处)
- `app/tasks/cover_image_tasks.py` (1处)

### 案例2: Celery异步事件循环冲突（2026-01-30）

**问题**: 类似的Event Loop冲突问题

**修复**: 引入了`event_loop_manager.py`和持久loop架构

**文档**: `backend/docs/20260130_修复Celery异步事件循环冲突问题.md`

---

## 🔍 排查清单

遇到Event Loop相关错误时，按此顺序检查：

- [ ] **错误信息确认**  
  是否包含`bound to a different event loop`或`got Future attached to a different loop`

- [ ] **任务代码检查**  
  Celery任务中是否使用了`asyncio.run()`

- [ ] **Event Loop初始化检查**  
  `worker_process_init`中是否调用了`setup_event_loop()`

- [ ] **OrchestratorFactory初始化检查**  
  是否在持久loop中初始化（`loop.run_until_complete(OrchestratorFactory.initialize())`）

- [ ] **导入检查**  
  任务文件是否导入了`from app.tasks.event_loop_manager import run_async_in_worker_loop`

---

## 📖 使用指南

### 场景1: 新增Celery异步任务

```python
# ✅ 标准模板
from app.core.celery_app import celery_app
from app.tasks.event_loop_manager import run_async_in_worker_loop

@celery_app.task(name="my_module.my_task")
def my_task(param1: str, param2: int):
    """
    Celery任务入口（同步函数）
    
    Args:
        param1: 参数1
        param2: 参数2
        
    Returns:
        任务结果
    """
    # 使用持久loop执行异步逻辑
    result = run_async_in_worker_loop(
        _my_async_logic(param1, param2)
    )
    return result


async def _my_async_logic(param1: str, param2: int):
    """
    异步业务逻辑（内部函数）
    
    所有asyncio操作都在这里进行。
    """
    # 可以安全使用任何asyncio特性
    async with some_lock:
        result = await do_something(param1, param2)
    
    return result
```

### 场景2: 使用LangGraph Checkpointer

```python
# ✅ 正确：使用持久loop
from app.tasks.event_loop_manager import run_async_in_worker_loop

@celery_app.task
def langgraph_task():
    result = run_async_in_worker_loop(_execute_graph())
    return result


async def _execute_graph():
    """执行LangGraph工作流"""
    from app.core.orchestrator_factory import OrchestratorFactory
    
    # ✅ OrchestratorFactory已在Worker初始化时绑定到持久loop
    executor = OrchestratorFactory.get_executor()
    
    # ✅ 在同一个loop中执行，Lock对象可以正常使用
    result = await executor.execute(...)
    return result
```

### 场景3: 多个异步操作

```python
# ✅ 正确：所有异步操作在同一个loop中
@celery_app.task
def complex_task():
    result = run_async_in_worker_loop(_complex_async_logic())
    return result


async def _complex_async_logic():
    """复杂的异步逻辑（多个步骤）"""
    # 第一步：查询数据
    async with get_celery_session() as session:
        data = await fetch_data(session)
    
    # 第二步：执行子图
    subgraph_result = await execute_subgraph(data)
    
    # 第三步：保存结果
    async with get_celery_session() as session:
        await save_result(session, subgraph_result)
    
    return subgraph_result
```

---

## 🧪 测试验证

### 验证Lock对象使用

```python
from app.tasks.event_loop_manager import setup_event_loop, run_async_in_worker_loop
import asyncio

# 初始化持久loop
setup_event_loop()

async def task_with_lock():
    """使用Lock的任务"""
    lock = asyncio.Lock()
    async with lock:
        await asyncio.sleep(0.1)
        return "success"

# 测试：多次调用应该都成功
result1 = run_async_in_worker_loop(task_with_lock())  # ✅
result2 = run_async_in_worker_loop(task_with_lock())  # ✅
result3 = run_async_in_worker_loop(task_with_lock())  # ✅

# 如果使用asyncio.run()，第二次调用会失败
result = asyncio.run(task_with_lock())  # ❌ RuntimeError
```

---

## 🚨 禁止模式

### 禁止1: 在任务中使用asyncio.run()

```python
# ❌ 绝对禁止
@celery_app.task
def bad_task():
    result = asyncio.run(my_async_function())  # ❌ 创建新loop
    return result
```

### 禁止2: 在任务中创建新Event Loop

```python
# ❌ 绝对禁止
@celery_app.task
def bad_task():
    loop = asyncio.new_event_loop()  # ❌
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(my_async_function())
    loop.close()
    return result
```

### 禁止3: 混用不同loop执行方法

```python
# ❌ 绝对禁止
@celery_app.task
def bad_task():
    # 第一次使用持久loop
    result1 = run_async_in_worker_loop(func1())  # ✅
    
    # 第二次使用新loop
    result2 = asyncio.run(func2())  # ❌ 破坏一致性
    
    return result1, result2
```

---

## ✅ 推荐模式

### 模式1: 简单异步任务

```python
from app.tasks.event_loop_manager import run_async_in_worker_loop

@celery_app.task
def simple_task(data: dict):
    """简单的异步任务"""
    result = run_async_in_worker_loop(_process_data(data))
    return result


async def _process_data(data: dict):
    """异步处理逻辑"""
    async with get_celery_session() as session:
        result = await session.execute(...)
    return result
```

### 模式2: LangGraph工作流任务

```python
from app.tasks.event_loop_manager import run_async_in_worker_loop

@celery_app.task
def workflow_task(task_id: str):
    """LangGraph工作流任务"""
    result = run_async_in_worker_loop(_execute_workflow(task_id))
    return result


async def _execute_workflow(task_id: str):
    """执行工作流"""
    from app.core.orchestrator_factory import OrchestratorFactory
    
    # ✅ 使用已初始化的OrchestratorFactory（绑定到持久loop）
    executor = OrchestratorFactory.get_executor()
    
    # ✅ 所有异步操作在同一loop中
    result = await executor.execute(...)
    return result
```

### 模式3: 多步骤异步任务

```python
from app.tasks.event_loop_manager import run_async_in_worker_loop

@celery_app.task
def multi_step_task(roadmap_id: str):
    """多步骤任务"""
    result = run_async_in_worker_loop(
        _multi_step_async(roadmap_id)
    )
    return result


async def _multi_step_async(roadmap_id: str):
    """多步骤异步逻辑"""
    # 所有步骤在同一个async函数中
    data = await step1(roadmap_id)
    result = await step2(data)
    await step3(result)
    return result
```

---

## 🛡️ Worker配置要点

### 必需配置（`backend/app/core/celery_app.py`）

```python
@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """Worker子进程初始化（关键配置）"""
    
    # ✅ 步骤1: 创建持久Event Loop
    from app.tasks.event_loop_manager import setup_event_loop
    setup_event_loop()
    
    # ✅ 步骤2: 重置数据库引擎（避免跨进程共享连接）
    from app.db.session import reset_engine_cache
    reset_engine_cache()
    
    # ✅ 步骤3: 在持久loop中初始化OrchestratorFactory
    # 这一步至关重要！确保AsyncPostgresSaver绑定到持久loop
    from app.core.orchestrator_factory import OrchestratorFactory
    import asyncio
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(OrchestratorFactory.initialize())


@worker_process_shutdown.connect
def on_worker_process_shutdown(**kwargs):
    """Worker关闭时清理"""
    from app.tasks.event_loop_manager import cleanup_event_loop
    cleanup_event_loop()
```

---

## 🔧 故障排查

### 症状1: RuntimeError - bound to a different event loop

**定位**:
```bash
# 搜索任务代码中是否使用了asyncio.run()
grep -r "asyncio.run(" backend/app/tasks/
```

**修复**:
```python
# 替换所有 asyncio.run() 为 run_async_in_worker_loop()
- result = asyncio.run(async_func())
+ from app.tasks.event_loop_manager import run_async_in_worker_loop
+ result = run_async_in_worker_loop(async_func())
```

### 症状2: got Future attached to a different loop

**定位**: 检查是否有异步对象（Future、Task）在不同loop间传递

**修复**: 确保所有异步操作在同一个async函数中完成

### 症状3: Worker启动慢或初始化失败

**定位**: 检查`worker_process_init`日志

**检查要点**:
```python
# 确认持久loop已创建
✅ worker_event_loop_created
✅ worker_event_loop_setup_complete

# 确认OrchestratorFactory已初始化
✅ worker_orchestrator_factory_reinitialized
```

---

## 📊 性能对比

| 方式 | Loop创建次数 | 性能 | 资源使用 |
|-----|------------|------|---------|
| ❌ asyncio.run() | 每个任务1次 | 慢（~10ms开销/任务） | 高（频繁创建/销毁） |
| ✅ 持久loop | Worker启动时1次 | 快（无开销） | 低（复用loop） |

**实测数据**（100个任务）:
- `asyncio.run()`: 总开销 ~1000ms
- `run_async_in_worker_loop()`: 总开销 ~0ms

---

## 💡 关键要点

1. **一个Worker一个Loop**: 持久Event Loop在Worker启动时创建，整个生命周期复用
2. **禁止asyncio.run()**: Celery任务中绝对禁止使用，必须用`run_async_in_worker_loop()`
3. **初始化顺序**: 先创建loop，再初始化OrchestratorFactory
4. **资源绑定**: 所有asyncio资源（Lock/Event/Checkpointer）自动绑定到持久loop
5. **线程安全**: `run_async_in_worker_loop()`内部使用`run_coroutine_threadsafe`确保线程安全
6. **异常传播**: 异步函数的异常会正确传播到Celery任务层
7. **性能优化**: 避免重复创建loop，节省~10ms/任务

---

## 📝 代码审查检查表

新增或修改Celery任务时：

- [ ] 是否使用了`asyncio.run()`？（如果是，必须替换）
- [ ] 是否导入了`run_async_in_worker_loop`？
- [ ] 异步逻辑是否封装在独立的async函数中？
- [ ] 是否使用了LangGraph Checkpointer？（如果是，必须用持久loop）
- [ ] 是否创建了新的Event Loop？（如果是，必须删除）
- [ ] 是否混用了不同的loop执行方式？（如果是，统一为持久loop）

---

## 🎓 延伸阅读

### AsyncIO最佳实践
- [Python官方文档 - Running and stopping the loop](https://docs.python.org/3/library/asyncio-eventloop.html)
- [Celery文档 - Worker Process Init](https://docs.celeryq.dev/en/stable/userguide/signals.html#worker-process-init)

### 相关修复记录
- `backend/docs/20260130_修复Celery异步事件循环冲突问题.md`
- `backend/docs/20260131_Celery_Worker_SIGSEGV_修复.md`
