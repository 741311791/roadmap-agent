"use client";

import { useEffect, useState, type ReactNode } from "react";
import {
  ArrowDown,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronDown,
  Copy,
  ExternalLink,
  FileText,
  Globe,
  ListTodo,
  Map as MapIcon,
  Search,
  Sparkles,
  UserRound,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import {
  MessagePrimitive,
  ThreadPrimitive,
  useMessage,
  useThread,
  useThreadViewport,
  type MessageState,
} from "@assistant-ui/react";
import ReactMarkdown from "react-markdown";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import { useTranslations } from "next-intl";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { MermaidDiagram } from "@/components/tutorial/mermaid-diagram";
import type {
  MentorContentPart,
  MentorMessageMetadata,
  MentorQuickAction,
} from "@/components/mentor/types";
import { cn } from "@/lib/utils";

interface MentorThreadProps {
  onQuickAction: (action: MentorQuickAction) => void;
  footer: ReactNode;
}

/**
 * buildDefaultQuickActions - 构建默认快捷动作
 */

/**
 * extractRenderableText - 从消息 part 中提取可渲染文本
 * 同时折叠连续超过两个的空行，避免 ReactMarkdown 渲染时产生过多留白
 */
function extractMentorContentParts(
  content: MessageState["content"]
): MentorContentPart[] {
  return content.flatMap((part) => {
    if ("type" in part && part.type === "reasoning" && "text" in part) {
      return [
        {
          type: "thinking",
          text: part.text,
        } satisfies MentorContentPart,
      ];
    }

    if ("type" in part && part.type === "tool-call") {
      return [part as unknown as MentorContentPart];
    }

    if ("text" in part) {
      return [
        {
          type: "text",
          text: part.text,
        } satisfies MentorContentPart,
      ];
    }

    return [];
  });
}

/**
 * formatToolName - 将工具名格式化为更易读的标题
 */
function formatToolName(toolName: string): string {
  if (toolName === "web_search") {
    return "Web Search";
  }

  if (toolName === "web_fetch") {
    return "Web Fetch";
  }

  if (toolName === "context7_docs") {
    return "Context7 Docs";
  }

  return toolName;
}

/**
 * formatToolArgumentValue - 将工具参数压缩为适合 Badge 展示的文本
 */
function formatToolArgumentValue(value: unknown): string | null {
  if (typeof value === "string") {
    const normalizedValue = value.trim();
    if (!normalizedValue) {
      return null;
    }
    return normalizedValue.length > 40 ? `${normalizedValue.slice(0, 37)}...` : normalizedValue;
  }

  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return null;
}

/**
 * extractToolArgumentBadges - 提取适合展示的关键参数
 */
function extractToolArgumentBadges(argumentsValue?: Record<string, unknown>): string[] {
  if (!argumentsValue) {
    return [];
  }

  const candidateKeys = [
    "query",
    "url",
    "path",
    "concept_id",
    "conceptId",
    "roadmap_id",
    "roadmapId",
    "topic",
  ];

  return candidateKeys
    .map((key) => formatToolArgumentValue(argumentsValue[key]))
    .filter((value): value is string => Boolean(value))
    .slice(0, 2);
}

/**
 * getToolIcon - 获取工具图标
 */
function getToolIcon(toolName: string): LucideIcon {
  if (toolName === "web_search") {
    return Search;
  }

  if (toolName === "web_fetch") {
    return Globe;
  }

  if (toolName === "context7_docs") {
    return BookOpen;
  }

  if (toolName === "get_concept_tutorial") {
    return FileText;
  }

  if (toolName === "get_roadmap_metadata") {
    return MapIcon;
  }

  if (toolName === "get_user_profile") {
    return UserRound;
  }

  if (toolName === "mark_content_complete") {
    return CheckCircle2;
  }

  if (toolName === "write_todos") {
    return ListTodo;
  }

  return Wrench;
}

/**
 * getToolDescription - 生成工具调用摘要
 */
function getToolDescription(
  toolName: string,
  argumentsValue?: Record<string, unknown>
): string {
  const query = formatToolArgumentValue(argumentsValue?.query);
  const url = formatToolArgumentValue(argumentsValue?.url);
  const conceptId = formatToolArgumentValue(argumentsValue?.concept_id ?? argumentsValue?.conceptId);

  if (toolName === "web_search") {
    return query ? `搜索：${query}` : "搜索外部资料";
  }

  if (toolName === "web_fetch") {
    return url ? `抓取页面：${url}` : "抓取网页内容";
  }

  if (toolName === "context7_docs") {
    return query ? `检索文档：${query}` : "检索官方文档";
  }

  if (toolName === "get_concept_tutorial") {
    return conceptId ? `读取章节教程：${conceptId}` : "读取当前章节教程";
  }

  if (toolName === "get_roadmap_metadata") {
    return "读取路线图元数据";
  }

  if (toolName === "get_user_profile") {
    return "读取用户学习画像";
  }

  if (toolName === "mark_content_complete") {
    return "标记内容已完成";
  }

  return `调用 ${formatToolName(toolName)}`;
}

/**
 * SearchResultLink - 网络搜索结果链接结构
 */
interface SearchResultLink {
  title: string;
  url: string;
}

interface ToolResultLink {
  title: string;
  url: string;
}

/**
 * parseWebSearchResults - 解析 web_search 工具返回的结果，提取链接列表
 * 兼容 Tavily、SerpAPI 等多种返回格式
 */
function parseWebSearchResults(result: unknown): SearchResultLink[] {
  if (!result) {
    return [];
  }

  const resultStr = typeof result === "string" ? result : JSON.stringify(result);

  try {
    const parsed = JSON.parse(resultStr);

    // Tavily 格式：直接数组
    if (Array.isArray(parsed)) {
      return parsed
        .filter((item) => item?.url && item?.title)
        .map((item) => ({ title: String(item.title), url: String(item.url) }))
        .slice(0, 6);
    }

    // Tavily 格式：{ results: [...] }
    if (parsed?.results && Array.isArray(parsed.results)) {
      return parsed.results
        .filter((item: { url?: string; title?: string }) => item?.url && item?.title)
        .map((item: { title: string; url: string }) => ({ title: item.title, url: item.url }))
        .slice(0, 6);
    }

    // SerpAPI 格式：{ organic_results: [...] }
    if (parsed?.organic_results && Array.isArray(parsed.organic_results)) {
      return parsed.organic_results
        .filter((item: { link?: string; title?: string }) => item?.link && item?.title)
        .map((item: { title: string; link: string }) => ({ title: item.title, url: item.link }))
        .slice(0, 6);
    }
  } catch {
    // 尝试从 Markdown 链接语法中提取 URL
    const mdLinkPattern = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;
    const links: SearchResultLink[] = [];
    let match = mdLinkPattern.exec(resultStr);

    while (match !== null) {
      links.push({ title: match[1], url: match[2] });
      match = mdLinkPattern.exec(resultStr);
    }

    return links.slice(0, 6);
  }

  return [];
}

/**
 * parseToolResultPayload - 将工具结果尽量解析为 JSON 结构
 */
function parseToolResultPayload(result: unknown): unknown {
  if (typeof result !== "string") {
    return result;
  }

  const normalizedResult = result.trim();
  if (!normalizedResult) {
    return null;
  }

  try {
    return JSON.parse(normalizedResult);
  } catch {
    return result;
  }
}

/**
 * parseWebFetchLinks - 提取 web_fetch 可直接打开的链接
 */
function parseWebFetchLinks(params: {
  result: unknown;
  argumentsValue?: Record<string, unknown>;
}): ToolResultLink[] {
  const links: ToolResultLink[] = [];
  const payload = parseToolResultPayload(params.result);
  const resultUrl =
    typeof params.argumentsValue?.url === "string"
      ? params.argumentsValue.url
      : typeof (payload as { url?: unknown } | null)?.url === "string"
        ? String((payload as { url?: unknown }).url)
        : null;

  if (!resultUrl) {
    return [];
  }

  let title = resultUrl;
  if (payload && typeof payload === "object" && !Array.isArray(payload)) {
    const content = (payload as { content?: unknown }).content;
    if (typeof content === "string") {
      const firstHeading = content.match(/^#\s+(.+)$/m)?.[1]?.trim();
      if (firstHeading) {
        title = firstHeading;
      }
    }
  }

  links.push({
    title,
    url: resultUrl,
  });

  return links;
}

/**
 * parseToolResultLinksFromText - 从工具结果文本中提取 URL，生成可点击按钮
 */
function parseToolResultLinksFromText(result: unknown): ToolResultLink[] {
  if (typeof result !== "string") {
    return [];
  }

  const links = new Map<string, ToolResultLink>();
  const markdownLinkPattern = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;
  const urlPattern = /https?:\/\/[^\s)"'<>]+/g;

  let markdownMatch = markdownLinkPattern.exec(result);
  while (markdownMatch !== null) {
    links.set(markdownMatch[2], {
      title: markdownMatch[1],
      url: markdownMatch[2],
    });
    markdownMatch = markdownLinkPattern.exec(result);
  }

  let urlMatch = urlPattern.exec(result);
  while (urlMatch !== null) {
    const url = urlMatch[0];
    if (!links.has(url)) {
      let title = url;
      const sourceLine = result
        .split("\n")
        .find((line) => line.includes(url) || line.includes(`Source: ${url}`));

      if (sourceLine?.includes("Source:")) {
        title = sourceLine.replace("Source:", "").trim();
      }

      links.set(url, {
        title,
        url,
      });
    }

    urlMatch = urlPattern.exec(result);
  }

  return [...links.values()].slice(0, 6);
}

/**
 * formatToolResultPreview - 生成工具结果预览文本
 */
function formatToolResultPreview(result: unknown): string | null {
  if (!result) {
    return null;
  }

  if (typeof result === "string") {
    const normalizedResult = result.trim();
    if (!normalizedResult) {
      return null;
    }

    try {
      const parsed = JSON.parse(normalizedResult);
      const prettyJson = JSON.stringify(parsed, null, 2);
      return prettyJson.length > 1200 ? `${prettyJson.slice(0, 1200)}\n...(truncated)` : prettyJson;
    } catch {
      return normalizedResult.length > 800 ? `${normalizedResult.slice(0, 800)}\n...(truncated)` : normalizedResult;
    }
  }

  const prettyJson = JSON.stringify(result, null, 2);
  if (!prettyJson) {
    return null;
  }

  return prettyJson.length > 1200 ? `${prettyJson.slice(0, 1200)}\n...(truncated)` : prettyJson;
}

/**
 * MentorToolCallStep - 工具调用时间线步骤
 * 以紧凑单行形式展示，web_search 额外渲染可点击链接标签
 */
function MentorToolCallStep({
  part,
  isUser,
  isLastInGroup,
}: {
  part: Extract<MentorContentPart, { type: "tool-call" }>;
  isUser: boolean;
  isLastInGroup: boolean;
}) {
  const t = useTranslations("mentor");
  const ToolIcon = getToolIcon(part.toolName);
  const toolDescription =
    part.toolName === "write_todos"
      ? t("toolWriteTodos")
      : getToolDescription(part.toolName, part.arguments);
  const isRunning = part.state === "running";
  const isError = part.isError;
  const [isExpanded, setIsExpanded] = useState(isRunning);
  const searchLinks =
    part.toolName === "web_search" && !isRunning ? parseWebSearchResults(part.result) : [];
  const webFetchLinks =
    part.toolName === "web_fetch" && !isRunning
      ? parseWebFetchLinks({
          result: part.result,
          argumentsValue: part.arguments,
        })
      : [];
  const extractedResultLinks =
    !isRunning && searchLinks.length === 0 && webFetchLinks.length === 0
      ? parseToolResultLinksFromText(typeof part.result === "string" ? part.result : "")
      : [];
  const resultPreview = formatToolResultPreview(part.result);

  return (
    <div className="relative flex gap-2.5">
      {/* 时间线左侧轨道 */}
      <div className="relative flex shrink-0 flex-col items-center" style={{ width: 18 }}>
        {/* 步骤圆点 */}
        <div
          className={cn(
            "relative z-10 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border",
            isRunning
              ? isUser
                ? "border-white/30 bg-white/10"
                : "border-slate-300 bg-white"
              : isError
                ? "border-red-200 bg-red-50"
                : isUser
                  ? "border-white/30 bg-white/15"
                  : "border-slate-200 bg-white"
          )}
        >
          {isRunning ? (
            <span
              className={cn(
                "h-1.5 w-1.5 animate-pulse rounded-full",
                isUser ? "bg-white/60" : "bg-slate-400"
              )}
            />
          ) : (
            <ToolIcon
              className={cn(
                "h-2.5 w-2.5",
                isError
                  ? "text-red-400"
                  : isUser
                    ? "text-white/70"
                    : "text-slate-400"
              )}
            />
          )}
        </div>
        {/* 连接线（非末项时显示） */}
        {!isLastInGroup ? (
          <div
            className={cn(
              "mt-0.5 w-px flex-1",
              isUser ? "bg-white/15" : "bg-slate-200"
            )}
          />
        ) : null}
      </div>

      {/* 右侧内容区 */}
      <div className={cn("min-w-0 flex-1", isLastInGroup ? "pb-0" : "pb-2")}>
        <button
          type="button"
          className="flex w-full items-center gap-2 text-left"
          onClick={() => setIsExpanded((previousState) => !previousState)}
        >
          <span
            className={cn(
              "truncate text-xs leading-[18px]",
              isUser ? "text-white/75" : "text-slate-500"
            )}
          >
            {toolDescription}
          </span>
          {!isRunning ? (
            <span
              className={cn(
                "shrink-0 rounded-sm px-1 py-px text-[10px] font-medium leading-tight",
                isError
                  ? "bg-red-50 text-red-500"
                  : isUser
                    ? "bg-white/10 text-white/60"
                    : "bg-emerald-50 text-emerald-600"
              )}
            >
              {isError ? "Failed" : "Done"}
            </span>
          ) : null}
          <ChevronDown
            className={cn(
              "ml-auto h-3.5 w-3.5 shrink-0 transition-transform duration-200",
              isUser ? "text-white/45" : "text-slate-400",
              isExpanded ? "rotate-180" : "rotate-0"
            )}
          />
        </button>

        {isExpanded ? (
          <div className="mt-2 space-y-2">
            {extractToolArgumentBadges(part.arguments).length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {extractToolArgumentBadges(part.arguments).map((badge) => (
                  <span
                    key={`${part.toolCallId}-${badge}`}
                    className={cn(
                      "inline-flex max-w-[220px] items-center rounded-md border px-2 py-0.5 text-[11px]",
                      isUser
                        ? "border-white/15 bg-white/5 text-white/70"
                        : "border-slate-200 bg-white text-slate-500"
                    )}
                  >
                    <span className="truncate">{badge}</span>
                  </span>
                ))}
              </div>
            ) : null}

            {searchLinks.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {searchLinks.map((link) => (
                  <a
                    key={link.url}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(
                      "inline-flex max-w-[220px] items-center gap-1 rounded-md border px-2 py-1 text-[11px] transition-colors",
                      isUser
                        ? "border-white/15 bg-white/5 text-white/80 hover:bg-white/10"
                        : "border-slate-200 bg-background text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                    )}
                  >
                    <ExternalLink
                      className={cn(
                        "h-2.5 w-2.5 shrink-0",
                        isUser ? "text-white/40" : "text-slate-400"
                      )}
                    />
                    <span className="truncate">{link.title}</span>
                  </a>
                ))}
              </div>
            ) : null}

            {webFetchLinks.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {webFetchLinks.map((link) => (
                  <a
                    key={link.url}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(
                      "inline-flex max-w-[240px] items-center gap-1 rounded-md border px-2 py-1 text-[11px] transition-colors",
                      isUser
                        ? "border-white/15 bg-white/5 text-white/80 hover:bg-white/10"
                        : "border-slate-200 bg-background text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                    )}
                  >
                    <Globe
                      className={cn(
                        "h-2.5 w-2.5 shrink-0",
                        isUser ? "text-white/40" : "text-slate-400"
                      )}
                    />
                    <span className="truncate">{link.title}</span>
                  </a>
                ))}
              </div>
            ) : null}

            {extractedResultLinks.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {extractedResultLinks.map((link) => (
                  <a
                    key={link.url}
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(
                      "inline-flex max-w-[240px] items-center gap-1 rounded-md border px-2 py-1 text-[11px] transition-colors",
                      isUser
                        ? "border-white/15 bg-white/5 text-white/80 hover:bg-white/10"
                        : "border-slate-200 bg-background text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                    )}
                  >
                    <ExternalLink
                      className={cn(
                        "h-2.5 w-2.5 shrink-0",
                        isUser ? "text-white/40" : "text-slate-400"
                      )}
                    />
                    <span className="truncate">{link.title}</span>
                  </a>
                ))}
              </div>
            ) : null}

            {resultPreview ? (
              <pre
                className={cn(
                  "max-h-48 overflow-auto rounded-lg border px-3 py-2 text-[11px] leading-5",
                  isUser
                    ? "border-white/10 bg-black/10 text-white/75"
                    : "border-slate-200 bg-white text-slate-600"
                )}
              >
                <code className="whitespace-pre-wrap break-words font-mono">{resultPreview}</code>
              </pre>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}

/**
 * MentorToolCallGroup - 将连续的工具调用步骤渲染为整体时间线区块
 */
function MentorToolCallGroup({
  parts,
  isUser,
}: {
  parts: Array<{ part: Extract<MentorContentPart, { type: "tool-call" }>; index: number }>;
  isUser: boolean;
}) {
  const hasRunningStep = parts.some(({ part }) => part.state === "running");
  const hasErrorStep = parts.some(({ part }) => part.isError);
  const [isExpanded, setIsExpanded] = useState(hasRunningStep);

  return (
    <div
      className={cn(
        "my-2 rounded-lg border px-3 py-2.5",
        isUser ? "border-white/15 bg-white/5" : "border-slate-100 bg-slate-50/60"
      )}
    >
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 text-left"
        onClick={() => setIsExpanded((previousState) => !previousState)}
      >
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-md",
              isUser ? "bg-white/10 text-white/80" : "bg-slate-200 text-slate-600"
            )}
          >
            <Wrench className="h-3.5 w-3.5" />
          </div>
          <div>
            <div className={cn("text-sm font-medium", isUser ? "text-white/90" : "text-slate-800")}>
              工具调用
            </div>
            <div className={cn("text-[11px]", isUser ? "text-white/55" : "text-slate-500")}>
              共 {parts.length} 步
              {hasRunningStep ? "，执行中" : hasErrorStep ? "，含失败项" : "，已完成"}
            </div>
          </div>
        </div>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 transition-transform duration-200",
            isUser ? "text-white/45" : "text-slate-400",
            isExpanded ? "rotate-180" : "rotate-0"
          )}
        />
      </button>

      {isExpanded ? (
        <div className="mt-3">
          {parts.map(({ part, index }, groupIndex) => (
            <MentorToolCallStep
              key={part.toolCallId ?? `tool-${index}`}
              part={part}
              isUser={isUser}
              isLastInGroup={groupIndex === parts.length - 1}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

interface MentorMarkdownContentProps {
  plainText: string;
  isUser: boolean;
  isStreaming?: boolean;
}

/**
 * normalizeInlineCodeMarkdown - 规范化模型常见的双反引号行内代码写法
 */
function normalizeInlineCodeMarkdown(plainText: string): string {
  return plainText
    .replace(/(?<!`)``\s*`([^`\n]+)`\s*``(?!`)/g, "`$1`")
    .replace(/(?<!`)``([^`\n]+)``(?!`)/g, "`$1`");
}

/**
 * MentorMarkdownContent - 学习助手消息 Markdown 渲染器
 * 为导师消息补充 GFM 表格解析与响应式表格样式
 */
export function MentorMarkdownContent({
  plainText,
  isUser,
  isStreaming,
}: MentorMarkdownContentProps) {
  const normalizedPlainText = normalizeInlineCodeMarkdown(plainText);

  return (
    <div
      className={cn(
        "prose prose-sm prose-slate max-w-none break-words",
        "prose-code:before:content-[''] prose-code:after:content-['']",
        isUser ? "prose-invert text-white" : "text-slate-800",
        isStreaming && "streaming-active"
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex, rehypeHighlight]}
        components={{
          pre({ children }) {
            return <>{children}</>;
          },
          code({ className, children, ...props }) {
            const isInline = !className?.includes("language-");
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : "";
            const code = String(children).replace(/\n$/, "");

            if (!isInline && language === "mermaid") {
              return <MermaidDiagram chart={code} className="my-3" />;
            }

            if (!isInline) {
              return (
                <div className="my-3 overflow-hidden rounded-lg border border-slate-700/30 bg-slate-950/95 shadow-sm">
                  <div className="border-b border-slate-800 bg-slate-900/95 px-3 py-2 text-[11px] uppercase tracking-[0.14em] text-slate-400">
                    {language || "code"}
                  </div>
                  <div className="overflow-x-auto">
                    <pre className="m-0 p-4 text-sm leading-6 text-slate-100">
                      <code className={cn(className, "whitespace-pre")} {...props}>
                        {children}
                      </code>
                    </pre>
                  </div>
                </div>
              );
            }

            return (
              <code
                className={cn(
                  "rounded-md px-1.5 py-0.5 font-mono text-[0.9em]",
                  isUser
                    ? "bg-white/20 text-white"
                    : "bg-slate-100 text-slate-900"
                )}
                {...props}
              >
                {children}
              </code>
            );
          },
          table({ children, ...props }) {
            return (
              <div className="my-4 w-full overflow-x-auto">
                <table
                  className={cn(
                    "w-full border-collapse text-sm",
                    isUser ? "text-white" : "text-slate-800"
                  )}
                  {...props}
                >
                  {children}
                </table>
              </div>
            );
          },
          thead({ children, ...props }) {
            return (
              <thead
                className={cn(
                  isUser ? "bg-white/10" : "bg-slate-100"
                )}
                {...props}
              >
                {children}
              </thead>
            );
          },
          tr({ children, ...props }) {
            return (
              <tr
                className={cn(
                  "border-b transition-colors",
                  isUser 
                    ? "border-white/10 hover:bg-white/5 even:bg-white/5" 
                    : "border-slate-200 hover:bg-slate-50/50 even:bg-slate-50"
                )}
                {...props}
              >
                {children}
              </tr>
            );
          },
          th({ children, ...props }) {
            return (
              <th
                className={cn(
                  "border px-4 py-2 text-left font-semibold",
                  isUser ? "border-white/20 text-white" : "border-slate-200 text-slate-900"
                )}
                {...props}
              >
                {children}
              </th>
            );
          },
          td({ children, ...props }) {
            return (
              <td
                className={cn(
                  "border px-4 py-2",
                  isUser ? "border-white/20 text-white/90" : "border-slate-200 text-slate-700"
                )}
                {...props}
              >
                {children}
              </td>
            );
          },
          blockquote({ children, ...props }) {
            return (
              <blockquote
                className={cn(
                  "my-3 rounded-r-lg border-l-4 px-4 py-1 italic",
                  isUser
                    ? "border-white/40 bg-white/5 text-white/90"
                    : "border-sage-300 bg-sage-50/60 text-slate-700"
                )}
                {...props}
              >
                {children}
              </blockquote>
            );
          },
          a({ href, children, ...props }) {
            const isExternal = href?.startsWith("http");

            return (
              <a
                href={href}
                target={isExternal ? "_blank" : undefined}
                rel={isExternal ? "noopener noreferrer" : undefined}
                className={cn(
                  "font-medium underline underline-offset-4",
                  isUser ? "text-white" : "text-sage-700"
                )}
                {...props}
              >
                {children}
              </a>
            );
          },
          ul({ children, ...props }) {
            return (
              <ul className="list-disc pl-6" {...props}>
                {children}
              </ul>
            );
          },
          ol({ children, ...props }) {
            return (
              <ol className="list-decimal pl-6" {...props}>
                {children}
              </ol>
            );
          },
          hr(props) {
            return (
              <hr
                className={cn(
                  "my-4 border-dashed",
                  isUser ? "border-white/20" : "border-border/70"
                )}
                {...props}
              />
            );
          },
          img({ src, alt, ...props }) {
            return (
              <img
                src={src}
                alt={alt}
                loading="lazy"
                className="my-3 rounded-lg border border-border/60 shadow-sm"
                {...props}
              />
            );
          },
        }}
      >
        {normalizedPlainText}
      </ReactMarkdown>
    </div>
  );
}

interface MentorThinkingBlockProps {
  text: string;
  isStreaming: boolean;
}

/**
 * MentorThinkingBlock - 可折叠思考过程区域
 */
function MentorThinkingBlock({ text, isStreaming }: MentorThinkingBlockProps) {
  const t = useTranslations("mentor");
  const [isExpanded, setIsExpanded] = useState(isStreaming);

  useEffect(() => {
    if (isStreaming) {
      setIsExpanded(true);
    }
  }, [isStreaming]);

  if (!text) {
    return null;
  }

  return (
    <div className="my-3 rounded-xl border border-slate-200/90 bg-slate-50/90 p-3">
      <button
        type="button"
        className="flex w-full items-center justify-between gap-3 text-left"
        onClick={() => setIsExpanded((previousState) => !previousState)}
      >
        <div className="text-sm font-medium text-slate-700">{t("thinkingProcess")}</div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>{isExpanded ? t("hideSteps") : t("showSteps")}</span>
          <ChevronDown
            className={cn(
              "h-4 w-4 transition-transform duration-200",
              isExpanded ? "rotate-180" : "rotate-0"
            )}
          />
        </div>
      </button>

      {isExpanded ? (
        <div className="mt-3 border-l border-slate-200 pl-4">
          <MentorMarkdownContent plainText={text} isUser={false} />
        </div>
      ) : null}
    </div>
  );
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
 * OrganizedContent - 将内容 parts 整理为三个独立区块的结构
 * 工具调用统一前置，避免文本段被工具卡片截断
 */
interface OrganizedContent {
  /** 思考过程（可折叠） */
  thinking: Array<{ text: string; index: number }>;
  /** 所有工具调用，统一渲染为一个时间线区块 */
  toolCalls: Array<{
    part: Extract<MentorContentPart, { type: "tool-call" }>;
    index: number;
  }>;
  /** 合并后的文本内容（去除因工具调用插入造成的碎片化） */
  mergedText: string;
}

/**
 * organizeContentParts - 整理内容 parts，统一将工具调用提升至文本之前
 *
 * 当模型在流式输出中途插入工具调用时（如：文本A → 工具调用 → 文本B），
 * 直接按顺序渲染会造成句子被工具卡片截断的视觉问题。
 * 此函数将所有碎片化文本合并为一段，工具调用统一前置，
 * 保证文本内容的完整性和可读性。
 */
function organizeContentParts(contentParts: MentorContentPart[]): OrganizedContent {
  const thinking: OrganizedContent["thinking"] = [];
  const toolCalls: OrganizedContent["toolCalls"] = [];
  const textFragments: string[] = [];

  for (let i = 0; i < contentParts.length; i++) {
    const part = contentParts[i];

    if (part.type === "thinking") {
      thinking.push({ text: (part as { type: "thinking"; text: string }).text, index: i });
    } else if (part.type === "tool-call") {
      toolCalls.push({
        part: part as Extract<MentorContentPart, { type: "tool-call" }>,
        index: i,
      });
    } else if (part.type === "text") {
      const text = (part as { type: "text"; text: string }).text;
      if (text) {
        textFragments.push(text);
      }
    }
  }

  return {
    thinking,
    toolCalls,
    mergedText: textFragments.join("").trim().replace(/\n{3,}/g, "\n\n"),
  };
}

/**
 * MentorMessageBubble - 单条消息气泡
 * 仅以气泡颜色区分角色，不显示头像和名称。
 * 工具调用统一前置渲染，避免文本被截断。
 */
function MentorMessageBubble() {
  const role = useMessage((state) => state.role);
  const content = useMessage((state) => state.content);
  const status = useMessage((state) => state.status);
  const metadata = useMessage(
    (state) => state.metadata as { custom?: MentorMessageMetadata } | undefined
  );
  const contentParts = extractMentorContentParts(content);
  const isUser = role === "user";
  const [isCopied, setIsCopied] = useState(false);
  const responseDurationLabel = formatResponseDuration(
    metadata?.custom?.responseDurationMs
  );
  const isStreaming = status?.type === "running";

  const { thinking, toolCalls, mergedText } = organizeContentParts(contentParts);

  /**
   * handleCopyMarkdown - 复制原始 Markdown 文本
   */
  async function handleCopyMarkdown() {
    if (!mergedText) {
      return;
    }

    try {
      await navigator.clipboard.writeText(mergedText);
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
          "group max-w-[90%] rounded-2xl px-4 py-3",
          isUser
            ? "bg-sage-600 text-white shadow-sm"
            : "border border-border/70 bg-background text-slate-900 shadow-sm"
        )}
      >
        {/* 1. 思考过程（可折叠，始终在最前） */}
        {thinking.map((item) => (
          <MentorThinkingBlock
            key={`thinking-${item.index}`}
            text={item.text}
            isStreaming={isStreaming}
          />
        ))}

        {/* 2. 所有工具调用统一前置，避免截断正文 */}
        {toolCalls.length > 0 ? (
          <MentorToolCallGroup parts={toolCalls} isUser={isUser} />
        ) : null}

        {/* 3. 合并后的完整文本内容 */}
        {mergedText ? (
          <MentorMarkdownContent
            plainText={mergedText}
            isUser={isUser}
            isStreaming={isStreaming}
          />
        ) : null}

        {/* 流式加载中且尚无文本时显示等待点 */}
        {isStreaming && !mergedText ? (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:120ms]" />
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current [animation-delay:240ms]" />
          </div>
        ) : null}

        {!isUser && (responseDurationLabel || mergedText) && !isStreaming ? (
          <div className="mt-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
            <span>{responseDurationLabel ? `响应耗时 ${responseDurationLabel}` : " "}</span>
            {mergedText ? (
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
export function MentorThread({
  onQuickAction,
  footer,
}: MentorThreadProps) {
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
