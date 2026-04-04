"use client";

import { useCallback, useEffect, useMemo, useRef } from "react";
import { BookOpenText, History, Plus, Send, Square } from "lucide-react";
import { ComposerPrimitive, useThread } from "@assistant-ui/react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { MentorToolbar } from "@/components/mentor/mentor-toolbar";
import type {
  MentorAgentKind,
  MentorModelOption,
  MentorQaStyle,
  MentorQuickAction,
} from "@/components/mentor/types";

interface MentorComposerProps {
  className?: string;
  /** 为 true 时与上方 To-dos 连成一体：内层输入卡片取消顶圆角，避免衔接处露底 */
  isDockedWithTodosAbove?: boolean;
  threadId: string;
  chapterName?: string;
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  modelId: string;
  modelOptions: MentorModelOption[];
  isModelsLoading?: boolean;
  queuedAction: {
    nonce: string;
    action: MentorQuickAction;
  } | null;
  onQueuedActionConsumed: () => void;
  onQuickAction: (action: MentorQuickAction) => void;
  onAgentKindChange: (agentKind: MentorAgentKind) => void;
  onQaStyleChange: (qaStyle: MentorQaStyle) => void;
  onModelChange: (modelId: string) => void;
  onNewThread: () => void;
  onOpenHistory: () => void;
}

/**
 * setComposerInputValue - 通过原生事件驱动 assistant-ui 输入框
 */
function setComposerInputValue(
  element: HTMLTextAreaElement | HTMLInputElement,
  value: string
) {
  const prototype =
    element instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
  const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");

  descriptor?.set?.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.focus();
}

/**
 * MentorComposer - 输入区与线程操作区
 */
export function MentorComposer({
  className,
  isDockedWithTodosAbove = false,
  threadId,
  chapterName,
  agentKind,
  qaStyle,
  modelId,
  modelOptions,
  isModelsLoading = false,
  queuedAction,
  onQueuedActionConsumed,
  onQuickAction,
  onAgentKindChange,
  onQaStyleChange,
  onModelChange,
  onNewThread,
  onOpenHistory,
}: MentorComposerProps) {
  const isRunning = useThread((state) => state.isRunning);
  const t = useTranslations("mentor");
  const rootRef = useRef<HTMLDivElement | null>(null);

  /**
   * applyQueuedAction - 把快捷动作写入输入框，并在需要时自动发送
   */
  const applyQueuedAction = useCallback(
    (action: MentorQuickAction) => {
      const rootElement = rootRef.current;
      const composerInput = rootElement?.querySelector("textarea, input");

      if (
        !composerInput ||
        !(composerInput instanceof HTMLTextAreaElement || composerInput instanceof HTMLInputElement)
      ) {
        return;
      }

      setComposerInputValue(composerInput, action.prompt);

      if (!action.autoSend) {
        return;
      }

      window.setTimeout(() => {
        const submitButton = rootElement?.querySelector('button[type="submit"]');
        if (submitButton instanceof HTMLButtonElement) {
          submitButton.click();
        }
      }, 0);
    },
    []
  );

  useEffect(() => {
    if (!queuedAction) {
      return;
    }

    applyQueuedAction(queuedAction.action);
    onQueuedActionConsumed();
  }, [applyQueuedAction, onQueuedActionConsumed, queuedAction]);

  return (
    <div
      className={cn(
        "bg-background/95 backdrop-blur",
        isDockedWithTodosAbove
          ? "border-t-0 px-0 pt-0 pb-3"
          : "border-t border-border/60 px-4 py-4",
        className
      )}
    >
      <div ref={rootRef} className={cn(isDockedWithTodosAbove && "px-4 pt-0")}>
        <ComposerPrimitive.Root
          key={threadId}
          className={cn(
            "border border-border/70 bg-background p-3",
            isDockedWithTodosAbove
              ? "w-full rounded-none border-0 shadow-none"
              : "rounded-xl shadow-sm"
          )}
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
              agentKind={agentKind}
              qaStyle={qaStyle}
              modelId={modelId}
              modelOptions={modelOptions}
              isLoading={isModelsLoading}
              onAgentKindChange={onAgentKindChange}
              onQaStyleChange={onQaStyleChange}
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
      </div>

      <div
        className={cn(
          "mt-3 flex items-center justify-between gap-3",
          isDockedWithTodosAbove && "px-4"
        )}
      >
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
