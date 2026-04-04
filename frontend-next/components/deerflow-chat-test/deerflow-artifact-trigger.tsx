"use client";

import { FilesIcon } from "lucide-react";

import { useDeerFlowArtifacts } from "@/components/deerflow-chat-test/deerflow-artifacts-context";
import { Button } from "@/components/ui/button";

/**
 * Deer-Flow artifacts 面板触发器。
 */
export function DeerFlowArtifactTrigger() {
  const { artifacts, setOpen } = useDeerFlowArtifacts();

  if (artifacts.length === 0) {
    return null;
  }

  return (
    <Button
      className="text-muted-foreground hover:text-foreground"
      type="button"
      variant="ghost"
      onClick={() => setOpen(true)}
    >
      <FilesIcon className="size-4" />
      文件
    </Button>
  );
}
