"use client";

/**
 * 根据文件路径提取文件名。
 */
export function getArtifactFileName(path: string): string {
  return path.split("/").filter(Boolean).pop() || path;
}

/**
 * 获取文件扩展名。
 */
export function getArtifactFileExtension(path: string): string {
  return getArtifactFileName(path).split(".").pop()?.toLowerCase() || "";
}

/**
 * 产物扩展名的展示文案（与 Deer-Flow 官方 `getFileExtensionDisplayName` 对齐）。
 */
export function getArtifactExtensionDisplayName(path: string): string {
  const fileName = getArtifactFileName(path);
  const segments = fileName.split(".");
  if (segments.length < 2) {
    return "FILE";
  }
  const extension = segments.pop()!.toLowerCase();
  switch (extension) {
    case "doc":
    case "docx":
      return "Word";
    case "md":
    case "markdown":
      return "Markdown";
    case "txt":
      return "Text";
    case "ppt":
    case "pptx":
      return "PowerPoint";
    case "xls":
    case "xlsx":
      return "Excel";
    default:
      return extension.toUpperCase();
  }
}

/**
 * 判断是否为图片类产物。
 */
export function isArtifactImage(path: string): boolean {
  return ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp"].includes(
    getArtifactFileExtension(path)
  );
}

/**
 * 判断是否为文本类产物。
 */
export function isArtifactText(path: string): boolean {
  return [
    "md",
    "txt",
    "py",
    "ts",
    "tsx",
    "js",
    "jsx",
    "json",
    "yaml",
    "yml",
    "html",
    "htm",
    "css",
    "xml",
    "sql",
    "sh",
  ].includes(getArtifactFileExtension(path));
}

/**
 * 产物预览能力（与官方 `artifact-file-detail` 的 markdown / html 预览一致）。
 */
export type DeerFlowArtifactPreviewLanguage = "markdown" | "html";

export interface DeerFlowArtifactPreviewSupport {
  /** 是否提供「源码 / 预览」切换 */
  isPreviewable: boolean;
  /** 预览渲染方式；不可预览时为 null */
  previewLanguage: DeerFlowArtifactPreviewLanguage | null;
  /** 是否按文本拉取并展示源码区 */
  isTextArtifact: boolean;
}

/**
 * 根据路径判断预览与文本类型。
 *
 * Args:
 *   path: 产物路径或 `/mnt/...` 形式
 *
 * Returns:
 *   预览与文本标志
 */
export function getArtifactPreviewSupport(path: string): DeerFlowArtifactPreviewSupport {
  const ext = getArtifactFileExtension(path);

  if (ext === "md" || ext === "markdown") {
    return {
      isPreviewable: true,
      previewLanguage: "markdown",
      isTextArtifact: true,
    };
  }

  if (ext === "html" || ext === "htm") {
    return {
      isPreviewable: true,
      previewLanguage: "html",
      isTextArtifact: true,
    };
  }

  if (isArtifactImage(path)) {
    return {
      isPreviewable: false,
      previewLanguage: null,
      isTextArtifact: false,
    };
  }

  if (isArtifactText(path)) {
    return {
      isPreviewable: false,
      previewLanguage: null,
      isTextArtifact: true,
    };
  }

  return {
    isPreviewable: false,
    previewLanguage: null,
    isTextArtifact: false,
  };
}
