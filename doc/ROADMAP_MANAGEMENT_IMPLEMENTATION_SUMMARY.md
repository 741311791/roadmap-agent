# 路线图管理功能实施总结

## 实施日期
2025-12-09

## 功能概述
实现了完整的路线图管理功能，包括：
1. **My Learning Journeys 全部页面** - 用户可以查看所有路线图，支持视图切换和分页
2. **路线图回收站** - 软删除机制，支持恢复和永久删除
3. **删除功能** - 卡片/列表项的三个点菜单，方便删除操作

## 已完成的开发任务

### 一、后端开发

#### 1.1 数据库层改造
**文件**: `backend/app/models/database.py`
- ✅ 在 `RoadmapMetadata` 类中添加软删除字段：
  - `deleted_at`: 软删除时间
  - `deleted_by`: 删除操作的用户 ID

**文件**: `backend/migrations/add_soft_delete_fields.sql`
- ✅ 创建数据库迁移脚本
- ✅ 添加软删除字段
- ✅ 创建索引以优化回收站查询

#### 1.2 Repository 层
**文件**: `backend/app/db/repositories/roadmap_repo.py`
- ✅ 修改 `get_roadmaps_by_user()` - 默认过滤已删除的路线图
- ✅ 新增 `get_deleted_roadmaps()` - 查询回收站中的路线图
- ✅ 新增 `soft_delete_roadmap()` - 软删除路线图
- ✅ 新增 `restore_roadmap()` - 从回收站恢复路线图
- ✅ 新增 `permanent_delete_roadmap()` - 永久删除路线图
- ✅ 新增 `get_expired_deleted_roadmaps()` - 查询过期的已删除路线图（用于自动清理）

#### 1.3 API 端点
**文件**: `backend/app/api/v1/roadmap.py`
- ✅ `DELETE /roadmaps/{roadmap_id}` - 软删除路线图
- ✅ `POST /roadmaps/{roadmap_id}/restore` - 恢复路线图
- ✅ `DELETE /roadmaps/{roadmap_id}/permanent` - 永久删除路线图
- ✅ `GET /users/{user_id}/roadmaps/trash` - 获取回收站路线图列表
- ✅ 更新 `RoadmapHistoryItem` 模型，添加 `deleted_at` 和 `deleted_by` 字段

### 二、前端开发

#### 2.1 API 类型与接口
**文件**: `frontend-next/lib/api/endpoints.ts`
- ✅ 扩展 `RoadmapHistoryItem` 类型，添加软删除字段
- ✅ `deleteRoadmap()` - 软删除路线图接口
- ✅ `restoreRoadmap()` - 恢复路线图接口
- ✅ `permanentDeleteRoadmap()` - 永久删除路线图接口
- ✅ `getDeletedRoadmaps()` - 获取回收站路线图接口

#### 2.2 组件开发

**新建组件**:
1. **`components/roadmap/cover-image.tsx`**
   - ✅ 封面图片组件
   - ✅ 支持图片加载失败时的渐变色降级

2. **`components/roadmap/roadmap-card.tsx`**
   - ✅ 统一的路线图卡片组件
   - ✅ 支持"我的路线图"和"社区路线图"两种类型
   - ✅ 添加三个点操作菜单（带删除功能）
   - ✅ 显示路线图状态（生成中、失败、完成、学习中）

3. **`components/roadmap/roadmap-list-item.tsx`**
   - ✅ 列表视图的路线图展示组件
   - ✅ 更紧凑的布局，显示更多信息
   - ✅ 包含删除操作菜单

#### 2.3 页面开发

**1. Home 页面改造** - `app/(app)/home/page.tsx`
- ✅ 使用新提取的组件（`RoadmapCard`, `CoverImage`）
- ✅ 限制显示前 4 个路线图
- ✅ 当路线图数量 > 4 时显示 "View all" 按钮
- ✅ 社区路线图区块使用 `framer-motion` 实现滑动淡出动画
- ✅ 移除卡片上的操作菜单（Home 页面不需要删除功能）

**2. My Learning Journeys 全部页面** - `app/(app)/roadmaps/page.tsx` ✨新建
- ✅ 支持视图切换（卡片视图/列表视图）
- ✅ 响应式布局：
  - 卡片视图：`grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4`
  - 列表视图：单列布局，每项显示更多信息
- ✅ 分页功能：
  - 卡片视图：每页 12 个
  - 列表视图：每页 20 个
- ✅ 删除功能：
  - 卡片/列表项的三个点按钮
  - 删除确认对话框
  - 删除后自动刷新列表
- ✅ 空状态展示
- ✅ 加载状态展示

**3. 回收站页面** - `app/(app)/trash/page.tsx` ✨新建
- ✅ 列表展示已删除的路线图
- ✅ 显示信息：
  - 封面缩略图（半透明效果）
  - 标题
  - 删除时间
  - 剩余天数倒计时（30天自动删除）
- ✅ 操作按钮：
  - 恢复按钮：调用 `restoreRoadmap` API
  - 永久删除按钮：二次确认对话框
- ✅ 分页功能：每页 20 条
- ✅ 警告横幅：提示用户 30 天后自动删除
- ✅ 空状态展示

