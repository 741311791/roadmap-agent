"use client";

import { createContext, useContext } from "react";

import type { DeerFlowChatMessage } from "@/components/deerflow-chat-test/deerflow-chat-state";

export interface DeerFlowTodo {
  id: string;
  content: string;
  status: string;
}

/**
 * Deer-Flow 线程状态。
 */
export interface DeerFlowThreadState {
  id: string;
  title: string;
  messages: DeerFlowChatMessage[];
  artifacts: string[];
  todos?: DeerFlowTodo[];
}

/**
 * Deer-Flow 线程上下文值。
 */
export interface DeerFlowThreadContextValue {
  thread: DeerFlowThreadState;
}

const DeerFlowThreadContext = createContext<DeerFlowThreadContextValue | undefined>(
  undefined
);

/**
 * Deer-Flow 线程上下文 Provider。
 */
export const DeerFlowThreadProvider = DeerFlowThreadContext.Provider;

/**
 * 读取当前 Deer-Flow 线程上下文。
 */
export function useDeerFlowThread(): DeerFlowThreadContextValue {
  const context = useContext(DeerFlowThreadContext);
  if (!context) {
    throw new Error("useDeerFlowThread must be used within DeerFlowThreadProvider");
  }
  return context;
}
