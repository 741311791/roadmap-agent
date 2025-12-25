# Tavily API Key 批量管理功能

## 概述

新增了完整的 Tavily API Key 批量管理功能，允许超级管理员通过 Web 界面批量录入、查看、更新和删除 Tavily API Keys。

## 功能特性

### 1. 后端 API 端点

**文件位置**: `backend/app/api/v1/endpoints/admin.py`

新增以下端点（均需要超级管理员权限）：

- **GET /api/v1/admin/tavily-keys** - 获取所有 API Keys
- **POST /api/v1/admin/tavily-keys** - 添加单个 API Key
- **POST /api/v1/admin/tavily-keys/batch** - 批量添加 API Keys
- **PUT /api/v1/admin/tavily-keys/{api_key}** - 更新 API Key 配额
- **DELETE /api/v1/admin/tavily-keys/{api_key}** - 删除 API Key

#### 数据模型

```python
class TavilyAPIKeyInfo(BaseModel):
    api_key: str              # API Key（脱敏显示）
    plan_limit: int           # 计划总配额
    remaining_quota: int      # 剩余配额
    created_at: str          # 录入时间
    updated_at: str          # 最后更新时间

class BatchAddTavilyKeysRequest(BaseModel):
    keys: List[AddTavilyAPIKeyRequest]  # Key 列表

class BatchAddTavilyKeysResponse(BaseModel):
    success: int             # 成功添加的数量
    failed: int              # 失败的数量
    errors: List[dict]       # 失败详情列表
```

### 2. 前端 API 接口封装

**文件位置**: `frontend-next/lib/api/tavily-keys.ts`

提供了完整的 TypeScript 接口封装：

```typescript
// 获取所有 API Keys
export async function getTavilyAPIKeys(): Promise<TavilyAPIKeyListResponse>

// 添加单个 API Key
export async function addTavilyAPIKey(
  request: AddTavilyAPIKeyRequest
): Promise<TavilyAPIKeyInfo>

// 批量添加 API Keys
export async function batchAddTavilyAPIKeys(
  request: BatchAddTavilyKeysRequest
): Promise<BatchAddTavilyKeysResponse>

// 更新 API Key 配额
export async function updateTavilyAPIKey(
  apiKey: string,
  request: UpdateTavilyAPIKeyRequest
): Promise<TavilyAPIKeyInfo>

// 删除 API Key
export async function deleteTavilyAPIKey(
  apiKey: string
): Promise<DeleteTavilyAPIKeyResponse>
```

### 3. 前端管理页面

**文件位置**: `frontend-next/app/(app)/admin/api-keys/page.tsx`

#### 页面功能

1. **统计概览**
   - 显示 Key 总数
   - 显示总配额
   - 显示剩余配额

2. **添加单个 API Key**
   - 输入 API Key
   - 设置计划配额（默认 1000）
   - 实时添加并更新列表

3. **批量添加 API Keys**
   - 支持两种输入格式：
     - 每行一个 Key（使用默认配额 1000）
     - 每行格式：`key,limit`
   - 显示批量添加结果（成功数、失败数、错误详情）
   - 支持部分成功模式

4. **API Keys 列表**
   - 表格显示所有 Keys
   - 显示脱敏后的 Key（前10位...后4位）
   - 显示配额使用进度条
   - 配额颜色编码：
     - 绿色：≥50%
     - 黄色：20-50%
     - 红色：<20%
   - 显示创建和更新时间
   - 支持删除操作（带确认对话框）

5. **刷新功能**
   - 手动刷新 Keys 列表
   - 加载动画反馈

### 4. 导航菜单

**文件位置**: `frontend-next/components/layout/left-sidebar.tsx`

在左侧边栏的 Admin 组下新增了 "API Keys Management" 导航项：

- 图标：Key 🔑
- 路由：`/admin/api-keys`
- 权限：仅超级管理员可见

## 数据库架构

使用现有的 `tavily_api_keys` 表：

