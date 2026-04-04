"use client";

import { CopyIcon, DownloadIcon, Loader2, Maximize2Icon } from "lucide-react";
import { useCallback, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type MermaidShellStatus = "ok" | "loading" | "error";

/**
 * Mermaid 代码块外壳：亮色画布 + 复制源码 / 下载 SVG / 全屏预览（与产物侧栏工具栏行为对齐）。
 */
export function MermaidStreamdownShell({
  source,
  status,
  errorMessage,
  svgHtml,
}: {
  /** 原始 Mermaid 源码（用于复制） */
  source: string;
  status: MermaidShellStatus;
  errorMessage?: string;
  /** 已渲染的 SVG 文档字符串；loading / error 时可为 null */
  svgHtml: string | null;
}) {
  const [fullscreenOpen, setFullscreenOpen] = useState(false);

  const handleCopy = useCallback(async () => {
    if (!source.trim()) {
      return;
    }
    try {
      await navigator.clipboard.writeText(source);
      toast.success("已复制 Mermaid 源码");
    } catch {
      toast.error("复制失败");
    }
  }, [source]);

  const handleDownloadSvg = useCallback(() => {
    if (!svgHtml) {
      return;
    }
    try {
      const blob = new Blob([svgHtml], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "mermaid-diagram.svg";
      link.click();
      URL.revokeObjectURL(url);
      toast.success("已开始下载 SVG");
    } catch {
      toast.error("下载失败");
    }
  }, [svgHtml]);

  const canUseSvg = status === "ok" && Boolean(svgHtml);

  return (
    <TooltipProvider delayDuration={300}>
      <div
        className={cn(
          "border-border/60 my-4 overflow-hidden rounded-lg border border-slate-200 bg-[#FAFAFA] shadow-sm"
        )}
      >
        <div className="flex justify-end gap-0.5 border-b border-slate-200/80 bg-white/95 px-1.5 py-1 backdrop-blur-sm">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                className="size-8"
                disabled={!source.trim()}
                size="icon"
                type="button"
                variant="ghost"
                onClick={() => void handleCopy()}
              >
                <CopyIcon className="size-4" />
                <span className="sr-only">复制源码</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">复制 Mermaid 源码</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                className="size-8"
                disabled={!canUseSvg}
                size="icon"
                type="button"
                variant="ghost"
                onClick={() => handleDownloadSvg()}
              >
                <DownloadIcon className="size-4" />
                <span className="sr-only">下载 SVG</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">下载 SVG</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                className="size-8"
                disabled={!canUseSvg}
                size="icon"
                type="button"
                variant="ghost"
                onClick={() => setFullscreenOpen(true)}
              >
                <Maximize2Icon className="size-4" />
                <span className="sr-only">全屏预览</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">全屏预览</TooltipContent>
          </Tooltip>
        </div>

        <div className="max-h-[min(70vh,640px)] min-h-[200px] overflow-auto p-3">
          {status === "loading" ? (
            <div className="text-muted-foreground flex min-h-[160px] items-center justify-center gap-2 text-sm">
              <Loader2 className="size-4 animate-spin" />
              Mermaid 渲染中（官方引擎）…
            </div>
          ) : null}

          {status === "error" ? (
            <div className="text-destructive space-y-2 text-sm">
              <div className="font-medium">Mermaid 渲染失败</div>
              {errorMessage ? (
                <p className="text-muted-foreground text-xs">{errorMessage}</p>
              ) : null}
              <pre className="bg-muted/40 text-foreground max-h-48 overflow-auto rounded-md p-2 font-mono text-xs whitespace-pre-wrap">
                {source}
              </pre>
            </div>
          ) : null}

          {status === "ok" && svgHtml ? (
            <div
              className="text-slate-900 [&_svg]:max-w-none flex justify-center [&_svg]:text-slate-900"
              // 隔离父级 prose 的 color/currentColor，避免节点文字被压成与填充同色
              style={{ color: "#0f172a" }}
              dangerouslySetInnerHTML={{ __html: svgHtml }}
            />
          ) : null}
        </div>
      </div>

      <Dialog open={fullscreenOpen} onOpenChange={setFullscreenOpen}>
        <DialogContent
          className="flex max-h-[92vh] max-w-[min(96vw,1280px)] w-full flex-col gap-2 overflow-hidden p-4 sm:max-w-[min(96vw,1280px)]"
          onOpenAutoFocus={(event) => event.preventDefault()}
        >
          <DialogHeader className="shrink-0 space-y-1 pr-8 text-left">
            <DialogTitle>Mermaid 全屏预览</DialogTitle>
          </DialogHeader>
          <div className="bg-muted/30 min-h-0 flex-1 overflow-auto rounded-md border border-slate-200 p-4">
            {svgHtml ? (
              <div
                className="text-slate-900 [&_svg]:max-w-none flex min-h-[50vh] justify-center [&_svg]:text-slate-900"
                style={{ color: "#0f172a" }}
                dangerouslySetInnerHTML={{ __html: svgHtml }}
              />
            ) : null}
          </div>
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
}
