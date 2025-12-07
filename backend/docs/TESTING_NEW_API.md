# 新API端点测试文档

## 📋 测试概述

本文档说明如何测试阶段二重构后的新API端点结构，确保所有功能正常工作。

## 🎯 测试目标

1. ✅ 验证8个新拆分的端点模块正常工作
2. ✅ 确保API路由正确注册
3. ✅ 测试真实用户请求流程
4. ✅ 验证错误处理机制
5. ✅ 确保向后兼容性（如需要）

## 📁 测试文件位置

```
backend/
├── tests/
│   └── api/
│       ├── README.md                      # 测试指南
│       └── test_new_endpoints_e2e.py      # pytest测试套件
└── scripts/
    └── test_new_api_endpoints.py          # 独立测试脚本
```

## 🚀 快速开始

### 方式1：使用独立脚本（推荐）

**步骤1**: 启动后端服务

```bash
cd backend
uvicorn app.main:app --reload
```

**步骤2**: 运行测试脚本

```bash
python backend/scripts/test_new_api_endpoints.py
```

**预期输出**：

```
================================================================================
新API端点测试脚本
================================================================================

测试时间: 2025-12-05 21:00:00
基础URL: http://localhost:8000

================================================================================
测试1: 健康检查端点
================================================================================
✅ 请求成功: 200

================================================================================
测试2: 路线图生成端点 (generation.py)
================================================================================
✅ 请求成功: 200
ℹ️  获取到任务ID: 550e8400-e29b-41d4-a716-446655440000

...

================================================================================
测试结果汇总
================================================================================
总测试数: 12
✅ 通过: 12
❌ 失败: 0
成功率: 100.0%

🎉 所有测试通过！新API端点工作正常！
```

### 方式2：使用pytest

```bash
# 运行所有测试
pytest backend/tests/api/test_new_endpoints_e2e.py -v -s

# 运行特定测试
pytest backend/tests/api/test_new_endpoints_e2e.py::TestNewAPIEndpointsE2E::test_01_generation_endpoint -v
```

## 📊 测试覆盖清单

### 核心端点测试

- [x] **Generation API** (`generation.py`)
  - `POST /api/v1/roadmaps/generate` - 创建生成任务
  - `GET /api/v1/roadmaps/{task_id}/status` - 查询任务状态

- [x] **Retrieval API** (`retrieval.py`)
  - `GET /api/v1/roadmaps/{roadmap_id}` - 获取路线图
  - `GET /api/v1/roadmaps/{roadmap_id}/active-task` - 查询活跃任务

- [x] **Approval API** (`approval.py`)
  - `POST /api/v1/roadmaps/{task_id}/approve` - 人工审核

- [x] **Tutorial API** (`tutorial.py`)
  - `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials` - 版本历史
  - `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest` - 最新版本
  - `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/v{version}` - 指定版本

- [x] **Resource API** (`resource.py`)
  - `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources` - 学习资源

- [x] **Quiz API** (`quiz.py`)
  - `GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz` - 测验内容

- [x] **Modification API** (`modification.py`)
  - `POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify` - 修改教程
  - `POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources/modify` - 修改资源
  - `POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz/modify` - 修改测验

- [x] **Retry API** (`retry.py`)
  - `POST /api/v1/roadmaps/{roadmap_id}/retry-failed` - 重试失败内容
  - `POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/regenerate` - 重新生成

### 系统端点测试

- [x] `GET /health` - 健康检查
- [x] `GET /openapi.json` - OpenAPI规范
- [x] `GET /docs` - Swagger UI

## 🔍 详细测试场景

### 场景1：完整路线图生成流程

