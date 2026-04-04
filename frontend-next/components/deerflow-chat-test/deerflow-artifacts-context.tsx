"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

/**
 * Deer-Flow artifacts 状态上下文。
 */
export interface DeerFlowArtifactsContextValue {
  artifacts: string[];
  setArtifacts: (artifacts: string[]) => void;
  selectedArtifact: string | null;
  select: (artifact: string) => void;
  deselect: () => void;
  open: boolean;
  setOpen: (open: boolean) => void;
}

const DeerFlowArtifactsContext = createContext<DeerFlowArtifactsContextValue | undefined>(
  undefined
);

/**
 * Artifacts Provider 属性。
 */
interface DeerFlowArtifactsProviderProps {
  children: ReactNode;
}

/**
 * Deer-Flow 测试页 artifacts provider。
 */
export function DeerFlowArtifactsProvider({
  children,
}: DeerFlowArtifactsProviderProps) {
  const [artifacts, setArtifacts] = useState<string[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  const select = useCallback((artifact: string) => {
    setSelectedArtifact(artifact);
    setOpen(true);
  }, []);

  const deselect = useCallback(() => {
    setSelectedArtifact(null);
    setOpen(false);
  }, []);

  const value = useMemo<DeerFlowArtifactsContextValue>(
    () => ({
      artifacts,
      setArtifacts,
      selectedArtifact,
      select,
      deselect,
      open,
      setOpen,
    }),
    [artifacts, deselect, open, select, selectedArtifact]
  );

  return (
    <DeerFlowArtifactsContext.Provider value={value}>
      {children}
    </DeerFlowArtifactsContext.Provider>
  );
}

/**
 * 读取当前 artifacts 上下文。
 */
export function useDeerFlowArtifacts(): DeerFlowArtifactsContextValue {
  const context = useContext(DeerFlowArtifactsContext);
  if (!context) {
    throw new Error("useDeerFlowArtifacts must be used within DeerFlowArtifactsProvider");
  }
  return context;
}
