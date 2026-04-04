"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

/**
 * Deer-Flow 子任务。
 */
export interface DeerFlowSubtask {
  id: string;
  description?: string;
  status?: string;
  result?: string;
  error?: string;
}

interface DeerFlowSubtasksContextValue {
  tasks: Record<string, DeerFlowSubtask>;
  setTasks: (tasks: Record<string, DeerFlowSubtask>) => void;
}

const DeerFlowSubtasksContext = createContext<DeerFlowSubtasksContextValue>({
  tasks: {},
  setTasks: () => {
    // noop
  },
});

/**
 * Deer-Flow subtasks provider。
 */
export function DeerFlowSubtasksProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [tasks, setTasks] = useState<Record<string, DeerFlowSubtask>>({});

  return (
    <DeerFlowSubtasksContext.Provider value={{ tasks, setTasks }}>
      {children}
    </DeerFlowSubtasksContext.Provider>
  );
}

/**
 * 读取子任务上下文。
 */
export function useDeerFlowSubtasksContext() {
  return useContext(DeerFlowSubtasksContext);
}

/**
 * 更新指定子任务。
 */
export function useUpdateDeerFlowSubtask() {
  const { tasks, setTasks } = useDeerFlowSubtasksContext();

  return useCallback(
    (task: Partial<DeerFlowSubtask> & { id: string }) => {
      setTasks({
        ...tasks,
        [task.id]: {
          ...tasks[task.id],
          ...task,
        },
      });
    },
    [setTasks, tasks]
  );
}
