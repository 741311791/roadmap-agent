# 数据库连接超时和 LLM 输出解析问题修复报告

**修复日期**: 2025-12-07  
**任务 ID**: 连续的两个报错修复

---

## 问题 1: 数据库连接超时

### 问题描述
前端发起路线图生成请求后，后端报错：
```
psycopg.OperationalError: consuming input failed: could not receive data from server: Operation timed out
```

错误堆栈显示问题出在 `AsyncPostgresSaver` 的 `aget_tuple` 方法中，发生在 LangGraph 工作流执行时。

### 根本原因
在长时间运行的工作流中，`AsyncPostgresSaver` 使用的 psycopg 异步连接由于空闲时间过长被 PostgreSQL 服务器端关闭。当应用尝试使用已关闭的连接时，就会触发 `OperationalError`。

### 解决方案

#### 1. 添加 TCP Keepalive 参数
在 `backend/app/config/settings.py` 中修改 `CHECKPOINTER_DATABASE_URL` 属性，添加 TCP keepalive 参数：

```python
@property
def CHECKPOINTER_DATABASE_URL(self) -> str:
    """
    构建 Checkpointer 数据库连接 URL（用于 AsyncPostgresSaver）
    
    包含 TCP keepalive 参数以防止长时间运行的工作流中连接超时：
    - keepalives=1: 启用 TCP keepalive
    - keepalives_idle=30: 空闲 30 秒后发送 keepalive（默认是 2 小时）
    - keepalives_interval=10: keepalive 间隔 10 秒
    - keepalives_count=5: 最大重试 5 次
    - connect_timeout=10: 连接超时 10 秒
    """
    return (
        f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        f"?keepalives=1&keepalives_idle=30&keepalives_interval=10&keepalives_count=5&connect_timeout=10"
    )
```

**参数说明**：
- `keepalives=1`: 启用 TCP keepalive 机制
- `keepalives_idle=30`: 连接空闲 30 秒后发送第一个 keepalive 包（而不是默认的 2 小时）
- `keepalives_interval=10`: 每 10 秒发送一次 keepalive 包
- `keepalives_count=5`: 最多重试 5 次，如果都失败则判定连接已断开
- `connect_timeout=10`: 初始连接超时设置为 10 秒

#### 2. 使用连接池替代单一连接
在 `backend/app/core/orchestrator_factory.py` 中改用 `AsyncConnectionPool` 管理连接：

```python
from psycopg_pool import AsyncConnectionPool

# 使用连接池管理连接
cls._connection_pool = AsyncConnectionPool(
    conninfo=settings.CHECKPOINTER_DATABASE_URL,
    min_size=2,       # 最小保持 2 个连接
    max_size=10,      # 最大 10 个连接
    max_idle=300,     # 空闲连接最多保持 5 分钟
    timeout=30,       # 获取连接超时 30 秒
    reconnect_timeout=0,  # 自动重连（0 表示持续重试）
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
    },
)

await cls._connection_pool.open()
cls._checkpointer = AsyncPostgresSaver(cls._connection_pool)
await cls._checkpointer.setup()
```

**优势**：
1. **自动重连**: 连接池检测到连接断开后会自动重新建立连接
2. **连接复用**: 减少频繁创建/销毁连接的开销
3. **健康检查**: 连接池会定期检查连接健康状态
4. **并发支持**: 支持多个并发工作流同时运行

---

## 问题 2: LLM 输出格式解析失败

### 问题描述
数据库连接问题修复后，出现新的错误：
```
LLM 输出格式解析失败: 6 validation errors for RoadmapFramework
stages.0.modules.0.description
  Field required [type=missing, ...]
```

**问题**：无法在数据库日志中看到 LLM 的原始输出，难以调试。

### 根本原因
1. LLM 可能没有按照 prompt 要求的格式输出（Module 缺少括号中的描述）
2. 解析正则表达式过于严格，不接受没有描述的 Module
3. 缺少详细的日志记录 LLM 原始输出

### 解决方案

#### 1. 添加 LLM 原始输出日志
在 `backend/app/agents/curriculum_architect.py` 的 `design()` 方法中：

```python
# 解析输出
content = response.choices[0].message.content
logger.info(
    "curriculum_design_llm_response_received",
    response_length=len(content),
    # 记录完整输出以便调试（截取前1000字符避免日志过大）
    llm_output_preview=content[:1000] if len(content) > 1000 else content,
    llm_output_full_length=len(content),
)

# 为了方便调试，在 debug 级别记录完整输出
logger.debug(
    "curriculum_design_llm_full_output",
    llm_output_full=content,
)
```

**效果**：现在可以在日志中看到 LLM 的完整输出，方便调试和分析问题。

#### 2. 使 Module 描述字段更宽容
修改 Module 解析逻辑，支持没有描述的情况：

