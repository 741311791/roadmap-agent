"use client";

import {
  Code2Icon,
  CopyIcon,
  DownloadIcon,
  EyeIcon,
  FileTextIcon,
  Loader2,
  SquareArrowOutUpRightIcon,
  XIcon,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { useDeerFlowArtifacts } from "@/components/deerflow-chat-test/deerflow-artifacts-context";
import { RichStreamdown } from "@/components/markdown/rich-streamdown";
import {
  getArtifactFileName,
  getArtifactPreviewSupport,
  isArtifactImage,
  type DeerFlowArtifactPreviewLanguage,
} from "@/components/deerflow-chat-test/deerflow-artifact-utils";
import { fetchDeerFlowStandaloneArtifact } from "@/components/deerflow-chat-test/deerflow-standalone-api";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/**
 * Markdown / HTML 预览区（与官方 `ArtifactFilePreview` 行为对齐）。
 */
function DeerFlowArtifactPreviewPane({
  content,
  language,
}: {
  content: string;
  language: DeerFlowArtifactPreviewLanguage;
}) {
  if (language === "markdown") {
    return (
      <div className="min-h-0 flex-1 overflow-auto bg-[#FAFAFA] px-4 py-4">
        <div className="prose prose-slate prose-sm max-w-none text-slate-800 prose-headings:text-slate-900 prose-p:text-slate-800 prose-li:text-slate-800 prose-strong:text-slate-900 prose-code:before:content-[''] prose-code:after:content-['']">
          <RichStreamdown mode="static">{content}</RichStreamdown>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-white">
      <iframe
        className="min-h-0 w-full flex-1 border-0"
        sandbox="allow-scripts allow-forms"
        srcDoc={content}
        title="HTML preview"
      />
    </div>
  );
}

/**
 * 在新标签页打开文本内容（Bearer 无法挂在 URL 上，使用 Blob URL）。
 */
function openTextInNewTab(content: string, mime: string): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const handle = window.open(url, "_blank", "noopener,noreferrer");
  if (!handle) {
    URL.revokeObjectURL(url);
    toast.error("无法打开新窗口，请检查浏览器拦截设置");
    return;
  }

  window.setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 120_000);
}

/**
 * 产物详情：头部工具栏 + 源码/预览（Markdown、HTML）与官方 DeerFlow 侧栏对齐。
 */
