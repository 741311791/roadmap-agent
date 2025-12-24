# 快速修复：liancheng.ly@gmail.com 登录问题

## 问题
用户 `liancheng.ly@gmail.com` 收到邀请邮件后无法登录，因为系统中没有创建对应的用户账号。

## 解决方案（推荐）

### 方式 1：通过管理后台重新发送邀请（最简单）

1. 重置该用户的 waitlist 状态：

```bash
# 连接到数据库
psql -h 47.111.115.130 -U <username> -d roadmap

# 执行重置
UPDATE waitlist_emails
SET 
    invited = FALSE,
    invited_at = NULL,
    username = NULL,
    password = NULL,
    expires_at = NULL,
    sent_content = NULL
WHERE email = 'liancheng.ly@gmail.com'
  AND invited = TRUE;
```

2. 在管理后台重新发送邀请：
   - 访问 `/admin/waitlist`
   - 选择 `liancheng.ly@gmail.com`
   - 点击"Send Invites"

3. 用户会收到新邮件，使用新密码登录即可

### 方式 2：使用 SQL 手动创建用户（需要知道密码）

**问题：** 我们不知道之前发送的临时密码是什么（已经哈希存储）

**不推荐：** 除非用户保存了邮件中的临时密码，否则无法使用此方式

### 方式 3：直接使用 API 创建用户

```bash
# 使用 invite_user 接口（需要管理员权限）
curl -X POST "http://localhost:8000/api/v1/admin/invite-user" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "liancheng.ly@gmail.com",
    "password_validity_days": 30,
    "send_email": true
  }'
```

**注意：** 这会发送新的邮件，用户需要使用新邮件中的密码。

## 推荐步骤（最快）

1. **重置 Waitlist 记录**

```bash
# 进入后端目录
cd backend

# 运行 SQL 脚本
psql -h 47.111.115.130 -U <username> -d roadmap << EOF
UPDATE waitlist_emails
SET 
    invited = FALSE,
    invited_at = NULL,
    username = NULL,
    password = NULL,
    expires_at = NULL,
    sent_content = NULL
WHERE email = 'liancheng.ly@gmail.com';
EOF
```

2. **重启后端服务（如果需要）**

```bash
# 确保新代码已部署
git pull
cd backend
uv run uvicorn app.main:app --reload
```

3. **通过管理后台重新发送邀请**
   - 前端访问: http://localhost:3000/admin/waitlist
   - 选择用户并点击"Send Invites"

4. **通知用户**
   - 告知用户查收新邮件
   - 使用新邮件中的临时密码登录

## 验证

```bash
# 1. 检查用户是否存在
psql -h 47.111.115.130 -U <username> -d roadmap -c "
SELECT id, email, username, is_active, password_expires_at 
FROM users 
WHERE email = 'liancheng.ly@gmail.com';
"

# 2. 检查 waitlist 状态
psql -h 47.111.115.130 -U <username> -d roadmap -c "
SELECT email, invited, invited_at, expires_at 
FROM waitlist_emails 
WHERE email = 'liancheng.ly@gmail.com';
"

# 3. 测试登录（使用新邮件中的密码）
curl -X POST "http://localhost:8000/api/v1/auth/jwt/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=liancheng.ly@gmail.com&password=<新密码>"
```

## 时间估计

- 重置 waitlist 记录: 1 分钟
- 重新发送邮件: 1 分钟
- 用户登录验证: 1 分钟
- **总计: 约 3 分钟**

## 后续预防

修复已经部署到代码中，以后批量发送邀请会自动创建用户账号，不会再出现此问题。

相关 commit: `6005d81 - fix(auth): create user accounts in batch invite`

