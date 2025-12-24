# 部署文档索引

本文档汇总了所有与 Railway 部署相关的资源，帮助你快速找到需要的信息。

---

## 📑 文档列表

### 1. [RAILWAY_QUICK_START.md](./RAILWAY_QUICK_START.md) ⚡
**适合人群**：有经验的开发者，想要快速部署

**内容**：
- 5 分钟快速部署流程
- 核心配置步骤（精简版）
- 最小化环境变量配置

**使用场景**：第一次部署到 Railway，想要快速上手

---

### 2. [RAILWAY_DEPLOYMENT_GUIDE.md](./RAILWAY_DEPLOYMENT_GUIDE.md) 📖
**适合人群**：需要详细说明的开发者，或遇到问题需要排查

**内容**：
- 完整的部署步骤（从零开始）
- 详细的环境变量说明
- 常见问题排查指南
- 性能优化建议
- 成本估算

**使用场景**：首次部署或遇到部署问题时查阅

---

### 3. [RAILWAY_CHECKLIST.md](./RAILWAY_CHECKLIST.md) ✅
**适合人群**：所有部署人员

**内容**：
- 部署前检查清单（代码、配置、依赖）
- 部署中验证清单（日志、状态）
- 部署后测试清单（API、CORS、功能）
- 性能优化清单

**使用场景**：部署前/后逐项检查，确保没有遗漏

---

### 4. [RAILWAY_ENV_TEMPLATE.txt](./RAILWAY_ENV_TEMPLATE.txt) 🔧
**适合人群**：配置环境变量时使用

**内容**：
- 完整的环境变量模板（带注释）
- 数据库连接变量引用示例
- 可选配置说明

**使用场景**：复制粘贴到 Railway Variables 编辑器

---

## 🛠️ 辅助工具

### 1. 部署检查脚本
```bash
bash scripts/railway_deploy_check.sh
```
**功能**：检查本地代码是否满足 Railway 部署要求（Dockerfile、依赖、文件结构）

### 2. JWT Secret 生成器
```bash
bash scripts/generate_jwt_secret.sh
```
**功能**：生成安全的 JWT Secret Key，用于 Railway 环境变量配置

---

## 🚀 快速开始

### 第一次部署？

1. **阅读快速指南**：[RAILWAY_QUICK_START.md](./RAILWAY_QUICK_START.md)
2. **运行检查脚本**：`bash scripts/railway_deploy_check.sh`
3. **生成 JWT Secret**：`bash scripts/generate_jwt_secret.sh`
4. **准备环境变量**：参考 [RAILWAY_ENV_TEMPLATE.txt](./RAILWAY_ENV_TEMPLATE.txt)
5. **开始部署**：按照快速指南操作
6. **完成后检查**：使用 [RAILWAY_CHECKLIST.md](./RAILWAY_CHECKLIST.md) 验证

---

## 🆘 遇到问题？

### 常见问题速查

| 问题类型 | 查阅文档 | 章节 |
|---------|---------|------|
| 数据库连接失败 | RAILWAY_DEPLOYMENT_GUIDE.md | 常见问题排查 → 1 |
| Port binding 错误 | RAILWAY_DEPLOYMENT_GUIDE.md | 常见问题排查 → 2 |
| Alembic 迁移失败 | RAILWAY_DEPLOYMENT_GUIDE.md | 常见问题排查 → 3 |
| CORS 错误 | RAILWAY_DEPLOYMENT_GUIDE.md | 常见问题排查 → 4 |
| S3 连接超时 | RAILWAY_DEPLOYMENT_GUIDE.md | 常见问题排查 → 5 |
| 环境变量配置不确定 | RAILWAY_ENV_TEMPLATE.txt | 带注释的完整模板 |
| 不知道还缺什么 | RAILWAY_CHECKLIST.md | 逐项检查清单 |

---

## 📋 部署前必看清单

在开始部署前，请确认：

- [ ] 已推送代码到 GitHub
- [ ] 已准备好所有必需的 API Keys：
  - OpenAI API Key (至少 1 个)
  - Anthropic API Key (至少 1 个)
  - Tavily API Key (至少 1 个)
  - AWS S3 或 Cloudflare R2 凭证
- [ ] 已阅读 [RAILWAY_QUICK_START.md](./RAILWAY_QUICK_START.md)
- [ ] 已运行本地检查脚本：`bash scripts/railway_deploy_check.sh`

---

## 🎯 推荐工作流

### 标准部署流程

```
1. 本地准备
   ├─ 运行 scripts/railway_deploy_check.sh
   ├─ 生成 JWT Secret (scripts/generate_jwt_secret.sh)
   └─ 准备 API Keys

2. Railway 配置
   ├─ 创建项目并连接 GitHub
   ├─ 设置 Root Directory = /backend
   ├─ 添加 PostgreSQL 和 Redis
   └─ 配置环境变量（参考 RAILWAY_ENV_TEMPLATE.txt）

3. 部署与验证
   ├─ 查看部署日志
   ├─ 生成公网域名
   ├─ 测试 API (curl /health)
   └─ 使用 RAILWAY_CHECKLIST.md 逐项验证

4. 后续优化
   ├─ 更新 CORS 配置
   ├─ 配置自定义域名
   └─ 设置监控告警
```

---

## 📚 相关资源

### 后端相关
- [backend/README.md](./backend/README.md) - 后端本地开发指南
- [backend/Dockerfile](./backend/Dockerfile) - Railway 使用的 Docker 配置
- [backend/app/config/settings.py](./backend/app/config/settings.py) - 环境变量定义

### Railway 官方文档
- [Railway 文档](https://docs.railway.app/)
- [PostgreSQL 配置](https://docs.railway.app/databases/postgresql)
- [Redis 配置](https://docs.railway.app/databases/redis)
- [环境变量引用](https://docs.railway.app/develop/variables#referencing-another-services-variable)

### 外部服务
- [OpenAI API Keys](https://platform.openai.com/api-keys)
- [Anthropic API Keys](https://console.anthropic.com/settings/keys)
- [Tavily API](https://tavily.com/)
- [AWS S3](https://aws.amazon.com/s3/)
- [Cloudflare R2](https://www.cloudflare.com/products/r2/)
- [Resend (邮件服务)](https://resend.com/)

---

## 🔄 文档更新日志

| 日期 | 更新内容 |
|------|---------|
| 2025-12-24 | 创建 Railway 部署文档套件（快速指南、完整指南、检查清单、环境变量模板、辅助脚本） |

---

## 💡 提示

- **部署前**：务必运行 `bash scripts/railway_deploy_check.sh` 检查代码
- **配置时**：使用 `RAILWAY_ENV_TEMPLATE.txt` 作为参考，避免遗漏
- **部署后**：使用 `RAILWAY_CHECKLIST.md` 逐项验证
- **遇到问题**：先查 `RAILWAY_DEPLOYMENT_GUIDE.md` 的"常见问题排查"章节

---

**祝部署顺利！** 🚀

如有疑问，请参考对应文档或联系团队。

