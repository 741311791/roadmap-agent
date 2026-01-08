# Prometheus + Grafana 监控系统

完整的监控可视化方案，用于展示 Roadmap Agent 的性能指标。

---

## 🚀 快速启动

### 1. 启动监控栈

```bash
cd backend/monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

### 2. 访问服务

- **Grafana**: http://localhost:3001
  - 用户名: `admin`
  - 密码: `admin`
  - 首次登录会要求修改密码（可以跳过）

- **Prometheus**: http://localhost:9090
  - 直接访问，无需认证

### 3. 查看 Dashboard

Grafana 启动后会自动加载预配置的 Dashboard：
1. 登录 Grafana
2. 左侧菜单 → Dashboards → Browse
3. 选择 "Roadmap Agent - 应用监控"

---

## 📊 Dashboard 说明

### 面板 1: HTTP 请求速率 (QPS)
- **指标**: `rate(http_requests_total[5m])`
- **含义**: 每秒处理的 HTTP 请求数
- **用途**: 监控流量趋势

### 面板 2: HTTP 响应时间 (P95/P99)
- **指标**: `histogram_quantile(0.95/0.99, ...)`
- **含义**: 95%/99% 的请求响应时间
- **用途**: 发现性能瓶颈

### 面板 3: 成功率 (2xx)
- **指标**: 2xx 状态码占比
- **含义**: 成功请求的百分比
- **告警阈值**: 
  - 绿色: > 95%
  - 黄色: 80-95%
  - 红色: < 80%

### 面板 4: 当前 QPS
- **指标**: `sum(rate(http_requests_total[1m]))`
- **含义**: 实时请求速率
- **用途**: 监控当前负载

### 面板 5: 数据库连接池
- **指标**: 
  - `db_pool_checked_out_connections` - 已使用连接
  - `db_pool_size` - 连接池大小
- **用途**: 监控数据库连接使用情况

### 面板 6: Celery 任务速率
- **指标**: `rate(celery_tasks_total[5m])`
- **含义**: 任务执行速率（按状态分类）
- **用途**: 监控异步任务处理情况

### 面板 7: Redis 缓存命中率
- **指标**: `hits / (hits + misses)`
- **含义**: 缓存命中的百分比
- **目标**: > 80%

---

## ⚙️ 配置说明

### Prometheus 采集配置

编辑 `prometheus.yml` 修改采集目标：

```yaml
scrape_configs:
  - job_name: 'roadmap_agent'
    static_configs:
      # 根据部署方式选择：
      
      # 本地开发
      - targets: ['host.docker.internal:8000']
      
      # Docker 部署
      - targets: ['roadmap_api:8000']
      
      # 生产环境（多实例）
      - targets: 
        - 'api-1.example.com:8000'
        - 'api-2.example.com:8000'
```

### Grafana 数据源

数据源已自动配置，无需手动添加。

配置文件位置：
- `grafana/provisioning/datasources/prometheus.yml`

---

## 🔧 自定义 Dashboard

### 方法 1: 在 Grafana UI 中编辑

1. 打开 Dashboard
2. 点击右上角设置图标 ⚙️
3. 编辑面板或添加新面板
4. 保存后导出 JSON：Settings → JSON Model → Copy

### 方法 2: 直接编辑 JSON

编辑 `grafana/dashboards/roadmap_agent_dashboard.json`

常用 PromQL 查询示例：

```promql
# 请求速率
rate(http_requests_total[5m])

# 响应时间中位数
histogram_quantile(0.5, rate(http_request_duration_seconds_bucket[5m]))

# 错误率
rate(http_requests_total{status_code=~"5.."}[5m])

# 数据库连接使用率
db_pool_checked_out_connections / db_pool_size
```

---

## 🎯 告警配置（可选）

### 1. 创建告警规则

创建 `prometheus/alerts/api_alerts.yml`:

```yaml
groups:
  - name: api_alerts
    interval: 30s
    rules:
      # 高错误率告警
      - alert: HighErrorRate
        expr: |
          (
            sum(rate(http_requests_total{status_code=~"5.."}[5m]))
            /
            sum(rate(http_requests_total[5m]))
          ) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "高错误率 (> 5%)"
          description: "5分钟内错误率超过 5%"
      
      # 响应时间过高
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99, 
            rate(http_request_duration_seconds_bucket[5m])
          ) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "响应时间过高 (P99 > 1s)"
```

### 2. 配置 Alertmanager

在 `docker-compose.monitoring.yml` 中取消注释 Alertmanager 配置。

---

## 📈 监控最佳实践

### 1. 关键指标 (Golden Signals)

- **延迟 (Latency)**: P95/P99 响应时间
- **流量 (Traffic)**: QPS
- **错误 (Errors)**: 错误率
- **饱和度 (Saturation)**: 数据库连接池使用率

### 2. 告警阈值建议

| 指标 | 告警阈值 | 严重级别 |
|-----|---------|---------|
| 错误率 | > 5% | Critical |
| P99 响应时间 | > 1s | Warning |
| 数据库连接使用 | > 80% | Warning |
| 缓存命中率 | < 70% | Info |

### 3. Dashboard 刷新频率

- 开发环境: 10s（实时监控）
- 生产环境: 30s-1m（减少 Prometheus 负载）

---

## 🛠️ 故障排查

### 问题 1: Grafana 无法连接 Prometheus

**症状**: Dashboard 显示 "No data"

**解决方案**:
```bash
# 检查 Prometheus 是否运行
docker logs roadmap_prometheus

# 检查网络连接
docker exec roadmap_grafana ping prometheus

# 重启容器
docker-compose -f docker-compose.monitoring.yml restart
```

### 问题 2: FastAPI 指标未采集

**症状**: Prometheus Targets 页面显示 DOWN

**解决方案**:
1. 确认 FastAPI 已启动并暴露 `/metrics`
2. 检查 `prometheus.yml` 中的 targets 配置
3. 如果 FastAPI 在 Docker 中，使用服务名而不是 localhost

### 问题 3: Dashboard 为空

**症状**: Panel 显示 "No data points"

**原因**: FastAPI 应用还没有收到足够的请求

**解决方案**:
```bash
# 发送测试请求
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/roadmaps
```

---

## 🚪 停止监控栈

```bash
# 停止但保留数据
docker-compose -f docker-compose.monitoring.yml stop

# 停止并删除容器（保留数据卷）
docker-compose -f docker-compose.monitoring.yml down

# 完全清理（包括数据）
docker-compose -f docker-compose.monitoring.yml down -v
```

---

## 📚 参考资源

- [Prometheus 官方文档](https://prometheus.io/docs/)
- [Grafana 官方文档](https://grafana.com/docs/)
- [PromQL 查询语法](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard 最佳实践](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)

---

**配置完成日期**: 2026-01-09  
**版本**: v1.0

