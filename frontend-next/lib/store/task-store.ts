/**
 * 任务状态管理 Store
 * 
 * 专门管理路线图生成任务的状态，从 roadmap-store 中分离出来
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { TaskStore, TaskStoreState, TaskStoreActions } from '@/types/custom/store';

/**
 * 任务 Store 初始状态
 */
const initialState: TaskStoreState = {
  currentTaskId: null,
  taskStatus: null,
  taskProgress: 0,
  taskError: null,
};

/**
 * 任务 Store
 * 
 * 管理路线图生成任务的状态和进度
 */
export const useTaskStore = create<TaskStore>()(
  devtools(
    (set, get) => ({
      // ============================================================
      // State
      // ============================================================
      ...initialState,

      // ============================================================
      // Actions
      // ============================================================

      /**
       * 设置当前任务
       */
      setCurrentTask: (taskId) => {
        set({
          currentTaskId: taskId,
          taskStatus: taskId ? 'pending' : null,
          taskProgress: 0,
          taskError: null,
        });
      },

      /**
       * 更新任务状态
       */
      updateTaskStatus: (status) => {
        set({ taskStatus: status });
        
        // 如果任务完成或失败，重置进度
        if (status === 'completed' || status === 'failed') {
          set({ taskProgress: 100 });
        }
      },

      /**
       * 更新任务进度
       */
      updateTaskProgress: (progress) => {
        set({ taskProgress: Math.max(0, Math.min(100, progress)) });
      },

      /**
       * 设置任务错误
       */
      setTaskError: (error) => {
        set({
          taskError: error,
          taskStatus: error ? 'failed' : get().taskStatus,
        });
      },

      /**
       * 清空任务
       */
      clearTask: () => {
        set(initialState);
      },
    }),
    {
      name: 'task-store',
      enabled: process.env.NODE_ENV === 'development',
    }
  )
);

/**
 * 任务状态选择器（便捷导出）
 */
export const selectTaskId = (state: TaskStore) => state.currentTaskId;
export const selectTaskStatus = (state: TaskStore) => state.taskStatus;
export const selectTaskProgress = (state: TaskStore) => state.taskProgress;
export const selectTaskError = (state: TaskStore) => state.taskError;

