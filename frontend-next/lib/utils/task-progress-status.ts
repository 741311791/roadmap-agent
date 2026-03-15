import { WorkflowStep } from '@/lib/constants/workflow-steps';
import { TaskStatus } from '@/types/generated/constants';
import type { TaskStatusType } from '@/types/generated/constants';

/**
 * 从 progress 事件中提取可安全写入任务详情页的任务总状态。
 *
 * 设计原因：
 * - 后端 progress 事件里的 status 可能表示“节点完成”，而不是“整个任务完成”；
 * - 例如 intent_analysis/curriculum_design 节点结束时，会发送 status="completed"；
 * - 如果前端直接把它写入 task.status，会导致任务仍在 processing 时 UI 提前显示“已完成”。
 *
 * Args:
 *   step: progress 事件对应的步骤
 *   status: progress 事件携带的状态
 *
 * Returns:
 *   可以安全写入任务总状态的值；若该事件只代表节点状态，则返回 undefined
 */
export function getTaskStatusFromProgressEvent(
  step: string | null | undefined,
  status: string | null | undefined
): TaskStatusType | undefined {
  if (!status) {
    return undefined;
  }

  switch (status) {
    case TaskStatus.PENDING:
    case TaskStatus.PROCESSING:
    case TaskStatus.HUMAN_REVIEW:
    case TaskStatus.PARTIAL_FAILURE:
    case TaskStatus.FAILED:
    case TaskStatus.CANCELLED:
      return status;
    case TaskStatus.COMPLETED:
      return step === WorkflowStep.COMPLETED ? TaskStatus.COMPLETED : undefined;
    default:
      return undefined;
  }
}
