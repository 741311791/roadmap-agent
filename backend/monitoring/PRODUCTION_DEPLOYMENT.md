# 生产环境监控部署指南

> **场景**: Prometheus + Grafana 部署在独立监控服务器，FastAPI 应用分布在不同容器/服务器

---

## 📋 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│  监控服务器 (Monitor Server)                                  │
│  ┌──────────────┐         ┌──────────────┐                  │
│  │  Prometheus  │ ◄────── │   Grafana    │                  │
│  │  :9090       │         │   :3000      │                  │
│  └──────┬───────┘         └──────────────┘                  │
│         │                                                     │
└─────────┼─────────────────────────────────────────────────────┘
          │
          │ HTTP Pull (每15秒)
          │
          ├──────────────┬──────────────┬──────────────┐
          ▼              ▼              ▼              ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ FastAPI │    │ FastAPI │    │ FastAPI │    │ Celery  │
    │ Pod/容器1│    │ Pod/容器2│    │ Pod/容器3│    │ Worker  │
    │ /metrics│    │ /metrics│    │ /metrics│    │ /metrics│
    └─────────┘    └─────────┘    └─────────┘    └─────────┘
    api-1.com      api-2.com      api-3.com      worker.com
```

---

## 🎯 方案 1: 静态配置（适合固定 IP/域名）

### 1. FastAPI 应用配置

#### Dockerfile（无需修改）

你的 FastAPI Dockerfile 已经暴露了 `/metrics` 端点，无需额外配置：

```dockerfile
# 你现有的 Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install -r requirements.txt

# 确保暴露 8000 端口
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 网络要求

**关键**: 确保监控服务器能访问到各个 FastAPI 容器的 8000 端口（或你配置的端口）。

### 2. Prometheus 配置（监控服务器）

创建 `prometheus.yml`:

```yaml
# /etc/prometheus/prometheus.yml

global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    cluster: 'production'
    region: 'cn-north-1'

scrape_configs:
  # FastAPI 应用实例
  - job_name: 'roadmap_api'
    static_configs:
      # 方式 1: 使用公网 IP/域名
      - targets:
          - 'api-1.example.com:8000'
          - 'api-2.example.com:8000'
          - 'api-3.example.com:8000'
        labels:
          app: 'roadmap_agent'
          env: 'production'
          instance_type: 'api'
      
      # 方式 2: 使用内网 IP（如果在同一 VPC）
      # - targets:
      #     - '10.0.1.10:8000'
      #     - '10.0.1.11:8000'
      #     - '10.0.1.12:8000'
    
    metrics_path: '/metrics'
    scrape_timeout: 10s
    
    # 可选：添加健康检查
    # scheme: 'https'  # 如果使用 HTTPS
    # tls_config:
    #   insecure_skip_verify: false

  # Celery Worker 实例
  - job_name: 'roadmap_celery'
    static_configs:
      - targets:
          - 'worker-1.example.com:8000'
          - 'worker-2.example.com:8000'
        labels:
          app: 'roadmap_agent'
          env: 'production'
          instance_type: 'celery'

  # Prometheus 自身
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### 3. 部署 Prometheus（监控服务器）

#### 使用 Docker（推荐）

```bash
# 创建配置目录
mkdir -p /opt/prometheus

# 上传 prometheus.yml 到 /opt/prometheus/prometheus.yml

# 启动 Prometheus
docker run -d \
  --name prometheus \
  --restart=always \
  -p 9090:9090 \
  -v /opt/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml \
  -v prometheus_data:/prometheus \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus \
  --web.enable-lifecycle
```

#### 使用 Systemd（直接安装）

```bash
# 下载 Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-amd64.tar.gz
tar xvf prometheus-*.tar.gz
sudo mv prometheus-*/ /opt/prometheus

# 创建 systemd 服务
sudo tee /etc/systemd/system/prometheus.service > /dev/null <<EOF
[Unit]
Description=Prometheus
After=network.target

