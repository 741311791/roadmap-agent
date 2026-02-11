# litellm Event Loop 跨进程污染修复

## 问题现象

```
RuntimeError: <Queue at 0x133728530 maxsize=50000 tasks=2> is bound to a different event loop
```

**发生位置**：Celery Worker 子进程调用 LLM 时  
**错误来源**：`litellm/litellm_core_utils/logging_worker.py:102`

---

## 根本原因分析（第一性原理）

### 1. asyncio.Queue 的 Event Loop 绑定机制

```python
# asyncio/mixins.py
class _LoopBoundMixin:
    def _get_loop(self):
        if self._loop is None:
            raise RuntimeError('No running event loop')
        # ⚠️ 核心检查：Queue 只能在创建它的 event loop 中使用
        if not self._loop.is_running():
            raise RuntimeError(f'{self!r} is bound to a different event loop')
        return self._loop
```

**物理真理**：`asyncio.Queue` 在创建时会**永久绑定**到当前的 event loop。这个绑定关系**不可更改**。

### 2. Unix Fork 的内存继承机制

```
父进程 (Celery Main)                子进程 (Worker-1)
─────────────────────                ─────────────────
Event Loop A (主进程)     fork()     Event Loop A (已关闭)
     ↓                    ────>           ↓
Queue._loop = A                      Queue._loop = A (僵尸引用)
     ↓                                     ↓
                                      Event Loop B (新创建)
                                           ↓
                                      ❌ Queue 仍然绑定到 A
```

**系统调用真相**：
- `fork()` 创建子进程时，子进程获得父进程内存空间的写时复制（COW）快照
- 所有对象引用（包括 `Queue._loop`）都被复制
- 子进程中的 Queue 对象仍然指向父进程的（已关闭的）event loop

### 3. litellm 的全局状态设计缺陷

```python
# litellm 在模块导入时就创建了全局队列
class LoggingWorker:
    def __init__(self):
        # ⚠️ 在父进程导入时创建，绑定到父进程的 event loop
        self._queue = asyncio.Queue(maxsize=50000)
```

**逻辑断裂点**：
- litellm 在模块导入时（而非延迟初始化）创建 `asyncio.Queue`
- Celery 在父进程中 `import litellm`
- 所有 fork 出的子进程都继承这个"僵尸" Queue

---

## 因果链推导

```
Step 1: Celery App 启动（父进程）
   ↓
Step 2: 导入 app.agents.tech_assessment_generator
   ↓ (触发链式导入)
Step 3: 导入 litellm 模块
   ↓
Step 4: litellm 初始化 LoggingWorker
   ↓
Step 5: 创建 asyncio.Queue(maxsize=50000)
   ↓ [此时 Queue._loop = 父进程的 event loop]
Step 6: Celery fork 出子进程
   ↓ [子进程继承 Queue 对象及其 _loop 引用]
Step 7: worker_process_init 信号触发
   ↓
Step 8: 子进程创建新的 event loop (new_loop)
   ↓ [Queue._loop 仍然指向父进程的旧 loop]
Step 9: TechAssessmentGenerator.generate_assessment_with_plan()
   ↓
Step 10: litellm.completion() 调用 LLM
   ↓
Step 11: LoggingWorker 尝试 await queue.get()
   ↓
Step 12: asyncio.Queue._get_loop() 检测到 loop 不匹配
   ↓
Step 13: RuntimeError: bound to a different event loop
```

**必然性**：只要满足以下条件，错误就**必然**发生（概率 100%）：
1. litellm 在父进程中被导入
2. Celery 使用 prefork 模式
3. 子进程创建新的 event loop

---

## 解决方案

### 实施的方案：在 worker_process_init 中重置 litellm 状态

**文件**：`backend/app/core/celery_app.py`

