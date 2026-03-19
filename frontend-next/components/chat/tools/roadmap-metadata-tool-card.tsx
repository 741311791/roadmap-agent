'use client';

interface RoadmapMetadataToolCardProps {
  result: Record<string, unknown>;
}

/**
 * 路线图元数据工具结果卡片。
 */
export function RoadmapMetadataToolCard({ result }: RoadmapMetadataToolCardProps) {
  const title = typeof result.title === 'string' ? result.title : '未知路线图';
  const stagesCount =
    typeof result.stages_count === 'number' ? result.stages_count : null;
  const conceptsCount =
    typeof result.concepts_count === 'number' ? result.concepts_count : null;
  const message = typeof result.message === 'string' ? result.message : null;

  return (
    <div className="space-y-1 text-xs text-muted-foreground">
      <p className="font-medium text-foreground">{title}</p>
      {(stagesCount !== null || conceptsCount !== null) && (
        <p>
          阶段数：{stagesCount ?? '-'}，概念数：{conceptsCount ?? '-'}
        </p>
      )}
      {message && <p>{message}</p>}
    </div>
  );
}
