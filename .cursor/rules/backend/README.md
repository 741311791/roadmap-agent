# 后端开发规范 (Backend Development Rules)

本目录包含后端开发的Cursor规范文件，帮助Cursor更好地理解项目架构和开发规范。

## 📁 文件列表

| 文件名 | 说明 | 核心内容 |
|--------|------|----------|
| [`backend-architecture.mdc`](./backend-architecture.mdc) | **架构设计规范** | 分层架构职责、依赖注入模式、工厂模式、错误处理 |
| [`backend-agent-langgraph.mdc`](./backend-agent-langgraph.mdc) | **Agent与LangGraph规范** | Agent开发、Prompt设计、LangGraph工作流、WorkflowBrain使用 |
| [`backend-api-design.mdc`](./backend-api-design.mdc) | **API设计规范** | RESTful设计、路由组织、参数验证、响应格式、错误处理 |
| [`backend-database.mdc`](./backend-database.mdc) | **数据库操作规范** | Session管理、CRUD模式、Model设计、事务处理 |
| [`backend-naming.mdc`](./backend-naming.mdc) | **命名与文件组织规范** | 文件命名、类命名、函数命名、目录结构、代码风格 |

## 🎯 适用场景

### 1. backend-architecture.mdc
**何时参考**: 开发新功能、重构代码、不确定某个逻辑应该放在哪一层

**核心内容**:
- ✅ API层只负责HTTP适配，不包含业务逻辑
- ✅ Service层编排业务逻辑，控制事务边界
- ✅ CRUD层封装数据访问，只flush不commit
- ✅ 编排层使用WorkflowBrain统一管理状态和持久化

### 2. backend-agent-langgraph.mdc
**何时参考**: 开发新Agent、创建Prompt模板、添加工作流节点

**核心内容**:
- ✅ 所有Agent必须继承BaseAgent并实现Agent Protocol
- ✅ Prompt模板包含7个标准部分
- ✅ Node Runner使用WorkflowBrain的上下文管理器
- ✅ 状态更新通过返回字典而不是直接修改state

### 3. backend-api-design.mdc
**何时参考**: 设计新API端点、添加路由、处理请求参数

**核心内容**:
- ✅ URL使用名词复数形式，不包含动词
- ✅ 使用统一的ResponseModel格式
- ✅ 参数验证使用Annotated和Pydantic Field
- ✅ 使用标准HTTP状态码(200/400/404/500等)

### 4. backend-database.mdc
**何时参考**: 数据库查询、创建CRUD类、处理事务

**核心内容**:
- ✅ GET请求使用CurrentSession(只读)
- ✅ POST/PUT/DELETE使用CurrentSessionTransaction(事务)
- ✅ CRUD层只flush不commit
- ✅ 使用SQLAlchemy 2.0的Mapped语法定义Model

### 5. backend-naming.mdc
**何时参考**: 创建新文件、命名类/函数/变量、组织代码结构

**核心内容**:
- ✅ 文件名使用snake_case
- ✅ 类名使用PascalCase
- ✅ 函数名使用snake_case
- ✅ 常量使用UPPER_SNAKE_CASE
- ✅ 导入顺序: 标准库 → 第三方库 → 本地导入

## 🚀 快速开始

### 示例1: 创建新的API端点

1. 参考 [`backend-api-design.mdc`](./backend-api-design.mdc) 了解RESTful设计
2. 参考 [`backend-naming.mdc`](./backend-naming.mdc) 确定文件和函数命名
3. 参考 [`backend-architecture.mdc`](./backend-architecture.mdc) 确定调用Service层

```python
# backend/app/api/v1/endpoints/roadmaps/my_endpoint.py
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from app.db.session import CurrentSession
from app.services.roadmaps.roadmap_service import RoadmapService
from app.schemas.response import ResponseModel

router = APIRouter(prefix="/roadmaps", tags=["Roadmaps"])

@router.get("/{roadmap_id}")
async def get_roadmap(
    roadmap_id: Annotated[str, Path(description="路线图ID")],
    db: CurrentSession
) -> ResponseModel:
    """获取路线图详情"""
    roadmap = await roadmap_service.get_by_id(db=db, roadmap_id=roadmap_id)
    return ResponseModel(success=True, data=roadmap)
```

### 示例2: 创建新的Agent

