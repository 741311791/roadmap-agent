# 后端测试策略

## 测试目标

创建一个精简但有效的测试套件，确保后端服务的核心功能正常运行。测试全部通过即代表服务可以正常对外提供服务。

## 测试层级架构

```
┌─────────────────────────────────────────────┐
│  E2E Tests (端到端测试)                      │
│  - 健康检查                                  │
│  - 核心业务流程（路线图生成→审核→查询）      │
├─────────────────────────────────────────────┤
│  Integration Tests (集成测试)               │
│  - 认证授权                                  │
│  - 数据库CRUD                                │
│  - 关键Service层逻辑                         │
├─────────────────────────────────────────────┤
│  Unit Tests (单元测试)                       │
│  - 核心工具函数                              │
│  - Schema验证                                │
│  - 数据模型                                  │
└─────────────────────────────────────────────┘
```

## 测试范围

### 1. 健康检查测试（Critical）
- ✅ `/health` - 基础健康检查
- ✅ `/health/db` - 数据库连接
- ✅ `/health/detailed` - 详细健康状态

### 2. 认证授权测试（Critical）
- ✅ JWT登录/登出
- ✅ Token验证
- ✅ 权限控制（SuperUser vs Normal User）
- ✅ Token黑名单机制

### 3. 路线图核心流程测试（Critical）
- ✅ 创建路线图生成任务
- ✅ 查询路线图状态
- ✅ 查询路线图详情
- ✅ 路线图审核流程

### 4. 数据库CRUD测试（Important）
- ✅ 用户CRUD
- ✅ 路线图元数据CRUD
- ✅ 内容元数据CRUD（Tutorial/Resource/Quiz）

### 5. Service层集成测试（Important）
- ✅ RetrievalService - 路线图查询
- ✅ ContentService - 内容重试逻辑
- ✅ ConceptService - 概念状态管理

### 6. 工具函数单元测试（Nice to Have）
- ✅ S3相关工具
- ✅ 通知格式化工具
- ✅ Schema验证

## 测试策略

### 1. Mock策略
- **Mock外部依赖**：LLM API、Tavily API、S3存储
- **真实数据库**：使用测试数据库（PostgreSQL）
- **真实Redis**：使用测试Redis实例（或Fakeredis）

### 2. 测试数据管理
- **Fixtures**：使用pytest fixtures管理测试数据
- **数据隔离**：每个测试使用独立的数据库事务
- **清理策略**：测试结束后自动回滚

### 3. 测试执行顺序
1. 健康检查（最快，优先执行）
2. 单元测试（快速）
3. 集成测试（中速）
4. E2E测试（慢速，标记为`slow`）

### 4. CI/CD集成
```bash
# 快速测试（5分钟内）
pytest tests/ -m "not slow" --maxfail=3

# 完整测试（15分钟内）
pytest tests/ --maxfail=5

# 带覆盖率报告
pytest tests/ --cov=app --cov-report=html
```

## 测试文件结构

```
tests/
├── conftest.py                    # 全局fixtures
├── unit/                          # 单元测试
│   ├── test_schemas.py           # Schema验证测试
│   ├── test_utils.py             # 工具函数测试
│   └── test_models.py            # 数据模型测试
├── integration/                   # 集成测试
│   ├── test_auth.py              # 认证授权测试
│   ├── test_crud.py              # 数据库CRUD测试
│   ├── test_services.py          # Service层测试
│   └── test_middleware.py        # 中间件测试
└── e2e/                          # 端到端测试
    ├── test_health.py            # 健康检查测试
    ├── test_roadmap_flow.py      # 路线图核心流程测试
    └── test_content_flow.py      # 内容生成流程测试
```

## 成功标准

### 测试全部通过的定义
1. ✅ 所有健康检查端点返回200
2. ✅ 认证授权功能正常（登录/登出/权限验证）
3. ✅ 路线图可以正常创建和查询
4. ✅ 数据库连接正常，CRUD操作成功
5. ✅ 关键Service层逻辑无异常

### 不需要覆盖的部分
- ❌ LLM Agent的具体生成内容质量（Mock掉）
- ❌ 外部API的可用性（Mock掉）
- ❌ 性能压测（单独进行）
- ❌ 前端交互细节（前端自己测）

## 运行命令

```bash
# 1. 快速冒烟测试（只跑健康检查和认证）
pytest tests/e2e/test_health.py tests/integration/test_auth.py -v

# 2. 核心功能测试（跳过慢速测试）
pytest tests/ -m "not slow" -v

# 3. 完整测试套件
pytest tests/ -v

# 4. 查看覆盖率
pytest tests/ --cov=app --cov-report=term-missing

# 5. 并行执行（需要安装pytest-xdist）
pytest tests/ -n auto
```

## 维护规范

1. **新增API端点**：必须添加对应的集成测试
2. **修改数据模型**：必须更新相关的单元测试
3. **修改Service逻辑**：必须更新集成测试
4. **破坏性变更**：必须确保所有测试通过后才能合并

## 预期执行时间

- 单元测试：< 1分钟
- 集成测试：< 3分钟
- E2E测试（不含slow）：< 2分钟
- 完整测试套件：< 6分钟

