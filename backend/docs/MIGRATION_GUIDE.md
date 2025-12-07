# 从旧架构迁移指南

> **重要**: 本次重构**不保证向后兼容**，需要完全迁移到新架构

## 📋 变更概览

| 类别 | 变更内容 | 影响范围 | 迁移难度 |
|:---|:---|:---|:---:|
| **架构** | Orchestrator 拆分为多模块 | 内部实现 | 🟢 低 |
| **架构** | API 拆分为8个端点文件 | 内部实现 | 🟢 低 |
| **架构** | Repository 拆分为6个专用 Repo | 内部实现 | 🟢 低 |
| **接口** | Agent 方法名统一为 `execute()` | Agent 调用 | 🟢 低 |
| **数据库** | 表结构优化（字段、索引） | 数据库 Schema | 🟡 中 |
| **API** | URL 路径和响应格式优化 | 前端/客户端 | 🟡 中 |
| **配置** | 配置结构重组 | 环境变量 | 🟢 低 |

---

## 🗄️ 数据库变更

### 变更总览

**优化项**：
- ✅ 字段命名统一（snake_case）
- ✅ JSON 字段拆分（提升查询性能）
- ✅ 索引优化（基于实际查询模式）
- ✅ 外键规范化

### 详细变更

#### 1. `roadmap_metadata` 表

**变更内容**：
```sql
-- ❌ 旧表结构
CREATE TABLE roadmap_metadata (
    roadmap_id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500),
    topic VARCHAR(200),
    framework_data JSONB,  -- 包含所有 stages/modules/concepts
    user_id VARCHAR(255),
    task_id VARCHAR(255),
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- ✅ 新表结构
CREATE TABLE roadmap_metadata (
    id SERIAL PRIMARY KEY,
    roadmap_id VARCHAR(255) UNIQUE NOT NULL,
    title VARCHAR(500) NOT NULL,
    topic VARCHAR(200),
    difficulty_level VARCHAR(50),
    total_estimated_hours INTEGER,
    recommended_completion_weeks INTEGER,
    user_id VARCHAR(255) NOT NULL,
    task_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- 索引优化
    INDEX idx_roadmap_user_created (user_id, created_at DESC),
    INDEX idx_roadmap_status (status, created_at DESC),
    INDEX idx_roadmap_task (task_id)
);

-- framework_data 拆分为关联表
CREATE TABLE roadmap_stages (
    id SERIAL PRIMARY KEY,
    roadmap_id VARCHAR(255) REFERENCES roadmap_metadata(roadmap_id) ON DELETE CASCADE,
    stage_id VARCHAR(255) NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL,
    estimated_hours INTEGER,
    
    UNIQUE (roadmap_id, stage_id),
    INDEX idx_stage_roadmap (roadmap_id, order_index)
);

CREATE TABLE roadmap_modules (
    id SERIAL PRIMARY KEY,
    stage_id VARCHAR(255) NOT NULL,
    module_id VARCHAR(255) NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL,
    estimated_hours INTEGER,
    
    UNIQUE (stage_id, module_id),
    INDEX idx_module_stage (stage_id, order_index)
);

CREATE TABLE roadmap_concepts (
    id SERIAL PRIMARY KEY,
    module_id VARCHAR(255) NOT NULL,
    concept_id VARCHAR(255) NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL,
    difficulty VARCHAR(50),
    estimated_hours INTEGER,
    
    -- 内容状态
    content_status VARCHAR(50) DEFAULT 'pending',
    content_ref TEXT,
    content_summary TEXT,
    
    -- 资源状态
    resources_status VARCHAR(50) DEFAULT 'pending',
    resources_id VARCHAR(255),
    resources_count INTEGER DEFAULT 0,
    
    -- 测验状态
    quiz_status VARCHAR(50) DEFAULT 'pending',
    quiz_id VARCHAR(255),
    quiz_questions_count INTEGER DEFAULT 0,
    
    UNIQUE (module_id, concept_id),
    INDEX idx_concept_module (module_id, order_index),
    INDEX idx_concept_content_status (content_status),
    INDEX idx_concept_resources_status (resources_status),
    INDEX idx_concept_quiz_status (quiz_status)
);
```

#### 2. `tasks` 表

