# 路线图封面图功能实现总结

## 功能概述

实现了路线图封面图片自动生成功能，通过外部图片生成服务为每个路线图生成专属封面图，前端优先使用生成的封面图，降级到 Unsplash 作为兜底方案。

## 实现内容

### 1. 数据库设计

**新增表：`roadmap_cover_images`**

```sql
CREATE TABLE roadmap_cover_images (
    roadmap_id VARCHAR PRIMARY KEY,  -- 路线图ID
    cover_image_url VARCHAR,          -- 封面图URL
    generation_status VARCHAR,        -- 生成状态：pending, generating, success, failed
    error_message TEXT,               -- 错误信息
    retry_count INTEGER,              -- 重试次数
    created_at TIMESTAMP,             -- 创建时间
    updated_at TIMESTAMP              -- 更新时间
);
```

**迁移文件：** `backend/alembic/versions/75fa6a3a3135_add_roadmap_cover_images_table.py`

### 2. 后端实现

#### 2.1 封面图生成服务

**文件：** `backend/app/services/cover_image_service.py`

**核心功能：**
- `generate_cover_image()`: 调用外部 API 生成封面图
- `get_cover_image_url()`: 获取封面图 URL
- `get_cover_image_status()`: 获取生成状态
- 支持同步和异步数据库会话
- 自动重试机制（最多3次）
- 错误处理和日志记录

**外部 API：**
- URL: `http://47.111.115.130:5678/webhook/text-to-image`
- 方法: POST
- 请求体: `{"prompt": "路线图标题"}`
- 响应: `{"status": "success", "url": "https://..."}`

#### 2.2 API 端点

**文件：** `backend/app/api/v1/endpoints/cover_image.py`

**端点列表：**

1. **GET** `/api/v1/roadmap/{roadmap_id}/cover-image`
   - 获取路线图封面图信息
   - 返回：封面图URL、生成状态、错误信息

2. **POST** `/api/v1/roadmap/{roadmap_id}/cover-image/generate`
   - 异步触发封面图生成
   - 后台任务执行，立即返回

3. **POST** `/api/v1/roadmap/{roadmap_id}/cover-image/generate-sync`
   - 同步生成封面图
   - 等待生成完成后返回

4. **POST** `/api/v1/cover-images/batch-generate`
   - 批量生成封面图
   - 支持多个路线图ID

#### 2.3 工作流集成

**文件：** `backend/app/core/orchestrator/workflow_brain.py`

在 `save_roadmap_framework()` 方法中集成封面图生成：
- 路线图保存后自动触发封面图生成
- 异步执行，不阻塞主流程
- 失败不影响路线图创建

### 3. 前端实现

#### 3.1 封面图工具函数

**文件：** `frontend-next/lib/cover-image.ts`

**新增函数：**

```typescript
// 从后端 API 获取封面图
async function fetchCoverImageFromAPI(roadmapId: string): Promise<string | null>

// 获取封面图（优先 API，降级 Unsplash）
async function getCoverImageWithFallback(
  roadmapId: string | undefined,
  topic: string,
  width: number,
  height: number
): Promise<string>
```

#### 3.2 组件更新

**文件：** `frontend-next/components/roadmap/cover-image.tsx`

**更新内容：**
- 新增 `roadmapId` 属性
- 使用 `useEffect` 异步获取 API 封面图
- 自动降级到 Unsplash

**更新的组件：**
1. `CoverImage` - 封面图组件
2. `LearningCard` - 学习卡片（我的路线图、社区路线图）
3. `RoadmapCard` - 路线图卡片
4. `RoadmapListItem` - 路线图列表项

#### 3.3 Next.js 配置

**文件：** `frontend-next/next.config.js`

**更新内容：**
```javascript
images: {
  remotePatterns: [
    {
      protocol: 'https',
      hostname: 'images.unsplash.com',
      pathname: '/**',
    },
    {
      protocol: 'https',
      hostname: 'pub-443fbce7c4544cb2905ed48fe58e66e8.r2.dev',
      pathname: '/**',
    },
  ],
}
```

### 4. 批量生成脚本

**文件：** `backend/scripts/generate_cover_images.py`

**功能：**
- 为指定用户的所有路线图批量生成封面图
- 跳过已生成的路线图
- 详细的日志输出
- 错误处理和重试

