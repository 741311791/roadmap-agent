"use client";

import {
  BookOpenTextIcon,
  ChevronUp,
  FolderOpenIcon,
  GlobeIcon,
  LightbulbIcon,
  ListTodoIcon,
  Loader2,
  MessageCircleQuestionIcon,
  NotebookPenIcon,
  SearchIcon,
  SquareTerminalIcon,
  WrenchIcon,
} from "lucide-react";
import { useMemo, useState, type ComponentProps, type ReactNode } from "react";
import { RichStreamdown } from "@/components/markdown/rich-streamdown";

import {
  ChainOfThought,
  ChainOfThoughtContent,
  ChainOfThoughtSearchResult,
  ChainOfThoughtSearchResults,
  ChainOfThoughtStep,
} from "@/components/deerflow-native/ai-elements/chain-of-thought";
import type { DeerFlowChatMessagePart } from "@/components/deerflow-chat-test/deerflow-chat-state";
import { parseTodosPayload } from "@/components/deerflow-chat-test/deerflow-chat-state";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

/**
 * 将工具链片段转为 Chain-of-Thought 步骤（对齐官方 `convertToSteps`，省略 LangGraph Message 形态）。
 */
interface CoTReasoningStep {
  id: string;
  type: "reasoning";
  reasoning: string;
}