**变更内容**：
```sql
-- 新增字段
ALTER TABLE tasks 
ADD COLUMN execution_summary JSONB,
ADD COLUMN failed_concepts JSONB;

-- 新增索引
CREATE INDEX idx_task_roadmap ON tasks(roadmap_id) WHERE roadmap_id IS NOT NULL;
CREATE INDEX idx_task_user_created ON tasks(user_id, created_at DESC);
CREATE INDEX idx_task_status ON tasks(status, created_at DESC);
```

#### 3. 其他表优化

**`tutorial_metadata`**:
```sql
-- 添加索引
CREATE INDEX idx_tutorial_concept ON tutorial_metadata(concept_id, content_version DESC);
CREATE INDEX idx_tutorial_status ON tutorial_metadata(content_status);
```

**`resource_recommendation_metadata`**:
```sql
-- 添加索引
CREATE INDEX idx_resource_concept ON resource_recommendation_metadata(concept_id);
```

**`quiz_metadata`**:
```sql
-- 添加索引
CREATE INDEX idx_quiz_concept ON quiz_metadata(concept_id);
```

### 迁移脚本

**自动迁移**（推荐）：
```bash
# 1. 备份数据库
pg_dump -h localhost -U postgres roadmap_db > backup_before_refactor.sql

# 2. 运行迁移脚本
cd backend
alembic upgrade head

# 3. 验证迁移
poetry run python scripts/verify_migration.py
```

**手动迁移**（如果需要）：
```sql
-- 见 backend/alembic/versions/xxxx_refactor_schema.py
```

---

## 🌐 API 变更

### URL 路径变更

| 旧路径 | 新路径 | HTTP 方法 | 说明 |
|:---|:---|:---:|:---|
| `POST /api/v1/roadmaps/generate` | `POST /api/v1/roadmaps` | POST | 创建路线图 |
| `GET /api/v1/roadmaps/{task_id}/status` | `GET /api/v1/tasks/{task_id}` | GET | 查询任务状态 |
| `POST /api/v1/roadmaps/{task_id}/approve` | `PATCH /api/v1/tasks/{task_id}` | PATCH | 更新任务（审核） |
| `GET /api/v1/roadmaps/{roadmap_id}` | `GET /api/v1/roadmaps/{roadmap_id}` | GET | 获取路线图（不变） |
| `GET /api/v1/roadmaps/{roadmap_id}/active-task` | `GET /api/v1/roadmaps/{roadmap_id}/tasks/active` | GET | 获取活跃任务 |

### 响应格式变更

#### 统一成功响应

**旧格式**：
```json
{
  "task_id": "xxx",
  "status": "processing",
  "message": "任务已创建"
}
```

**新格式**：
```json
{
  "success": true,
  "data": {
    "task_id": "xxx",
    "status": "processing",
    "created_at": "2025-01-04T10:00:00Z"
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2025-01-04T10:00:00Z"
  }
}
```

#### 统一错误响应

**旧格式**：
```json
{
  "detail": "Roadmap not found"
}
```

**新格式**：
```json
{
  "success": false,
  "error": {
    "code": "ROADMAP_NOT_FOUND",
    "message": "路线图不存在",
    "details": {
      "roadmap_id": "xxx"
    }
  },
  "metadata": {
    "request_id": "req_abc123",
    "timestamp": "2025-01-04T10:00:00Z"
  }
}
```

### 前端适配

**Step 1: 更新 API 端点**
```typescript
// ❌ 旧代码
const response = await fetch('/api/v1/roadmaps/generate', {
  method: 'POST',
  body: JSON.stringify(request),
});

// ✅ 新代码
const response = await fetch('/api/v1/roadmaps', {
  method: 'POST',
  body: JSON.stringify(request),
});
```

**Step 2: 更新响应处理**
```typescript
// ❌ 旧代码
const { task_id, status } = await response.json();

// ✅ 新代码
const { data } = await response.json();
const { task_id, status } = data;
```

**Step 3: 更新类型生成**
```bash
# 重新生成前端类型
cd frontend-next
npm run generate:types
```

---

## ⚙️ 配置变更

### 环境变量重组

**旧配置**（扁平结构）：
```bash
# .env
INTENT_ANALYZER_PROVIDER=openai
INTENT_ANALYZER_MODEL=gpt-4o-mini
INTENT_ANALYZER_BASE_URL=https://api.openai.com/v1
INTENT_ANALYZER_API_KEY=sk-xxx

SKIP_STRUCTURE_VALIDATION=false
SKIP_HUMAN_REVIEW=false
MAX_FRAMEWORK_RETRY=3
```

