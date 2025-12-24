# 批量邀请登录问题修复

## 问题描述

用户通过批量邀请功能收到邮件和临时密码后，无法使用这些凭证登录系统，登录请求返回 400 错误。

### 根本原因

在 `batch_send_invites` 接口中，原有逻辑**仅更新了 Waitlist 记录并发送邮件，但没有创建真实的用户账号**。

```python
# ❌ 旧逻辑（错误）
# 1. 更新 waitlist 记录（添加临时密码）
waitlist_entry.password = temp_password
# 2. 发送邮件
await email_service.send_invite_email(...)
# 3. 标记为已邀请
waitlist_entry.invited = True
await db.commit()
# ❌ 但没有创建 User 对象！
```

### 对比正确的逻辑

`invite_user` 接口会正确创建用户账号：

```python
# ✅ 正确逻辑
# 1. 创建用户账号
new_user = await user_manager.create(user_create)
# 2. 设置密码过期时间
new_user.password_expires_at = expires_at
# 3. 发送邮件
await email_service.send_invite_email(...)
```

## 修复方案

### 1. 修复 batch_send_invites 逻辑

在发送邮件前创建用户账号，并使用事务控制确保原子性：

```python
# ✅ 新逻辑
# 1. 检查用户是否已存在
existing_user = await db.execute(
    select(User).where(User.email == email)
)
if existing_user.scalar_one_or_none():
    # 跳过已存在的用户
    continue

# 2. 创建用户账号（不立即提交）
user_create = UserCreate(
    email=email,
    username=username,
    password=temp_password,
)
new_user = await user_manager.create(user_create)
new_user.password_expires_at = expires_at

# 3. 更新 waitlist 记录（不立即提交）
waitlist_entry.username = username
waitlist_entry.password = temp_password
waitlist_entry.expires_at = expires_at

# 4. 发送邮件
email_sent = await email_service.send_invite_email(...)

# 5. 根据邮件发送结果决定是否提交
if email_sent:
    waitlist_entry.invited = True
    waitlist_entry.invited_at = beijing_now()
    await db.commit()  # ✅ 用户创建和 waitlist 更新一起提交
else:
    await db.rollback()  # ❌ 邮件发送失败，回滚所有更改
```

### 2. 事务控制改进

**关键点：事务的原子性**

- **创建用户账号** 和 **发送邮件** 必须作为一个整体成功或失败
- 如果邮件发送失败，应该回滚用户创建，避免用户存在但没有收到凭证的情况
- 旧逻辑中在创建用户后立即 commit，导致回滚无法撤销用户创建

**修复方式：**
- 创建用户后不立即 commit
- 发送邮件后根据结果决定 commit 或 rollback

### 3. 域名更新

同时将邮件相关域名从 `fastlearning.dev` 和 `fastlearning.ai` 统一更新为 `fastlearning.app`：

- `backend/app/config/settings.py`: `RESEND_FROM_EMAIL = "noreply@fastlearning.app"`
- `frontend-next/app/(marketing)/about/page.tsx`: 联系邮箱 `hello@fastlearning.app`

## 修复已受影响的用户

对于已经收到邮件但账号未创建的用户，提供了修复脚本：

### 使用方式

```bash
cd backend
uv run python scripts/fix_invited_users_without_accounts.py
```

### 脚本功能

1. 查找所有已标记为 `invited=True` 的 waitlist 记录
2. 检查对应的用户账号是否存在
3. 如果账号不存在且有必要信息（密码、用户名、过期时间），则创建账号
4. 输出修复结果统计

### 脚本输出示例

```
找到 5 条已发送邀请的记录
✓ user1@example.com - 用户账号已存在，跳过
✓ user2@example.com - 用户账号已创建（ID: abc123）
✗ user3@example.com - 缺少必要信息（密码/用户名/过期时间），跳过
✓ user4@example.com - 用户账号已创建（ID: def456）
✓ user5@example.com - 用户账号已存在，跳过

============================================================
修复完成:
  - 成功创建: 2
  - 已存在跳过: 3
  - 失败: 0
============================================================
```