[Service]
Type=simple
User=prometheus
ExecStart=/opt/prometheus/prometheus \\
  --config.file=/opt/prometheus/prometheus.yml \\
  --storage.tsdb.path=/var/lib/prometheus
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable prometheus
sudo systemctl start prometheus
```

### 4. 部署 Grafana（监控服务器）

#### 使用 Docker

```bash
docker run -d \
  --name grafana \
  --restart=always \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=your_secure_password \
  -e GF_INSTALL_PLUGINS=grafana-piechart-panel \
  -v grafana_data:/var/lib/grafana \
  grafana/grafana:latest
```

#### 配置 Prometheus 数据源

1. 访问 Grafana: `http://monitor-server:3000`
2. 登录（admin / your_secure_password）
3. Configuration → Data Sources → Add data source
4. 选择 Prometheus
5. URL: `http://localhost:9090`（如果 Grafana 和 Prometheus 在同一台机器）
6. 点击 "Save & Test"

### 5. 导入 Dashboard

1. 在 Grafana 中点击 "+" → Import
2. 上传 `grafana/dashboards/roadmap_agent_dashboard.json`
3. 选择 Prometheus 数据源
4. 点击 Import

---

## 🚀 方案 2: Kubernetes 服务发现（推荐）

### 1. Kubernetes Deployment

#### FastAPI 应用

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: roadmap-api
  labels:
    app: roadmap-agent
    component: api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: roadmap-agent
      component: api
  template:
    metadata:
      labels:
        app: roadmap-agent
        component: api
      annotations:
        prometheus.io/scrape: "true"    # ← 关键：启用 Prometheus 抓取
        prometheus.io/port: "8000"       # ← 指标端口
        prometheus.io/path: "/metrics"   # ← 指标路径
    spec:
      containers:
      - name: api
        image: your-registry/roadmap-agent:latest
        ports:
        - containerPort: 8000
          name: http
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: roadmap-api
  labels:
    app: roadmap-agent
spec:
  selector:
    app: roadmap-agent
    component: api
  ports:
  - port: 8000
    targetPort: 8000
    name: http
```

### 2. Prometheus Kubernetes 配置

```yaml
# prometheus-k8s-config.yml

global:
  scrape_interval: 15s

scrape_configs:
  # Kubernetes Pod 自动发现
  - job_name: 'kubernetes-pods'
    kubernetes_sd_configs:
      - role: pod
    
    relabel_configs:
      # 只抓取带有 prometheus.io/scrape=true 注解的 Pod
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
      
      # 使用自定义端口
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_port]
        action: replace
        target_label: __address__
        regex: ([^:]+)(?::\d+)?;(\d+)
        replacement: $1:$2
      
      # 使用自定义路径
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
        action: replace
        target_label: __metrics_path__
        regex: (.+)
      
      # 添加 Pod 标签
      - source_labels: [__meta_kubernetes_namespace]
        target_label: kubernetes_namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: kubernetes_pod_name
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
```

### 3. 部署到 Kubernetes

```bash
# 部署 Prometheus
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml

# 应用配置
kubectl apply -f prometheus-k8s-config.yml

# 部署 Grafana
kubectl apply -f grafana-deployment.yaml
```

---

## 🔐 安全配置

### 1. 防火墙规则

如果使用公网 IP，配置防火墙：

```bash
# 仅允许监控服务器访问 /metrics
# 示例：iptables
iptables -A INPUT -p tcp --dport 8000 -s <监控服务器IP> -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP
```

### 2. Nginx 反向代理（推荐）

在 FastAPI 前面加一层 Nginx，限制 `/metrics` 访问：

```nginx
# /etc/nginx/sites-available/roadmap-api

upstream fastapi {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;

    # 业务 API（公开）
    location /api {
        proxy_pass http://fastapi;
    }

    # Metrics 端点（限制 IP）
    location /metrics {
        allow 10.0.0.0/8;        # 内网
        allow <监控服务器IP>;     # 监控服务器
        deny all;
        
        proxy_pass http://fastapi;
    }
}
```

### 3. 认证（可选）

为 Prometheus 添加 Basic Auth：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'roadmap_api'
    basic_auth:
      username: 'prometheus'
      password: 'secure_password'
    static_configs:
      - targets: ['api.example.com:8000']
```

