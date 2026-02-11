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
 * 工作流步骤枚举值（与后端WorkflowStep枚举完全对齐）
 * 
 * @see backend/app/models/constants.py::WorkflowStep
 * 
 * 核心步骤：
 * - 主路节点：INTENT_ANALYSIS → CURRICULUM_DESIGN → STRUCTURE_VALIDATION → HUMAN_REVIEW → CONTENT_GENERATION
 * - 共享编辑节点：EDIT_PLAN_ANALYSIS、ROADMAP_EDIT（由edit_source区分来源）
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
  
  // 共享编辑节点（由edit_source区分来源：validation_failed或human_review）
  EDIT_PLAN_ANALYSIS: 'edit_plan_analysis',
  ROADMAP_EDIT: 'roadmap_edit',
  
  // 内容生成阶段
  CONTENT_GENERATION_QUEUED: 'content_generation_queued',
  CONTENT_GENERATION: 'content_generation',
  
  // 完成阶段
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
];

/**
 * 共享编辑分支的步骤（validation失败或review拒绝都使用）
 * 通过edit_source区分来源：
 * - edit_source=validation_failed：validation分支
 * - edit_source=human_review：review分支
 */
export const SHARED_EDIT_STEPS: WorkflowStepValue[] = [
  WorkflowStep.EDIT_PLAN_ANALYSIS,
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
    WorkflowStep.EDIT_PLAN_ANALYSIS,
    WorkflowStep.ROADMAP_EDIT,
    WorkflowStep.HUMAN_REVIEW,
    WorkflowStep.CONTENT_GENERATION_QUEUED,
    WorkflowStep.CONTENT_GENERATION,
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
    WorkflowStep.EDIT_PLAN_ANALYSIS,
    WorkflowStep.ROADMAP_EDIT,
    WorkflowStep.HUMAN_REVIEW,
    WorkflowStep.CONTENT_GENERATION_QUEUED,
    WorkflowStep.CONTENT_GENERATION,
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
  [WorkflowStep.HUMAN_REVIEW]: { label: 'Human Review', description: 'Awaiting your review...' },
  [WorkflowStep.EDIT_PLAN_ANALYSIS]: { label: 'Edit Plan Analysis', description: 'Analyzing modification needs...' },
  [WorkflowStep.ROADMAP_EDIT]: { label: 'Roadmap Edit', description: 'Applying modifications...' },
  [WorkflowStep.CONTENT_GENERATION_QUEUED]: { label: 'Content Queued', description: 'Preparing content generation...' },
  [WorkflowStep.CONTENT_GENERATION]: { label: 'Content Generation', description: 'Generating learning content...' },
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

/**
 * 将后端步骤映射到前端显示步骤
 * 
 * 目的：合并中间步骤，避免UI快速闪烁
 * 原理：将多个内部步骤映射到同一个用户可见的步骤
 * 
 * @param backendStep 后端返回的步骤名称
 * @returns 前端应该显示的步骤名称
 */
export function mapToDisplayStep(backendStep: string | null): string | null {
  if (!backendStep) return null;
  
  // 内容生成阶段的所有子步骤都映射到 content_generation
  const contentGenerationSteps = [
    WorkflowStep.CONTENT_GENERATION_QUEUED,
    // 向后兼容：映射已废弃的步骤（旧数据可能仍然存在）
    'tutorial_generation',
    'resource_recommendation',
    'quiz_generation',
  ];
  
  if (contentGenerationSteps.includes(backendStep)) {
    return WorkflowStep.CONTENT_GENERATION;
  }
  
  // 初始化阶段的步骤都映射到 starting
  const initSteps = [
    WorkflowStep.INIT,
    WorkflowStep.QUEUED,
  ] as const;
  
  if (initSteps.includes(backendStep as any)) {
    return WorkflowStep.STARTING;
  }
  
  // 其他步骤保持原样
  return backendStep;
}

