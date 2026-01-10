# 测试指南

## 快速开始

### 运行单元测试（无需外部依赖）

```bash
cd backend
./scripts/run_tests.sh unit
```

### 运行完整测试套件（需要数据库）

```bash
# 1. 启动依赖服务
docker-compose up -d postgres redis

# 2. 创建测试数据库
psql -U postgres -c "CREATE DATABASE roadmap_test;"

# 3. 运行测试
./scripts/run_tests.sh all
```

## 测试文件结构

```
tests/
├── conftest.py              # 全局fixtures和测试配置
├── unit/                    # 单元测试
│   └── test_schemas.py      # Schema验证测试（10个测试）
├── integration/             # 集成测试
│   ├── test_auth.py         # 认证授权测试（9个测试）
│   └── test_services.py     # Service层测试（7个测试）
└── e2e/                     # 端到端测试
    └── test_health.py       # 健康检查测试（4个测试）
```

## 测试模式

| 模式 | 命令 | 说明 | 执行时间 |
|------|------|------|----------|
| **单元测试** | `./scripts/run_tests.sh unit` | 仅Schema验证，无需依赖 | < 1秒 |
| **集成测试** | `./scripts/run_tests.sh integration` | 需要数据库和Redis | < 3分钟 |
| **E2E测试** | `./scripts/run_tests.sh e2e` | 需要应用启动 | < 2分钟 |
| **冒烟测试** | `./scripts/run_tests.sh smoke` | 健康检查+认证 | < 1分钟 |
| **快速测试** | `./scripts/run_tests.sh fast` | 跳过slow标记 | < 3分钟 |
| **完整测试** | `./scripts/run_tests.sh all` | 所有测试 | < 6分钟 |
| **覆盖率报告** | `./scripts/run_tests.sh coverage` | 生成覆盖率 | < 6分钟 |

## 编写测试规范

### 单元测试示例

```python
def test_learning_preferences_valid():
    """
    测试有效的学习偏好
    
    验证：
    - 所有必填字段都提供时可以正常创建
    - 字段类型正确
    """
    prefs = LearningPreferences(
        learning_goal="成为全栈开发工程师",
        available_hours_per_week=15,
        # ...其他字段
    )
    
    assert prefs.learning_goal == "成为全栈开发工程师"
    assert prefs.available_hours_per_week == 15
```

### 集成测试示例

```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_login_success(client: AsyncClient, test_user: User):
    """
    测试用户登录成功
    
    验证：
    - 正确的邮箱和密码可以登录
    - 返回有效的JWT token
    """
    response = await client.post(
        "/api/v1/auth/jwt/login",
        data={
            "username": test_user.email,
            "password": "testpassword123",
        },
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
```

### E2E测试示例

```python
@pytest.mark.asyncio
async def test_basic_health_check(client: AsyncClient):
    """
    测试基础健康检查
    
    验证：
    - 服务可以正常响应
    - 返回200状态码
    """
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

## 常用Fixtures

### 基础数据Fixtures

```python
def test_example(
    sample_learning_preferences,  # LearningPreferences对象
    sample_user_request,           # UserRequest对象
    sample_roadmap_framework,      # 完整的路线图框架
):
    # 使用fixtures进行测试
    pass
```

### 数据库Fixtures

```python
@pytest.mark.asyncio
async def test_example(
    test_session,     # 数据库会话
    test_user,        # 测试用户
    test_roadmap,     # 测试路线图
):
    # 使用数据库fixtures进行测试
    pass
```

### Mock Fixtures

```python
def test_example(
    mock_litellm,         # Mock LiteLLM调用
    mock_s3_tool,         # Mock S3工具
    mock_web_search_tool, # Mock Web搜索
):
    # 使用mock进行测试
    pass
```

## 测试标记

```python
@pytest.mark.asyncio        # 异步测试
@pytest.mark.integration    # 集成测试标记
@pytest.mark.slow           # 慢速测试标记（会被fast模式跳过）
async def test_example():
    pass
```

## 调试测试

### 运行单个测试文件

```bash
uv run pytest tests/unit/test_schemas.py -v
```

### 运行单个测试用例

```bash
uv run pytest tests/unit/test_schemas.py::test_learning_preferences_valid -v
```

### 查看详细日志

```bash
uv run pytest tests/unit/test_schemas.py -v --log-cli-level=DEBUG
```

### 在失败时进入调试器

```bash
uv run pytest tests/unit/test_schemas.py --pdb
```

## 测试通过标准

### 最小标准（开发环境）

单元测试全部通过：
```bash
./scripts/run_tests.sh unit
# 期望: 10 passed
```

### 完整标准（CI/CD）

所有测试全部通过：
```bash
./scripts/run_tests.sh all
# 期望: 30 passed
```

## 常见问题

### Q: 测试提示数据库连接失败？

A: 确保PostgreSQL正在运行，并且创建了测试数据库：
```bash
docker-compose up -d postgres
psql -U postgres -c "CREATE DATABASE roadmap_test;"
```

### Q: 如何跳过需要外部依赖的测试？

A: 只运行单元测试：
```bash
./scripts/run_tests.sh unit
```

### Q: 如何查看测试覆盖率？

A: 运行覆盖率模式：
```bash
./scripts/run_tests.sh coverage
# 查看报告: open htmlcov/index.html
```

### Q: 测试运行很慢怎么办？

A: 使用并行模式（需要安装pytest-xdist）：
```bash
uv pip install pytest-xdist
./scripts/run_tests.sh parallel
```

## 更多信息

详细的测试策略请参考：
- `TEST_STRATEGY.md` - 测试策略文档
- `doc/20260109_后端测试策略实施完成.md` - 实施总结

