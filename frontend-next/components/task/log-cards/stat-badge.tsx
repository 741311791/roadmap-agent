/**
 * StatBadge - 统计数据徽章组件
 * 
 * 用于展示统计数据（label + value）
 */
import { cn } from '@/lib/utils';

interface StatBadgeProps {
  label: string;
  value: string | number;
  className?: string;
}

export function StatBadge({ label, value, className }: StatBadgeProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center p-3 rounded-lg bg-background border',
        className
      )}
    >
      <div className="text-2xl font-bold text-foreground">{value}</div>
      <div className="text-xs text-muted-foreground mt-1">{label}</div>
    </div>
  );
}





