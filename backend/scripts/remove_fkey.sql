-- 移除 intent_analysis_metadata 表的外键约束
-- 原因：intent_analysis 在 roadmap_metadata 创建之前执行
-- 解决：移除外键约束，由应用层保证数据一致性

-- 检查外键是否存在
SELECT 
    constraint_name,
    table_name,
    constraint_type
FROM information_schema.table_constraints 
WHERE table_name = 'intent_analysis_metadata' 
AND constraint_type = 'FOREIGN KEY'
AND constraint_name = 'intent_analysis_metadata_roadmap_id_fkey';

-- 删除外键约束
ALTER TABLE intent_analysis_metadata 
DROP CONSTRAINT IF EXISTS intent_analysis_metadata_roadmap_id_fkey;

-- 确认索引存在（用于查询性能）
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename = 'intent_analysis_metadata' 
AND indexname LIKE '%roadmap_id%';

-- 完成提示
SELECT '✅ 成功移除外键约束: intent_analysis_metadata_roadmap_id_fkey' AS status;