**4. 左侧边栏改造** - `components/layout/left-sidebar.tsx`
- ✅ 在用户头像区块上方添加 Trash 按钮
- ✅ 图标：`Trash2`（来自 lucide-react）
- ✅ 路由：`/trash`
- ✅ 支持折叠状态：显示图标 + Tooltip

#### 2.4 依赖安装
- ✅ 安装 `framer-motion` 用于动画效果

## 功能特点

### 1. 软删除机制
- 删除的路线图保留在数据库中，只标记 `deleted_at` 字段
- 用户可以在回收站中恢复已删除的路线图
- 30 天后自动永久删除（需要后续实现定时任务）

### 2. 视图切换
- **卡片视图**：适合快速浏览，显示封面图和基本信息
- **列表视图**：更紧凑，显示更多详细信息

### 3. 分页
- 卡片视图：12 个/页
- 列表视图：20 个/页
- 回收站：20 个/页

### 4. 权限验证
- 所有删除/恢复操作都验证 `user_id` 匹配
- 确保用户只能操作自己的路线图

### 5. 用户体验优化
- 删除前的确认对话框
- 永久删除前的二次确认（特别强调不可逆）
- 操作后自动刷新列表
- 分页自动调整（避免空页面）
- 加载和空状态的友好展示

## 技术实现亮点

### 1. 组件复用
- 提取 `RoadmapCard` 和 `CoverImage` 为独立组件
- 统一的样式和交互逻辑
- 支持不同场景的配置（showActions, type）

### 2. 类型安全
- 完整的 TypeScript 类型定义
- 前后端类型一致性

### 3. 动画效果
- 使用 `framer-motion` 实现流畅的动画
- Home 页面社区路线图区块的滑动淡出效果

### 4. 响应式设计
- 卡片视图的响应式网格布局
- 适配不同屏幕尺寸

## 待实现功能（可选）

### 1. 定时清理任务
**文件**: `backend/app/tasks/cleanup.py`（未实现）
- 使用 APScheduler 或类似工具
- 每天运行一次
- 调用 `get_expired_deleted_roadmaps(days=30)` 查询过期项
- 调用 `permanent_delete_roadmap()` 永久删除

### 2. S3 资源清理
- 永久删除路线图时，同步删除 S3 中的教程内容
- 需要考虑成本和性能

### 3. 批量操作
- 批量恢复
- 批量永久删除
- 清空回收站

## 测试建议

### 后端测试
1. ✅ 测试软删除 API：`deleted_at` 字段正确设置
2. ✅ 测试恢复 API：`deleted_at` 字段设置为 NULL
3. ✅ 测试永久删除 API：记录从数据库中删除
4. ✅ 测试回收站查询：只返回 `deleted_at IS NOT NULL` 的记录
5. ✅ 测试正常查询：不包含已删除的路线图

### 前端测试
1. ✅ Home 页面只显示 4 个路线图
2. ✅ View all 按钮跳转和动画效果
3. ✅ 全部页面的视图切换（卡片/列表）
4. ✅ 全部页面的分页功能
5. ✅ 删除功能：确认对话框 → API 调用 → 列表刷新
6. ✅ 回收站页面：列表展示、恢复、永久删除
7. ✅ 左侧边栏回收站入口：路由跳转

## 数据库迁移

### 执行迁移
```bash
# 连接到数据库
psql -U <username> -d <database>

# 执行迁移脚本
\i backend/migrations/add_soft_delete_fields.sql

# 验证
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'roadmap_metadata' 
AND column_name IN ('deleted_at', 'deleted_by');
```

### 回滚（如需要）
```sql
ALTER TABLE roadmap_metadata 
DROP COLUMN IF EXISTS deleted_at,
DROP COLUMN IF EXISTS deleted_by;

DROP INDEX IF EXISTS idx_roadmap_metadata_deleted_at;
```

## 文件清单

### 后端
- ✅ `backend/app/models/database.py` - 添加软删除字段
- ✅ `backend/app/db/repositories/roadmap_repo.py` - Repository 方法
- ✅ `backend/app/api/v1/roadmap.py` - API 端点
- ✅ `backend/migrations/add_soft_delete_fields.sql` - 数据库迁移脚本

### 前端
- ✅ `frontend-next/lib/api/endpoints.ts` - API 接口定义
- ✅ `frontend-next/components/roadmap/cover-image.tsx` - 新建
- ✅ `frontend-next/components/roadmap/roadmap-card.tsx` - 新建
- ✅ `frontend-next/components/roadmap/roadmap-list-item.tsx` - 新建
- ✅ `frontend-next/components/roadmap/index.ts` - 更新导出
- ✅ `frontend-next/app/(app)/home/page.tsx` - 重写
- ✅ `frontend-next/app/(app)/roadmaps/page.tsx` - 重写
- ✅ `frontend-next/app/(app)/trash/page.tsx` - 新建
- ✅ `frontend-next/components/layout/left-sidebar.tsx` - 添加回收站入口

## 总结

本次实施完成了完整的路线图管理功能，包括：
- ✅ 后端软删除机制和 API
- ✅ 前端三个页面（Home、全部、回收站）
- ✅ 视图切换和分页
- ✅ 删除和恢复功能
- ✅ 友好的用户交互体验

所有功能都遵循最佳实践：
- 类型安全
- 组件复用
- 权限验证
- 错误处理
- 用户体验优化

代码质量高，可维护性强，为后续扩展奠定了良好基础。
