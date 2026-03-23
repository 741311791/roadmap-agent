"use client";

import { useMemo, useState } from "react";
import { History, Loader2, MessageSquare, Trash2 } from "lucide-react";

import { useTranslations } from "next-intl";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { MentorThreadRecord } from "@/components/mentor/types";

interface MentorThreadHistoryProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  threads: MentorThreadRecord[];
  currentThreadId: string | null;
  onSwitchThread: (threadId: string) => void;
  onDeleteThread: (threadId: string) => Promise<void> | void;
  deletingThreadId: string | null;
  historyDescription: string;
}

/**
 * formatRelativeTime - 将时间戳格式化为简短可读文本
 */
function formatRelativeTime(timestamp: number): string {
  const diffMinutes = Math.max(1, Math.round((Date.now() - timestamp) / 1000 / 60));

  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }

  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

/**
 * getThreadStatusLabel - 将线程状态转换为展示文案
 */
function getThreadStatusLabel(thread: MentorThreadRecord, t: (key: string) => string): string {
  if (thread.status === "streaming") {
    return t("statusSyncing");
  }

  if (thread.status === "error") {
    return t("statusError");
  }

  return thread.remoteSessionId ? t("statusSynced") : t("statusLocal");
}

/**
 * MentorThreadHistory - 历史会话抽屉
 */
export function MentorThreadHistory({
  open,
  onOpenChange,
  threads,
  currentThreadId,
  onSwitchThread,
  onDeleteThread,
  deletingThreadId,
  historyDescription,
}: MentorThreadHistoryProps) {
  const t = useTranslations("mentor");
  const [threadIdPendingDelete, setThreadIdPendingDelete] = useState<string | null>(null);
  const pendingDeleteThread = useMemo(
    () => threads.find((thread) => thread.id === threadIdPendingDelete) ?? null,
    [threadIdPendingDelete, threads]
  );

  /**
   * handleDeleteConfirm - 确认删除会话
   */
  const handleDeleteConfirm = async () => {
    if (!pendingDeleteThread) {
      return;
    }

    await onDeleteThread(pendingDeleteThread.id);
    setThreadIdPendingDelete(null);
  };

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent
          side="right"
          className="w-full max-w-[340px] border-l border-border/60 bg-background/95 px-0 backdrop-blur"
        >
          <SheetHeader className="border-b border-border/60 px-5 pb-4">
            <div className="flex items-center gap-2 text-slate-700">
              <History className="h-4 w-4" />
              <SheetTitle>{t("threadHistory")}</SheetTitle>
            </div>
            <SheetDescription>{historyDescription}</SheetDescription>
          </SheetHeader>

          <div className="flex h-full flex-col overflow-hidden px-3 pb-4 pt-4">
            <div className="space-y-2 overflow-y-auto pr-2">
              {threads.map((thread) => {
                const isActive = thread.id === currentThreadId;
                const isDeleting = deletingThreadId === thread.id;
                const hasPendingDeletion = Boolean(deletingThreadId);
                const messageCount = thread.messages.length > 0 ? thread.messages.length : thread.messageCount ?? 0;

                return (
                  <div
                    key={thread.id}
                    className={cn(
                      "flex items-start gap-2 rounded-2xl border px-2 py-2",
                      isActive
                        ? "border-sage-600 bg-sage-50 text-sage-900"
                        : "border-border/60 bg-background text-slate-900"
                    )}
                  >
                    <button
                      type="button"
                      disabled={hasPendingDeletion}
                      onClick={() => {
                        onSwitchThread(thread.id);
                        onOpenChange(false);
                      }}
                      className="flex min-w-0 flex-1 text-left disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      <div className="flex w-full flex-col gap-2 rounded-xl px-2 py-1 hover:bg-slate-50/80">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-sm font-medium">{thread.title}</div>
                            <div
                              className={cn(
                                "mt-1 flex items-center gap-1 text-xs",
                                isActive ? "text-sage-700" : "text-muted-foreground"
                              )}
                            >
                              <MessageSquare className="h-3.5 w-3.5" />
                              <span>{messageCount} {t("messages")}</span>
                            </div>
                            <div
                              className={cn(
                                "mt-2 inline-flex rounded-full px-2 py-1 text-[10px] font-medium uppercase tracking-wide",
                                thread.status === "error"
                                  ? "bg-red-100 text-red-700"
                                  : thread.status === "streaming"
                                    ? "bg-amber-100 text-amber-700"
                                    : thread.remoteSessionId
                                      ? "bg-sky-100 text-sky-700"
                                      : "bg-slate-100 text-slate-600"
                              )}
                            >
                              {getThreadStatusLabel(thread, t)}
                            </div>
                          </div>

                          {isActive ? (
                            <div className="rounded-full bg-sage-200 px-2 py-1 text-[10px] font-medium uppercase tracking-wide text-sage-800">
                              {t("current")}
                            </div>
                          ) : null}
                        </div>

                        <div
                          className={cn(
                            "flex items-center justify-between text-xs",
                            isActive ? "text-sage-700" : "text-muted-foreground"
                          )}
                        >
                          <span>{thread.chapterContext.conceptName ?? t("noChapter")}</span>
                          <span>{formatRelativeTime(thread.updatedAt)}</span>
                        </div>
                      </div>
                    </button>

                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      disabled={thread.status === "streaming" || hasPendingDeletion}
                      onClick={() => setThreadIdPendingDelete(thread.id)}
                      className="mt-1 h-8 w-8 shrink-0 rounded-full text-muted-foreground hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
                      title={isDeleting ? t("deleteThreadLoading") : t("deleteThread")}
                    >
                      {isDeleting ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                );
              })}
            </div>
          </div>
        </SheetContent>
      </Sheet>

      <AlertDialog open={Boolean(pendingDeleteThread)} onOpenChange={(openState) => {
        if (!openState && !deletingThreadId) {
          setThreadIdPendingDelete(null);
        }
      }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("deleteThreadConfirmTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("deleteThreadConfirmDesc")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={Boolean(deletingThreadId)}>
              {t("deleteThreadCancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              disabled={Boolean(deletingThreadId)}
              className="bg-red-600 text-white hover:bg-red-700"
              onClick={() => {
                void handleDeleteConfirm();
              }}
            >
              {deletingThreadId ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t("deleteThreadLoading")}
                </span>
              ) : (
                t("deleteThreadAction")
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
