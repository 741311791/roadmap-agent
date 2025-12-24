/**
 * 日志分组和限制工具
 * 
 * 按执行阶段（step）对日志进行分组，并限制每个阶段的日志数量，
 * 确保每个阶段的日志都能完整显示，不会被某个阶段的大量日志占满限额。
 */

export interface ExecutionLog {
  id: string;
  task_id: string;
  level: 'debug' | 'info' | 'success' | 'warning' | 'error';
  category: string;
  step: string | null;
  agent_name: string | null;
  message: string;
  details: any;
  duration_ms: number | null;
  created_at: string;
}

/**
 * 按 step 分组日志，每个 step 最多保留指定数量的日志
 * 
 * @param logs - 原始日志列表
 * @param maxLogsPerStep - 每个 step 最多保留的日志数（默认 100）
 * @returns 处理后的日志列表（按时间排序）
 */
export function limitLogsByStep(
  logs: ExecutionLog[],
  maxLogsPerStep: number = 100
): ExecutionLog[] {
  // 按 step 分组
  const logsByStep = new Map<string, ExecutionLog[]>();
  
  for (const log of logs) {
    const step = log.step || 'unknown';
    if (!logsByStep.has(step)) {
      logsByStep.set(step, []);
    }
    logsByStep.get(step)!.push(log);
  }
  
  // 对每个 step 的日志进行排序（按创建时间），并限制数量
  const limitedLogs: ExecutionLog[] = [];
  
  for (const [step, stepLogs] of logsByStep.entries()) {
    // 按时间排序（最新的在前）
    const sortedLogs = stepLogs.sort((a, b) => {
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    
    // 取前 maxLogsPerStep 条
    const limitedStepLogs = sortedLogs.slice(0, maxLogsPerStep);
    limitedLogs.push(...limitedStepLogs);
    
    // 如果日志被截断，添加提示日志
    if (sortedLogs.length > maxLogsPerStep) {
      const truncatedCount = sortedLogs.length - maxLogsPerStep;
      console.info(
        `[LogGrouping] Step "${step}" has ${sortedLogs.length} logs, limited to ${maxLogsPerStep}. Truncated ${truncatedCount} logs.`
      );
    }
  }
  
  // 最终按时间排序（保持整体时间顺序）
  return limitedLogs.sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

/**
 * 获取日志统计信息（按 step 分组）
 * 
 * @param logs - 日志列表
 * @returns 每个 step 的日志数量统计
 */
export function getLogStatsByStep(logs: ExecutionLog[]): Record<string, number> {
  const stats: Record<string, number> = {};
  
  for (const log of logs) {
    const step = log.step || 'unknown';
    stats[step] = (stats[step] || 0) + 1;
  }
  
  return stats;
}

