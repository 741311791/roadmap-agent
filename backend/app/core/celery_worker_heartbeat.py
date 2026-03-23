"""
Celery Worker heartbeat 管理

设计目标：
1. 在 inspect 不可用时，仍能知道 Worker 是否在线。
2. 为监控页提供比 Celery remote control 更稳定的在线性信号。
3. 为强制清理卡住任务提供额外判断依据。
"""

from __future__ import annotations

import socket
import threading
from datetime import datetime
from typing import Any, Optional

import redis
import structlog

from app.config.settings import settings
from app.db.redis_client import redis_client
from app.utils.serializers import fast_dumps, fast_loads

logger = structlog.get_logger()

HEARTBEAT_KEY_PREFIX = "celery:worker_heartbeat"
HEARTBEAT_INTERVAL_SECONDS = 10
HEARTBEAT_TTL_SECONDS = 30


class CeleryWorkerHeartbeatManager:
    """
    Celery Worker heartbeat 管理器

    使用同步 Redis 客户端在后台线程中持续上报心跳，
    避免依赖 Celery inspect 这条容易超时的控制面链路。
    """

    def __init__(self) -> None:
        self._publisher_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._worker_hostname: Optional[str] = None
        self._worker_payload: dict[str, Any] = {}
        self._redis_client: Optional[redis.Redis] = None

    def start(self, *, worker_hostname: str, queues: list[str]) -> None:
        """
        启动 heartbeat 上报

        Args:
            worker_hostname: Worker 主机名
            queues: Worker 监听的队列列表
        """
        if self._publisher_thread and self._publisher_thread.is_alive():
            logger.info("celery_worker_heartbeat_already_running", worker_hostname=self._worker_hostname)
            return

        self._worker_hostname = worker_hostname
        self._worker_payload = {
            "hostname": worker_hostname,
            "queues": queues,
            "started_at": datetime.utcnow().isoformat(),
        }
        self._stop_event.clear()
        self._redis_client = redis.Redis.from_url(
            settings.get_redis_url,
            socket_timeout=5,
            socket_connect_timeout=5,
            socket_keepalive=True,
            retry_on_timeout=True,
        )
        self._publisher_thread = threading.Thread(
            target=self._publish_loop,
            daemon=True,
            name=f"worker-heartbeat-{worker_hostname}",
        )
        self._publisher_thread.start()
        logger.info(
            "celery_worker_heartbeat_started",
            worker_hostname=worker_hostname,
            queues=queues,
            interval_seconds=HEARTBEAT_INTERVAL_SECONDS,
            ttl_seconds=HEARTBEAT_TTL_SECONDS,
        )

    def stop(self) -> None:
        """
        停止 heartbeat 上报，并删除对应 heartbeat key
        """
        self._stop_event.set()

        if self._publisher_thread and self._publisher_thread.is_alive():
            self._publisher_thread.join(timeout=2)

        if self._redis_client and self._worker_hostname:
            try:
                self._redis_client.delete(self._build_key(self._worker_hostname))
            except Exception as exc:
                logger.warning(
                    "celery_worker_heartbeat_delete_failed",
                    worker_hostname=self._worker_hostname,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        self._publisher_thread = None
        self._redis_client = None
        self._worker_hostname = None
        self._worker_payload = {}
        logger.info("celery_worker_heartbeat_stopped")

    def _publish_loop(self) -> None:
        """
        后台线程循环发布 heartbeat
        """
        while not self._stop_event.is_set():
            try:
                if self._redis_client and self._worker_hostname:
                    payload = {
                        **self._worker_payload,
                        "updated_at": datetime.utcnow().isoformat(),
                    }
                    self._redis_client.set(
                        self._build_key(self._worker_hostname),
                        fast_dumps(payload),
                        ex=HEARTBEAT_TTL_SECONDS,
                    )
            except Exception as exc:
                logger.warning(
                    "celery_worker_heartbeat_publish_failed",
                    worker_hostname=self._worker_hostname,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

            self._stop_event.wait(timeout=HEARTBEAT_INTERVAL_SECONDS)

    @staticmethod
    def _build_key(worker_hostname: str) -> str:
        """
        构造 heartbeat Redis key

        Args:
            worker_hostname: Worker 主机名

        Returns:
            Redis key
        """
        return f"{HEARTBEAT_KEY_PREFIX}:{worker_hostname}"


heartbeat_manager = CeleryWorkerHeartbeatManager()


def infer_worker_queues(worker_hostname: str) -> list[str]:
    """
    根据 Worker 主机名推断队列

    Args:
        worker_hostname: Worker 主机名

    Returns:
        队列列表
    """
    if worker_hostname.startswith("content@"):
        return ["content_generation"]
    if worker_hostname.startswith("mentor-persist@"):
        return ["mentor_persist"]
    if worker_hostname.startswith("mentor-memory@"):
        return ["mentor_memory"]
    return ["celery"]


def resolve_worker_hostname(sender: Any = None, **kwargs) -> str:
    """
    从 Celery signal 上下文解析 Worker 主机名

    Args:
        sender: Signal sender
        **kwargs: 其他 signal 参数

    Returns:
        Worker 主机名
    """
    candidates = [
        getattr(sender, "hostname", None),
        getattr(kwargs.get("sender"), "hostname", None),
        kwargs.get("hostname"),
        kwargs.get("nodename"),
    ]
    for candidate in candidates:
        if candidate:
            return str(candidate)

    return f"worker@{socket.gethostname()}"


async def get_live_worker_heartbeats() -> list[dict[str, Any]]:
    """
    读取当前所有在线 Worker heartbeat

    Returns:
        heartbeat 列表；Redis 不可用时返回空列表
    """
    try:
        await redis_client.connect()
        results: list[dict[str, Any]] = []
        async for key in redis_client._client.scan_iter(match=f"{HEARTBEAT_KEY_PREFIX}:*"):
            data = await redis_client._client.get(key)
            if not data:
                continue
            results.append(fast_loads(data))

        results.sort(key=lambda item: item.get("hostname", ""))
        return results
    except Exception as exc:
        logger.warning(
            "celery_worker_heartbeat_fetch_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return []

