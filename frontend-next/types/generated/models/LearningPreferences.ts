/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 学习偏好配置
 */
export type LearningPreferences = {
    /**
     * 学习目标，如'成为全栈工程师'
     */
    learning_goal: string;
    /**
     * 每周可投入小时数
     */
    available_hours_per_week: number;
    /**
     * 学习动机，如'转行'、'升职'、'兴趣'
     */
    motivation: string;
    /**
     * 当前掌握程度
     */
    current_level: 'beginner' | 'intermediate' | 'advanced';
    /**
     * 职业背景，如'市场营销 5 年经验'
     */
    career_background: string;
    /**
     * 偏好的内容类型
     */
    content_preference?: Array<'visual' | 'text' | 'audio' | 'hands_on'>;
    /**
     * 期望完成时间
     */
    target_deadline?: (string | null);
    /**
     * 所属行业
     */
    industry?: (string | null);
    /**
     * 当前职位
     */
    current_role?: (string | null);
    /**
     * 技术栈列表
     */
    tech_stack?: Array<{
        name: string;
        proficiency: 'beginner' | 'intermediate' | 'advanced';
    }> | null;
    /**
     * 偏好的学习语言（向后兼容）
     */
    preferred_language?: (string | null);
    /**
     * 主要语言（教程、路线图语言）
     */
    primary_language?: string;
    /**
     * 次要语言（资源推荐补充语言）
     */
    secondary_language?: (string | null);
};

