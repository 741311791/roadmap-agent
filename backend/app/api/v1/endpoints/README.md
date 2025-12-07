# API端点说明

## 概述

本目录包含所有按功能拆分的API端点模块。每个模块负责特定领域的API功能，遵循单一职责原则。

## 端点模块

### 1. generation.py - 路线图生成

**功能**：处理路线图的异步生成请求

**端点**：
- `POST /roadmaps/generate` - 创建新的路线图生成任务
- `GET /roadmaps/{task_id}/status` - 查询任务状态

**特点**：
- 使用后台任务异步处理
- 通过WebSocket推送进度更新
- 独立的数据库会话管理

### 2. retrieval.py - 路线图查询

**功能**：查询路线图数据和状态

**端点**：
- `GET /roadmaps/{roadmap_id}` - 获取完整路线图
- `GET /roadmaps/{roadmap_id}/active-task` - 获取活跃任务

**特点**：
- 支持正在生成中的路线图查询
- 返回实时任务状态

### 3. approval.py - 人工审核

**功能**：Human-in-the-Loop审核功能

**端点**：
- `POST /roadmaps/{task_id}/approve` - 审核路线图

**特点**：
- 支持批准/拒绝决策
- 可提供反馈意见
- 继续或中断工作流

### 4. tutorial.py - 教程管理

**功能**：教程内容的查询和版本管理

**端点**：
- `GET /roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials` - 获取教程版本历史
- `GET /roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest` - 获取最新版本
- `GET /roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/v{version}` - 获取指定版本

**特点**：
- 完整的版本历史追踪
- 支持多版本并存
- 版本元数据管理

### 5. resource.py - 资源管理

**功能**：学习资源推荐的查询

**端点**：
- `GET /roadmaps/{roadmap_id}/concepts/{concept_id}/resources` - 获取资源列表

**特点**：
- 包含资源类型分类
- 搜索查询记录
- 资源数量统计

### 6. quiz.py - 测验管理

**功能**：测验内容的查询

**端点**：
- `GET /roadmaps/{roadmap_id}/concepts/{concept_id}/quiz` - 获取测验

**特点**：
- 题目难度分级
- 完整题目列表
- 答案和解析

### 7. modification.py - 内容修改

**功能**：使用Modifier Agent修改现有内容

**端点**：
- `POST /roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify` - 修改教程
- `POST /roadmaps/{roadmap_id}/concepts/{concept_id}/resources/modify` - 修改资源
- `POST /roadmaps/{roadmap_id}/concepts/{concept_id}/quiz/modify` - 修改测验

**特点**：
- 增量修改现有内容
- 版本自动递增
- 修改记录追踪

### 8. retry.py - 失败重试

**功能**：重试失败的内容生成

**端点**：
- `POST /roadmaps/{roadmap_id}/retry-failed` - 批量重试失败内容
- `POST /roadmaps/{roadmap_id}/concepts/{concept_id}/regenerate` - 重新生成指定内容

**特点**：
- 断点续传支持
- 按内容类型筛选
- 批量并发处理

### 9. utils.py - 辅助工具

**功能**：提供各端点共用的辅助函数

**主要函数**：
- `get_failed_content_items()` - 提取失败项目
- `find_concept_in_framework()` - 查找概念
- `extract_concepts_from_framework()` - 提取所有概念

## 架构优势

### 1. 模块化
- 每个文件独立负责一个功能域
- 文件大小控制在200行以内
- 易于理解和维护

### 2. 可扩展性
- 新增端点只需创建新模块
- 不影响现有代码
- 易于测试和调试

### 3. 职责清晰
- 端点只负责请求处理
- 业务逻辑在Service层
- 数据访问在Repository层

### 4. 统一规范
- 统一的错误处理
- 一致的日志记录
- 标准的文档注释

## 使用示例

### 生成路线图

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/roadmaps/generate",
    json={
        "user_id": "user-001",
        "preferences": {
            "learning_goal": "学习Python Web开发",
            "current_level": "beginner",
            "time_commitment_hours": 20
        }
    }
)

task_id = response.json()["task_id"]
```

### 查询路线图

```python
import requests

response = requests.get(
    f"http://localhost:8000/api/v1/roadmaps/{roadmap_id}"
)

roadmap = response.json()
```

### 修改教程

```python
import requests

response = requests.post(
    f"http://localhost:8000/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify",
    json={
        "user_id": "user-001",
        "preferences": {...},
        "requirements": [
            "增加更多代码示例",
            "简化技术术语"
        ]
    }
)
```

## 测试

运行端点测试：

```bash
pytest backend/tests/api/ -v
```

运行特定模块测试：

```bash
pytest backend/tests/api/test_generation.py -v
```

## 文档

查看完整API文档：

```bash
# 启动服务器后访问
http://localhost:8000/docs
```
