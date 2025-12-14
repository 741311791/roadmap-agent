/**
 * LogCardRouter - 日志卡片路由器
 * 
 * 根据日志类型渲染对应的卡片组件
 */
import { IntentAnalysisCard } from './intent-analysis-card';
import { CurriculumDesignCard } from './curriculum-design-card';
import { ValidationResultCard } from './validation-result-card';
import { ReviewStatusCard } from './review-status-card';
import { ContentProgressCard } from './content-progress-card';
import { TaskCompletedCard } from './task-completed-card';

interface ExecutionLog {
  id: string;
  task_id: string;
  roadmap_id?: string;
  concept_id?: string;
  level: string;
  category: string;
  step: string | null;
  agent_name?: string | null;
  message: string;
  details?: any;
  duration_ms?: number | null;
  created_at: string;
}

interface LogCardRouterProps {
  log: ExecutionLog;
}

/**
 * 根据日志类型渲染对应的卡片组件
 */
export function LogCardRouter({ log }: LogCardRouterProps) {
  const logType = log.details?.log_type;

  // 如果没有log_type，返回null（使用默认的日志展示）
  if (!logType) {
    return null;
  }

  // Intent Analysis 输出
  if (logType === 'intent_analysis_output') {
    return <IntentAnalysisCard outputSummary={log.details.output_summary} />;
  }

  // Curriculum Design 输出
  if (logType === 'curriculum_design_output') {
    return <CurriculumDesignCard outputSummary={log.details.output_summary} />;
  }

  // Validation 结果
  if (
    logType === 'validation_passed' ||
    logType === 'validation_failed' ||
    logType === 'validation_skipped'
  ) {
    return <ValidationResultCard logType={logType} details={log.details} />;
  }

  // Review 状态
  if (
    logType === 'review_waiting' ||
    logType === 'review_approved' ||
    logType === 'review_modification_requested'
  ) {
    return <ReviewStatusCard logType={logType} details={log.details} />;
  }

  // Content Generation 进度
  if (
    logType === 'content_generation_start' ||
    logType === 'concept_completed' ||
    logType === 'content_generation_failed'
  ) {
    return (
      <ContentProgressCard logType={logType} details={log.details} message={log.message} />
    );
  }

  // Task Completed
  if (logType === 'task_completed') {
    return <TaskCompletedCard details={log.details} />;
  }

  // 未知类型，返回null（使用默认展示）
  return null;
}

// 导出所有卡片组件
export { IntentAnalysisCard } from './intent-analysis-card';
export { CurriculumDesignCard } from './curriculum-design-card';
export { ValidationResultCard } from './validation-result-card';
export { ReviewStatusCard } from './review-status-card';
export { ContentProgressCard } from './content-progress-card';
export { TaskCompletedCard } from './task-completed-card';
export { StatBadge } from './stat-badge';

