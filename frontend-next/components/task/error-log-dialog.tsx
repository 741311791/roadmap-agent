/**
 * ErrorLogDialog 组件
 * 
 * 用于显示任务错误日志的对话框，支持复制功能
 */
'use client';

import { useState } from 'react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { AlertCircle, Copy, Check } from 'lucide-react';

interface ErrorLogDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  taskTitle: string;
  errorMessage: string;
}

export function ErrorLogDialog({
  open,
  onOpenChange,
  taskTitle,
  errorMessage,
}: ErrorLogDialogProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(errorMessage);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent className="max-w-3xl">
        <AlertDialogHeader>
          <div className="flex items-center justify-between">
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertCircle className="h-5 w-5 text-red-600" />
              Error Log
            </AlertDialogTitle>
            <Button
              size="sm"
              variant="outline"
              onClick={handleCopy}
              className="gap-1.5"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  Copy
                </>
              )}
            </Button>
          </div>
          <AlertDialogDescription className="text-left">
            Task: <span className="font-medium text-foreground">{taskTitle}</span>
          </AlertDialogDescription>
        </AlertDialogHeader>

        <div className="rounded-md border border-border bg-muted/50 p-4">
          <pre className="text-xs text-foreground whitespace-pre-wrap break-words max-h-[400px] overflow-y-auto">
            {errorMessage}
          </pre>
        </div>

        <AlertDialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

