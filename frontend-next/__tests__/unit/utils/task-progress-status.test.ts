/**
 * progress 事件任务状态映射单元测试
 */

import { WorkflowStep } from '@/lib/constants/workflow-steps';
import { TaskStatus } from '@/types/generated/constants';
import { getTaskStatusFromProgressEvent } from '@/lib/utils/task-progress-status';

describe('task-progress-status', () => {
  it('应该忽略中间节点的 completed 事件，避免误判整个任务已完成', () => {
    expect(
      getTaskStatusFromProgressEvent(WorkflowStep.CURRICULUM_DESIGN, TaskStatus.COMPLETED)
    ).toBeUndefined();
  });

  it('应该保留 processing 状态事件', () => {
    expect(
      getTaskStatusFromProgressEvent(WorkflowStep.CURRICULUM_DESIGN, TaskStatus.PROCESSING)
    ).toBe(TaskStatus.PROCESSING);
  });

  it('应该允许真正的 completed 终态事件更新任务状态', () => {
    expect(
      getTaskStatusFromProgressEvent(WorkflowStep.COMPLETED, TaskStatus.COMPLETED)
    ).toBe(TaskStatus.COMPLETED);
  });

  it('应该允许 partial_failure 终态事件更新任务状态', () => {
    expect(
      getTaskStatusFromProgressEvent(WorkflowStep.CONTENT_GENERATION, TaskStatus.PARTIAL_FAILURE)
    ).toBe(TaskStatus.PARTIAL_FAILURE);
  });
});
