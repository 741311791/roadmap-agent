'use client';

interface ConceptTutorialToolCardProps {
  result: Record<string, unknown>;
}

/**
 * 概念教程工具结果卡片。
 */
export function ConceptTutorialToolCard({ result }: ConceptTutorialToolCardProps) {
  const title = typeof result.title === 'string' ? result.title : null;
  const summary = typeof result.summary === 'string' ? result.summary : null;
  const duration =
    typeof result.estimated_completion_time === 'number'
      ? result.estimated_completion_time
      : null;
  const message = typeof result.message === 'string' ? result.message : null;

  return (
    <div className="space-y-1 text-xs text-muted-foreground">
      {title && <p className="font-medium text-foreground">{title}</p>}
      {summary && <p>{summary}</p>}
      {duration !== null && <p>预估学习时长：{duration} 分钟</p>}
      {message && <p>{message}</p>}
    </div>
  );
}