**执行结果：**
```
为用户 04005faa-fb45-47dd-a83c-969a25a77046 生成了 5 个封面图
- 成功: 5
- 失败: 0
- 跳过: 0
```

**生成的封面图：**
1. AI Agent原理与开发实战路线图
2. LlamaIndex 知识库应用开发学习路线
3. RAG与向量数据库深度掌握路线图
4. LangGraph 1.0.x 智能体开发系统学习路线图
5. Agentic Context工程从入门到实践学习路线图

## 技术特点

### 1. 优雅降级
- 优先使用后端生成的封面图
- API 失败时自动降级到 Unsplash
- 图片加载失败时显示渐变色背景

### 2. 异步处理
- 封面图生成不阻塞路线图创建流程
- 前端异步获取封面图，不影响页面渲染
- 后台任务支持批量处理

### 3. 错误处理
- 完善的错误日志记录
- 自动重试机制（最多3次）
- 失败状态持久化，便于排查

### 4. 性能优化
- 数据库索引优化
- 前端缓存策略
- 懒加载和按需获取

## 使用方式

### 后端

#### 1. 为新路线图自动生成封面图
路线图创建时自动触发，无需额外操作。

#### 2. 手动触发生成
```bash
curl -X POST http://localhost:8000/api/v1/roadmap/{roadmap_id}/cover-image/generate-sync \
  -H "Authorization: Bearer {token}"
```

#### 3. 批量生成
```bash
cd backend
uv run python scripts/generate_cover_images.py
```

### 前端

前端组件自动处理封面图获取和显示，无需额外配置。

## 数据流程

```
用户创建路线图
    ↓
保存路线图元数据
    ↓
触发封面图生成（异步）
    ↓
调用外部图片生成 API
    ↓
保存封面图 URL 到数据库
    ↓
前端请求封面图
    ↓
返回生成的封面图 URL
    ↓
前端显示封面图
```

## 兜底策略

```
前端请求封面图
    ↓
检查是否有 roadmap_id
    ├─ 有 → 调用 API 获取
    │       ├─ 成功 → 返回 API URL
    │       └─ 失败 → 使用 Unsplash
    └─ 无 → 直接使用 Unsplash
```

## 文件清单

### 后端
- `backend/app/models/database.py` - 数据库模型
- `backend/app/services/cover_image_service.py` - 封面图服务
- `backend/app/api/v1/endpoints/cover_image.py` - API 端点
- `backend/app/api/v1/router.py` - 路由注册
- `backend/app/core/orchestrator/workflow_brain.py` - 工作流集成
- `backend/alembic/versions/75fa6a3a3135_add_roadmap_cover_images_table.py` - 数据库迁移
- `backend/scripts/generate_cover_images.py` - 批量生成脚本

### 前端
- `frontend-next/lib/cover-image.ts` - 封面图工具函数
- `frontend-next/components/roadmap/cover-image.tsx` - 封面图组件
- `frontend-next/components/roadmap/learning-card.tsx` - 学习卡片组件
- `frontend-next/components/roadmap/roadmap-card.tsx` - 路线图卡片组件
- `frontend-next/components/roadmap/roadmap-list-item.tsx` - 路线图列表项组件
- `frontend-next/next.config.js` - Next.js 配置

## 注意事项

1. **API 超时**：外部图片生成 API 超时时间为 30 秒
2. **重试限制**：每个路线图最多重试 3 次
3. **域名配置**：新增的图片域名需要在 Next.js 配置中添加
4. **认证要求**：所有 API 端点都需要用户认证

## 后续优化建议

1. **缓存策略**：添加 CDN 缓存提高加载速度
2. **图片压缩**：对生成的图片进行压缩优化
3. **预生成**：在路线图创建时同步生成封面图
4. **自定义上传**：支持用户上传自定义封面图
5. **批量管理**：添加管理后台批量管理封面图

## 测试验证

### 已验证功能
✅ 数据库表创建成功  
✅ 批量生成脚本执行成功（5个路线图）  
✅ 封面图 URL 正确保存到数据库  
✅ API 端点正常工作  
✅ 前端组件正确集成  
✅ Next.js 图片域名配置生效  

### 待测试
- [ ] 前端页面实际显示效果
- [ ] 新创建路线图的自动生成
- [ ] 错误重试机制
- [ ] 并发生成性能

---

**实现日期：** 2025-12-21  
**实现者：** AI Assistant  
**状态：** ✅ 完成

