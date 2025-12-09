-- 添加软删除字段到 roadmap_metadata 表
-- 执行时间: 2025-12-09
-- 描述: 为路线图元数据表添加软删除支持，用于回收站功能

-- 添加软删除字段
ALTER TABLE roadmap_metadata 
ADD COLUMN deleted_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL,
ADD COLUMN deleted_by VARCHAR DEFAULT NULL;

-- 添加索引以优化回收站查询
CREATE INDEX idx_roadmap_metadata_deleted_at ON roadmap_metadata(deleted_at) WHERE deleted_at IS NOT NULL;

-- 添加注释
COMMENT ON COLUMN roadmap_metadata.deleted_at IS '软删除时间，NULL 表示未删除';
COMMENT ON COLUMN roadmap_metadata.deleted_by IS '删除操作的用户 ID';
