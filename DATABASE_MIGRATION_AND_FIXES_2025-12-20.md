# 数据库迁移和修复记录 - 2025-12-20

## 📋 问题总结

### 1. 前端编译错误
**错误信息**：
```
Module not found: Can't resolve '@/components/ui/accordion'
```

**原因**：`ValidationResultPanel` 组件使用了 Accordion，但该组件未创建

### 2. 后端 API 错误
**错误信息**：
```
asyncpg.exceptions.UndefinedTableError: relation "users" does not exist
```

**原因**：迁移 `6ed81a4d4310` 错误地删除了 `users` 表

### 3. CORS 错误（假象）
**错误信息**：
```
Access to XMLHttpRequest at 'http://localhost:8000/api/v1/featured/roadmaps' 
from origin 'http://localhost:3000' has been blocked by CORS policy
```

**实际原因**：后端 500 错误导致无 CORS 响应头，CORS 配置本身正常

---

## ✅ 已完成的修复

### 一、前端修复

#### 1. 创建 Accordion 组件
**文件**：`frontend-next/components/ui/accordion.tsx`

```typescript
- 基于 @radix-ui/react-accordion
- 支持单选/多选模式
- 包含动画效果
- 导出 Accordion, AccordionItem, AccordionTrigger, AccordionContent
```

#### 2. 安装依赖
```bash
npm install @radix-ui/react-accordion
```

#### 3. 更新导出
**文件**：`frontend-next/components/ui/index.ts`
- 添加了 Accordion 组件的导出

#### 4. Tailwind 配置
**文件**：`frontend-next/tailwind.config.ts`
- 已包含 accordion-up 和 accordion-down 动画（无需修改）

---

### 二、后端数据库修复

#### 1. 新增验证和编辑记录表
**迁移**：`18666a4389a6_add_structure_validation_and_roadmap_.py`

##### 新增表：`structure_validation_records`
存储路线图结构验证的历史记录

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| task_id | String | 关联任务 ID |
| roadmap_id | String | 关联路线图 ID |
| is_valid | Boolean | 验证是否通过 |
| overall_score | Float | 总体评分 (0-100) |
| issues | JSON | 问题详情列表 |
| validation_round | Integer | 验证轮次 |
| critical_count | Integer | 严重问题数 |
| warning_count | Integer | 警告数 |
| suggestion_count | Integer | 建议数 |
| created_at | DateTime | 创建时间 |

##### 新增表：`roadmap_edit_records`
存储路线图编辑前后的对比数据

| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| task_id | String | 关联任务 ID |
| roadmap_id | String | 关联路线图 ID |
| origin_framework_data | JSON | 编辑前的完整框架数据 |
| modified_framework_data | JSON | 编辑后的完整框架数据 |
| modification_summary | Text | 修改摘要 |
| modified_node_ids | JSON | 修改的节点 ID 列表 |
| edit_round | Integer | 编辑轮次 |
| created_at | DateTime | 创建时间 |

#### 2. 重新创建 Users 表
**迁移**：`ef6a7e5aabd5_recreate_users_table.py`

##### Users 表结构

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | 主键 (UUID) |
| email | String | 邮箱（唯一索引） |
| username | String(100) | 用户名 |
| hashed_password | String(1024) | 密码哈希 |
| is_active | Boolean | 是否激活 |
| is_superuser | Boolean | 是否超级管理员 |
| is_verified | Boolean | 是否已验证邮箱 |
| password_expires_at | DateTime | 密码过期时间（可选） |
| created_at | DateTime | 创建时间 |

#### 3. 创建管理员账号
**脚本**：`backend/scripts/create_admin_user.py`

已创建的管理员账号：
```
User ID: 04005faa-fb45-47dd-a83c-969a25a77046
Email: admin@example.com
Username: admin
密码: admin123
超级管理员: 是
创建时间: 2025-12-20 21:41:29
```

---

## 📊 当前数据库状态

### 迁移版本
```
当前版本: ef6a7e5aabd5 (head)
迁移历史: 23 个迁移
```

### 数据库表（共 23 张）
```
✅ users                              - 用户表（已修复）
✅ roadmap_tasks                      - 路线图任务
✅ roadmap_metadata                   - 路线图元数据
✅ tutorial_metadata                  - 教程元数据
✅ intent_analysis_metadata           - 需求分析元数据
✅ resource_recommendation_metadata   - 资源推荐元数据
✅ quiz_metadata                      - 测验元数据
✅ tech_stack_assessments            - 技术栈测评
✅ user_profiles                      - 用户画像
✅ execution_logs                     - 执行日志
✅ concept_progress                   - 概念学习进度
✅ quiz_attempts                      - 测验答题记录
✅ structure_validation_records      - 验证记录（新增）
✅ roadmap_edit_records              - 编辑记录（新增）
✅ chat_sessions                      - 聊天会话
✅ chat_messages                      - 聊天消息
✅ learning_notes                     - 学习笔记
✅ waitlist_emails                    - 候补名单
✅ checkpoint_blobs                   - Langgraph 检查点
✅ checkpoint_writes                  - Langgraph 写入记录
✅ checkpoints                        - Langgraph 检查点
✅ checkpoint_migrations              - Langgraph 迁移版本
✅ alembic_version                    - Alembic 版本记录
```

---

## 🔧 可复用脚本

### 创建管理员用户
```bash
# 使用默认参数（admin@example.com / admin123）
cd backend
uv run python scripts/create_admin_user.py

# 自定义参数
uv run python scripts/create_admin_user.py \
  --email custom@example.com \
  --password mypassword \
  --username customadmin
```

---

## 📝 注意事项

### 1. 环境变量检查
确保 `.env` 文件中配置了正确的数据库连接：
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
```

### 2. 迁移执行顺序
所有迁移必须按顺序执行：
```bash
cd backend
uv run alembic upgrade head
```

### 3. 密码安全
- 生产环境请更改默认管理员密码
- 使用强密码（至少 12 位，包含大小写字母、数字、特殊字符）
- 定期轮换管理员密码

### 4. Alembic 模型导入
确保 `backend/alembic/env.py` 导入了所有模型：
```python
from app.models.database import (
    User, RoadmapTask, RoadmapMetadata, TutorialMetadata,
    IntentAnalysisMetadata, ResourceRecommendationMetadata,
    QuizMetadata, TechStackAssessment, UserProfile,
    ExecutionLog, ConceptProgress, QuizAttempt,
    StructureValidationRecord, RoadmapEditRecord,
    ChatSession, ChatMessage, LearningNote, WaitlistEmail,
)
```

---

## ✅ 验证清单

- [x] 前端 Accordion 组件正常工作
- [x] 前端构建无错误
- [x] 数据库迁移版本正确（ef6a7e5aabd5）
- [x] Users 表已创建
- [x] 管理员账号已创建
- [x] structure_validation_records 表已创建
- [x] roadmap_edit_records 表已创建
- [x] 后端 API 正常响应
- [x] CORS 配置正确

---

## 🎉 完成状态

**状态**: ✅ 所有问题已修复

**测试建议**：
1. 刷新前端页面 (http://localhost:3000)
2. 检查首页是否正常加载
3. 尝试使用管理员账号登录
4. 创建测试路线图，验证验证和编辑记录功能

---

**修复时间**: 2025-12-20  
**修复人员**: AI Assistant  
**文档版本**: 1.0

