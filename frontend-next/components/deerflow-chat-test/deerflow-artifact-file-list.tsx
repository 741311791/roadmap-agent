"use client";

import { DownloadIcon } from "lucide-react";

import { useDeerFlowArtifacts } from "@/components/deerflow-chat-test/deerflow-artifacts-context";
import { DeerFlowArtifactFileIcon } from "@/components/deerflow-chat-test/deerflow-artifact-file-icon";
import { fetchDeerFlowStandaloneArtifact } from "@/components/deerflow-chat-test/deerflow-standalone-api";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

import {
  getArtifactExtensionDisplayName,
  getArtifactFileName,
} from "./deerflow-artifact-utils";

/**
 * 产物文件列表（布局与 Deer-Flow 官方 `artifact-file-list.tsx` 一致）。
 */
export function DeerFlowArtifactFileList({
  className,
  files,
  threadId,
}: {
  className?: string;
  files: string[];
  threadId: string;
}) {
  const { select, setOpen } = useDeerFlowArtifacts();

  return (
    <ul className={cn("flex w-full flex-col gap-4", className)}>
      {files.map((file) => (
        <li key={file} className="w-full">
          <Card
            className="relative cursor-pointer gap-0 p-3 shadow-sm"
            onClick={() => {
              select(file);
              setOpen(true);
            }}
          >
            <div className="grid w-full grid-cols-1 items-start gap-2 pr-2 pl-1 sm:grid-cols-[1fr_auto]">
              <div className="min-w-0">
                <div className="relative pl-8">
                  <div className="absolute top-2 -left-0.5 shrink-0">
                    <DeerFlowArtifactFileIcon
                      path={file}
                      className="size-6 text-muted-foreground"
                    />
                  </div>
                  <div className="truncate text-sm font-semibold leading-none">
                    {getArtifactFileName(file)}
                  </div>
                </div>
                <p className="pl-8 text-xs text-muted-foreground">
                  {getArtifactExtensionDisplayName(file)} file
                </p>
              </div>
              <div className="flex justify-end sm:row-span-2 sm:justify-start sm:self-start sm:pt-0.5">
                <Button
                  size="sm"
                  type="button"
                  variant="ghost"
                  onClick={async (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    const response = await fetchDeerFlowStandaloneArtifact({
                      threadId,
                      artifactPath: file,
                      download: true,
                    });
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement("a");
                    link.href = url;
                    link.download = getArtifactFileName(file);
                    link.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  <DownloadIcon className="size-4" />
                  Download
                </Button>
              </div>
            </div>
          </Card>
        </li>
      ))}
    </ul>
  );
}
