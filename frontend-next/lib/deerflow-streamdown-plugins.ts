import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import {
  defaultRehypePlugins,
  defaultRemarkPlugins,
  type StreamdownProps,
} from "streamdown";

/**
 * DeerFlow 官方 `streamdownPlugins` 在 Streamdown 2.x 下的等价配置。
 *
 * Streamdown 2.x 默认已包含 `rehype-raw`、sanitize、harden 与 remark-gfm；
 * 此处在其基础上追加 `remark-math` + `rehype-katex`，与官方
 * `deer-flow/frontend/src/core/streamdown/plugins.ts` 的意图一致（GFM、单美元公式、HTML、KaTeX）。
 */
export const deerflowAssistantMarkdownPlugins = {
  remarkPlugins: [
    ...Object.values(defaultRemarkPlugins),
    [remarkMath, { singleDollarTextMath: true }],
  ] as StreamdownProps["remarkPlugins"],
  rehypePlugins: [
    ...Object.values(defaultRehypePlugins),
    [rehypeKatex, { output: "html" }],
  ] as StreamdownProps["rehypePlugins"],
};

/**
 * 用户消息专用：与官方 `humanMessagePlugins` 一致，不包含 remark-gfm，避免自动链接破坏相邻文本。
 */
export const deerflowHumanMarkdownPlugins = {
  remarkPlugins: [
    [remarkMath, { singleDollarTextMath: true }],
  ] as StreamdownProps["remarkPlugins"],
  rehypePlugins: [
    [rehypeKatex, { output: "html" }],
  ] as StreamdownProps["rehypePlugins"],
};