export function DeerFlowArtifactDetail({
  filepath,
  threadId,
  availableFiles,
}: {
  filepath: string;
  threadId: string;
  /** 与聊天区合并后的路径列表，用于多文件下拉切换 */
  availableFiles?: string[];
}) {
  const { select, setOpen } = useDeerFlowArtifacts();
  const [content, setContent] = useState<string>("");
  const [objectUrl, setObjectUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"code" | "preview">("code");

  const fileName = useMemo(() => getArtifactFileName(filepath), [filepath]);
  const isImage = useMemo(() => isArtifactImage(filepath), [filepath]);
  const support = useMemo(() => getArtifactPreviewSupport(filepath), [filepath]);
  const fileOptions = useMemo(() => {
    const raw = availableFiles?.length ? availableFiles : [filepath];
    return Array.from(new Set(raw.filter((p) => typeof p === "string" && p.trim().length > 0)));
  }, [availableFiles, filepath]);

  useEffect(() => {
    if (support.isPreviewable) {
      setViewMode("preview");
    } else {
      setViewMode("code");
    }
  }, [support.isPreviewable, filepath]);

  useEffect(() => {
    let isCancelled = false;
    let currentObjectUrl: string | null = null;

    /**
     * 拉取产物正文或图片 Blob。
     */
    async function loadArtifact() {
      setIsLoading(true);
      setErrorMessage(null);
      setContent("");
      setObjectUrl((previousUrl) => {
        if (previousUrl) {
          URL.revokeObjectURL(previousUrl);
        }
        return null;
      });

      try {
        const response = await fetchDeerFlowStandaloneArtifact({
          threadId,
          artifactPath: filepath,
        });

        if (isImage) {
          const blob = await response.blob();
          currentObjectUrl = URL.createObjectURL(blob);
          if (!isCancelled) {
            setObjectUrl(currentObjectUrl);
          }
          return;
        }

        if (support.isTextArtifact) {
          const text = await response.text();
          if (!isCancelled) {
            setContent(text);
          }
          return;
        }

        if (!isCancelled) {
          setErrorMessage("暂不支持该类型在线预览，请下载查看。");
        }
      } catch (error) {
        if (!isCancelled) {
          setErrorMessage(
            error instanceof Error ? error.message : "Failed to load artifact."
          );
        }
      } finally {
        if (!isCancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadArtifact();

    return () => {
      isCancelled = true;
      if (currentObjectUrl) {
        URL.revokeObjectURL(currentObjectUrl);
      }
    };
  }, [filepath, isImage, support.isTextArtifact, threadId]);

  const handleDownload = useCallback(async () => {
    try {
      const response = await fetchDeerFlowStandaloneArtifact({
        threadId,
        artifactPath: filepath,
        download: true,
      });
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      link.click();
      URL.revokeObjectURL(url);
      toast.success("已开始下载");
    } catch {
      toast.error("下载失败");
    }
  }, [fileName, filepath, threadId]);

  const handleCopy = useCallback(async () => {
    if (!content) {
      return;
    }

    try {
      await navigator.clipboard.writeText(content);
      toast.success("已复制到剪贴板");
    } catch {
      toast.error("复制失败");
    }
  }, [content]);

  const handleOpenNewWindow = useCallback(() => {
    if (support.isTextArtifact && content) {
      if (support.previewLanguage === "html") {
        openTextInNewTab(content, "text/html");
        return;
      }

      if (support.previewLanguage === "markdown") {
        openTextInNewTab(content, "text/markdown");
        return;
      }

      openTextInNewTab(content, "text/plain");
      return;
    }

    if (isImage && objectUrl) {
      window.open(objectUrl, "_blank", "noopener,noreferrer");
    }
  }, [content, isImage, objectUrl, support.isTextArtifact, support.previewLanguage]);

  const showAssetToolbarActions =
    !isLoading && !errorMessage && (Boolean(content) || Boolean(objectUrl));

  return (
    <TooltipProvider delayDuration={300}>
      <div
        className={cn(
          "bg-background flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden rounded-lg border shadow-md"
        )}
      >
        <div className="bg-muted/50 flex shrink-0 items-center justify-between gap-2 border-b px-2 py-2.5">
          <div className="min-w-0 flex-1">
            {fileOptions.length > 1 ? (
              <Select
                value={filepath}
                onValueChange={(value) => {
                  select(value);
                }}
              >
                <SelectTrigger className="h-9 max-w-[200px] border-none bg-transparent shadow-none focus:ring-0 md:max-w-[240px]">
                  <SelectValue placeholder="选择文件" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {fileOptions.map((path) => (
                      <SelectItem key={path} value={path}>
                        {getArtifactFileName(path)}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            ) : (
              <div className="text-foreground truncate px-2 text-sm font-medium">{fileName}</div>
            )}
          </div>

          <div className="flex shrink-0 items-center justify-center">
            {support.isPreviewable ? (
              <div className="inline-flex rounded-md border border-input bg-background shadow-sm">
                <Button
                  className={cn(
                    "size-8 rounded-r-none",
                    viewMode === "code" ? "bg-muted" : "bg-transparent"
                  )}
                  size="icon"
                  type="button"
                  variant="ghost"
                  onClick={() => setViewMode("code")}
                >
                  <Code2Icon className="size-4" />
                  <span className="sr-only">源码模式</span>
                </Button>
                <Button
                  className={cn(
                    "size-8 rounded-l-none border-l border-input",
                    viewMode === "preview" ? "bg-muted" : "bg-transparent"
                  )}
                  size="icon"
                  type="button"
                  variant="ghost"
                  onClick={() => setViewMode("preview")}
                >
                  <EyeIcon className="size-4" />
                  <span className="sr-only">预览模式</span>
                </Button>
              </div>
            ) : null}
          </div>

          <div className="flex shrink-0 items-center gap-0.5">
            {showAssetToolbarActions ? (
              <>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      className="size-8"
                      disabled={
                        support.isTextArtifact ? !content : isImage ? !objectUrl : true
                      }
                      size="icon"
                      type="button"
                      variant="ghost"
                      onClick={() => handleOpenNewWindow()}
                    >
                      <SquareArrowOutUpRightIcon className="size-4" />
                      <span className="sr-only">新窗口打开</span>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">新窗口打开</TooltipContent>
                </Tooltip>

                {support.isTextArtifact ? (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        className="size-8"
                        disabled={!content}
                        size="icon"
                        type="button"
                        variant="ghost"
                        onClick={() => void handleCopy()}
                      >
                        <CopyIcon className="size-4" />
                        <span className="sr-only">复制</span>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">复制</TooltipContent>
                  </Tooltip>
                ) : null}

              </>
            ) : null}

            {!isLoading ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    className="size-8"
                    size="icon"
                    type="button"
                    variant="ghost"
                    onClick={() => void handleDownload()}
                  >
                    <DownloadIcon className="size-4" />
                    <span className="sr-only">下载</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom">下载</TooltipContent>
              </Tooltip>
            ) : null}

            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  className="size-8"
                  size="icon"
                  type="button"
                  variant="ghost"
                  onClick={() => setOpen(false)}
                >
                  <XIcon className="size-4" />
                  <span className="sr-only">关闭侧栏</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">关闭</TooltipContent>
            </Tooltip>
          </div>
        </div>

        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
          {isLoading ? (
            <div className="flex min-h-[240px] flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              加载中…
            </div>
          ) : null}

          {!isLoading && errorMessage ? (
            <div className="flex min-h-[240px] flex-1 flex-col items-center justify-center gap-3 p-6 text-center text-sm text-muted-foreground">
              <FileTextIcon className="size-6" />
              <div>{errorMessage}</div>
              <Button size="sm" type="button" variant="outline" onClick={() => void handleDownload()}>
                <DownloadIcon className="mr-2 size-4" />
                下载
              </Button>
            </div>
          ) : null}

          {!isLoading && isImage && objectUrl ? (
            <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto p-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img alt={fileName} className="max-h-full max-w-full rounded-md" src={objectUrl} />
            </div>
          ) : null}

          {!isLoading && support.isTextArtifact && !isImage && !errorMessage ? (
            <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
              {support.isPreviewable &&
              viewMode === "preview" &&
              support.previewLanguage ? (
                <DeerFlowArtifactPreviewPane
                  content={content}
                  language={support.previewLanguage}
                />
              ) : (
                <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words p-4 font-mono text-xs leading-relaxed text-foreground">
                  {content}
                </pre>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </TooltipProvider>
  );
}