1. 参考 [`backend-agent-langgraph.mdc`](./backend-agent-langgraph.mdc) 了解Agent开发规范
2. 参考 [`backend-naming.mdc`](./backend-naming.mdc) 确定文件和类命名
3. 创建对应的Prompt模板

```python
# backend/app/agents/my_agent.py
from app.agents.base import BaseAgent
from app.agents.protocol import Agent
from app.models.domain import MyInput, MyOutput
from app.config.settings import settings

class MyAgent(BaseAgent, Agent[MyInput, MyOutput]):
    """自定义Agent"""
    agent_id = "my_agent"
    
    def __init__(self, settings: Settings):
        super().__init__(
            agent_id=self.agent_id,
            model_provider=settings.MY_AGENT_PROVIDER,
            model_name=settings.MY_AGENT_MODEL,
            base_url=settings.MY_AGENT_BASE_URL,
            api_key=settings.MY_AGENT_API_KEY,
            temperature=0.7,
            max_tokens=4096,
        )
    
    async def execute(self, input_data: MyInput) -> MyOutput:
        prompt = await self.load_prompt("my_agent.j2", **input_data.model_dump())
        response = await self.call_llm(prompt)
        return MyOutput.model_validate_json(response)
```

### 示例3: 创建新的CRUD类

1. 参考 [`backend-database.mdc`](./backend-database.mdc) 了解CRUD模式
2. 参考 [`backend-naming.mdc`](./backend-naming.mdc) 确定文件命名

```python
# backend/app/crud/crud_my_model.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud.base import CRUDBase
from app.models.database import MyModel

class CRUDMyModel(CRUDBase[MyModel]):
    """自定义模型CRUD"""
    
    async def get_by_custom_field(
        self,
        db: AsyncSession,
        field_value: str
    ) -> MyModel | None:
        """根据自定义字段查询"""
        stmt = select(self.model).where(
            self.model.custom_field == field_value
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

def get_my_model_crud() -> CRUDMyModel:
    return CRUDMyModel(MyModel)
```

## 📊 规范覆盖范围

- ✅ **架构分层**: API → Service → CRUD → Model
- ✅ **Agent开发**: 基类继承、Protocol实现、配置管理
- ✅ **LangGraph工作流**: State定义、Runner开发、路由函数
- ✅ **API设计**: RESTful规范、参数验证、错误处理
- ✅ **数据库操作**: Session管理、CRUD封装、事务控制
- ✅ **命名规范**: 文件、类、函数、变量的一致性命名
- ✅ **代码风格**: 导入顺序、类型注解、Docstring

## 🔍 与其他规范的关系

这些后端规范与项目根目录的 `.cursor/rules/` 中的其他规范配合使用：

- [`code-comment-rule.mdc`](../.cursor/rules/code-comment-rule.mdc) - 中文注释规范（适用于所有代码）
- [`git-rule.mdc`](../.cursor/rules/git-rule.mdc) - Git提交规范（适用于版本控制）
- [`dev-rule.mdc`](../.cursor/rules/dev-rule.mdc) - MVP开发哲学（激进重构、无向后兼容）
- [`strict-enum-and-constant-consistency.mdc`](../.cursor/rules/strict-enum-and-constant-consistency.mdc) - 枚举和常量一致性

## 📝 维护说明

### 更新规范

当后端架构或开发模式发生变化时，应及时更新对应的MDC文件：

1. 修改相应的 `.mdc` 文件
2. 确保示例代码与实际代码保持一致
3. 更新本README的快速参考部分

### 添加新规范

如需添加新的规范文件（如测试规范、部署规范等）：

1. 创建新的 `.mdc` 文件
2. 添加YAML front matter: `---\nalwaysApply: true\n---`
3. 遵循现有文件的格式和结构
4. 更新本README的文件列表

## ✅ 验收清单

所有生成的文件都满足以下标准：

- [x] 包含正确的YAML front matter
- [x] 包含清晰的标题和描述
- [x] 包含正确✅和错误❌的代码对比示例
- [x] 包含实际项目代码的引用
- [x] 明确定义职责边界和禁止事项
- [x] 遵循中文注释规范
- [x] 包含快速参考表格
- [x] 格式与现有 `.mdc` 文件一致

---

**创建日期**: 2026-01-11  
**维护者**: Backend Team  
**版本**: v1.0.0