```sql
CREATE TABLE tavily_api_keys (
    api_key VARCHAR PRIMARY KEY,
    plan_limit INTEGER NOT NULL,
    remaining_quota INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 使用流程

### 添加单个 Key

1. 访问 `/admin/api-keys` 页面
2. 在 "Add New API Key" 区域输入：
   - API Key
   - Plan Limit（可选，默认 1000）
3. 点击 "Add Key" 按钮
4. 系统自动更新列表

### 批量添加 Keys

1. 访问 `/admin/api-keys` 页面
2. 在 "Batch Add API Keys" 区域输入 Keys：
   ```
   tvly-xxxxxxxxxxxxxxxxxxxxx
   tvly-yyyyyyyyyyyyyyyyyyyyy,2000
   tvly-zzzzzzzzzzzzzzzzzzzzz
   ```
3. 点击 "Batch Add" 按钮
4. 查看批量添加结果
5. 系统自动更新列表

### 删除 Key

1. 在列表中找到要删除的 Key
2. 点击该行的删除按钮（垃圾桶图标）
3. 在确认对话框中点击 "Delete"
4. 系统自动更新列表

## 安全特性

1. **权限控制**
   - 所有端点均需要超级管理员权限
   - 前端页面检查权限，未授权用户无法访问

2. **数据脱敏**
   - 前端显示时脱敏 Key（仅显示前10位和后4位）
   - 后端返回时脱敏处理

3. **操作审计**
   - 所有操作记录结构化日志
   - 包含操作者 ID、操作类型、时间戳等

4. **错误处理**
   - 批量操作支持部分成功模式
   - 详细的错误信息反馈
   - 自动回滚失败的事务

## 集成说明

### Web Search 工具集成

系统会自动使用数据库中剩余配额最多的 Key 进行搜索：

1. `TavilyAPISearchTool` 从数据库读取 Keys
2. `TavilyKeyRepository.get_best_key()` 选择最优 Key
3. 优先级：剩余配额降序排序
4. 如果没有可用 Key，自动回退到 DuckDuckGo

### 配额追踪

- 配额追踪由外部项目维护（定期更新 `remaining_quota` 字段）
- 本系统仅负责 Keys 的 CRUD 操作
- 可通过更新接口手动调整配额

## 技术栈

### 后端
- FastAPI
- SQLAlchemy (异步)
- Pydantic (数据验证)
- structlog (结构化日志)

### 前端
- Next.js 14 (App Router)
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui 组件库
- Zustand (状态管理)

## 开发规范

### 注释规范
- 所有代码注释使用简体中文
- 包含详细的文档注释（Docstrings）
- 解释"为什么"而不仅仅是"做什么"

### 代码风格
- 遵循 MVP 开发哲学
- 使用最新的语言特性
- 无向后兼容的防御性检查
- 优先考虑可读性和开发速度

## 后续优化建议

1. **配额自动更新**
   - 集成 Tavily API 的配额查询接口
   - 定时任务自动更新配额信息

2. **使用统计**
   - 记录每个 Key 的使用次数和时间
   - 生成使用报表

3. **Key 轮换策略**
   - 智能负载均衡
   - 避免单个 Key 配额耗尽

4. **批量导入**
   - 支持 CSV/JSON 文件上传
   - 支持从环境变量批量导入

5. **配额告警**
   - 配额低于阈值时发送通知
   - 邮件/Webhook 通知

## 测试建议

1. **功能测试**
   - 测试添加、删除、批量添加功能
   - 测试权限控制
   - 测试错误处理

2. **集成测试**
   - 测试与 Web Search 工具的集成
   - 测试 Key 选择逻辑

3. **性能测试**
   - 测试批量添加大量 Keys 的性能
   - 测试列表加载性能

## 参考文档

- [Tavily API 文档](https://docs.tavily.com/)
- [后端重构文档](./REFACTORING_PLAN.md)
- [Tavily MCP 设置](./TAVILY_MCP_SETUP.md)
- [Web Search 架构分析](./WEB_SEARCH_ARCHITECTURE_ANALYSIS.md)

## 更新日期

2025-12-26

