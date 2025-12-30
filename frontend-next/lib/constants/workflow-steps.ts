/**
 * 工作流步骤常量定义
 * 
 * 与后端 WorkflowStep 枚举保持同步
 * @see backend/app/models/constants.py
 * 
 * 这是前端的单一真相来源（Single Source of Truth），
 * 所有前端代码应该引用这里的常量，而不是使用字符串字面量。
 */

/**
 * 工作流步骤枚举值
 */
export const WorkflowStep = {
  // 初始化阶段
  INIT: 'init',
  QUEUED: 'queued',
  STARTING: 'starting',
  
  // 主路节点
  INTENT_ANALYSIS: 'intent_analysis',
  CURRICULUM_DESIGN: 'curriculum_design',
  STRUCTURE_VALIDATION: 'structure_validation',
  HUMAN_REVIEW: 'human_review',
  
  // 验证分支节点（验证失败触发）
  VALIDATION_EDIT_PLAN_ANALYSIS: 'validation_edit_plan_analysis',
  
  // 审核分支节点（用户拒绝触发）
  EDIT_PLAN_ANALYSIS: 'edit_plan_analysis',
  
  // 共享的编辑节点
  ROADMAP_EDIT: 'roadmap_edit',
  
  // 内容生成阶段
  CONTENT_GENERATION_QUEUED: 'content_generation_queued',
  CONTENT_GENERATION: 'content_generation',
  TUTORIAL_GENERATION: 'tutorial_generation',
  RESOURCE_RECOMMENDATION: 'resource_recommendation',
  QUIZ_GENERATION: 'quiz_generation',
  
  // 完成阶段
  FINALIZING: 'finalizing',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;

export type WorkflowStepValue = (typeof WorkflowStep)[keyof typeof WorkflowStep];

/**
 * 初始化阶段的步骤
 */
export const INIT_STEPS: WorkflowStepValue[] = [
  WorkflowStep.INIT,
  WorkflowStep.QUEUED,
  WorkflowStep.STARTING,
];

/**
 * Intent Analysis 阶段的步骤（包含初始化）
 */
export const ANALYSIS_STEPS: WorkflowStepValue[] = [
  ...INIT_STEPS,
  WorkflowStep.INTENT_ANALYSIS,
];

/**
 * Curriculum Design 阶段的步骤
 */
export const DESIGN_STEPS: WorkflowStepValue[] = [
  WorkflowStep.CURRICULUM_DESIGN,
];

/**
 * Structure Validation 阶段的步骤
 */
export const VALIDATION_STEPS: WorkflowStepValue[] = [
  WorkflowStep.STRUCTURE_VALIDATION,
];

/**
 * Human Review 阶段的步骤
 */
export const REVIEW_STEPS: WorkflowStepValue[] = [
  WorkflowStep.HUMAN_REVIEW,
];

/**
 * Content Generation 阶段的步骤
 */
export const CONTENT_STEPS: WorkflowStepValue[] = [
  WorkflowStep.CONTENT_GENERATION_QUEUED,
  WorkflowStep.CONTENT_GENERATION,
  WorkflowStep.TUTORIAL_GENERATION,
  WorkflowStep.RESOURCE_RECOMMENDATION,
  WorkflowStep.QUIZ_GENERATION,
];

/**
 * 验证分支的步骤（验证失败触发）
 */
export const VALIDATION_BRANCH_STEPS: WorkflowStepValue[] = [
  WorkflowStep.VALIDATION_EDIT_PLAN_ANALYSIS,
];

/**
 * 审核分支的步骤（用户拒绝触发）
 */
export const REVIEW_BRANCH_STEPS: WorkflowStepValue[] = [
  WorkflowStep.EDIT_PLAN_ANALYSIS,
];

/**
 * 共享的编辑步骤
 */
export const EDIT_STEPS: WorkflowStepValue[] = [
  WorkflowStep.ROADMAP_EDIT,
];

/**
 * 判断步骤是否处于 Intent Analysis 完成后的阶段
 * （用于决定是否显示 Intent Analysis Card）
 */
export function isAfterIntentAnalysis(step: string | null): boolean {
  if (!step) return false;
  
  const stepsAfterIntent: string[] = [
    WorkflowStep.INTENT_ANALYSIS,
    WorkflowStep.CURRICULUM_DESIGN,
    WorkflowStep.STRUCTURE_VALIDATION,
    WorkflowStep.VALIDATION_EDIT_PLAN_ANALYSIS,
    WorkflowStep.EDIT_PLAN_ANALYSIS,
    WorkflowStep.ROADMAP_EDIT,
    WorkflowStep.HUMAN_REVIEW,
    WorkflowStep.CONTENT_GENERATION_QUEUED,
    WorkflowStep.CONTENT_GENERATION,
    WorkflowStep.TUTORIAL_GENERATION,
    WorkflowStep.RESOURCE_RECOMMENDATION,
    WorkflowStep.QUIZ_GENERATION,
    WorkflowStep.FINALIZING,
    WorkflowStep.COMPLETED,
  ];
  
  return stepsAfterIntent.includes(step);
}

/**
 * 判断步骤是否处于 Curriculum Design 完成后的阶段
 * （用于决定是否显示 Roadmap Tree）
 */
export function isAfterCurriculumDesign(step: string | null): boolean {
  if (!step) return false;
  
  const stepsAfterDesign: string[] = [
    WorkflowStep.STRUCTURE_VALIDATION,
    WorkflowStep.VALIDATION_EDIT_PLAN_ANALYSIS,
    WorkflowStep.EDIT_PLAN_ANALYSIS,
    WorkflowStep.ROADMAP_EDIT,
    WorkflowStep.HUMAN_REVIEW,
    WorkflowStep.CONTENT_GENERATION_QUEUED,
    WorkflowStep.CONTENT_GENERATION,
    WorkflowStep.TUTORIAL_GENERATION,
    WorkflowStep.RESOURCE_RECOMMENDATION,
    WorkflowStep.QUIZ_GENERATION,
    WorkflowStep.FINALIZING,
    WorkflowStep.COMPLETED,
  ];
  
  return stepsAfterDesign.includes(step);
}

/**
 * 步骤显示配置
 */
export const STEP_DISPLAY_CONFIG: Record<string, { label: string; description: string }> = {
  [WorkflowStep.INIT]: { label: 'Initialize', description: 'Initializing workflow...' },
  [WorkflowStep.QUEUED]: { label: 'Queued', description: 'Initializing workflow...' },
  [WorkflowStep.STARTING]: { label: 'Starting', description: 'Starting your roadmap generation...' },
  [WorkflowStep.INTENT_ANALYSIS]: { label: 'Intent Analysis', description: 'Analyzing your learning goals...' },
  [WorkflowStep.CURRICULUM_DESIGN]: { label: 'Curriculum Design', description: 'Designing roadmap structure...' },
  [WorkflowStep.STRUCTURE_VALIDATION]: { label: 'Structure Validation', description: 'Validating roadmap structure...' },
  [WorkflowStep.VALIDATION_EDIT_PLAN_ANALYSIS]: { label: 'Validation Edit Plan', description: 'Analyzing validation issues...' },
  [WorkflowStep.EDIT_PLAN_ANALYSIS]: { label: 'Review Edit Plan', description: 'Analyzing your feedback...' },
  [WorkflowStep.ROADMAP_EDIT]: { label: 'Roadmap Edit', description: 'Applying modifications...' },
  [WorkflowStep.HUMAN_REVIEW]: { label: 'Human Review', description: 'Awaiting your review...' },
  [WorkflowStep.CONTENT_GENERATION_QUEUED]: { label: 'Content Queued', description: 'Preparing content generation...' },
  [WorkflowStep.CONTENT_GENERATION]: { label: 'Content Generation', description: 'Generating learning content...' },
  [WorkflowStep.TUTORIAL_GENERATION]: { label: 'Tutorial Generation', description: 'Generating tutorials...' },
  [WorkflowStep.RESOURCE_RECOMMENDATION]: { label: 'Resource Recommendation', description: 'Finding learning resources...' },
  [WorkflowStep.QUIZ_GENERATION]: { label: 'Quiz Generation', description: 'Creating quiz questions...' },
  [WorkflowStep.FINALIZING]: { label: 'Finalizing', description: 'Finalizing your roadmap...' },
  [WorkflowStep.COMPLETED]: { label: 'Completed', description: 'Roadmap generation completed!' },
  [WorkflowStep.FAILED]: { label: 'Failed', description: 'Roadmap generation failed.' },
};

/**
 * 获取步骤的显示标签
 */
export function getStepLabel(step: string | null): string {
  if (!step) return 'Unknown';
  return STEP_DISPLAY_CONFIG[step]?.label || step;
}

/**
 * 获取步骤的显示描述
 */
export function getStepDescription(step: string | null): string {
  if (!step) return 'Preparing your roadmap...';
  return STEP_DISPLAY_CONFIG[step]?.description || 'Preparing your roadmap...';
}

