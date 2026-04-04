"use client";

import { renderMermaidSVG, THEMES } from "beautiful-mermaid";
import { memo, useEffect, useMemo, useState } from "react";
import {
  Streamdown,
  type CustomRenderer,
  type CustomRendererProps,
  type StreamdownProps,
} from "streamdown";

import { MermaidStreamdownShell } from "@/components/markdown/mermaid-streamdown-shell";
import { renderOfficialMermaidSvg } from "@/lib/mermaid-official-render";
import { cn } from "@/lib/utils";

type MermaidBlockState =
  | { kind: "idle" }
  | { kind: "beautiful"; svg: string }
  | { kind: "fallback" };

/** 产物 / Streamdown 内 Mermaid：固定亮色主题，避免 CSS 变量在 SVG 内解析异常导致「一团黑」。 */
const MERMAID_LIGHT_THEME = {
  ...THEMES["github-light"],
  transparent: false,
  font: "ui-sans-serif, system-ui, sans-serif",
} as const;

/**
 * Streamdown 的 mermaid 代码块：优先 beautiful-mermaid（亮色 github-light）；不支持时回退官方 mermaid（同样固定亮色）。
 */
const BeautifulMermaidStreamdownBlock = memo(function BeautifulMermaidStreamdownBlock({
  code,
  isIncomplete,
}: CustomRendererProps) {
  const trimmed = code.trim();

  const blockState = useMemo((): MermaidBlockState => {
    if (!trimmed || isIncomplete) {
      return { kind: "idle" };
    }
    try {
      return {
        kind: "beautiful",
        svg: renderMermaidSVG(trimmed, { ...MERMAID_LIGHT_THEME }),
      };
    } catch {
      return { kind: "fallback" };
    }
  }, [trimmed, isIncomplete]);

  const [officialSvg, setOfficialSvg] = useState<string | null>(null);
  const [officialError, setOfficialError] = useState<string | null>(null);
  const [officialLoading, setOfficialLoading] = useState(false);

  useEffect(() => {
    if (blockState.kind !== "fallback" || isIncomplete || !trimmed) {
      setOfficialSvg(null);
      setOfficialError(null);
      setOfficialLoading(false);
      return;
    }

    let cancelled = false;
    setOfficialLoading(true);
    setOfficialError(null);
    setOfficialSvg(null);

    void renderOfficialMermaidSvg(trimmed)
      .then((svg) => {
        if (!cancelled) {
          setOfficialSvg(svg);
          setOfficialError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setOfficialSvg(null);
          setOfficialError(err instanceof Error ? err.message : String(err));
        }
      })
      .finally(() => {
        if (!cancelled) {
          setOfficialLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [blockState.kind, trimmed, isIncomplete]);

  if (isIncomplete) {
    return (
      <div
        className={cn(
          "border-border/60 bg-muted/20 my-4 rounded-lg border border-dashed p-4"
        )}
      >
        <div className="text-muted-foreground mb-2 text-xs font-medium">Mermaid（流式输出中）</div>
        <pre className="text-foreground max-h-56 overflow-auto font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
          {code || "…"}
        </pre>
      </div>
    );
  }

  if (!trimmed) {
    return null;
  }

  if (blockState.kind === "beautiful") {
    return (
      <MermaidStreamdownShell source={trimmed} status="ok" svgHtml={blockState.svg} />
    );
  }

  if (blockState.kind === "fallback") {
    if (officialLoading) {
      return (
        <MermaidStreamdownShell source={trimmed} status="loading" svgHtml={null} />
      );
    }
    if (officialError) {
      return (
        <MermaidStreamdownShell
          source={trimmed}
          status="error"
          errorMessage={officialError}
          svgHtml={null}
        />
      );
    }
    if (officialSvg) {
      return (
        <MermaidStreamdownShell source={trimmed} status="ok" svgHtml={officialSvg} />
      );
    }
  }

  return null;
});

BeautifulMermaidStreamdownBlock.displayName = "BeautifulMermaidStreamdownBlock";

const BEAUTIFUL_MERMAID_RENDERERS: CustomRenderer[] = [
  { language: "mermaid", component: BeautifulMermaidStreamdownBlock },
];

/**
 * 合并插件配置，追加 Mermaid 自定义渲染器（保留调用方已有 renderers）。
 */
function mergeStreamdownPlugins(
  plugins: StreamdownProps["plugins"] | undefined
): StreamdownProps["plugins"] {
  const existing = plugins?.renderers ?? [];
  return {
    ...plugins,
    renderers: [...existing, ...BEAUTIFUL_MERMAID_RENDERERS],
  };
}

/**
 * RichStreamdown：在 Streamdown 上启用 Mermaid（beautiful-mermaid，失败时回退官方 mermaid）。
 */
export function RichStreamdown({ plugins, ...rest }: StreamdownProps) {
  return <Streamdown plugins={mergeStreamdownPlugins(plugins)} {...rest} />;
}
