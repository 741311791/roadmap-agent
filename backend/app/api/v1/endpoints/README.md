# API Endpoints 目录说明

> **架构版本**: v2.0 (工作流驱动架构)  
> **重构日期**: 2026-01-11  
> **组织原则**: 按业务领域分组，支持多工作流扩展

---

## 目录结构

```
endpoints/
├── workflows/              # 工作流执行
│   └── generation/         # 路线图生成工作流
│       ├── generation.py   # 发起生成任务
│       └── approval.py     # 人工审核
│
├── roadmaps/               # 路线图资源管理
│   ├── retrieval.py        # 查询路线图
│   ├── status.py           # 状态查询
│   ├── streaming.py        # 流式查询
│   ├── management.py       # 删除/恢复/更新
│   ├── featured.py         # 精选路线图
│   ├── cover_image.py      # 封面图管理
│   ├── intent.py           # 意图分析元数据
│   ├── validation.py       # 验证记录
│   └── edit.py             # 编辑记录
│
├── content/                # 内容管理
│   ├── content.py          # 内容CRUD查询
│   ├── modification.py     # 内容修改
│   └── concept_status.py   # 概念生成状态
│
├── learning/               # 学习体验
│   ├── progress.py         # 学习进度追踪
│   ├── mentor.py           # 伴学交互
│   └── assessment.py       # 技术评估
│
├── users/                  # 用户与认证
│   ├── users.py            # 用户管理
│   ├── auth.py             # 认证扩展
│   └── waitlist.py         # 候补名单
│
└── admin/                  # 平台管理
    ├── admin.py            # 管理员功能
    ├── monitoring.py       # Celery监控
    └── trace.py            # 执行追踪
```

---

## 业务领域说明

### 1. Workflows - 工作流执行

**路径前缀**: `/api/v1/workflows/`

#### Generation 工作流

负责路线图生成的完整工作流，包括：
- 意图分析 (Intent Analysis)
- 课程设计 (Curriculum Design)
- 结构验证 (Validation)
- 人工审核 (Review)
- 内容生成 (Content Generation)

**主要端点**:
- `POST /workflows/generation/generate` - 发起路线图生成
- `POST /workflows/generation/approve/{task_id}` - 人工审核决策

**预留工作流**:
- Company 工作流 - 伴学模式（未来）
- Guidance 工作流 - 导学模式（未来）

---

### 2. Roadmaps - 路线图资源管理

**路径前缀**: `/api/v1/roadmaps/`

负责路线图资源的CRUD操作和状态管理。

**主要端点**:
- `GET /roadmaps/{roadmap_id}` - 获取完整路线图
- `GET /roadmaps/{roadmap_id}/status` - 查询生成状态
- `GET /roadmaps/{roadmap_id}/stream` - 流式查询进度
- `DELETE /roadmaps/{roadmap_id}` - 软删除路线图
- `GET /roadmaps/intent/{task_id}` - 查询意图分析元数据
- `GET /roadmaps/validation/{task_id}` - 查询验证记录
- `GET /roadmaps/edit/{task_id}` - 查询编辑记录

**特点**:
- 支持正在生成中的路线图查询
- 提供实时状态更新
- 精选路线图策展
- 完整的元数据追踪（意图、验证、编辑）

---

### 3. Content - 内容管理

**路径前缀**: `/api/v1/content/`

负责教程、资源、测验等内容的管理和修改。

**主要端点**:
- `GET /content/{roadmap_id}/concepts/{concept_id}/tutorials` - 获取教程
- `POST /content/{roadmap_id}/concepts/{concept_id}/tutorial/modify` - 修改教程
- `GET /content/concept-status` - 查询概念生成状态

**特点**:
- 支持内容版本管理
- 提供修改历史追踪
- 实时生成状态更新

---

### 4. Learning - 学习体验

**路径前缀**: `/api/v1/learning/`

负责学习进度追踪、伴学交互、能力评估。

**主要端点**:
- `GET /learning/progress` - 获取学习进度
- `POST /learning/mentor/chat` - 伴学聊天
- `GET /learning/assessments` - 技术评估列表

