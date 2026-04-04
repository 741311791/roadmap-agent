"use client";

import {
  BookOpenText,
  Compass,
  FileCode2,
  FileCog,
  FileText,
  FileVideo,
  Image as ImageIcon,
} from "lucide-react";

import {
  getArtifactFileExtension,
  getArtifactFileName,
  isArtifactImage,
  isArtifactText,
} from "./deerflow-artifact-utils";

/**
 * 按扩展名选择图标（对齐 Deer-Flow 官方 `getFileIcon` 规则）。
 */
export function DeerFlowArtifactFileIcon({
  path,
  className,
}: {
  path: string;
  className?: string;
}) {
  const ext = getArtifactFileExtension(path);
  const lowerName = getArtifactFileName(path).toLowerCase();

  if (lowerName.endsWith(".skill") || ext === "skill") {
    return <FileCog className={className} />;
  }
  if (ext === "html" || ext === "htm") {
    return <Compass className={className} />;
  }
  if (ext === "txt" || ext === "md" || ext === "markdown") {
    return <BookOpenText className={className} />;
  }
  if (isArtifactImage(path)) {
    return <ImageIcon className={className} />;
  }
  if (
    [
      "mp3",
      "wav",
      "ogg",
      "aac",
      "m4a",
      "flac",
      "wma",
      "aiff",
      "ape",
      "mp4",
      "mov",
      "m4v",
    ].includes(ext)
  ) {
    return <FileVideo className={className} />;
  }
  if (isArtifactText(path)) {
    return <FileCode2 className={className} />;
  }
  return <FileText className={className} />;
}
