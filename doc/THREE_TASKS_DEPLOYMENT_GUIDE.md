# 三项优化任务部署指南

**修改日期**: 2025-12-25  
**部署状态**: 已完成代码修改，待测试验证

---

## 修改摘要

### ✅ 任务 1: 落地页响应式布局
- **文件**: `frontend-next/components/landing/workflow-animation.tsx`
- **修改内容**:
  - 容器高度从固定 600px 改为响应式 `min-h-[400px] h-[600px] lg:h-[700px]`
  - 布局从横向改为移动端垂直堆叠 `flex-col lg:flex-row`
  - 树形图添加缩放 `scale-[0.7] md:scale-[0.85] lg:scale-100`
  - Input Card 宽度响应式 `w-full max-w-[340px] sm:w-[340px]`

### ✅ 任务 2: 能力测验题目数量优化
- **文件**: `backend/app/api/v1/endpoints/tech_assessment.py`
- **修改内容**:
  - 题目总数: 20 → 10
  - Beginner: 14+4+2 → 7+2+1
  - Intermediate: 4+12+4 → 2+6+2
  - Expert: 2+6+12 → 1+3+6
  - 更新文档注释和验证逻辑

### ✅ 任务 3: 迁移至 Cloudflare R2
- **修改文件**:
  - `backend/app/config/settings.py` - 更新配置注释，添加 R2 说明
  - `backend/app/tools/storage/s3_client.py` - 替换为 aioboto3
  - `backend/app/db/s3_init.py` - 新建（替代 minio_init.py）
  - `backend/app/main.py` - 更新导入引用
  - `backend/pyproject.toml` - 移除 minio 依赖

---

## 部署步骤

### 第一步：前端部署

```bash
cd frontend-next

# 验证代码更改
git diff components/landing/workflow-animation.tsx

# 提交
git add components/landing/workflow-animation.tsx
git commit -m "feat: 实现落地页 hero 区域响应式布局

- 移动端垂直堆叠，桌面端横向布局
- 添加流程图缩放适配不同屏幕
- Input Card 宽度响应式"
```

**验证响应式布局**:
1. 打开浏览器 DevTools
2. 测试以下分辨率:
   - 375px (Mobile)
   - 768px (Tablet)
   - 1440px (Desktop)
3. 确认流程图完整可见且不溢出

---

### 第二步：后端部署 - 题目数量优化

```bash
cd backend

# 验证代码更改
git diff app/api/v1/endpoints/tech_assessment.py

# 提交
git add app/api/v1/endpoints/tech_assessment.py
git commit -m "feat: 优化能力测验题目数量从 20 题降至 10 题

- 调整抽题分布保持比例
- 更新文档和验证逻辑"
```

**验证题目数量**:
```bash
# 调用 API 测试
curl http://localhost:8000/api/v1/tech-assessments/python/beginner

# 确认返回 JSON 中 total_questions = 10
# 确认 questions 数组长度为 10
```

---

### 第三步：后端部署 - R2 迁移

#### 3.1 更新环境变量

在 Railway Dashboard 或 `.env` 中配置：

```bash
# Cloudflare R2 配置
S3_ENDPOINT_URL=https://<your_account_id>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=<your_r2_access_key_id>
S3_SECRET_ACCESS_KEY=<your_r2_secret_access_key>
S3_BUCKET_NAME=roadmap-content
S3_REGION=auto
```

**获取 R2 凭证**:
1. 登录 Cloudflare Dashboard
2. 进入 R2 → Overview
3. Account ID 在右侧显示
4. 点击 "Manage R2 API Tokens" 创建 Access Key

#### 3.2 更新依赖并部署

```bash
cd backend

# 更新依赖（移除 minio，aioboto3 已存在）
uv lock
uv sync

# 验证所有文件
git status

# 提交所有更改
git add app/config/settings.py \
        app/tools/storage/s3_client.py \
        app/db/s3_init.py \
        app/main.py \
        pyproject.toml

git commit -m "feat: 迁移对象存储至 Cloudflare R2

- 替换 MinIO SDK 为 aioboto3（原生异步）
- 创建 s3_init.py 替代 minio_init.py
- 支持 S3 兼容协议（R2/S3/MinIO）
- 移除 pyproject.toml 中的 minio 依赖"

# 推送到远程仓库
git push origin main
```

