/**
 * 技术栈能力测试相关类型定义
 */

export interface AssessmentQuestion {
  question: string;
  type: 'single_choice' | 'multiple_choice' | 'true_false';
  options: string[];
  proficiency_level?: 'beginner' | 'intermediate' | 'expert';
}

export interface TechAssessment {
  assessment_id: string;
  technology: string;
  proficiency_level: string;
  questions: AssessmentQuestion[];
  total_questions: number;
}

export interface AssessmentEvaluationResult {
  score: number;
  max_score: number;
  percentage: number;
  correct_count: number;
  total_questions: number;
  recommendation: 'confirmed' | 'adjust' | 'downgrade';
  message: string;
}

export interface EvaluateRequest {
  assessment_id: string;
  answers: string[];
}

// ============================================================
// 能力分析相关类型（新增）
// ============================================================

/**
 * 知识缺口
 */
export interface KnowledgeGap {
  topic: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  recommendations: string[];
}

/**
 * 能力级别验证
 */
export interface ProficiencyVerification {
  claimed_level: string;
  verified_level: string;
  confidence: 'high' | 'medium' | 'low';
  reasoning: string;
}

/**
 * 分数细分项
 */
export interface ScoreBreakdownItem {
  correct: number;
  total: number;
  percentage: number;
}

/**
 * 分数细分（按 proficiency_level）
 */
export interface ScoreBreakdown {
  beginner: ScoreBreakdownItem;
  intermediate: ScoreBreakdownItem;
  expert: ScoreBreakdownItem;
}

/**
 * 能力分析结果
 */
export interface CapabilityAnalysisResult {
  technology: string;
  proficiency_level: string;
  overall_assessment: string;
  strengths: string[];
  weaknesses: string[];
  knowledge_gaps: KnowledgeGap[];
  learning_suggestions: string[];
  proficiency_verification: ProficiencyVerification;
  score_breakdown: ScoreBreakdown;
}

/**
 * 能力分析请求
 */
export interface AnalyzeCapabilityRequest {
  user_id: string;
  assessment_id: string;
  answers: string[];
  save_to_profile: boolean;
}

/**
 * 用户画像中的技术栈项（包含能力分析）
 */
export interface TechStackItemWithAnalysis {
  technology: string;
  proficiency: string;
  capability_analysis?: {
    overall_assessment: string;
    strengths: string[];
    weaknesses: string[];
    knowledge_gaps: KnowledgeGap[];
    learning_suggestions: string[];
    proficiency_verification: ProficiencyVerification;
    score_breakdown: ScoreBreakdown;
    analyzed_at: string;
  };
}