interface CoTToolCallStep {
  id: string;
  type: "toolCall";
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

type CoTStep = CoTReasoningStep | CoTToolCallStep;

/**
 * 从工具参数中解析文件路径（对齐官方 read_file/write_file 的 path，兼容少数模型使用的别名键）。
 */
function resolveSandboxPathFromArgs(args: Record<string, unknown>): string {
  const keys = [
    "path",
    "file_path",
    "filepath",
    "filePath",
    "target_file",
    "target_path",
    "filename",
  ] as const;
  for (const key of keys) {
    const value = args[key];
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
  }
  return "";
}

function convertPartsToCoTSteps(parts: DeerFlowChatMessagePart[]): CoTStep[] {
  const steps: CoTStep[] = [];
  let reasoningIndex = 0;
  let toolIndex = 0;

  for (const part of parts) {
    if (part.type === "thinking" && part.text.trim()) {
      steps.push({
        id: `reasoning-${reasoningIndex}`,
        type: "reasoning",
        reasoning: part.text,
      });
      reasoningIndex += 1;
      continue;
    }

    if (part.type === "tool") {
      steps.push({
        id: part.toolCallId || `tool-${toolIndex}-${part.name}`,
        type: "toolCall",
        name: part.name,
        args: part.arguments ?? {},
        result: part.result,
      });
      toolIndex += 1;
    }
  }

  return steps;
}

function tryParseJsonArray(value: string): unknown[] | null {
  try {
    const parsed: unknown = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function tryParseJsonRecord(value: string): Record<string, unknown> | null {
  try {
    const parsed: unknown = JSON.parse(value);
    return typeof parsed === "object" && parsed !== null && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

type ToolCallChainStepProps = ComponentProps<typeof ChainOfThoughtStep> & {
  isLast: boolean;
  isLoading: boolean;
};

/**
 * 工具步骤行：流式进行中且为当前消息最后一步时，以旋转 Loader 与 active 状态提示仍在执行（对齐官方子任务 in_progress 的 Loader 反馈）。
 */
function ToolCallChainStep({
  isLast,
  isLoading,
  icon,
  status: _ignoredStatus,
  ...rest
}: ToolCallChainStepProps) {
  const streaming = isLast && isLoading;
  return (
    <ChainOfThoughtStep
      {...rest}
      icon={
        streaming ? (
          <Loader2
            aria-hidden
            className="size-4 animate-spin text-muted-foreground"
          />
        ) : (
          icon
        )
      }
      status={streaming ? "active" : "complete"}
    />
  );
}

/**
 * 单条工具在 Chain-of-Thought 中的展示（与官方 `message-group.tsx` 的 ToolCall 对齐子集）。
 */
function ToolCallStepView({
  step,
  isLast = false,
  isLoading = false,
}: {
  step: CoTToolCallStep;
  isLast?: boolean;
  isLoading?: boolean;
}) {
  const { name, args, result } = step;

  if (name === "web_search") {
    let label: ReactNode = "检索相关资料";
    if (typeof args.query === "string" && args.query.trim()) {
      label = `在网络上搜索：${args.query}`;
    }
    const parsed =
      typeof result === "string" ? tryParseJsonArray(result) : null;
    const items =
      parsed?.filter(
        (item): item is { url: string; title: string } =>
          typeof item === "object" &&
          item !== null &&
          "url" in item &&
          typeof (item as { url: unknown }).url === "string",
      ) ?? [];
    return (
      <ToolCallChainStep isLast={isLast} isLoading={isLoading} icon={SearchIcon} label={label}>
        {items.length > 0 ? (
          <ChainOfThoughtSearchResults>
            {items.map((item) => (
              <ChainOfThoughtSearchResult key={item.url}>
                <a href={item.url} rel="noreferrer" target="_blank">
                  {item.title || item.url}
                </a>
              </ChainOfThoughtSearchResult>
            ))}
          </ChainOfThoughtSearchResults>
        ) : null}
      </ToolCallChainStep>
    );
  }

  if (name === "image_search") {
    let label: ReactNode = "检索相关图片";
    if (typeof args.query === "string" && args.query.trim()) {
      label = `图片搜索：${args.query}`;
    }
    const record =
      typeof result === "string" ? tryParseJsonRecord(result) : null;
    const results = record?.results;
    const imageItems = Array.isArray(results) ? results : [];
    return (
      <ToolCallChainStep isLast={isLast} isLoading={isLoading} icon={SearchIcon} label={label}>
        {imageItems.length > 0 ? (
          <ChainOfThoughtSearchResults>
            {imageItems.map((item: unknown) => {
              if (
                typeof item !== "object" ||
                item === null ||
                !("image_url" in item) ||
                typeof (item as { image_url: unknown }).image_url !== "string"
              ) {
                return null;
              }
              const typed = item as {
                image_url: string;
                thumbnail_url?: string;
                source_url?: string;
                title?: string;
              };
              const href = typed.source_url || typed.image_url;
              const thumb = typed.thumbnail_url || typed.image_url;
              return (
                <a
                  key={typed.image_url}
                  className="size-24 overflow-hidden rounded-lg object-cover"
                  href={href}
                  rel="noreferrer"
                  target="_blank"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    alt={typed.title || ""}
                    className="size-full object-cover"
                    height={100}
                    src={thumb}
                    width={100}
                  />
                </a>
              );
            })}
          </ChainOfThoughtSearchResults>
        ) : null}
      </ToolCallChainStep>
    );
  }

  if (name === "web_fetch") {
    const url = typeof args.url === "string" ? args.url : "";
    const title = url;
    return (
      <ToolCallChainStep
        isLast={isLast}
        isLoading={isLoading}
        className={url ? "cursor-pointer" : undefined}
        icon={GlobeIcon}
        label="打开网页"
        onClick={() => {
          if (url) {
            window.open(url, "_blank");
          }
        }}
      >
        {url ? (
          <ChainOfThoughtSearchResult>
            <a href={url} rel="noreferrer" target="_blank">
              {title}
            </a>
          </ChainOfThoughtSearchResult>
        ) : null}
      </ToolCallChainStep>
    );
  }

  if (name === "ls") {
    const description =
      typeof args.description === "string" && args.description.trim()
        ? args.description
        : "列出目录";
    const path = resolveSandboxPathFromArgs(args);
    return (
      <ToolCallChainStep isLast={isLast} isLoading={isLoading} icon={FolderOpenIcon} label={description}>
        {path ? (
          <ChainOfThoughtSearchResult className="cursor-pointer">{path}</ChainOfThoughtSearchResult>
        ) : null}
      </ToolCallChainStep>
    );
  }

  if (name === "read_file") {
    const description =
      typeof args.description === "string" && args.description.trim()
        ? args.description
        : "读取文件";
    const path = resolveSandboxPathFromArgs(args);
    return (
      <ToolCallChainStep isLast={isLast} isLoading={isLoading} icon={BookOpenTextIcon} label={description}>
        {path ? (
          <ChainOfThoughtSearchResult className="cursor-pointer">{path}</ChainOfThoughtSearchResult>
        ) : null}
      </ToolCallChainStep>
    );
  }

  if (name === "write_file" || name === "str_replace") {
    const description =
      typeof args.description === "string" && args.description.trim()
        ? args.description
        : name === "write_file"
          ? "写入文件"
          : "替换文件内容";
    const path = resolveSandboxPathFromArgs(args);
    return (
      <ToolCallChainStep isLast={isLast} isLoading={isLoading} icon={NotebookPenIcon} label={description}>
        {path ? (
          <ChainOfThoughtSearchResult className="cursor-pointer">{path}</ChainOfThoughtSearchResult>
        ) : null}
      </ToolCallChainStep>
    );
  }

  if (name === "bash") {
    const description =
      typeof args.description === "string" && args.description.trim()
        ? args.description
        : "执行命令";
    const command = typeof args.command === "string" ? args.command : "";
    return (
      <ToolCallChainStep isLast={isLast} isLoading={isLoading} icon={SquareTerminalIcon} label={description}>
        {command ? (
          <pre className="bg-muted/60 max-h-40 overflow-auto rounded-md p-2 text-xs">{command}</pre>
        ) : null}
      </ToolCallChainStep>
    );
  }

  if (name === "ask_clarification") {
    return (
      <ToolCallChainStep
        isLast={isLast}
        isLoading={isLoading}
        icon={MessageCircleQuestionIcon}
        label="需要你补充信息"
      />
    );
  }

  if (name === "write_todos") {
    const todosFromArgs = parseTodosPayload(args.todos ?? args);
    const todosFromResult = typeof result === "string" ? parseTodosPayload(result) : [];
    const todos = todosFromArgs.length > 0 ? todosFromArgs : todosFromResult;
    return (
      <ToolCallChainStep isLast={isLast} isLoading={isLoading} icon={ListTodoIcon} label="更新任务列表">
        {todos.length > 0 ? (
          <Collapsible>
            <CollapsibleTrigger className="text-muted-foreground hover:text-foreground text-xs underline-offset-2 hover:underline">
              查看 {todos.length} 项任务
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-2">
              <ul className="text-muted-foreground space-y-1 text-xs">
                {todos.map((todo) => (
                  <li key={todo.id}>
                    <span className="text-foreground/80 mr-2">[{todo.status}]</span>
                    {todo.content}
                  </li>
                ))}
              </ul>
            </CollapsibleContent>
          </Collapsible>
        ) : null}
      </ToolCallChainStep>
    );
  }

  const description =
    typeof args.description === "string" && args.description.trim()
      ? args.description
      : `调用工具：${name}`;

  return (
    <ToolCallChainStep isLast={isLast} isLoading={isLoading} icon={WrenchIcon} label={description}>
      {result && name !== "write_todos" ? (
        <pre className="bg-muted/40 max-h-36 overflow-auto rounded-md p-2 text-[11px] leading-relaxed wrap-break-word whitespace-pre-wrap">
          {result.length > 2000 ? `${result.slice(0, 2000)}…` : result}
        </pre>
      ) : null}
    </ToolCallChainStep>
  );
}

/**
 * DeerFlowMessageGroup — 与官方 `MessageGroup` 一致的工具链容器：更多步骤折叠、末步高亮、尾部思考折叠。
 */
export function DeerFlowMessageGroup({
  className,
  parts,
  isLoading = false,
}: {
  className?: string;
  parts: DeerFlowChatMessagePart[];
  isLoading?: boolean;
}) {
  const steps = useMemo(() => convertPartsToCoTSteps(parts), [parts]);
  const [showAbove, setShowAbove] = useState(false);
  const [showLastThinking, setShowLastThinking] = useState(false);

  const lastToolCallStep = useMemo(() => {
    const filtered = steps.filter((step) => step.type === "toolCall");
    return filtered[filtered.length - 1];
  }, [steps]);

  const aboveLastToolCallSteps = useMemo(() => {
    if (!lastToolCallStep) {
      return [];
    }
    const index = steps.indexOf(lastToolCallStep);
    return steps.slice(0, index);
  }, [lastToolCallStep, steps]);

  /** 仅当存在「末次工具调用」时，才单独折叠展示其后的思考（与官方布局一致，避免仅有 reasoning 时重复渲染）。 */
  const lastReasoningStep = useMemo(() => {
    if (!lastToolCallStep) {
      return undefined;
    }
    const index = steps.indexOf(lastToolCallStep);
    return steps.slice(index + 1).find((step) => step.type === "reasoning");
  }, [lastToolCallStep, steps]);

  if (steps.length === 0) {
    return null;
  }

  return (
    <ChainOfThought
      className={cn("w-full gap-2 rounded-lg border border-black/10 bg-white/60 p-0.5", className)}
      open
    >
      {aboveLastToolCallSteps.length > 0 ? (
        <Button
          className="h-auto w-full items-start justify-start py-2 text-left"
          type="button"
          variant="ghost"
          onClick={() => setShowAbove(!showAbove)}
        >
          <ChainOfThoughtStep
            icon={
              <ChevronUp
                className={cn("size-4 opacity-60 transition-transform duration-200", showAbove ? "rotate-180" : "")}
              />
            }
            label={
              <span className="opacity-60">
                {showAbove ? "收起较早步骤" : `查看其他 ${aboveLastToolCallSteps.length} 步`}
              </span>
            }
          />
        </Button>
      ) : null}

      {lastToolCallStep ? (
        <ChainOfThoughtContent className="px-4 pb-2">
          {showAbove
            ? aboveLastToolCallSteps.map((step) =>
                step.type === "reasoning" ? (
                  <ChainOfThoughtStep
                    key={step.id}
                    label={
                      <div className="prose prose-sm dark:prose-invert max-w-none prose-code:before:content-[''] prose-code:after:content-['']">
                        <RichStreamdown>{step.reasoning}</RichStreamdown>
                      </div>
                    }
                  />
                ) : (
                  <ToolCallStepView
                    key={step.id}
                    isLoading={isLoading}
                    step={step}
                  />
                ),
              )
            : null}
          <ToolCallStepView isLast isLoading={isLoading} step={lastToolCallStep as CoTToolCallStep} />
        </ChainOfThoughtContent>
      ) : (
        <ChainOfThoughtContent className="px-4 pb-2">
          {steps.map((step) =>
            step.type === "reasoning" ? (
              <ChainOfThoughtStep
                key={step.id}
                label={
                  <div className="prose prose-sm dark:prose-invert max-w-none prose-code:before:content-[''] prose-code:after:content-['']">
                    <RichStreamdown>{step.reasoning}</RichStreamdown>
                  </div>
                }
              />
            ) : (
              <ToolCallStepView key={step.id} isLoading={isLoading} step={step} />
            ),
          )}
        </ChainOfThoughtContent>
      )}

      {lastReasoningStep && lastReasoningStep.type === "reasoning" ? (
        <>
          <Button
            className="h-auto w-full items-start justify-start py-2 text-left"
            type="button"
            variant="ghost"
            onClick={() => setShowLastThinking(!showLastThinking)}
          >
            <div className="flex w-full items-center justify-between">
              <ChainOfThoughtStep className="font-normal" icon={LightbulbIcon} label="思考过程" />
              <ChevronUp
                className={cn("text-muted-foreground size-4", showLastThinking ? "" : "rotate-180")}
              />
            </div>
          </Button>
          {showLastThinking ? (
            <ChainOfThoughtContent className="px-4 pb-2">
              <ChainOfThoughtStep
                label={
                  <div className="prose prose-sm dark:prose-invert max-w-none prose-code:before:content-[''] prose-code:after:content-['']">
                    <RichStreamdown>{lastReasoningStep.reasoning}</RichStreamdown>
                  </div>
                }
              />
            </ChainOfThoughtContent>
          ) : null}
        </>
      ) : null}
    </ChainOfThought>
  );
}
