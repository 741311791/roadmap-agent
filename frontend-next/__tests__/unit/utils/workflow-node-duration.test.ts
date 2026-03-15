import { collectWorkflowNodeDurations } from '@/lib/utils/workflow-node-duration';
import type { ExecutionLog } from '@/types/content-generation';

function createLog(overrides: Partial<ExecutionLog>): ExecutionLog {
  return {
    id: crypto.randomUUID(),
    task_id: 'task-1',
    roadmap_id: 'roadmap-1',
    concept_id: null,
    level: 'info',
    category: 'workflow',
    step: 'intent_analysis',
    agent_name: null,
    message: 'test',
    details: null,
    duration_ms: 100,
    created_at: '2026-03-15T00:00:00.000Z',
    ...overrides,
  };
}

describe('workflow-node-duration', () => {
  it('应该读取课程设计节点最近一次 workflow 完成耗时', () => {
    const durations = collectWorkflowNodeDurations([
      createLog({
        step: 'curriculum_design',
        duration_ms: 12_345,
        created_at: '2026-03-15T00:00:01.000Z',
        details: { log_type: 'workflow_node_complete' },
      }),
    ]);

    expect(durations.design).toMatchObject({
      totalMs: 12_345,
      latestMs: 12_345,
      count: 1,
    });
  });

  it('应该优先读取内容阶段 workflow 汇总耗时', () => {
    const durations = collectWorkflowNodeDurations([
      createLog({
        category: 'workflow',
        step: 'content_generation',
        duration_ms: 15_200,
        created_at: '2026-03-15T00:00:04.000Z',
        details: { log_type: 'content_generation_complete' },
      }),
      createLog({
        category: 'content',
        step: 'content_generation',
        concept_id: 'concept-1',
        duration_ms: 3_000,
        created_at: '2026-03-15T00:00:02.000Z',
      }),
    ]);

    expect(durations.content).toMatchObject({
      totalMs: 15_200,
      latestMs: 15_200,
      count: 1,
      lastUpdatedAt: '2026-03-15T00:00:04.000Z',
    });
  });

  it('应该在缺少汇总日志时回退为所有 content 日志总和', () => {
    const durations = collectWorkflowNodeDurations([
      createLog({
        category: 'content',
        step: 'content_generation',
        concept_id: 'concept-1',
        duration_ms: 3_000,
        created_at: '2026-03-15T00:00:02.000Z',
      }),
      createLog({
        category: 'content',
        step: 'content_generation',
        concept_id: 'concept-2',
        duration_ms: 4_500,
        created_at: '2026-03-15T00:00:03.000Z',
      }),
    ]);

    expect(durations.content).toMatchObject({
      totalMs: 7_500,
      latestMs: 7_500,
      count: 2,
      lastUpdatedAt: '2026-03-15T00:00:03.000Z',
    });
  });
});
