-- 检查已发送邀请但没有对应用户账号的 Waitlist 记录
-- 
-- 运行方式:
--   psql -h <host> -U <user> -d roadmap -f check_invited_users.sql
-- 
-- 或在 psql 中:
--   \i backend/scripts/check_invited_users.sql

SELECT 
    w.email,
    w.username,
    w.invited,
    w.invited_at,
    w.expires_at,
    CASE 
        WHEN u.id IS NOT NULL THEN '✓ 账号已存在'
        WHEN w.password IS NULL THEN '✗ 缺少密码'
        WHEN w.username IS NULL THEN '✗ 缺少用户名'
        WHEN w.expires_at IS NULL THEN '✗ 缺少过期时间'
        ELSE '⚠ 需要创建账号'
    END AS status
FROM waitlist_emails w
LEFT JOIN users u ON w.email = u.email
WHERE w.invited = TRUE
ORDER BY w.invited_at DESC;

-- 统计信息
SELECT 
    COUNT(*) FILTER (WHERE u.id IS NOT NULL) as "已有账号",
    COUNT(*) FILTER (WHERE u.id IS NULL AND w.password IS NOT NULL) as "需要创建账号",
    COUNT(*) FILTER (WHERE u.id IS NULL AND w.password IS NULL) as "数据不完整",
    COUNT(*) as "总计"
FROM waitlist_emails w
LEFT JOIN users u ON w.email = u.email
WHERE w.invited = TRUE;

