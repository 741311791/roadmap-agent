'use client';

interface UserProfileToolCardProps {
  result: Record<string, unknown>;
}

/**
 * 用户画像工具结果卡片。
 */
export function UserProfileToolCard({ result }: UserProfileToolCardProps) {
  const currentRole =
    typeof result.current_role === 'string' ? result.current_role : null;
  const industry = typeof result.industry === 'string' ? result.industry : null;
  const weeklyHours =
    typeof result.weekly_commitment_hours === 'number'
      ? result.weekly_commitment_hours
      : null;
  const primaryLanguage =
    typeof result.primary_language === 'string' ? result.primary_language : null;

  return (
    <div className="space-y-1 text-xs text-muted-foreground">
      {currentRole && <p>当前角色：{currentRole}</p>}
      {industry && <p>行业：{industry}</p>}
      {weeklyHours !== null && <p>每周学习时长：{weeklyHours} 小时</p>}
      {primaryLanguage && <p>主要语言：{primaryLanguage}</p>}
    </div>
  );
}
