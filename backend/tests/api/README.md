# API端点测试指南

## 概述

本目录包含新拆分API端点的完整测试套件，用于验证阶段二重构后的API功能是否正常。

## 测试文件

### 1. `test_new_endpoints_e2e.py`

完整的pytest端到端测试套件。

**测试内容**：
- ✅ 所有8个新拆分的端点模块
- ✅ 健康检查和OpenAPI文档
- ✅ 完整的用户流程集成测试
- ✅ 真实HTTP请求和响应验证

**运行方式**：

```bash
# 运行所有测试
pytest backend/tests/api/test_new_endpoints_e2e.py -v -s

# 运行特定测试类
pytest backend/tests/api/test_new_endpoints_e2e.py::TestNewAPIEndpointsE2E -v -s

# 运行特定测试方法
pytest backend/tests/api/test_new_endpoints_e2e.py::TestNewAPIEndpointsE2E::test_01_generation_endpoint -v -s

# 运行完整流程测试
pytest backend/tests/api/test_new_endpoints_e2e.py::test_complete_workflow_integration -v -s
```

### 2. `test_new_api_endpoints.py` (脚本)

位于 `backend/scripts/test_new_api_endpoints.py`

独立的Python脚本，无需pytest即可运行。

**特点**：
- 🎨 彩色终端输出
- 📊 详细的测试报告
- 🚀 快速验证端点可用性
- 💡 用户友好的错误提示

**运行方式**：

```bash
# 方式1：直接运行
python backend/scripts/test_new_api_endpoints.py

# 方式2：作为模块运行
python -m backend.scripts.test_new_api_endpoints

# 方式3：如果赋予了执行权限
./backend/scripts/test_new_api_endpoints.py
```

## 测试覆盖

### 端点模块测试

| 模块 | 端点 | 测试覆盖 |
|:---|:---|:---:|
| `generation.py` | POST /generate, GET /status | ✅ |
| `retrieval.py` | GET /{roadmap_id}, GET /active-task | ✅ |
| `approval.py` | POST /approve | ✅ |
| `tutorial.py` | GET /tutorials/* | ✅ |
| `resource.py` | GET /resources | ✅ |
| `quiz.py` | GET /quiz | ✅ |
| `modification.py` | POST /*/modify | ✅ |
| `retry.py` | POST /retry-failed | ✅ |

### 测试场景

#### 1. 单元端点测试
每个端点独立测试，验证：
- HTTP状态码正确
- 响应格式符合预期
- 错误处理正常

#### 2. 集成流程测试
完整用户流程：
```
创建任务 → 轮询状态 → 获取路线图 → 查询内容
```

#### 3. 错误场景测试
- 404 (资源不存在)
- 400 (参数错误)
- 500 (服务器错误)

## 前置条件

### 1. 启动后端服务

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 2. 确保依赖已安装

```bash
pip install httpx pytest pytest-asyncio
```

### 3. 环境配置

确保以下环境变量已配置：
- 数据库连接
- Redis连接（如果使用）
- LLM API密钥

## 快速开始

### 方式1：使用pytest（推荐用于CI/CD）

```bash
# 1. 启动服务
uvicorn app.main:app --reload &

# 2. 等待服务启动
sleep 5

# 3. 运行测试
pytest backend/tests/api/test_new_endpoints_e2e.py -v

# 4. 查看覆盖率报告
pytest backend/tests/api/test_new_endpoints_e2e.py --cov=app.api.v1 --cov-report=html
```

### 方式2：使用脚本（推荐用于开发）

```bash
# 1. 启动服务
uvicorn app.main:app --reload

# 2. 在另一个终端运行测试
python backend/scripts/test_new_api_endpoints.py
```

## 测试输出示例

### pytest输出

```
============================= test session starts ==============================
backend/tests/api/test_new_endpoints_e2e.py::TestNewAPIEndpointsE2E::test_01_generation_endpoint PASSED
backend/tests/api/test_new_endpoints_e2e.py::TestNewAPIEndpointsE2E::test_02_task_status_endpoint PASSED
...
======================= 12 passed in 15.32s ===============================
```

### 脚本输出

```
================================================================================
新API端点测试脚本
================================================================================

测试时间: 2025-12-05 21:00:00
基础URL: http://localhost:8000

================================================================================
测试1: 健康检查端点
================================================================================

测试: 应用健康状态
方法: GET
端点: /health
状态码: 200
✅ 请求成功: 200
响应摘要: {"status": "healthy", "version": "1.0.0"}

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

## 常见问题

### Q1: 测试失败，显示连接错误

**原因**：后端服务未启动或端口不正确

**解决**：
```bash
# 检查服务是否运行
curl http://localhost:8000/health

# 如果没有运行，启动服务
uvicorn app.main:app --reload
```

### Q2: 某些测试返回404

**原因**：测试数据不存在（正常现象）

**说明**：404响应被认为是正常的，因为测试环境可能没有真实数据。重点是验证端点能正确响应，而不是数据内容。

### Q3: 完整流程测试超时

**原因**：LLM调用较慢或工作流执行时间长

**解决**：
- 增加timeout设置
- 使用mock数据代替真实LLM调用
- 检查日志定位慢的步骤

### Q4: pytest找不到模块

**原因**：PYTHONPATH未设置

**解决**：
```bash
# 在项目根目录运行
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest backend/tests/api/test_new_endpoints_e2e.py -v
```

## 持续集成

### GitHub Actions示例

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx
      
      - name: Start backend
        run: |
          uvicorn app.main:app --port 8000 &
          sleep 10
      
      - name: Run API tests
        run: |
          pytest backend/tests/api/test_new_endpoints_e2e.py -v
```

## 下一步

完成API测试后，建议：

1. ✅ 验证所有端点正常工作
2. ✅ 备份旧的`roadmap.py`文件
3. ✅ 删除旧文件，完全切换到新架构
4. 📝 更新API文档
5. 🚀 部署到测试环境

## 参考资料

- [FastAPI测试文档](https://fastapi.tiangolo.com/tutorial/testing/)
- [Pytest异步测试](https://pytest-asyncio.readthedocs.io/)
- [HTTPX文档](https://www.python-httpx.org/)

---

**维护者**: Roadmap Agent Team  
**最后更新**: 2025-12-05  
**版本**: v1.0
