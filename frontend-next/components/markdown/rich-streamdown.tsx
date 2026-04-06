"use client";

import "streamdown/styles.css";

import { code as streamdownShikiCodePlugin } from "@streamdown/code";
import { renderMermaidSVG, THEMES } from "beautiful-mermaid";
import { memo, useEffect, useMemo, useState } from "react";
import {
  Streamdown,
  type BundledTheme,
  type CustomRenderer,
  type CustomRendererProps,
  type LinkSafetyConfig,
  type StreamdownProps,
} from "streamdown";

import { MermaidStreamdownShell } from "@/components/markdown/mermaid-streamdown-shell";
import { StreamdownLinkSafetyModal } from "@/components/markdown/streamdown-link-safety-modal";
import {
  deerflowAssistantMarkdownPlugins,
  deerflowHumanMarkdownPlugins,
} from "@/lib/deerflow-streamdown-plugins";
import { renderOfficialMermaidSvg } from "@/lib/mermaid-official-render";
import { cn } from "@/lib/utils";

/** 与 DeerFlow 官方 MessageResponse / 用户气泡插件策略对齐 */
export type DeerFlowMarkdownProfile = "assistant" | "human";

export type RichStreamdownProps = StreamdownProps & {
  markdownProfile?: DeerFlowMarkdownProfile;
};

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

/** 与 `@streamdown/code` 默认主题一致，供 Streamdown 上下文与 Shiki 双主题着色对齐 */
const DEFAULT_SHIKI_THEMES: [BundledTheme, BundledTheme] = ["github-light", "github-dark"];

/**
 * 合并插件配置：启用 Shiki（@streamdown/code，见 https://shiki.style/），并追加 Mermaid 自定义渲染器。
 */
function mergeStreamdownPlugins(
  plugins: StreamdownProps["plugins"] | undefined
): StreamdownProps["plugins"] {
  const existingRenderers = plugins?.renderers ?? [];
  return {
    ...plugins,
    code: plugins?.code ?? streamdownShikiCodePlugin,
    renderers: [...existingRenderers, ...BEAUTIFUL_MERMAID_RENDERERS],
  };
}

/**
 * 合并 Streamdown `linkSafety`：在未显式关闭且未自定义 `renderModal` 时，使用 Portal + 程序化 `<a>` 打开的弹窗。
 *
 * Args:
 *   user: 调用方传入的 `linkSafety`。
 *
 * Returns:
 *   传入 `Streamdown` 的最终 `linkSafety` 配置。
 *
 * Raises:
 *   无。
 */
function resolveLinkSafety(user?: LinkSafetyConfig): LinkSafetyConfig | undefined {
  if (user?.enabled === false) {
    return user;
  }
  if (user?.renderModal) {
    return user;
  }
  return {
    enabled: user?.enabled ?? true,
    onLinkCheck: user?.onLinkCheck,
    renderModal: (props) => <StreamdownLinkSafetyModal {...props} />,
  };
}

/**
 * RichStreamdown：在 Streamdown 上启用 Mermaid（beautiful-mermaid，失败时回退官方 mermaid）；
 * 默认按 DeerFlow 官方补齐 remark-math / rehype-katex 与（助手侧）内嵌 HTML 管线。
 */
export function RichStreamdown({
  plugins,
  remarkPlugins,
  rehypePlugins,
  markdownProfile = "assistant",
  shikiTheme = DEFAULT_SHIKI_THEMES,
  linkSafety,
  ...rest
}: RichStreamdownProps) {
  const base =
    markdownProfile === "human"
      ? deerflowHumanMarkdownPlugins
      : deerflowAssistantMarkdownPlugins;

  const resolvedLinkSafety = useMemo(() => resolveLinkSafety(linkSafety), [linkSafety]);

  return (
    <Streamdown
      {...rest}
      linkSafety={resolvedLinkSafety}
      remarkPlugins={remarkPlugins ?? base.remarkPlugins}
      rehypePlugins={rehypePlugins ?? base.rehypePlugins}
      shikiTheme={shikiTheme}
      plugins={mergeStreamdownPlugins(plugins)}
    />
  );
}