**特点**:
- 个性化学习路径
- AI伴学功能
- 能力评估系统

---

### 5. Users - 用户与认证

**路径前缀**: `/api/v1/users/`

负责用户管理、认证、候补名单。

**主要端点**:
- `GET /users/me` - 获取当前用户信息
- `PATCH /users/me` - 更新用户信息
- `POST /users/auth/logout` - 用户登出
- `GET /users/waitlist` - 候补名单

**特点**:
- JWT认证
- 用户画像管理
- 候补名单系统

---

### 6. Admin - 平台管理

**路径前缀**: `/api/v1/admin/`

负责管理员功能、系统监控、执行追踪。

**主要端点**:
- `GET /admin/users` - 用户管理
- `GET /admin/monitoring/celery/stats` - Celery监控
- `GET /admin/trace/{execution_id}` - 执行追踪

**特点**:
- 用户邀请系统
- Tavily配额管理
- 系统监控告警

---

## 路由组织原则

### 分层路由

```
主路由 (router.py)
  ├── Workflows路由 (workflows/generation/router.py)
  ├── Roadmaps路由 (roadmaps/router.py)
  ├── Content路由 (content/router.py)
  ├── Learning路由 (learning/router.py)
  ├── Users路由 (users/router.py)
  └── Admin路由 (admin/router.py)
```

### 路由聚合示例

**workflows/generation/router.py**:
```python
from fastapi import APIRouter
from . import generation, approval, intent, validation, edit

router = APIRouter(
    prefix="/workflows/generation",
    tags=["Generation Workflow"]
)

router.include_router(generation.router)
router.include_router(approval.router)
router.include_router(intent.router)
router.include_router(validation.router)
router.include_router(edit.router)
```

---

## 开发规范

### 1. 文件命名

- 使用小写字母和下划线：`tech_assessment.py` → `assessment.py`
- 名称简洁清晰：`celery_monitor.py` → `monitoring.py`

### 2. 路由前缀

- 工作流：由router.py统一管理，endpoint文件不设prefix
- 资源管理：在endpoint文件中设置prefix
- 保持一致性和可预测性

### 3. 依赖注入

```python
from typing import Annotated
from fastapi import APIRouter, Depends

from app.services.workflows.generation.intent_service import IntentService

router = APIRouter(tags=["intent-analysis"])

@router.get("/{task_id}")
async def get_intent_analysis(
    task_id: str,
    service: Annotated[IntentService, Depends()],
):
    ...
```

### 4. 错误处理

```python
from app.core.custom_exceptions import errors

if not record:
    raise errors.NotFoundError(msg="未找到验证记录")
```

### 5. 响应格式

```python
from app.core.response_schema import ResponseSchemaModel, response_base

@router.get("/{task_id}", response_model=ResponseSchemaModel[DataType])
async def endpoint(...):
    return response_base.success(data=result)
```

---

## 测试

### 运行所有API测试

```bash
pytest backend/tests/api/ -v
```

### 运行特定业务领域测试

```bash
# 工作流测试
pytest backend/tests/api/test_generation.py -v

# 路线图测试
pytest backend/tests/api/test_retrieval.py -v
```

---

## API文档

启动服务器后访问Swagger文档：

```
http://localhost:8000/docs
```

按业务领域分组的API端点，清晰易读。

---

## 扩展指南

### 添加新的工作流

1. 在 `workflows/` 下创建新目录（如 `company/`）
2. 创建 `__init__.py` 和 `router.py`
3. 添加endpoint文件
4. 在 `workflows/__init__.py` 中导出路由
5. 在主 `router.py` 中注册

### 添加新的业务领域

1. 在 `endpoints/` 下创建新目录
2. 创建 `__init__.py` 和 `router.py`
3. 添加endpoint文件
4. 在主 `router.py` 中注册

---

## 迁移指南

如果你是从旧版本（v1.0）迁移，请查看：

- `docs/20260111_API路径迁移清单.md` - API路径变化详情
- `docs/20260111_工作流驱动架构重构完成总结.md` - 完整重构说明

---

**文档版本**: v2.0  
**最后更新**: 2026-01-11  
**维护者**: Backend Team