```python
# 1. 创建生成任务
response = await client.post("/api/v1/roadmaps/generate", json={
    "user_id": "test-user",
    "preferences": {
        "learning_goal": "学习Python Web开发",
        ...
    }
})
task_id = response.json()["task_id"]

# 2. 轮询任务状态
while True:
    status = await client.get(f"/api/v1/roadmaps/{task_id}/status")
    if status.json()["status"] == "completed":
        break
    await asyncio.sleep(2)

# 3. 获取完整路线图
roadmap = await client.get(f"/api/v1/roadmaps/{roadmap_id}")

# 4. 查询具体内容
tutorial = await client.get(
    f"/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest"
)
```

### 场景2：内容修改流程

```python
# 1. 查询现有教程
tutorial = await client.get(
    f"/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest"
)

# 2. 提交修改请求
result = await client.post(
    f"/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify",
    json={
        "user_id": "test-user",
        "requirements": ["增加代码示例", "简化术语"],
        "preferences": {...}
    }
)

# 3. 验证新版本
new_tutorial = await client.get(
    f"/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest"
)
assert new_tutorial.json()["content_version"] > tutorial.json()["content_version"]
```

### 场景3：失败重试流程

```python
# 1. 查询路线图状态
roadmap = await client.get(f"/api/v1/roadmaps/{roadmap_id}")

# 2. 提交重试请求
result = await client.post(
    f"/api/v1/roadmaps/{roadmap_id}/retry-failed",
    json={
        "user_id": "test-user",
        "content_types": ["tutorial", "resources"],
        "preferences": {...}
    }
)

# 3. 监控重试进度
# 通过WebSocket或轮询任务状态
```

## ✅ 验收标准

### 功能性验收

- [ ] 所有12个测试场景通过
- [ ] HTTP状态码符合预期
- [ ] 响应格式正确
- [ ] 错误处理正确

### 性能验收

- [ ] 端点响应时间 < 500ms (P95)
- [ ] 并发100请求无错误
- [ ] 内存使用无异常增长

### 文档验收

- [ ] OpenAPI规范完整
- [ ] 所有端点有文档注释
- [ ] Swagger UI可访问

## 🐛 常见问题排查

### 问题1：连接被拒绝

**症状**：
```
httpx.ConnectError: [Errno 61] Connection refused
```

**原因**：后端服务未启动

**解决**：
```bash
# 检查服务状态
curl http://localhost:8000/health

# 启动服务
uvicorn app.main:app --reload
```

### 问题2：404错误

**症状**：所有请求返回404

**原因**：路由未正确注册

**解决**：
```python
# 检查 app/main.py
app.include_router(api_router_v1)  # 确保路由已注册

# 检查 app/api/v1/router.py
router.include_router(generation.router)  # 确保子路由已注册
```

### 问题3：导入错误

**症状**：
```
ModuleNotFoundError: No module named 'app'
```

**原因**：PYTHONPATH未设置

**解决**：
```bash
# 在项目根目录运行
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python backend/scripts/test_new_api_endpoints.py
```

### 问题4：测试超时

**症状**：某些测试运行很慢或超时

**原因**：LLM调用或数据库操作慢

**解决**：
- 使用mock代替真实调用
- 增加timeout设置
- 优化数据库查询

## 📈 后续步骤

测试通过后：

1. **备份旧代码**
   ```bash
   cp backend/app/api/v1/roadmap.py backend/app/api/v1/roadmap.py.backup
   ```

2. **删除旧文件**
   ```bash
   git rm backend/app/api/v1/roadmap.py
   ```

3. **提交更改**
   ```bash
   git add .
   git commit -m "refactor(api): 完成API层拆分，所有测试通过"
   ```

4. **部署到测试环境**
   - 运行完整回归测试
   - 性能基准测试
   - 用户验收测试

5. **监控上线**
   - 配置监控告警
   - 观察错误日志
   - 收集性能指标

## 🔗 相关文档

- [API端点README](../tests/api/README.md)
- [阶段二完成总结](./PHASE2_COMPLETION_SUMMARY.md)
- [重构任务清单](./REFACTORING_TASKS.md)

---

**维护者**: Roadmap Agent Team  
**创建日期**: 2025-12-05  
**状态**: ✅ 已完成
