#!/usr/bin/env python3
"""
Tavily API 配额自动更新定时任务

功能：
- 每小时自动查询所有 Tavily API Key 的使用量
- 通过官方 API 接口获取最新配额信息
- 更新数据库中的 remaining_quota 字段
- 支持优雅关闭和错误重试

运行方式：
- 本地测试: python scripts/update_tavily_quota.py
- Railway 部署: 通过 railway_entrypoint.sh 启动（SERVICE_TYPE=tavily_quota_updater）
"""
import asyncio
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
import schedule
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config.settings import settings
from app.db.session import AsyncSessionLocal
from app.models.database import TavilyAPIKey

# 配置日志
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# 全局关闭标志
shutdown_flag = False

# 配置参数
TAVILY_USAGE_API_URL = "https://api.tavily.com/usage"
UPDATE_INTERVAL_HOURS = int(getattr(settings, "QUOTA_UPDATE_INTERVAL_HOURS", 1))
HTTP_TIMEOUT = 30.0  # API 请求超时时间（秒）
MAX_RETRIES = 3  # 最大重试次数


def signal_handler(signum: int, frame) -> None:
    """
    信号处理器：优雅关闭
    
    Args:
        signum: 信号编号
        frame: 当前栈帧
    """
    global shutdown_flag
    logger.info(
        "received_shutdown_signal",
        signal=signal.Signals(signum).name,
        timestamp=datetime.now().isoformat()
    )
    shutdown_flag = True


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    reraise=True,
)
async def fetch_tavily_usage(api_key: str, client: httpx.AsyncClient) -> dict:
    """
    调用 Tavily 官方 API 查询配额使用情况（带重试）
    
    Args:
        api_key: Tavily API Key
        client: HTTP 客户端
        
    Returns:
        包含配额信息的字典
        
    Raises:
        httpx.HTTPError: HTTP 请求错误
        httpx.TimeoutException: 请求超时
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    response = await client.get(
        TAVILY_USAGE_API_URL,
        headers=headers,
        timeout=HTTP_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


async def update_single_key_quota(
    key_record: TavilyAPIKey,
    session: AsyncSession,
    client: httpx.AsyncClient
) -> bool:
    """
    更新单个 API Key 的配额信息
    
    Args:
        key_record: TavilyAPIKey 数据库记录
        session: 数据库会话
        client: HTTP 客户端
        
    Returns:
        更新是否成功
    """
    api_key = key_record.api_key
    key_prefix = api_key[:10] + "..." if len(api_key) > 10 else api_key
    old_quota = key_record.remaining_quota
    old_limit = key_record.plan_limit
    
    try:
        # 调用 Tavily API 获取使用量
        logger.debug(
            "fetching_tavily_usage",
            key_prefix=key_prefix,
            old_quota=old_quota
        )
        
        usage_data = await fetch_tavily_usage(api_key, client)
        
        # 解析响应数据
        account_data = usage_data.get("account", {})
        plan_usage = account_data.get("plan_usage", 0)
        plan_limit = account_data.get("plan_limit", 0)
        
        if plan_limit == 0:
            logger.warning(
                "tavily_plan_limit_zero",
                key_prefix=key_prefix,
                usage_data=usage_data
            )
            return False
        
        # 计算剩余配额
        remaining_quota = plan_limit - plan_usage
        
        # 更新数据库（仅在值发生变化时）
        if remaining_quota != old_quota or plan_limit != old_limit:
            key_record.remaining_quota = remaining_quota
            key_record.plan_limit = plan_limit
            # updated_at 会通过 onupdate 自动更新
            
            await session.commit()
            
            logger.info(
                "tavily_quota_updated",
                key_prefix=key_prefix,
                old_quota=old_quota,
                new_quota=remaining_quota,
                plan_limit=plan_limit,
                plan_usage=plan_usage,
                quota_change=remaining_quota - old_quota
            )
        else:
            logger.debug(
                "tavily_quota_unchanged",
                key_prefix=key_prefix,
                quota=remaining_quota,
                limit=plan_limit
            )
        
        return True
        
    except httpx.HTTPStatusError as e:
        logger.error(
            "tavily_api_http_error",
            key_prefix=key_prefix,
            status_code=e.response.status_code,
            error=str(e),
            response_text=e.response.text[:200] if e.response else None
        )
        await session.rollback()
        return False
        
    except httpx.TimeoutException as e:
        logger.error(
            "tavily_api_timeout",
            key_prefix=key_prefix,
            error=str(e),
            timeout=HTTP_TIMEOUT
        )
        await session.rollback()
        return False
        
    except Exception as e:
        logger.error(
            "tavily_quota_update_failed",
            key_prefix=key_prefix,
            error=str(e),
            error_type=type(e).__name__
        )
        await session.rollback()
        return False


async def update_all_keys_quota() -> None:
    """
    批量更新所有 API Keys 的配额信息
    
    执行流程：
    1. 查询所有需要更新的 Key（remaining_quota <= plan_limit）
    2. 逐个调用 Tavily API 获取最新配额
    3. 更新数据库，单个失败不影响其他 Key
    """
    start_time = time.time()
    
    logger.info(
        "tavily_quota_update_started",
        interval_hours=UPDATE_INTERVAL_HOURS,
        timestamp=datetime.now().isoformat()
    )
    
    async with AsyncSessionLocal() as session:
        try:
            # 查询所有 Key（条件：remaining_quota <= plan_limit，排除异常数据）
            stmt = select(TavilyAPIKey).where(
                TavilyAPIKey.remaining_quota <= TavilyAPIKey.plan_limit
            )
            result = await session.execute(stmt)
            keys = result.scalars().all()
            
            total_keys = len(keys)
            if total_keys == 0:
                logger.warning("no_tavily_keys_found")
                return
            
            logger.info(
                "tavily_keys_fetched",
                total_keys=total_keys
            )
            
            # 创建 HTTP 客户端（复用连接）
            async with httpx.AsyncClient() as client:
                success_count = 0
                failed_count = 0
                
                # 逐个更新 Key
                for key_record in keys:
                    if shutdown_flag:
                        logger.info("shutdown_requested_aborting_update")
                        break
                    
                    success = await update_single_key_quota(key_record, session, client)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                
                elapsed_time = time.time() - start_time
                
                logger.info(
                    "tavily_quota_update_completed",
                    total_keys=total_keys,
                    success_count=success_count,
                    failed_count=failed_count,
                    elapsed_seconds=round(elapsed_time, 2)
                )
                
        except Exception as e:
            logger.error(
                "tavily_quota_update_batch_failed",
                error=str(e),
                error_type=type(e).__name__
            )


def run_update_job() -> None:
    """
    同步包装器：在新的事件循环中运行异步更新任务
    
    注意：schedule 库是同步的，需要创建新的事件循环
    """
    try:
        # 创建新的事件循环（避免与主事件循环冲突）
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(update_all_keys_quota())
        loop.close()
    except Exception as e:
        logger.error(
            "update_job_failed",
            error=str(e),
            error_type=type(e).__name__
        )


def run_scheduler() -> None:
    """
    主调度循环：每小时执行一次配额更新任务
    
    特性：
    - 支持自定义更新间隔（环境变量：QUOTA_UPDATE_INTERVAL_HOURS）
    - 优雅关闭（响应 SIGTERM/SIGINT 信号）
    - 立即执行一次初始更新
    """
    logger.info(
        "tavily_quota_updater_starting",
        update_interval_hours=UPDATE_INTERVAL_HOURS,
        environment=settings.ENVIRONMENT,
        database_host=settings.POSTGRES_HOST
    )
    
    # 注册信号处理器
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # 配置调度任务
    schedule.every(UPDATE_INTERVAL_HOURS).hours.do(run_update_job)
    
    # 立即执行一次初始更新
    logger.info("running_initial_update")
    run_update_job()
    
    # 主循环
    logger.info("scheduler_loop_started")
    while not shutdown_flag:
        schedule.run_pending()
        time.sleep(1)  # 每秒检查一次
    
    logger.info("tavily_quota_updater_stopped")


if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        logger.info("keyboard_interrupt_received")
        sys.exit(0)
    except Exception as e:
        logger.critical(
            "tavily_quota_updater_crashed",
            error=str(e),
            error_type=type(e).__name__
        )
        sys.exit(1)

