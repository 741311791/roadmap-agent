# Redis SSL 连接错误修复

**日期**: 2025-12-27  
**状态**: ✅ 已修复

---

## 问题描述

生成路线图过程中，后端报错：

```
2025-12-27 20:33:45 [error] notification_publish_failed 
error="AbstractConnection.__init__() got an unexpected keyword argument 'ssl'" 
event_type=progress 
task_id=bd548168-1820-4cb3-9e8b-c5546166609d
```

## 根本原因

在 `backend/app/db/redis_client.py` 中，使用了错误的 SSL 配置方式：

```python
# ❌ 错误的配置
self._client = await aioredis.from_url(
    redis_url,
    encoding="utf-8",
    decode_responses=True,
    ssl=use_ssl,  # redis-py 5.x 不接受这个参数！
    ssl_cert_reqs="required" if use_ssl else None,
    ...
)
```

**问题原因**：

- `redis.asyncio.from_url()` 方法（redis-py 5.x）不接受 `ssl` 作为布尔参数
- Redis 客户端会根据 URL 协议自动判断是否启用 SSL：
  - `redis://` → 普通连接
  - `rediss://` → 自动启用 TLS/SSL

## 修复方案

### 1. 修改 Redis 客户端配置

**文件**: `backend/app/db/redis_client.py`

**修改内容**:

```python
# ✅ 正确的配置
# 构建连接参数
connection_kwargs = {
    "encoding": "utf-8",
    "decode_responses": True,
    # 超时配置和连接池设置
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
    "socket_keepalive": True,
    "max_connections": 50,
    "retry_on_timeout": True,
}

# SSL/TLS 配置（Upstash 等云服务需要）
# 注意：redis-py 5.x 会根据 rediss:// 协议自动启用 SSL
# 不需要传递 ssl=True/False 参数
if use_ssl:
    connection_kwargs["ssl_cert_reqs"] = "required"

self._client = await aioredis.from_url(redis_url, **connection_kwargs)
```

**关键改进**：

1. **移除 `ssl` 布尔参数**：不再显式传递 `ssl=True/False`
2. **保留 `ssl_cert_reqs`**：仅在使用 `rediss://` 时设置证书验证要求
3. **使用 `**connection_kwargs`**：更清晰的参数组织方式

### 2. 创建测试脚本

**文件**: `backend/scripts/test_redis_connection.py`

用于验证 Redis 连接和 SSL 配置是否正常工作。

## 验证结果

运行测试脚本：

```bash
cd backend
uv run python scripts/test_redis_connection.py
```

**输出结果**:

```
2025-12-27 20:37:29 [info] testing_redis_connection
2025-12-27 20:37:29 [info] redis_client_initialized ssl_enabled=True
2025-12-27 20:37:29 [info] testing_redis_ping
2025-12-27 20:37:29 [info] redis_ping_success result=True
2025-12-27 20:37:29 [info] testing_redis_json_operations
2025-12-27 20:37:29 [info] redis_json_retrieved
2025-12-27 20:37:29 [info] redis_data_consistency_verified
2025-12-27 20:37:30 [info] redis_delete_success
2025-12-27 20:37:30 [info] redis_connection_test_completed status=success

✅ Redis 连接测试成功！SSL 配置修复已生效。
```

## 影响范围

### 受影响的服务

1. **NotificationService** (`backend/app/services/notification_service.py`)
   - WebSocket 实时通知
   - 任务进度推送
   
2. **Redis Client** (`backend/app/db/redis_client.py`)
   - 所有 Redis 读写操作
   - 缓存服务
   
3. **Celery Worker** (`backend/app/core/celery_app.py`)
   - 使用 Redis 作为 broker 和 backend
   - 异步任务处理

### 需要重启的服务

- ✅ **FastAPI 应用**：使用 `--reload` 自动重载
- ⚠️ **Celery Worker**：需要手动重启
- ⚠️ **Celery Flower**：需要手动重启（可选）

## 重启 Celery 服务

### 方法 1：手动重启（推荐）

在终端 3 中（运行 Celery Worker 的终端）：

1. 按 `Ctrl+C` 停止当前 Worker
2. 重新启动：

```bash
cd backend
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --queues=logs \
    --concurrency=4 \
    --pool=prefork \
    --hostname=logs@%h \
    --max-tasks-per-child=500
```

### 方法 2：使用脚本重启

```bash
# 在 backend 目录下
pkill -f "celery.*worker"
sleep 2
uv run celery -A app.core.celery_app worker \
    --loglevel=info \
    --queues=logs \
    --concurrency=4 \
    --pool=prefork \
    --hostname=logs@%h \
    --max-tasks-per-child=500
```

## 技术细节

### redis-py 5.x SSL 连接机制

1. **自动 SSL 检测**：
   - `redis://` → 普通 TCP 连接
   - `rediss://` → 自动启用 TLS/SSL

2. **SSL 配置参数**（可选）：
   - `ssl_cert_reqs`: 证书验证要求（`"none"`, `"optional"`, `"required"`）
   - `ssl_ca_certs`: CA 证书文件路径
   - `ssl_certfile`: 客户端证书路径
   - `ssl_keyfile`: 客户端私钥路径

3. **Upstash Redis**：
   - 使用 `rediss://` 协议
   - 需要 `ssl_cert_reqs="required"`
   - 不需要手动指定证书文件（使用系统证书）

### Celery 配置

`backend/app/core/celery_app.py` 已正确配置 SSL：

```python
# 如果使用 rediss://，Celery 要求在 URL 中包含 ssl_cert_reqs 参数
if use_ssl and "ssl_cert_reqs" not in redis_url:
    separator = "&" if "?" in redis_url else "?"
    redis_url = f"{redis_url}{separator}ssl_cert_reqs=required"
```

这是 Celery 特有的配置方式，与 redis-py 的直接连接不同。

## 预防措施

### 1. 本地测试 SSL 连接

在部署到生产环境前，使用测试脚本验证：

```bash
uv run python backend/scripts/test_redis_connection.py
```

### 2. 监控 Redis 连接

在 `notification_service.py` 中已有完善的错误处理：

```python
try:
    await redis_client._client.publish(channel, message)
except asyncio.TimeoutError:
    logger.error("notification_publish_timeout", ...)
except Exception as e:
    logger.error("notification_publish_failed", error=str(e))
```

### 3. 健康检查

FastAPI 应用包含 Redis 健康检查端点：

```bash
curl http://localhost:8000/health
```

## 相关文档

- [redis-py 文档](https://redis-py.readthedocs.io/)
- [Upstash Redis 文档](https://docs.upstash.com/redis)
- [Celery Redis Backend](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)

## 总结

### 问题根源
- 使用了不兼容的 SSL 参数配置方式

### 解决方案
- 移除 `ssl` 布尔参数
- 依赖 redis-py 的自动 SSL 检测机制
- 仅在必要时配置 `ssl_cert_reqs`

### 验证状态
- ✅ Redis 连接测试通过
- ✅ SSL 连接正常工作
- ✅ Upstash Redis 兼容

### 下一步行动
- ⚠️ 重启 Celery Worker 服务
- ✅ 监控路线图生成流程
- ✅ 验证 WebSocket 通知功能

---

**修复者**: AI Assistant  
**审核者**: 待审核  
**版本**: v1.0