**新配置**（嵌套结构）：
```bash
# .env
# 工作流配置
WORKFLOW__SKIP_STRUCTURE_VALIDATION=false
WORKFLOW__SKIP_HUMAN_REVIEW=false
WORKFLOW__MAX_FRAMEWORK_RETRY=3
WORKFLOW__PARALLEL_TUTORIAL_LIMIT=5

# Agent 配置
AGENTS__INTENT_ANALYZER__PROVIDER=openai
AGENTS__INTENT_ANALYZER__MODEL=gpt-4o-mini
AGENTS__INTENT_ANALYZER__BASE_URL=https://api.openai.com/v1
AGENTS__INTENT_ANALYZER__API_KEY=sk-xxx

# 数据库配置
DATABASE__HOST=localhost
DATABASE__PORT=5432
DATABASE__DATABASE=roadmap_db
DATABASE__USER=postgres
DATABASE__PASSWORD=password
DATABASE__POOL_SIZE=10
```

### 配置迁移工具

```bash
# 自动迁移配置
poetry run python scripts/migrate_config.py --input .env.old --output .env

# 验证配置
poetry run python -c "from app.config.settings import settings; print(settings.model_dump_json(indent=2))"
```

---

## 🔧 代码变更

### Agent 方法名变更

**所有 Agent 统一使用 `execute()` 方法**：

```python
# ❌ 旧代码
agent = IntentAnalyzerAgent()
result = await agent.analyze(request)

agent = CurriculumArchitectAgent()
result = await agent.design(intent_analysis, preferences, roadmap_id)

# ✅ 新代码
agent = IntentAnalyzerAgent()
result = await agent.execute(request)

agent = CurriculumArchitectAgent()
input_data = CurriculumInput(
    intent_analysis=intent_analysis,
    preferences=preferences,
    roadmap_id=roadmap_id,
)
result = await agent.execute(input_data)
```

### 依赖注入使用

**旧代码**（硬编码创建）：
```python
agent = IntentAnalyzerAgent()
```

**新代码**（通过工厂创建）：
```python
from app.core.dependencies import get_agent_factory

agent_factory = get_agent_factory()
agent = agent_factory.create_intent_analyzer()
```

---

## ✅ 迁移检查清单

### 数据库
- [ ] 备份生产数据库
- [ ] 在开发环境运行迁移脚本
- [ ] 验证数据完整性
- [ ] 在预发环境运行迁移
- [ ] 准备回滚脚本（如需要）

### 后端代码
- [ ] 更新所有 Agent 调用（使用 `execute()`）
- [ ] 更新环境变量配置
- [ ] 运行完整测试套件
- [ ] 验证 API 端点可访问
- [ ] 验证 WebSocket 正常

### 前端代码
- [ ] 更新 API 端点路径
- [ ] 重新生成类型定义
- [ ] 更新响应处理逻辑
- [ ] 更新错误处理
- [ ] 运行 E2E 测试

### 部署
- [ ] 更新 CI/CD 配置
- [ ] 更新 Docker 镜像
- [ ] 更新 Kubernetes 配置（如有）
- [ ] 准备回滚方案
- [ ] 通知相关团队

---

## 🚨 回滚方案

虽然不考虑向后兼容，但仍需准备回滚方案：

### 数据库回滚
```bash
# 从备份恢复
psql -h localhost -U postgres -d roadmap_db < backup_before_refactor.sql
```

### 代码回滚
```bash
# 回滚到重构前的 commit
git checkout <commit-before-refactor>

# 重新部署
docker-compose up -d --build
```

### 验证回滚成功
```bash
# 运行健康检查
curl http://localhost:8000/health

# 运行冒烟测试
pytest tests/smoke/
```

---

## 📞 支持

**遇到问题？**
1. 查看 [REFACTORING_PLAN.md](./REFACTORING_PLAN.md) 了解架构设计
2. 查看 [REFACTORING_TASKS.md](./REFACTORING_TASKS.md) 了解任务详情
3. 查看 [REFACTORING_OPTIMIZATION.md](./REFACTORING_OPTIMIZATION.md) 了解优化点

**联系方式**：
- 技术问题：提交 GitHub Issue
- 紧急问题：联系后端团队

---

**文档版本**: v1.0  
**最后更新**: 2025-01-04  
**维护者**: Backend Team