FastAPI 端配置（在 `/metrics` 路由添加认证）：

```python
# app/main.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()

def verify_prometheus_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username != "prometheus" or credentials.password != "secure_password":
        raise HTTPException(status_code=401)
    return True

# 保护 /metrics 端点
@app.get("/metrics", dependencies=[Depends(verify_prometheus_auth)])
async def metrics():
    # 返回 Prometheus 指标
    ...
```

---

## 📊 方案 3: 使用云服务（最简单）

### Grafana Cloud（推荐）

**优势**: 免费额度，无需自己维护

1. 注册 [Grafana Cloud](https://grafana.com/products/cloud/)
2. 获取 Prometheus Remote Write 配置
3. 在你的 FastAPI 容器中添加 Prometheus Agent

```yaml
# prometheus-agent.yml（部署在应用服务器）
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'local_app'
    static_configs:
      - targets: ['localhost:8000']

remote_write:
  - url: https://prometheus-prod-01-eu-west-0.grafana.net/api/prom/push
    basic_auth:
      username: <your_username>
      password: <your_api_key>
```

### AWS CloudWatch + Grafana

如果部署在 AWS：

1. 使用 CloudWatch Agent 采集指标
2. Grafana 连接 CloudWatch 数据源
3. 无需自己部署 Prometheus

---

## 🧪 验证部署

### 1. 测试 Metrics 端点

```bash
# 从监控服务器测试
curl http://api-1.example.com:8000/metrics

# 应该看到类似输出：
# http_requests_total{method="GET",path="/health"} 42
```

### 2. 检查 Prometheus Targets

访问 `http://monitor-server:9090/targets`，确认所有实例状态为 **UP**。

### 3. 测试 Grafana 查询

在 Grafana → Explore 中运行：

```promql
rate(http_requests_total[5m])
```

应该看到数据返回。

---

## 🚨 常见问题

### Q1: Prometheus 无法访问 FastAPI 容器

**症状**: Targets 页面显示 "Connection refused"

**解决方案**:
```bash
# 1. 检查网络连通性
ping api-1.example.com

# 2. 检查端口开放
telnet api-1.example.com 8000

# 3. 检查防火墙
iptables -L | grep 8000
```

### Q2: 容器 IP 动态变化

**症状**: 容器重启后 IP 改变，Prometheus 找不到

**解决方案**:
- 使用固定域名（通过 DNS 或负载均衡器）
- 使用 Kubernetes 服务发现
- 使用 Consul/Etcd 进行服务注册

### Q3: 多个容器如何区分

**方案**: 使用标签

```python
# app/middleware/prometheus_middleware.py
from app.core.prometheus.instruments import REQUEST_COUNTER

# 添加实例标签
import socket
HOSTNAME = socket.gethostname()

REQUEST_COUNTER.labels(
    app_name="roadmap_agent",
    instance=HOSTNAME,  # ← 自动区分容器
    method=method,
    path=path,
    status_code=status_code,
).inc()
```

---

## 📋 部署检查清单

生产环境上线前检查：

- [ ] Prometheus 能访问所有 FastAPI 实例
- [ ] `/metrics` 端点已限制访问（IP 白名单或认证）
- [ ] Grafana Dashboard 已导入并测试
- [ ] 数据保留策略已配置（默认 15 天）
- [ ] 告警规则已配置并测试
- [ ] 备份策略已设置（Grafana 配置和 Prometheus 数据）
- [ ] 监控服务器资源充足（推荐 4GB+ 内存）

---

## 📚 参考资源

- [Prometheus Remote Write](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#remote_write)
- [Kubernetes Service Discovery](https://prometheus.io/docs/prometheus/latest/configuration/configuration/#kubernetes_sd_config)
- [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/)

---

**文档版本**: v1.0  
**更新日期**: 2026-01-09

