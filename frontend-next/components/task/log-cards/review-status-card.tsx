/**
 * ReviewStatusCard - 人工审核状态卡片
 * 
 * 展示审核等待、批准或修改请求的状态
 */
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Pause, CheckCircle2, Edit3, ExternalLink } from 'lucide-react';
import Link from 'next/link';

interface ReviewStatusCardProps {
  logType: 'review_waiting' | 'review_approved' | 'review_modification_requested';
  details: any;
}

export function ReviewStatusCard({ logType, details }: ReviewStatusCardProps) {
  // 等待审核
  if (logType === 'review_waiting') {
    return (
      <Card className="border-amber-200 bg-amber-50/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Pause className="w-4 h-4 text-amber-600" />
            Awaiting Your Review
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-foreground">
            Roadmap structure is ready. Please review and confirm to proceed with content generation.
          </p>

          {/* 路线图摘要 */}
          {details.summary && (
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="p-2 bg-white rounded border">
                <div className="text-muted-foreground">Concepts</div>
                <div className="font-semibold text-foreground">
                  {details.summary.total_concepts}
                </div>
              </div>
              <div className="p-2 bg-white rounded border">
                <div className="text-muted-foreground">Hours</div>
                <div className="font-semibold text-foreground">
                  {details.summary.total_hours}
                </div>
              </div>
              <div className="p-2 bg-white rounded border">
                <div className="text-muted-foreground">Weeks</div>
                <div className="font-semibold text-foreground">
                  {details.summary.estimated_weeks}
                </div>
              </div>
            </div>
          )}

          {/* 查看路线图按钮 */}
          {details.roadmap_url && (
            <Link href={details.roadmap_url} target="_blank">
              <Button variant="outline" size="sm" className="w-full">
                <ExternalLink className="w-3 h-3 mr-2" />
                View Roadmap Preview
              </Button>
            </Link>
          )}
        </CardContent>
      </Card>
    );
  }

  // 审核通过
  if (logType === 'review_approved') {
    return (
      <Card className="border-sage-200 bg-sage-50/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-sage-600" />
            Roadmap Approved
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-foreground">
            You approved the roadmap structure. Content generation will now begin.
          </p>
          {details.user_feedback && (
            <div className="mt-2 p-2 bg-white rounded border text-xs">
              <div className="text-muted-foreground mb-1">Your feedback:</div>
              <p className="text-foreground italic">"{details.user_feedback}"</p>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // 请求修改
  if (logType === 'review_modification_requested') {
    return (
      <Card className="border-sage-200 bg-sage-50/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Edit3 className="w-4 h-4 text-sage-600" />
            Modification Requested
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <p className="text-foreground">
            You requested modifications to the roadmap structure.
          </p>
          {details.user_feedback && (
            <div className="p-2 bg-white rounded border text-xs">
              <div className="text-muted-foreground mb-1">Your feedback:</div>
              <p className="text-foreground italic">"{details.user_feedback}"</p>
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            AI will update the roadmap based on your feedback...
          </p>
        </CardContent>
      </Card>
    );
  }

  return null;
}

