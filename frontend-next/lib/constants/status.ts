/**
 * 任务状态枚举
 * 与后端 API 完全对齐
 */
export enum TaskStatus {
  PENDING = 'pending',                      // 待处理
  PROCESSING = 'processing',                // 处理中
  HUMAN_REVIEW_PENDING = 'human_review_pending',  // 等待人工审核
  COMPLETED = 'completed',                  // 已完成
  PARTIAL_FAILURE = 'partial_failure',      // 部分失败
  FAILED = 'failed'                         // 失败
}

/**
 * 内容状态枚举
 */
export enum ContentStatus {
  PENDING = 'pending',                      // 待生成
  GENERATING = 'generating',                // 生成中（前端临时状态）
  COMPLETED = 'completed',                  // 已完成
  FAILED = 'failed'                         // 失败
}

/**
 * 工作流步骤枚举
 */
export enum WorkflowStep {
  INIT = 'init',                            // 初始化
  QUEUED = 'queued',                        // 已入队
  STARTING = 'starting',                    // 启动中
  INTENT_ANALYSIS = 'intent_analysis',      // 需求分析
  CURRICULUM_DESIGN = 'curriculum_design',  // 课程设计
  STRUCTURE_VALIDATION = 'structure_validation',  // 结构验证
  HUMAN_REVIEW = 'human_review',            // 人工审核
  ROADMAP_EDIT = 'roadmap_edit',            // 路线图修正
  CONTENT_GENERATION = 'content_generation',// 内容生成
  TUTORIAL_GENERATION = 'tutorial_generation',    // 教程生成
  RESOURCE_RECOMMENDATION = 'resource_recommendation',  // 资源推荐
  QUIZ_GENERATION = 'quiz_generation',      // 测验生成
  FINALIZING = 'finalizing',                // 收尾中
  COMPLETED = 'completed',                  // 已完成
  FAILED = 'failed'                         // 失败
}

/**
 * 任务状态显示配置
 */
export const TASK_STATUS_CONFIG: Record<TaskStatus, { label: string; color: string }> = {
  [TaskStatus.PENDING]: { label: '排队中', color: 'gray' },
  [TaskStatus.PROCESSING]: { label: '处理中', color: 'blue' },
  [TaskStatus.HUMAN_REVIEW_PENDING]: { label: '等待审核', color: 'yellow' },
  [TaskStatus.COMPLETED]: { label: '已完成', color: 'green' },
  [TaskStatus.PARTIAL_FAILURE]: { label: '部分失败', color: 'orange' },
  [TaskStatus.FAILED]: { label: '失败', color: 'red' },
};

/**
 * 内容状态显示配置
 */
export const CONTENT_STATUS_CONFIG: Record<ContentStatus, { label: string; color: string }> = {
  [ContentStatus.PENDING]: { label: '待生成', color: 'gray' },
  [ContentStatus.GENERATING]: { label: '生成中', color: 'blue' },
  [ContentStatus.COMPLETED]: { label: '已完成', color: 'green' },
  [ContentStatus.FAILED]: { label: '失败', color: 'red' },
};

/**
 * 工作流步骤显示配置
 */
export const WORKFLOW_STEP_CONFIG: Record<WorkflowStep, { label: string; description: string }> = {
  [WorkflowStep.INIT]: { label: '初始化', description: '准备开始...' },
  [WorkflowStep.QUEUED]: { label: '已入队', description: '等待处理...' },
  [WorkflowStep.STARTING]: { label: '启动中', description: '正在启动任务...' },
  [WorkflowStep.INTENT_ANALYSIS]: { label: '需求分析', description: '正在分析您的学习需求...' },
  [WorkflowStep.CURRICULUM_DESIGN]: { label: '课程设计', description: '正在设计学习路线图...' },
  [WorkflowStep.STRUCTURE_VALIDATION]: { label: '结构验证', description: '正在验证路线图结构...' },
  [WorkflowStep.HUMAN_REVIEW]: { label: '人工审核', description: '等待您的审核...' },
  [WorkflowStep.ROADMAP_EDIT]: { label: '路线图修正', description: '正在根据反馈修正路线图...' },
  [WorkflowStep.CONTENT_GENERATION]: { label: '内容生成', description: '正在生成学习内容...' },
  [WorkflowStep.TUTORIAL_GENERATION]: { label: '教程生成', description: '正在生成教程...' },
  [WorkflowStep.RESOURCE_RECOMMENDATION]: { label: '资源推荐', description: '正在推荐学习资源...' },
  [WorkflowStep.QUIZ_GENERATION]: { label: '测验生成', description: '正在生成测验题目...' },
  [WorkflowStep.FINALIZING]: { label: '收尾中', description: '即将完成...' },
  [WorkflowStep.COMPLETED]: { label: '已完成', description: '路线图已生成完成！' },
  [WorkflowStep.FAILED]: { label: '失败', description: '生成失败，请重试' },
};
