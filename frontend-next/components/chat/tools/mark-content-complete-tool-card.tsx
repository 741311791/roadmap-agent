'use client';

interface MarkContentCompleteToolCardProps {
  result: Record<string, unknown>;
}

/**
 * 标记学习完成工具结果卡片。
 */
export function MarkContentCompleteToolCard({
  result,
}: MarkContentCompleteToolCardProps) {
  const conceptId =
    typeof result.concept_id === 'string' ? result.concept_id : null;
  const isCompleted =
    typeof result.is_completed === 'boolean' ? result.is_completed : null;
  const message = typeof result.message === 'string' ? result.message : null;

  return (
    <div className="space-y-1 text-xs text-muted-foreground">
      {conceptId && <p>概念：{conceptId}</p>}
      {isCompleted !== null && (
        <p>状态：{isCompleted ? '已标记完成' : '已取消完成'}</p>
      )}
      {message && <p>{message}</p>}
    </div>
  );
}
