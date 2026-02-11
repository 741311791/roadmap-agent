# 单 Concept 内容生成 API 测试指南

## 测试目标

验证单个 Concept 内容生成子图 API (`/api/v1/content/subgraph/generate-single-concept`) 的功能，包括：
- API 端点正确性
- 参数验证
- 内容生成逻辑
- 数据库保存
- 错误处理

## 测试脚本

**文件路径**: `backend/scripts/test_single_concept_generation.py`

## 使用方法

### 方式1: 自动模式（推荐）

自动查找可用的 Roadmap 和 Concept 进行测试：

```bash
cd backend
uv run python scripts/test_single_concept_generation.py --auto
```

### 方式2: 手动指定

指定具体的 Roadmap ID 和 Concept ID：

```bash
cd backend
uv run python scripts/test_single_concept_generation.py \
  --roadmap-id roadmap_abc123 \
  --concept-id C-1-1-1
```

### 方式3: 强制重新生成

即使内容已存在，也强制重新生成：

```bash
cd backend
uv run python scripts/test_single_concept_generation.py \
  --roadmap-id roadmap_abc123 \
  --concept-id C-1-1-1 \
  --force-regenerate
```

## 测试流程

脚本会自动执行以下步骤：

1. **用户登录**: 使用测试用户 `e2e_test_permanent@example.com` 登录
2. **查找/验证资源**: 
   - 自动模式：查找可用的 Roadmap 和 Concept
   - 手动模式：验证提供的 ID 是否存在
3. **生成内容**: 调用 `/api/v1/content/subgraph/generate-single-concept` API
4. **显示结果**: 展示生成的教程、资源、测验内容
5. **验证保存**: 查询 Concept 状态确认数据已保存到数据库

## 预期输出

### 成功输出示例

```
######################################################################
# 单 Concept 内容生成 API 测试脚本
# 服务地址: http://localhost:8000
# 测试时间: 2026-01-13 10:30:00
######################################################################

======================================================================
🔐 步骤1: 用户登录
======================================================================
   用户邮箱: e2e_test_permanent@example.com
   ✅ 登录成功
   Token: eyJhbGciOiJIUzI1NiIsInR5cCI6...

======================================================================
🔍 步骤2: 自动查找可用的 Roadmap 和 Concept
======================================================================
   检查 Roadmap: roadmap_abc123
   ✅ 找到可用的 Concept
      Roadmap ID: roadmap_abc123
      Roadmap Title: 成为Python全栈开发工程师
      Concept ID: C-1-1-1
      Concept Name: Python基础语法

======================================================================
🚀 步骤3: 生成单 Concept 内容
======================================================================
   Roadmap ID: roadmap_abc123
   Concept ID: C-1-1-1
   Force Regenerate: False

   ⏳ 正在调用 API...
   ✅ 内容生成成功
   耗时: 45.23秒

======================================================================
📊 步骤4: 生成结果详情
======================================================================

   基本信息:
   - Concept ID: C-1-1-1
   - Concept Name: Python基础语法
   - 已保存: ✅ 是

   📝 教程内容:
      - 标题: Python基础语法入门
      - 估计时长: 2.5小时
      - 难度: beginner
      - 概述长度: 523 字符
      - 核心要点数: 5
        示例: 变量声明和数据类型（int, float, str, bool）...
      - 实战应用数: 3
        示例: 编写简单的计算器程序，练习变量和运算符的使...
      - 示例代码数: 4
      - 常见陷阱数: 3

   🔗 学习资源:
      - 官方文档数: 2
        示例: Python Official Tutorial - https://docs.pytho...
      - 教程资源数: 3
      - 视频资源数: 2
      - 练习网站数: 2

   ❓ 测验:
      - 题目数: 5
      - 示例题目:
        类型: multiple_choice
        难度: easy
        问题: 以下哪个是Python的合法变量名？...

======================================================================
🔍 步骤5: 验证数据库保存状态
======================================================================
   ✅ 状态查询成功:
      - Concept ID: C-1-1-1
      - Status: generated
      - 有教程: ✅
      - 有资源: ✅
      - 有测验: ✅
      - 错误信息: N/A

######################################################################
# ✅ 测试完成
######################################################################
```

## 常见问题

### 1. 未找到 Roadmap

**错误信息**:
```
❌ 未找到任何 Roadmap
提示: 请先运行 test_roadmap_generation.py 创建一个 Roadmap
```

**解决方案**:
先运行路线图生成脚本创建测试数据：
```bash
uv run python scripts/test_roadmap_generation.py
```

### 2. Concept ID 格式错误

**错误信息**:
```
❌ API 调用失败: HTTP 400
```

**解决方案**:
确保 Concept ID 格式为 `C-<stage>-<module>-<concept>`，例如 `C-1-1-1`

### 3. 权限错误

**错误信息**:
```
❌ API 调用失败: HTTP 403
```

**解决方案**:
确保 Roadmap 属于当前登录的测试用户

### 4. 超时错误

**错误信息**:
```
❌ 请求超时（超过5分钟）
```

**可能原因**:
- LLM API 响应慢
- 网络问题
- 服务器负载高

**解决方案**:
检查后端日志，确认 LLM API 连接正常

## 验证点

测试完成后，请验证以下内容：

- [ ] API 调用成功（HTTP 200）
- [ ] 返回的 JSON 结构正确
- [ ] 教程内容完整（overview, key_points, examples 等）
- [ ] 学习资源有效（至少2个官方文档）
- [ ] 测验题目合理（至少3道题）
- [ ] 数据库已保存（status = 'generated'）
- [ ] 后端日志无错误

## API 接口说明

脚本使用以下 API 接口：

1. **用户认证**
   - `POST /api/v1/auth/jwt/login` - 用户登录

2. **获取用户信息**
   - `GET /api/v1/users/me` - 获取当前用户信息

3. **获取路线图列表**
   - `GET /api/v1/users/{user_id}/roadmaps` - 获取用户的路线图列表

4. **获取路线图详情**
   - `GET /api/v1/roadmaps/{roadmap_id}` - 获取单个路线图的完整数据

5. **生成单个 Concept 内容**
   - `POST /api/v1/content/subgraph/generate-single-concept` - 核心测试接口

6. **查询 Concept 状态**
   - `GET /api/v1/content/{roadmap_id}/concept-status/{concept_id}` - 验证保存状态

## 相关文档

- [两层FanOut_FanIn架构重构完成](./20260113_两层FanOut_FanIn架构重构完成.md)
- [内容生成子图 API 文档](../app/api/v1/endpoints/content/subgraph.py)
- [SubgraphService 实现](../app/services/content/subgraph_service.py)

