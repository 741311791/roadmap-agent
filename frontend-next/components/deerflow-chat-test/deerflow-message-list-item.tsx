"use client";

import { useMemo } from "react";
import {
  Bot,
  BoxesIcon,
  CheckCircle2,
  ChevronDown,
  Loader2,
  Sparkles,
} from "lucide-react";

import { partitionAssistantParts } from "@/components/deerflow-chat-test/deerflow-assistant-segments";
import { DeerFlowArtifactFileList } from "@/components/deerflow-chat-test/deerflow-artifact-file-list";
import type { DeerFlowChatMessage } from "@/components/deerflow-chat-test/deerflow-chat-state";
import { extractMessagePlainText } from "@/components/deerflow-chat-test/deerflow-chat-state";
import { DeerFlowMessageGroup } from "@/components/deerflow-chat-test/deerflow-message-group";
import { DeerFlowStreamingIndicator } from "@/components/deerflow-chat-test/deerflow-streaming-indicator";
import { useDeerFlowThread } from "@/components/deerflow-chat-test/deerflow-thread-context";
import {
  Message,
  MessageContent,
  MessageText,
} from "@/components/deerflow-native/ai-elements/message";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

/**
 * 单条 Deer-Flow 消息（对齐官方 MessageListItem + MessageGroup 组合渲染）。
 */
export function DeerFlowMessageListItem({
  message,
  threadId,
  isLoading = false,
}: {
  message: DeerFlowChatMessage;
  /** 用于 present_files 产物列表拉取与预览 */
  threadId?: string;
  /** 线程级加载中（流式），传入工具链动画状态 */
  isLoading?: boolean;
}) {
  if (message.role === "user") {
    return <DeerFlowUserMessageRow message={message} />;
  }

  return (
    <DeerFlowAssistantMessageRow
      isLoading={isLoading}
      message={message}
      threadId={threadId}
    />
  );
}

/**
 * 用户消息行：`ml-auto` + `w-fit` 气泡（测试页不提供悬停复制，避免与「仅复制最终正文」需求混淆）。
 */
function DeerFlowUserMessageRow({ message }: { message: DeerFlowChatMessage }) {
  const plain = extractMessagePlainText(message);

  return (
    <Message className="w-full" from="user">
      <div className="ml-auto flex w-full max-w-[min(100%,48rem)] flex-col items-end gap-2">
        {plain ? (
          <MessageContent className="w-fit max-w-full">
            <MessageText markdownProfile="human">{plain}</MessageText>
          </MessageContent>
        ) : null}
      </div>
    </Message>
  );
}

/**
 * 助手消息：按分段渲染工具链、产物列表、子任务卡片与正文。
 */
function DeerFlowAssistantMessageRow({
  message,
  threadId,
  isLoading,
}: {
  message: DeerFlowChatMessage;
  threadId?: string;
  isLoading: boolean;
}) {
  const { thread } = useDeerFlowThread();
  const threadTodosFallback = thread.todos ?? [];
  /**
   * 同一条助手消息在流式合并后可能包含多个 cot 段（例如 task 会 flush 出「主流程工具链 → 子任务 → 子流程工具链」）。
   * 若对每个 MessageGroup 都传入线程级 isLoading，则每一段都会在「本段最后一步」上显示转圈，造成「读取文件」与「检索资料」同时加载的错觉。
   * 仅对时间上最后一段 cot 启用末步 loading，与「当前仍在推进的步骤」一致。
   */
  const { segments, lastCotSegmentIndex } = useMemo(() => {
    const segs = partitionAssistantParts(message.parts);
    let lastCot = -1;
    for (let i = segs.length - 1; i >= 0; i -= 1) {
      if (segs[i].type === "cot") {
        lastCot = i;
        break;
      }
    }
    return { segments: segs, lastCotSegmentIndex: lastCot };
  }, [message.parts]);
  const showStreamingPlaceholder =
    Boolean(message.isStreaming) && message.parts.length === 0;

  return (
    <Message className="w-full" from="assistant">
      <MessageContent className="w-full max-w-[min(100%,48rem)]">
        <div className="text-muted-foreground mb-2 flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em]">
          <Bot className="h-3.5 w-3.5" />
          Deer-Flow
        </div>

        <div className="w-full space-y-6">
          {(() => {
            /**
             * 分段 key 使用「该段在 message.parts 中的起始下标」，避免流式过程中因插入 text / present_files
             * 等导致 segment 的数组 index 变化，从而卸载 DeerFlowMessageGroup 并重置「较早步骤」展开状态。
             */
            let partsOffset = 0;
            return segments.map((segment, index) => {
              if (segment.type === "cot") {
                const stableKey = `cot-${message.id}-@${partsOffset}`;
                partsOffset += segment.parts.length;
                return (
                  <DeerFlowMessageGroup
                    key={stableKey}
                    allowThreadTodosFallback={message.isStreaming === true}
                    isLoading={
                      isLoading &&
                      message.isStreaming === true &&
                      index === lastCotSegmentIndex
                    }
                    parts={segment.parts}
                    threadTodosFallback={threadTodosFallback}
                  />
                );
              }

              if (segment.type === "present_files") {
                const stableKey = `pf-${message.id}-@${partsOffset}`;
                partsOffset += 1;
                const filepaths = segment.part.arguments?.filepaths;
                const paths = Array.isArray(filepaths)
                  ? filepaths.filter((p): p is string => typeof p === "string" && p.trim().length > 0)
                  : [];
                if (paths.length === 0) {
                  return null;
                }
                if (!threadId) {
                  return (
                    <div key={stableKey} className="text-muted-foreground text-sm">
                      已生成 {paths.length} 个文件（需线程 ID 以预览）
                    </div>
                  );
                }
                return (
                  <div key={stableKey} className="w-full space-y-2">
                    <div className="text-muted-foreground text-xs font-medium tracking-wide">
                      产物文件
                    </div>
                    <DeerFlowArtifactFileList files={paths} threadId={threadId} />
                  </div>
                );
              }

              if (segment.type === "subagent") {
                const stableKey = `sub-${message.id}-@${partsOffset}`;
                partsOffset += segment.parts.length;
                return <DeerFlowSubagentSection key={stableKey} parts={segment.parts} />;
              }

              const stableKey = `txt-${message.id}-@${partsOffset}`;
              partsOffset += 1;
              return (
                <div key={stableKey} className="w-full">
                  <MessageText>{segment.part.text}</MessageText>
                </div>
              );
            });
          })()}

          {showStreamingPlaceholder ? (
            <div className="border-border/60 rounded-xl border bg-white/70 px-4 py-3">
              <DeerFlowStreamingIndicator size="sm" variant="labeled" />
            </div>
          ) : null}
        </div>

        <div className="text-muted-foreground mt-3 text-[11px]">
          {new Date(message.createdAt).toLocaleString()}
        </div>
      </MessageContent>
    </Message>
  );
}