## 手动修复方案（备选）

如果修复脚本无法使用，管理员可以：

### 方案 A：重新发送邀请

1. 在管理后台，将受影响用户的 waitlist 记录重置：
   ```sql
   UPDATE waitlist_emails 
   SET invited = FALSE, 
       username = NULL, 
       password = NULL, 
       expires_at = NULL
   WHERE email = 'affected_user@example.com';
   ```

2. 在管理后台重新批量发送邀请

### 方案 B：使用 invite_user 接口

直接调用 `POST /api/v1/admin/invite-user` 接口为受影响用户创建账号。

## 测试验证

### 1. 新用户邀请流程

```bash
# 1. 批量发送邀请
POST /api/v1/admin/waitlist-invites/batch-send
{
  "emails": ["newuser@example.com"],
  "password_validity_days": 30
}

# 2. 验证用户账号已创建
GET /api/v1/admin/users?email=newuser@example.com
# 应该返回用户信息

# 3. 使用邮件中的凭证登录
POST /api/v1/auth/jwt/login
{
  "username": "newuser@example.com",
  "password": "<邮件中的临时密码>"
}
# 应该返回 200 和 JWT token
```

### 2. 邮件发送失败场景

```bash
# 如果邮件发送失败，用户账号不应该被创建
# 可以通过断开 Resend API 或使用无效 API key 测试
```

## 相关文件

### 修改的文件

- `backend/app/api/v1/endpoints/admin.py`: 修复 batch_send_invites 逻辑
- `backend/app/config/settings.py`: 更新邮件域名
- `frontend-next/app/(marketing)/about/page.tsx`: 更新联系邮箱

### 新增的文件

- `backend/scripts/fix_invited_users_without_accounts.py`: 修复脚本

## 影响范围

### 受益功能

- ✅ 批量邀请功能现在可以正常使用
- ✅ 用户收到邮件后可以成功登录
- ✅ 邮件发送失败不会创建无凭证的僵尸账号

### 不受影响

- ✅ 单个用户邀请 (`invite_user`) 功能本身是正确的，未修改
- ✅ 已经通过 `invite_user` 创建的用户不受影响
- ✅ 已经登录的用户不受影响

## 后续建议

### 1. 数据一致性检查

定期运行检查脚本，确保 waitlist 和 user 表的一致性：

```python
# 检查已标记为 invited 但没有对应用户账号的记录
SELECT w.email 
FROM waitlist_emails w 
LEFT JOIN users u ON w.email = u.email 
WHERE w.invited = TRUE AND u.id IS NULL;
```

### 2. 监控告警

添加监控指标：
- 邮件发送成功率
- 用户创建失败率
- waitlist 和 user 表的不一致数量

### 3. 用户体验改进

- 邮件中添加"无法登录？"的帮助链接
- 登录失败时提供更明确的错误信息
- 管理后台添加"重新发送邀请"功能

## 提交信息

```
fix(auth): create user accounts in batch invite and update email domain to fastlearning.app

- Fix batch_send_invites to actually create user accounts before sending emails
- Use transaction control: create user + send email atomically
- Rollback user creation if email sending fails
- Update RESEND_FROM_EMAIL from fastlearning.dev to fastlearning.app
- Update contact email in About page to hello@fastlearning.app
- Add fix script for users who received invites but accounts were not created
```

## 时间线

- **2025-12-24 13:38**: 发现问题 - 用户 `liancheng.ly@gmail.com` 收到邮件后无法登录
- **2025-12-24 14:00**: 确认根本原因 - batch_send_invites 未创建用户账号
- **2025-12-24 14:30**: 修复代码并更新域名
- **2025-12-24 14:45**: 创建修复脚本
- **2025-12-24 15:00**: 提交代码并推送

## 参考文档

- `WAITLIST_INVITE_MANAGEMENT_IMPLEMENTATION.md`: Waitlist 邀请管理功能实现文档
- `WAITLIST_TESTING_GUIDE.md`: Waitlist 功能测试指南

