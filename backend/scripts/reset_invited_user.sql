-- 重置特定用户的 Waitlist 邀请状态
-- 这将允许管理员重新发送邀请，并正确创建用户账号
-- 
-- 使用方式：
--   1. 替换下面的 'user@example.com' 为实际的用户邮箱
--   2. 在 psql 中运行此脚本
-- 
-- 注意：
--   - 这不会删除已发送的邮件（用户仍然会收到旧邮件）
--   - 重新发送邀请后，用户需要使用新邮件中的临时密码

BEGIN;

-- 查看当前状态
SELECT 
    email,
    username,
    invited,
    invited_at,
    expires_at,
    created_at
FROM waitlist_emails
WHERE email = 'liancheng.ly@gmail.com';  -- 替换为实际邮箱

-- 重置邀请状态
UPDATE waitlist_emails
SET 
    invited = FALSE,
    invited_at = NULL,
    username = NULL,
    password = NULL,
    expires_at = NULL,
    sent_content = NULL
WHERE email = 'liancheng.ly@gmail.com'  -- 替换为实际邮箱
  AND invited = TRUE;

-- 查看更新后的状态
SELECT 
    email,
    username,
    invited,
    invited_at,
    expires_at,
    created_at
FROM waitlist_emails
WHERE email = 'liancheng.ly@gmail.com';  -- 替换为实际邮箱

-- 如果一切正常，提交更改
COMMIT;

-- 如果需要撤销，运行：
-- ROLLBACK;

