import type { ExecutionLog } from '@/types/content-generation';

export type WorkflowNodeId =
  | 'analysis'
  | 'design'
  | 'validate'
  | 'review'
  | 'content'
  | 'plan1'
  | 'edit1'
  | 'plan2'
  | 'edit2';

export interface WorkflowNodeDurationStat {
  totalMs: number;
  latestMs: number;
  count: number;
  lastUpdatedAt?: string;
}

export type WorkflowNodeDurationMap = Partial<Record<WorkflowNodeId, WorkflowNodeDurationStat>>;

interface WorkflowDurationLogRule {
  nodeId: WorkflowNodeId;
  matches: (log: ExecutionLog) => boolean;
  aggregate?: (logs: ExecutionLog[]) => WorkflowNodeDurationStat | null;
}

function sortLogsByCreatedAtDesc(logs: ExecutionLog[]): ExecutionLog[] {
  return [...logs].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
}

function collectLatestDuration(logs: ExecutionLog[]): WorkflowNodeDurationStat | null {
  const latestLog = sortLogsByCreatedAtDesc(logs)[0];

  if (!latestLog || typeof latestLog.duration_ms !== 'number') {
    return null;
  }

  return {
    totalMs: latestLog.duration_ms,
    latestMs: latestLog.duration_ms,
    count: 1,
    lastUpdatedAt: latestLog.created_at,
  };
}

function collectSummedDurations(logs: ExecutionLog[]): WorkflowNodeDurationStat | null {
  if (logs.length === 0) {
    return null;
  }

  const sortedLogs = sortLogsByCreatedAtDesc(logs);
  const totalMs = logs.reduce((sum, log) => sum + (typeof log.duration_ms === 'number' ? log.duration_ms : 0), 0);

  return {
    totalMs,
    latestMs: totalMs,
    count: logs.length,
    lastUpdatedAt: sortedLogs[0]?.created_at,
  };
}

function collectContentNodeDuration(logs: ExecutionLog[]): WorkflowNodeDurationStat | null {
  const workflowSummaryLogs = logs.filter(
    (log) =>
      log.category === 'workflow' &&
      log.step === 'content_generation' &&
      (
        log.details?.log_type === 'content_generation_complete' ||
        log.details?.log_type === 'content_generation_failed'
      )
  );

  // 优先使用后端落库的“内容阶段总耗时”日志。
  // 这条日志代表整个内容生成阶段的真实墙钟时间，比逐个 Concept 求和更符合用户感知。
  const workflowSummaryDuration = collectLatestDuration(workflowSummaryLogs);
  if (workflowSummaryDuration) {
    return workflowSummaryDuration;
  }

  const conceptContentLogs = logs.filter((log) => log.category === 'content');
  return collectSummedDurations(conceptContentLogs);
}

const WORKFLOW_DURATION_LOG_RULES: WorkflowDurationLogRule[] = [
  {
    nodeId: 'analysis',
    matches: (log) =>
      log.category === 'workflow' &&
      log.step === 'intent_analysis' &&
      log.details?.log_type === 'workflow_node_complete',
  },
  {
    nodeId: 'design',
    matches: (log) =>
      log.category === 'workflow' &&
      log.step === 'curriculum_design' &&
      log.details?.log_type === 'workflow_node_complete',
  },
  {
    nodeId: 'validate',
    matches: (log) =>
      log.category === 'workflow' &&
      log.step === 'structure_validation' &&
      log.details?.log_type === 'workflow_node_complete',
  },
  {
    nodeId: 'plan1',
    matches: (log) =>
      log.category === 'workflow' &&
      log.step === 'edit_plan_analysis' &&
      log.details?.log_type === 'workflow_node_complete' &&
      log.details?.edit_source === 'validation_failed',
  },
  {
    nodeId: 'edit1',
    matches: (log) =>
      log.category === 'workflow' &&
      log.step === 'roadmap_edit' &&
      log.details?.log_type === 'workflow_node_complete' &&
      log.details?.edit_source === 'validation_failed',
  },
  {
    nodeId: 'plan2',
    matches: (log) =>
      log.category === 'workflow' &&
      log.step === 'edit_plan_analysis' &&
      log.details?.log_type === 'workflow_node_complete' &&
      log.details?.edit_source === 'human_review',
  },
  {
    nodeId: 'edit2',
    matches: (log) =>
      log.category === 'workflow' &&
      log.step === 'roadmap_edit' &&
      log.details?.log_type === 'workflow_node_complete' &&
      log.details?.edit_source === 'human_review',
  },
  {
    nodeId: 'content',
    matches: (log) =>
      log.category === 'content' ||
      (
        log.category === 'workflow' &&
        log.step === 'content_generation' &&
        (
          log.details?.log_type === 'content_generation_complete' ||
          log.details?.log_type === 'content_generation_failed'
        )
      ),
    aggregate: collectContentNodeDuration,
  },
];

/**
 * 从执行日志中提取每个拓扑节点最近一次完成耗时。
 *
 * 规则：
 * - 只读取 `workflow` 分类中的节点完成日志。
 * - 每个节点仅保留最近一次完成记录，对齐拓扑图和详情面板的展示语义。
 */
export function collectWorkflowNodeDurations(logs: ExecutionLog[]): WorkflowNodeDurationMap {
  return WORKFLOW_DURATION_LOG_RULES.reduce<WorkflowNodeDurationMap>((accumulator, rule) => {
    const matchedLogs = logs
      .filter((log) => typeof log.duration_ms === 'number' && log.duration_ms >= 0)
      .filter(rule.matches);

    const durationStat = rule.aggregate
      ? rule.aggregate(matchedLogs)
      : collectLatestDuration(matchedLogs);

    if (!durationStat) {
      return accumulator;
    }

    accumulator[rule.nodeId] = durationStat;

    return accumulator;
  }, {});
}

/**
 * 格式化耗时显示。
 */
export function formatWorkflowDuration(durationMs: number): string {
  if (durationMs < 1000) {
    return `${Math.round(durationMs)}ms`;
  }

  if (durationMs < 10_000) {
    return `${(durationMs / 1000).toFixed(1)}s`;
  }

  if (durationMs < 60_000) {
    return `${Math.round(durationMs / 1000)}s`;
  }

  const minutes = Math.floor(durationMs / 60_000);
  const seconds = Math.round((durationMs % 60_000) / 1000);
  return seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`;
}
