"""
LangGraph Node 级 RetryPolicy 配置

定义标准的重试策略，用于不同类型的节点。

LangGraph 1.0 最佳实践：
- 每个 Node 独立配置 RetryPolicy
- 针对不同异常类型使用不同策略
- 使用指数退避避免雷群效应
- 最大重试次数：3-5 次

重试层级说明：
- Layer 1: BaseAgent.tenacity 重试（LLM 单次调用快速重试，3 次）
- Layer 2: LangGraph Node RetryPolicy（Node 级重试，5 次）
- Layer 3: Checkpointer 断点续传（用户触发重试，无限次）
"""
import litellm
from langgraph.types import RetryPolicy
from requests.exceptions import Timeout, ConnectionError
from sqlalchemy.exc import OperationalError


# ====================================================================
# LLM 调用节点的标准重试策略
# ====================================================================
LLM_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    retry_on=(litellm.RateLimitError, litellm.APIError, litellm.Timeout),
    backoff_factor=2.0,
    initial_interval=1.0,
    max_interval=60.0,
    jitter=True,
)
"""
LLM 调用节点重试策略

适用节点：Intent Analysis, Curriculum Design, Tutorial/Resource/Quiz Generation

参数说明：
- max_attempts: 最多重试 5 次
- retry_on: 仅针对 LLM 相关错误重试（限流、API 错误、超时）
- backoff_factor: 指数退避（1s, 2s, 4s, 8s, 16s）
- jitter: 随机抖动（避免雷群效应）
"""


# ====================================================================
# 外部 API 调用（Tavily 搜索）的重试策略
# ====================================================================
TAVILY_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    retry_on=(Timeout, ConnectionError, Exception),  # 网络相关错误
    backoff_factor=1.5,
    initial_interval=0.5,
    max_interval=5.0,
    jitter=True,
)
"""
外部 API 调用重试策略

适用节点：Resource Recommendation（使用 Tavily 搜索）

参数说明：
- max_attempts: 最多重试 3 次（外部 API 失败概率较高）
- retry_on: 网络相关错误
- backoff_factor: 较小的退避因子（0.5s, 0.75s, 1.12s）
"""


# ====================================================================
# 数据库操作的重试策略
# ====================================================================
DB_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    retry_on=(OperationalError,),  # 数据库连接错误
    backoff_factor=1.0,
    initial_interval=0.1,
    max_interval=1.0,
    jitter=False,  # 数据库操作不需要抖动
)
"""
数据库操作重试策略

适用场景：保存结果到数据库时出现连接错误

参数说明：
- max_attempts: 最多重试 3 次
- retry_on: 仅针对数据库连接错误
- backoff_factor: 线性退避（0.1s, 0.2s, 0.3s）
"""


# ====================================================================
# 纯逻辑节点（无需重试）
# ====================================================================
NO_RETRY_POLICY = RetryPolicy(
    max_attempts=1,
)
"""
纯逻辑节点重试策略（实际上不重试）

适用节点：Structure Validation, Edit Plan Analysis

说明：
- 纯逻辑节点不涉及外部调用，失败是确定性的
- 设置 max_attempts=1 表示不重试
"""


# ====================================================================
# 重试策略选择指南
# ====================================================================
"""
节点类型                          推荐策略
-----------------------------------------------
Intent Analysis                  LLM_RETRY_POLICY
Curriculum Design                LLM_RETRY_POLICY
Tutorial Generation              LLM_RETRY_POLICY
Resource Recommendation          TAVILY_RETRY_POLICY
Quiz Generation                  LLM_RETRY_POLICY
Structure Validation             NO_RETRY_POLICY
Edit Plan Analysis               NO_RETRY_POLICY
Roadmap Editor                   LLM_RETRY_POLICY
Human Review                     NO_RETRY_POLICY（使用 interrupt）

使用示例：
```python
from app.core.orchestrator.retry_policies import LLM_RETRY_POLICY

builder.add_node(
    "intent_analysis",
    intent_runner.run,
    retry_policy=LLM_RETRY_POLICY,
)
```
"""