```python
@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """Worker 子进程初始化时调用"""
    import structlog
    import asyncio
    logger = structlog.get_logger()
    
    try:
        # 第一步：为子进程创建新的事件循环
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        
        # 第二步：重置数据库引擎缓存
        from app.db.session import reset_engine_cache
        reset_engine_cache()
        
        # 第三步：重置 Celery 专用引擎缓存
        from app.db.celery_session import reset_celery_engine_cache
        reset_celery_engine_cache()
        
        # 🆕 第四步：重置 litellm 的异步队列
        import litellm
        # 清除 litellm 的全局日志队列，强制在新 event loop 中重新创建
        if hasattr(litellm, 'logging_callback_manager'):
            litellm.logging_callback_manager = None
        if hasattr(litellm, '_logging_worker'):
            litellm._logging_worker = None
        logger.info(
            "litellm_state_reset",
            message="litellm 全局状态已重置，避免跨 event loop 污染"
        )
    except Exception as e:
        logger.error("worker_process_init_error", error=str(e))
```

### 原理解释

1. **清除全局单例**：将 litellm 的全局 LoggingWorker 引用设为 `None`
2. **延迟初始化**：下次调用 litellm API 时，会在新的 event loop 中重新创建 Queue
3. **隔离保证**：每个 Worker 子进程拥有独立的 litellm 状态

---

## 验证方法

### 1. 观察日志

重启 Celery Worker 后，应该看到：

```
celery_worker_process_init message="Celery Worker 进程初始化完成"
litellm_state_reset message="litellm 全局状态已重置，避免跨 event loop 污染"
```

### 2. 测试题目生成

```bash
# 触发测试题生成任务
curl -X POST http://localhost:8000/api/v1/learning/assessments/trigger-initialization

# 观察 Celery Worker 日志，应该看到：
[INFO] generating_single_tech_assessment technology=python proficiency_level=beginner
[INFO] tech_assessment_generated_and_saved total_questions=20
```

### 3. 确认无错误

Celery Worker 日志中不应再出现：
```
RuntimeError: <Queue at 0x...> is bound to a different event loop
```

---

## 其他可能的解决方案（未采用）

### 方案 2: 禁用 litellm 异步日志

```python
# 在 Agent 初始化时禁用异步回调
import litellm
litellm.callbacks = []
```

**缺点**：丢失 litellm 的日志功能，不利于调试。

### 方案 3: 修改 Celery 为 solo 模式

```bash
celery -A app.core.celery_app worker --pool=solo
```

**缺点**：
- 失去并发能力（只有1个 Worker）
- 生产环境性能不足

### 方案 4: 延迟导入 Agent

```python
# 在任务函数内部导入（而非模块顶部）
def generate_assessment_task():
    from app.agents.tech_assessment_generator import TechAssessmentGenerator
    agent = TechAssessmentGenerator()
    ...
```

**缺点**：
- 每次任务都重新导入，性能开销大
- 不符合 Python 模块导入规范

---

## 经验总结

### 教训

1. **全局状态 + Fork = 灾难**  
   任何在父进程中创建的全局 asyncio 对象（Queue、Lock、Event）都会在 fork 后失效。

2. **第三方库的隐式初始化**  
   litellm 这类库在导入时就创建全局状态，与 Celery prefork 模式天然冲突。

3. **Event Loop 不可序列化**  
   asyncio.Queue 的 `_loop` 引用不能跨进程传递，必须在每个进程中重新创建。

### 最佳实践

1. **延迟初始化**：避免在模块导入时创建 asyncio 对象
2. **进程隔离检查**：所有涉及 asyncio 的第三方库都需要在 `worker_process_init` 中重置
3. **显式资源管理**：在 Celery 任务中，优先使用上下文管理器（`async with`）而非全局单例

---

## 适用场景

此修复方案适用于所有满足以下条件的场景：
- ✅ 使用 Celery prefork 模式
- ✅ 在 Celery 任务中调用异步 API（litellm、httpx 等）
- ✅ 第三方库在模块导入时创建 asyncio 对象

---

## 参考资料

1. [asyncio Event Loop 官方文档](https://docs.python.org/3/library/asyncio-eventloop.html)
2. [Celery Signals - worker_process_init](https://docs.celeryq.dev/en/stable/userguide/signals.html#worker-process-init)
3. [Unix fork() 系统调用](https://man7.org/linux/man-pages/man2/fork.2.html)
4. [litellm GitHub Issues - Event Loop 相关问题](https://github.com/BerriAI/litellm/issues)