/**
 * 子任务区：对齐官方「Executing N subtasks」+ 可折叠任务卡片。
 */
function DeerFlowSubagentSection({
  parts,
}: {
  parts: Array<Extract<DeerFlowChatMessage["parts"][number], { type: "tool" }>>;
}) {
  if (parts.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="text-muted-foreground pt-1 text-sm">
        正在执行 {parts.length} 个子任务
      </div>
      <div className="flex flex-col gap-3">
        {parts.map((part, index) => (
          <DeerFlowTaskToolCollapsible key={part.toolCallId || `task-${index}`} part={part} />
        ))}
      </div>
    </div>
  );
}

/**
 * 单个子任务工具：折叠展示描述、提示词与结果（对齐官方 Subtask 信息层级）。
 */
function DeerFlowTaskToolCollapsible({
  part,
}: {
  part: Extract<DeerFlowChatMessage["parts"][number], { type: "tool" }>;
}) {
  const description =
    typeof part.arguments?.description === "string"
      ? part.arguments.description
      : "子任务";
  const prompt = typeof part.arguments?.prompt === "string" ? part.arguments.prompt : "";
  const isDone = part.state === "completed";

  return (
    <Collapsible className="group/coll border-border/80 rounded-2xl border bg-gradient-to-b from-white to-slate-50/90 shadow-sm">
      <CollapsibleTrigger className="flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-black/[0.02]">
        <div className="mt-0.5 rounded-xl bg-slate-900 p-2 text-white">
          {isDone ? <CheckCircle2 className="h-4 w-4" /> : <BoxesIcon className="h-4 w-4" />}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <span className="text-sm font-medium text-slate-900">{description}</span>
            {isDone ? (
              <Sparkles className="h-4 w-4 shrink-0 text-emerald-500" />
            ) : (
              <Loader2 className="h-4 w-4 shrink-0 animate-spin text-amber-500" />
            )}
          </div>
          <div className="text-muted-foreground mt-0.5 text-xs">
            {isDone ? "子任务已完成" : "子任务进行中"}
          </div>
        </div>
        <ChevronDown className="text-muted-foreground group-data-[state=open]/coll:rotate-180 mt-1 size-4 shrink-0 transition-transform" />
      </CollapsibleTrigger>
      <CollapsibleContent className="border-border/60 space-y-3 border-t px-4 py-3">
        {prompt ? (
          <div>
            <div className="text-muted-foreground mb-1 text-[11px] font-medium uppercase tracking-wide">
              提示词
            </div>
            <pre className="bg-muted/50 max-h-48 overflow-auto rounded-lg p-3 text-xs leading-relaxed whitespace-pre-wrap">
              {prompt}
            </pre>
          </div>
        ) : null}
        {part.result ? (
          <div>
            <div className="text-muted-foreground mb-1 text-[11px] font-medium uppercase tracking-wide">
              输出
            </div>
            <div className="bg-slate-950 max-h-64 overflow-auto rounded-lg px-3 py-3 text-xs leading-relaxed whitespace-pre-wrap text-slate-100">
              {part.result}
            </div>
          </div>
        ) : null}
        {part.isError ? (
          <div className="text-xs font-medium text-rose-600">工具返回错误</div>
        ) : null}
      </CollapsibleContent>
    </Collapsible>
  );
}
