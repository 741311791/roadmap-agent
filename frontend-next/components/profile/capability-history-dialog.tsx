'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { CapabilityAnalysisReport } from './capability-analysis-report';
import type { CapabilityAnalysisResult } from '@/types/assessment';
import { Clock } from 'lucide-react';
import { format } from 'date-fns';
import { enUS } from 'date-fns/locale';

interface CapabilityHistoryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  technology: string;
  proficiency: string;
  capabilityAnalysis: CapabilityAnalysisResult & { analyzed_at: string };
}

export function CapabilityHistoryDialog({
  open,
  onOpenChange,
  technology,
  proficiency,
  capabilityAnalysis,
}: CapabilityHistoryDialogProps) {
  // 格式化时间
  const formattedDate = format(
    new Date(capabilityAnalysis.analyzed_at),
    'MMM dd, yyyy HH:mm',
    { locale: enUS }
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-2xl font-serif space-y-2">
            <div>{technology} - {proficiency} Capability Analysis</div>
            <div className="flex items-center gap-2 text-sm font-normal text-muted-foreground">
              <Clock className="w-4 h-4" />
              <span>Analyzed at: {formattedDate}</span>
            </div>
          </DialogTitle>
        </DialogHeader>

        <CapabilityAnalysisReport
          result={capabilityAnalysis}
          onClose={() => onOpenChange(false)}
          showActions={true}
        />
      </DialogContent>
    </Dialog>
  );
}

