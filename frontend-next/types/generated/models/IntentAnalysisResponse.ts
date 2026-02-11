/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 需求分析响应
 *
 * 包含路线图生成过程中的需求分析结果。
 *
 * 状态说明：
 * - available=True: 数据已生成，所有字段有效
 * - available=False: 数据尚未生成，仅 status/current_step/message 有效
 */
export type IntentAnalysisResponse = {
    /**
     * 数据是否可用
     */
    available?: boolean;
    /**
     * 意图分析ID（主键）
     */
    intent_id?: (string | null);
    /**
     * 路线图ID
     */
    roadmap_id?: (string | null);
    /**
     * 解析后的学习目标
     */
    parsed_goal?: (string | null);
    /**
     * 关键技术列表
     */
    key_technologies?: (Array<string> | null);
    /**
     * 难度画像
     */
    difficulty_profile?: (string | null);
    /**
     * 时间限制
     */
    time_constraint?: (string | null);
    /**
     * 推荐重点
     */
    recommended_focus?: (Array<string> | null);
    /**
     * 用户画像摘要
     */
    user_profile_summary?: (string | null);
    /**
     * 技能差距分析
     */
    skill_gap_analysis?: (Array<string> | null);
    /**
     * 个性化建议
     */
    personalized_suggestions?: (Array<string> | null);
    /**
     * 预估学习路径类型
     */
    estimated_learning_path_type?: (string | null);
    /**
     * 内容格式权重
     */
    content_format_weights?: (Record<string, any> | null);
    /**
     * 语言偏好
     */
    language_preferences?: (Record<string, any> | null);
    /**
     * 创建时间（ISO格式）
     */
    created_at?: (string | null);
    /**
     * 任务状态
     */
    status?: (string | null);
    /**
     * 当前步骤
     */
    current_step?: (string | null);
    /**
     * 状态消息
     */
    message?: (string | null);
};

