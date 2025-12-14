/**
 * TaskCompletedCard - 任务完成卡片
 * 
 * 展示任务完成的最终结果和后续操作
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { PartyPopper, ExternalLink, TrendingUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import Link from 'next/link';

interface TaskCompletedCardProps {
  details: {
    roadmap_id: string;
    roadmap_url: string;
    statistics?: {
      tutorials_generated: number;
      failed_concepts: number;
    };
    next_actions?: Array<{
      action: string;
      label: string;
      url: string;
      primary?: boolean;
    }>;
  };
}

export function TaskCompletedCard({ details }: TaskCompletedCardProps) {
  return (
    <Card className="border-sage-300 bg-gradient-to-br from-sage-50 to-emerald-50">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <PartyPopper className="w-5 h-5 text-sage-600" />
          Roadmap Ready!
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-foreground">
          🎉 Your personalized learning roadmap has been generated successfully!
        </p>

        {/* 统计信息 */}
        {details.statistics && (
          <div className="grid grid-cols-2 gap-2">
            <div className="p-3 bg-white rounded-lg border border-sage-200">
              <div className="text-2xl font-bold text-sage-600">
                {details.statistics.tutorials_generated}
              </div>
              <div className="text-xs text-muted-foreground">Tutorials Generated</div>
            </div>
            {details.statistics.failed_concepts > 0 && (
              <div className="p-3 bg-white rounded-lg border border-amber-200">
                <div className="text-2xl font-bold text-amber-600">
                  {details.statistics.failed_concepts}
                </div>
                <div className="text-xs text-muted-foreground">Partial Failures</div>
              </div>
            )}
          </div>
        )}

        {/* 下一步操作 */}
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground font-medium">Next Steps</div>

          {details.next_actions && details.next_actions.length > 0 ? (
            details.next_actions.map((action, index) => (
              <Link key={index} href={action.url}>
                <Button
                  variant={action.primary ? 'default' : 'outline'}
                  size="sm"
                  className={cn(
                    'w-full',
                    action.primary && 'bg-sage-600 hover:bg-sage-700'
                  )}
                >
                  <ExternalLink className="w-3 h-3 mr-2" />
                  {action.label}
                </Button>
              </Link>
            ))
          ) : (
            <Link href={details.roadmap_url}>
              <Button 
                size="sm" 
                className="w-full bg-sage-600 hover:bg-sage-700"
              >
                <TrendingUp className="w-3 h-3 mr-2" />
                Start Learning
              </Button>
            </Link>
          )}
        </div>

        {/* Roadmap ID */}
        <div className="text-[10px] text-muted-foreground font-mono">
          Roadmap ID: {details.roadmap_id}
        </div>
      </CardContent>
    </Card>
  );
}

