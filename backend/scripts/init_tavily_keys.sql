-- 初始化 Tavily API Keys 测试数据
-- 
-- 使用说明：
-- 1. 将下面的示例 API Keys 替换为你的真实 Key
-- 2. plan_limit 和 remaining_quota 应由外部项目定时更新
-- 3. 在 psql 或其他数据库客户端中运行此脚本

-- 清空现有数据（仅用于测试）
-- TRUNCATE TABLE tavily_api_keys;

-- 插入测试 API Keys
-- 注意：将 'tvly-xxxxx' 替换为你的真实 Tavily API Key
INSERT INTO tavily_api_keys (api_key, plan_limit, remaining_quota, created_at, updated_at)
VALUES 
    ('tvly-key-1-replace-with-real-key', 1000, 850, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('tvly-key-2-replace-with-real-key', 1000, 720, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('tvly-key-3-replace-with-real-key', 1000, 500, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (api_key) DO UPDATE SET
    plan_limit = EXCLUDED.plan_limit,
    remaining_quota = EXCLUDED.remaining_quota,
    updated_at = CURRENT_TIMESTAMP;

-- 查询验证
SELECT 
    api_key,
    plan_limit,
    remaining_quota,
    ROUND((remaining_quota::numeric / plan_limit::numeric) * 100, 2) as quota_percentage,
    created_at,
    updated_at
FROM tavily_api_keys
ORDER BY remaining_quota DESC;

-- 预期输出：
-- api_key                         | plan_limit | remaining_quota | quota_percentage | created_at          | updated_at
-- --------------------------------|------------|-----------------|------------------|---------------------|-------------------
-- tvly-key-1-replace-with-real... | 1000       | 850             | 85.00           | 2025-12-24 ...     | 2025-12-24 ...
-- tvly-key-2-replace-with-real... | 1000       | 720             | 72.00           | 2025-12-24 ...     | 2025-12-24 ...
-- tvly-key-3-replace-with-real... | 1000       | 500             | 50.00           | 2025-12-24 ...     | 2025-12-24 ...

