"use client";

import { BookOpenText, History, Plus, Send, Square } from "lucide-react";
import { ComposerPrimitive, useThread } from "@assistant-ui/react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { MentorToolbar } from "@/components/mentor/mentor-toolbar";
import type { MentorAgentType } from "@/components/mentor/types";

interface MentorComposerProps {
  threadId: string;
  chapterName?: string;
  agentType: MentorAgentType;
  modelId: string;
  onAgentChange: (agentType: MentorAgentType) => void;
  onModelChange: (modelId: string) => void;
  onNewThread: () => void;
  onOpenHistory: () => void;
}

/**
 * MentorComposer - 输入区与线程操作区
 */
export function MentorComposer({
  threadId,
  chapterName,
  agentType,
  modelId,
  onAgentChange,
  onModelChange,
  onNewThread,
  onOpenHistory,
}: MentorComposerProps) {
  const isRunning = useThread((state) => state.isRunning);
  const t = useTranslations("mentor");

  return (
    <div className="border-t border-border/60 bg-background/95 px-4 py-4 backdrop-blur">
      <ComposerPrimitive.Root
        key={threadId}
        className="rounded-xl border border-border/70 bg-background p-3 shadow-sm"
      >
        <div className="mb-3 flex items-center gap-2 text-xs text-muted-foreground">
          <BookOpenText className="h-3.5 w-3.5" />
          <span className="font-medium text-slate-700">{t("currentChapter")}</span>
          <span className="truncate rounded-full bg-muted px-2.5 py-1 text-foreground">
            {chapterName ?? t("noChapter")}
          </span>
        </div>

        <div className="flex flex-col gap-3">
          <ComposerPrimitive.Input
            submitMode="enter"
            placeholder={t("placeholder")}
            className={cn(
              "min-h-[60px] flex-1 resize-none border-0 bg-transparent px-1 py-1 text-sm leading-6 shadow-none outline-none",
              "placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-0"
            )}
          />

          <div className="flex items-center justify-between">
            <MentorToolbar
              agentType={agentType}
              modelId={modelId}
              onAgentChange={onAgentChange}
              onModelChange={onModelChange}
            />

            {isRunning ? (
              <ComposerPrimitive.Cancel asChild>
                <Button
                  type="button"
                  size="icon"
                  className="h-8 w-8 rounded-full bg-slate-900 text-white hover:bg-slate-800 shrink-0"
                >
                  <Square className="h-3.5 w-3.5 fill-current" />
                </Button>
              </ComposerPrimitive.Cancel>
            ) : (
              <ComposerPrimitive.Send asChild>
                <Button
                  type="submit"
                  size="icon"
                  className="h-8 w-8 rounded-full bg-slate-900 text-white hover:bg-slate-800 shrink-0"
                >
                  <Send className="h-3.5 w-3.5" />
                </Button>
              </ComposerPrimitive.Send>
            )}
          </div>
        </div>
      </ComposerPrimitive.Root>

      <div className="mt-3 flex items-center justify-between gap-3">
        <Button
          type="button"
          variant="ghost"
          onClick={onNewThread}
          className="h-9 rounded-full px-3 text-sm text-muted-foreground hover:bg-slate-100 hover:text-slate-900"
        >
          <Plus className="mr-1.5 h-4 w-4" />
          {t("newThread")}
        </Button>

        <Button
          type="button"
          variant="ghost"
          onClick={onOpenHistory}
          className="h-9 rounded-full px-3 text-sm text-muted-foreground hover:bg-slate-100 hover:text-slate-900"
        >
          <History className="mr-1.5 h-4 w-4" />
          {t("history")}
        </Button>
      </div>
    </div>
  );
}
