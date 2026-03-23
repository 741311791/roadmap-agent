"use client";

import { useState, type ReactNode } from "react";
import { ArrowDown, Bot, Check, Copy, Sparkles, User2 } from "lucide-react";
import {
  MessagePrimitive,
  ThreadPrimitive,
  useMessage,
  useThread,
  useThreadViewport,
  type MessageState,
} from "@assistant-ui/react";
import ReactMarkdown from "react-markdown";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import type { MentorMessageMetadata } from "@/components/mentor/types";
import { cn } from "@/lib/utils";

interface MentorThreadProps {
  footer: ReactNode;
}

/**
 * extractRenderableText - 从消息 part 中提取可渲染文本
 * 同时折叠连续超过两个的空行，避免 ReactMarkdown 渲染时产生过多留白
 */
function extractRenderableText(
  content: MessageState["content"]
): string {
  return content
    .map((part) => {
      if ("text" in part) {
        return part.text;
      }

      return "";
    })
    .join("")
    .trim()
    .replace(/\n{3,}/g, "\n\n");
}

/**
 * formatResponseDuration - 格式化响应耗时展示
 */
function formatResponseDuration(durationMs?: number): string | null {
  if (!durationMs || durationMs <= 0) {
    return null;
  }

  if (durationMs < 1000) {
    return `${durationMs}ms`;
  }

  if (durationMs < 10_000) {
    return `${(durationMs / 1000).toFixed(1)}s`;
  }

  return `${Math.round(durationMs / 1000)}s`;
}

/**
 * MentorEmptyState - 空状态欢迎区域
 */
function MentorEmptyState() {
  const t = useTranslations("mentor");
  return (
    <div className="flex h-full min-h-[320px] flex-col items-center justify-center px-8 text-center">
      <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-sage-100 text-sage-700 shadow-sm">
        <Sparkles className="h-6 w-6" />
      </div>
      <h3 className="text-xl font-semibold tracking-tight text-slate-900">
        {t("emptyStateTitle")}
      </h3>
      <p className="mt-3 max-w-sm text-sm leading-7 text-muted-foreground">
        {t("emptyStateDesc")}
      </p>
    </div>
  );
}

/**
 * MentorMessageBubble - 单条消息气泡
 */
function MentorMessageBubble() {
  const role = useMessage((state) => state.role);
  const content = useMessage((state) => state.content);
  const status = useMessage((state) => state.status);
  const metadata = useMessage(
    (state) => state.metadata as { custom?: MentorMessageMetadata } | undefined
  );
  const plainText = extractRenderableText(content);
  const isUser = role === "user";
  const [isCopied, setIsCopied] = useState(false);
  const t = useTranslations("mentor");
  const responseDurationLabel = formatResponseDuration(
    metadata?.custom?.responseDurationMs
  );

  /**
   * handleCopyMarkdown - 复制原始 Markdown 文本
   */
  async function handleCopyMarkdown() {
    if (!plainText) {
      return;
    }

    try {
      await navigator.clipboard.writeText(plainText);
      setIsCopied(true);
      window.setTimeout(() => setIsCopied(false), 1500);
      toast.success("Markdown 已复制");
    } catch {
      toast.error("复制失败，请稍后再试");
    }
  }

  return (
    <div className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "group flex max-w-[90%] gap-3 rounded-2xl px-4 py-3",
          isUser
            ? "bg-sage-600 text-white shadow-sm"
            : "border border-border/70 bg-background text-slate-900 shadow-sm"
        )}
      >
        <div
          className={cn(
            "mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
            isUser ? "bg-white/20 text-white" : "bg-sage-100 text-sage-700"
          )}
        >
          {isUser ? <User2 className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </div>

        <div className="min-w-0 flex-1">
          <div
            className={cn(
              "mb-2 text-xs font-medium uppercase tracking-[0.14em]",
              isUser ? "text-white/80" : "text-slate-500"
            )}
          >
            {isUser ? t("you") : t("mentor")}
          </div>

          {plainText ? (
            <div
              className={cn(
                "prose prose-sm max-w-none break-words",
                "[&>p]:my-1 [&>p:first-child]:mt-0 [&>p:last-child]:mb-0",
                "[&>ul]:my-1 [&>ol]:my-1 [&>li]:my-0.5",
                "[&>h1]:mt-3 [&>h2]:mt-3 [&>h3]:mt-2 [&>h1]:mb-1 [&>h2]:mb-1 [&>h3]:mb-1",
                "[&>blockquote]:my-1 [&>pre]:my-1",
                isUser ? "prose-invert text-white" : "text-slate-800"
              )}
            >
              <ReactMarkdown>{plainText}</ReactMarkdown>
            </div>
          ) : null}

          {status?.type === "running" ? (
            <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:120ms]" />
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:240ms]" />
            </div>
          ) : null}

          {!isUser && (responseDurationLabel || plainText) && status?.type !== "running" ? (
            <div className="mt-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
              <span>{responseDurationLabel ? `响应耗时 ${responseDurationLabel}` : " "}</span>
              {plainText ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 px-2 opacity-0 transition-opacity group-hover:opacity-100"
                  onClick={handleCopyMarkdown}
                >
                  {isCopied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                  <span>{isCopied ? "已复制" : "复制 Markdown"}</span>
                </Button>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="text-xs text-red-500">
          <MessagePrimitive.Error />
        </div>
      </div>
    </div>
  );
}

function JumpToLatestButton() {
  const isAtBottom = useThreadViewport((state) => state.isAtBottom);
  const t = useTranslations("mentor");

  if (isAtBottom) {
    return null;
  }

  return (
    <ThreadPrimitive.ScrollToBottom asChild>
      <Button
        type="button"
        variant="outline"
        className="absolute -top-14 left-1/2 h-10 -translate-x-1/2 rounded-full border-border/70 bg-background/95 px-3 shadow-sm backdrop-blur"
      >
        <ArrowDown className="mr-1 h-4 w-4" />
        {t("jumpToLatest")}
      </Button>
    </ThreadPrimitive.ScrollToBottom>
  );
}

/**
 * MentorThread - 线程主视图
 */
export function MentorThread({ footer }: MentorThreadProps) {
  const isEmpty = useThread((state) => state.messages.length === 0);

  return (
    <ThreadPrimitive.Root className="flex h-full flex-col bg-background">
      <ThreadPrimitive.Viewport className="relative flex flex-1 flex-col overflow-y-auto px-4 pt-4">
        {isEmpty ? <MentorEmptyState /> : null}

        <ThreadPrimitive.Messages>
          {() => (
            <div className="mx-auto mb-3 w-full max-w-2xl">
              <MentorMessageBubble />
            </div>
          )}
        </ThreadPrimitive.Messages>

        <ThreadPrimitive.ViewportFooter className="sticky bottom-0 mt-auto flex w-full flex-col bg-transparent">
          <JumpToLatestButton />
          {footer}
        </ThreadPrimitive.ViewportFooter>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
}
