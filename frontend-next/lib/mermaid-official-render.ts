"use client";

import mermaid from "mermaid";

/**
 * Streamdown / 产物预览用：固定亮色主题变量（不跟随 `html.dark`，避免流程图填色与文字对比异常）。
 */
const THEME_VARIABLES_LIGHT = {
  primaryColor: "#4f46e5",
  primaryTextColor: "#ffffff",
  primaryBorderColor: "#4338ca",
  lineColor: "#64748b",
  secondaryColor: "#7c3aed",
  tertiaryColor: "#0891b2",
  background: "#ffffff",
  mainBkg: "#f8fafc",
  secondaryBkg: "#f1f5f9",
  tertiaryBkg: "#e2e8f0",
  textColor: "#0f172a",
  actorBkg: "#f8fafc",
  actorBorder: "#4f46e5",
  actorTextColor: "#0f172a",
  actorLineColor: "#64748b",
  signalColor: "#0f172a",
  signalTextColor: "#0f172a",
  labelBoxBkgColor: "#f8fafc",
  labelBoxBorderColor: "#4f46e5",
  labelTextColor: "#0f172a",
  loopTextColor: "#0f172a",
  noteBkgColor: "#fef9c3",
  noteTextColor: "#854d0e",
  noteBorderColor: "#eab308",
  activationBkgColor: "#e0e7ff",
  activationBorderColor: "#6366f1",
  sequenceNumberColor: "#ffffff",
} as const;

/**
 * 使用官方 mermaid 将源码渲染为 SVG 字符串（固定亮色主题 + SVG 后处理）。
 *
 * Args:
 *   chart: 完整 Mermaid 源码
 *
 * Returns:
 *   序列化后的 SVG 文档字符串
 *
 * Raises:
 *   Error: 解析失败或 render 抛错
 */
export async function renderOfficialMermaidSvg(chart: string): Promise<string> {
  mermaid.initialize({
    startOnLoad: false,
    theme: "neutral",
    themeVariables: { ...THEME_VARIABLES_LIGHT },
    fontFamily: "ui-sans-serif, system-ui, sans-serif",
    securityLevel: "loose",
  });

  const parseResult = await mermaid.parse(chart, { suppressErrors: true });
  if (parseResult === false) {
    throw new Error("Mermaid 语法校验未通过（内容可能仍在流式生成中）");
  }

  const id = `streamdown-mermaid-${Math.random().toString(36).slice(2, 11)}`;
  const { svg } = await mermaid.render(id, chart);

  const parser = new DOMParser();
  const doc = parser.parseFromString(svg, "image/svg+xml");
  const svgEl = doc.querySelector("svg");
  if (svgEl) {
    const bgColor = "#ffffff";
    svgEl.style.backgroundColor = bgColor;
    svgEl.style.maxWidth = "none";
    svgEl.style.display = "block";

    const firstRect = svgEl.querySelector("rect");
    if (firstRect) {
      const fill = firstRect.getAttribute("fill");
      if (fill === "#1f2020" || fill === "rgb(31, 32, 32)") {
        firstRect.setAttribute("fill", bgColor);
      }
    }
  }

  return new XMLSerializer().serializeToString(doc.documentElement);
}