#### 3.3 Railway 自动部署

Railway 检测到代码更新后会自动：
1. 安装新依赖（aioboto3）
2. 重新构建镜像
3. 重启服务

**等待部署完成**（约 3-5 分钟）

---

## 验证清单

### ✅ 响应式布局验证

在 https://your-domain.com 测试：

- [ ] Mobile (375px): 流程图垂直堆叠，缩小至 70%
- [ ] Tablet (768px): 流程图缩小至 85%
- [ ] Desktop (1440px): 流程图保持 100%，横向布局
- [ ] 动画流畅，Xarrows 连线正常

### ✅ 题目数量验证

```bash
# 测试 API
curl https://your-backend.railway.app/api/v1/tech-assessments/python/beginner

# 验证点
# - "total_questions": 10
# - "questions" 数组长度为 10
# - 不同级别题目配比正确
```

### ✅ R2 存储验证

```bash
# 查看启动日志
# Railway Dashboard → Deployments → Logs

# 应该看到:
# s3_client_initialized endpoint=https://xxx.r2.cloudflarestorage.com
# s3_bucket_exists bucket=roadmap-content
```

**测试上传**:
1. 生成一个新路线图
2. 等待教程生成完成
3. 检查日志是否有 `s3_upload_success`
4. 在 Cloudflare Dashboard → R2 中查看文件

---

## 回滚方案

### 前端回滚
```bash
git revert <commit_hash>
git push origin main
```

### 后端回滚
如果 R2 迁移出现问题，快速回滚到 MinIO：

1. **恢复代码**:
```bash
git revert <commit_hash>
git push origin main
```

2. **恢复环境变量**:
```bash
S3_ENDPOINT_URL=http://your-minio:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin123
S3_REGION=
```

---

## 常见问题

### Q1: R2 上传失败 "Access Denied"
**A**: 检查 R2 API Token 权限，需要 "Object Read & Write" 权限。

### Q2: 响应式布局动画卡顿
**A**: 检查 `scale` transform 是否触发过多重绘，可以添加 `will-change: transform`。

### Q3: 题目数量还是显示 20 道
**A**: 清除 Redis 缓存或等待 2 小时缓存过期：
```bash
redis-cli FLUSHDB
```

---

## 数据迁移（可选）

如果需要将旧 MinIO 数据迁移到 R2：

```bash
# 安装 MinIO Client
brew install minio/stable/mc

# 配置 MinIO 源
mc alias set minio-src http://your-minio:9000 minioadmin minioadmin123

# 配置 R2 目标
mc alias set r2 https://<account_id>.r2.cloudflarestorage.com <key> <secret>

# 镜像同步
mc mirror minio-src/roadmap-content r2/roadmap-content --overwrite

# 验证文件数量
mc ls r2/roadmap-content --recursive | wc -l
```

---

## 监控建议

### 前端监控
- Google Analytics 跟踪响应式布局下的用户行为
- Sentry 监控前端错误率

### 后端监控
- 监控 R2 请求延迟（应 < 200ms）
- 监控上传成功率（应 > 99.5%）
- 设置告警：上传失败 > 5 次/小时

---

## 完成状态

| 任务 | 状态 | 备注 |
|------|------|------|
| ✅ 响应式布局 | 已完成 | 待测试多设备 |
| ✅ 题目数量优化 | 已完成 | 待 API 测试 |
| ✅ R2 配置更新 | 已完成 | 待环境变量配置 |
| ✅ S3 Client 重写 | 已完成 | 使用 aioboto3 |
| ✅ Bucket 初始化 | 已完成 | 创建 s3_init.py |
| ✅ 依赖包更新 | 已完成 | 移除 minio |
| ⏳ 生产环境验证 | 待执行 | 需配置 R2 凭证 |

---

**下一步操作**:
1. 配置 Railway 环境变量（R2 凭证）
2. 推送代码触发部署
3. 验证三项功能是否正常
4. 监控错误日志

