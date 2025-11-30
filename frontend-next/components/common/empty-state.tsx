import { cn } from '@/lib/utils';
import { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
  compact?: boolean;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center',
        compact ? 'py-8 px-4' : 'py-16 px-6',
        className
      )}
    >
      {Icon && (
        <div
          className={cn(
            'rounded-full bg-sage-100 flex items-center justify-center mb-4',
            compact ? 'w-12 h-12' : 'w-16 h-16'
          )}
        >
          <Icon
            className={cn(
              'text-sage-600',
              compact ? 'w-6 h-6' : 'w-8 h-8'
            )}
          />
        </div>
      )}
      <h3
        className={cn(
          'font-serif font-semibold text-foreground',
          compact ? 'text-lg' : 'text-xl'
        )}
      >
        {title}
      </h3>
      {description && (
        <p
          className={cn(
            'text-muted-foreground mt-2 max-w-sm',
            compact ? 'text-sm' : 'text-base'
          )}
        >
          {description}
        </p>
      )}
      {action && (
        <Button
          onClick={action.onClick}
          variant="sage"
          className="mt-4"
          size={compact ? 'sm' : 'default'}
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}