```python
# 解析 Module
elif line_stripped.startswith("Module "):
    # 尝试匹配有描述的格式
    match_with_desc = re.match(r'Module\s+\d+\.(\d+):\s*([^（(]+)[（(]([^）)]+)[）)]', line_stripped)
    # 尝试匹配无描述的格式
    match_without_desc = re.match(r'Module\s+\d+\.(\d+):\s*(.+)', line_stripped)
    
    if match_with_desc:
        # 有描述的格式
        module_name = match_with_desc.group(2).strip()
        module_desc = match_with_desc.group(3).strip()
    elif match_without_desc:
        # 无描述的格式（使用名称作为描述）
        module_name = match_without_desc.group(2).strip()
        module_desc = module_name  # 使用名称作为默认描述
        logger.warning(
            "module_missing_description",
            line=line_stripped,
            reason="Module 缺少描述，使用名称作为描述",
        )
```

**优势**：
- 更宽容的解析，不会因为格式细微差异而失败
- 提供默认描述（使用 Module 名称），确保字段不缺失
- 记录 warning 日志以便后续优化 prompt

#### 3. 添加详细的结构检查日志
在 Pydantic 验证之前添加详细的结构检查：

```python
# 检查每个 stage 和 module 的完整性
for stage_idx, stage in enumerate(framework_dict.get("stages", [])):
    logger.debug(
        "stage_structure_check",
        stage_idx=stage_idx,
        stage_id=stage.get("stage_id"),
        has_modules=bool(stage.get("modules")),
        modules_count=len(stage.get("modules", [])),
    )
    for module_idx, module in enumerate(stage.get("modules", [])):
        logger.debug(
            "module_structure_check",
            stage_idx=stage_idx,
            module_idx=module_idx,
            module_id=module.get("module_id"),
            has_name=bool(module.get("name")),
            has_description=bool(module.get("description")),
            has_concepts=bool(module.get("concepts")),
            concepts_count=len(module.get("concepts", [])),
        )
```

#### 4. 增强验证错误日志
在捕获 ValidationError 时记录完整的 LLM 输出：

```python
except ValueError as e:
    error_str = str(e)
    if "validation error" in error_str.lower():
        logger.error(
            "curriculum_design_validation_error",
            error=error_str,
            parsed_data_keys=list(framework_dict.keys()) if 'framework_dict' in locals() else None,
            stages_count=len(framework_dict.get("stages", [])) if 'framework_dict' in locals() else 0,
            content_length=len(content),
            content_full=content,  # 记录完整输出以便调试
        )
```

---

## 修改的文件清单

### 1. `backend/app/config/settings.py`
- ✅ 添加 TCP keepalive 参数到 `CHECKPOINTER_DATABASE_URL`

### 2. `backend/app/core/orchestrator_factory.py`
- ✅ 导入 `AsyncConnectionPool`
- ✅ 使用连接池替代单一连接
- ✅ 配置自动重连机制
- ✅ 更新清理逻辑

### 3. `backend/app/agents/curriculum_architect.py`
- ✅ 添加 LLM 原始输出日志（info 和 debug 级别）
- ✅ 使 Module 描述字段更宽容（支持无描述格式）
- ✅ 添加详细的结构检查日志
- ✅ 增强验证错误日志（记录完整 LLM 输出）

---

## 测试建议

### 1. 测试数据库连接稳定性
```bash
# 运行一个长时间的工作流（超过 2 分钟）
# 观察是否还会出现 OperationalError
```

### 2. 测试 LLM 输出解析
1. 检查日志中的 `curriculum_design_llm_response_received` 事件，查看 LLM 原始输出
2. 检查是否有 `module_missing_description` 警告
3. 如果有验证错误，查看 `curriculum_design_validation_error` 日志中的完整输出

### 3. 监控连接池状态
```python
# 可以添加定期日志记录连接池状态
logger.info(
    "connection_pool_stats",
    pool_size=cls._connection_pool.get_stats()["pool_size"],
    pool_available=cls._connection_pool.get_stats()["pool_available"],
)
```

---

## 预期效果

### ✅ 数据库连接问题
- 长时间运行的工作流不再出现连接超时
- 连接自动重连，无需手动干预
- 支持并发工作流

### ✅ LLM 输出解析问题
- 可以在日志中看到 LLM 的完整输出
- 更宽容的解析逻辑，减少因格式细微差异导致的失败
- 详细的结构检查日志，快速定位问题
- 验证错误时记录完整上下文，便于调试

---

## 后续优化建议

1. **优化 Prompt**: 根据 `module_missing_description` 警告，进一步优化 prompt 确保 LLM 始终输出描述
2. **添加重试机制**: 在解析失败时可以考虑重试 LLM 调用
3. **监控指标**: 添加 Prometheus 指标监控连接池使用情况和解析成功率
4. **单元测试**: 为 Module 解析逻辑添加单元测试，覆盖各种边界情况

---

## 参考资料

- [psycopg Connection Parameters](https://www.psycopg.org/psycopg3/docs/api/connections.html#connection-parameters)
- [psycopg_pool AsyncConnectionPool](https://www.psycopg.org/psycopg3/docs/api/pool.html#psycopg_pool.AsyncConnectionPool)
- [LangGraph AsyncPostgresSaver](https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint-postgres)
- [TCP Keepalive HOWTO](https://tldp.org/HOWTO/TCP-Keepalive-HOWTO/)
