/**
 * 根据模型的 display name（展示名）解析 Lobe Icons 静态 SVG 地址。
 *
 * 不按 provider 字段选图标；仅当展示名为空时无法匹配，回退为 magic 占位图标。
 *
 * 图标集合与 lobehub/lobe-icons 一致，使用 npm 包 @lobehub/icons-static-svg。
 *
 * Args:
 *   displayName: 后端返回的模型展示名（如 "Doubao-Seed-2.0-Pro"、"Gemini 2.5 Pro (Thinking)"）。
 *
 * Returns:
 *   可直接用于 <img src> 的 HTTPS URL（unpkg CDN，版本与 package.json 锁定一致）。
 */

/** 须与 frontend-next/package.json 中 @lobehub/icons-static-svg 版本保持一致 */
const LOBE_ICONS_STATIC_VERSION = "1.84.0";

const LOBE_ICONS_BASE_URL = `https://unpkg.com/@lobehub/icons-static-svg@${LOBE_ICONS_STATIC_VERSION}/icons`;

/**
 * 展示名归一化：小写、去首尾空格（用于正则匹配）
 */
function normalizeDisplayName(raw: string): string {
  return raw.trim().toLowerCase();
}

/**
 * DISPLAY_NAME_ICON_RULES - 按顺序匹配，先写更具体的规则
 *
 * 说明：
 * - 豆包 / Doubao / 火山 等 → 字节跳动品牌（bytedance-color），不用 doubao 子品牌标
 * - Gemini / PaLM / Bard 等 → 谷歌品牌（google-color）
 */
const DISPLAY_NAME_ICON_RULES: ReadonlyArray<{ test: RegExp; file: string }> = [
  {
    test: /\bdoubao\b|豆包|火山引擎|\bvolcengine\b|字节跳动|\bbytedance\b/i,
    file: "bytedance-color.svg",
  },
  { test: /gemini|palm|bard|deepmind|google/i, file: "google-color.svg" },
  { test: /gpt|openai|o3|o1|o4|chatgpt|codex|davinci|whisper/i, file: "openai.svg" },
  { test: /claude|anthropic/i, file: "anthropic.svg" },
  { test: /deepseek/i, file: "deepseek-color.svg" },
  { test: /qwen|通义|千问|tongyi/i, file: "qwen-color.svg" },
  { test: /kimi|moonshot|月之暗面/i, file: "moonshot.svg" },
  { test: /glm|智谱|zhipu|chatglm/i, file: "zhipu-color.svg" },
  { test: /mistral/i, file: "mistral-color.svg" },
  { test: /llama|meta[\s-]?ai|meta[\s-]llama/i, file: "meta-color.svg" },
  { test: /grok|x\.ai|xai\b/i, file: "xai-color.svg" },
  { test: /cohere/i, file: "cohere-color.svg" },
  { test: /perplexity/i, file: "perplexity-color.svg" },
  { test: /groq/i, file: "groq-color.svg" },
  { test: /vertex/i, file: "vertexai-color.svg" },
  { test: /azure\s*openai|azure/i, file: "azureai-color.svg" },
  { test: /bedrock|aws/i, file: "bedrock-color.svg" },
  { test: /ollama/i, file: "ollama.svg" },
  { test: /openrouter/i, file: "openrouter.svg" },
  { test: /siliconflow|silicon\s*cloud/i, file: "siliconcloud-color.svg" },
  { test: /fireworks/i, file: "fireworks-color.svg" },
];

/**
 * iconFileFromDisplayName - 仅从展示名解析图标文件名
 */
function iconFileFromDisplayName(displayName: string): string | null {
  const n = normalizeDisplayName(displayName);
  if (!n) {
    return null;
  }
  for (const { test, file } of DISPLAY_NAME_ICON_RULES) {
    if (test.test(n)) {
      return file;
    }
  }
  return null;
}

/**
 * getLobeModelIconSrc - 解析模型对应的 Lobe Icons SVG URL（仅依据展示名）
 */
export function getLobeModelIconSrc(displayName: string): string {
  const file = iconFileFromDisplayName(displayName);
  if (file) {
    return `${LOBE_ICONS_BASE_URL}/${file}`;
  }
  return `${LOBE_ICONS_BASE_URL}/magic.svg`;
}

/**
 * getLobeModelIconFallbackSrc - 加载失败时的兜底图标（magic）
 */
export function getLobeModelIconFallbackSrc(): string {
  return `${LOBE_ICONS_BASE_URL}/magic.svg`;
}
