/**
 * 学习进度状态管理 Store
 * 使用 Zustand 管理学习进度和用户偏好
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

/**
 * 学习进度
 */
export interface LearningProgress {
  conceptId: string;
  completed: boolean;
  timeSpent: number; // 分钟
  lastVisited: string; // ISO 8601
  score?: number; // 测验分数 (可选)
}

/**
 * 用户学习偏好
 */
export interface LearningPreferences {
  preferredLanguage: string;
  contentType: ('text' | 'video' | 'interactive')[];
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  dailyGoal: number; // 分钟/天
}

/**
 * 学习进度 Store 状态
 */
export interface LearningState {
  // 用户偏好
  preferences: LearningPreferences;

  // 进度追踪
  progress: Record<string, LearningProgress>;

  // 当前位置
  currentConceptId: string | null;
  lastVisitedAt: string | null;

  // 统计
  totalTimeSpent: number; // 总学习时间 (分钟)
  completedConcepts: number; // 完成的概念数
}

/**
 * 学习进度 Store Actions
 */
export interface LearningActions {
  // 偏好设置
  setPreferences: (preferences: Partial<LearningPreferences>) => void;

  // 进度管理
  markConceptComplete: (conceptId: string, score?: number) => void;
  updateTimeSpent: (conceptId: string, minutes: number) => void;
  setCurrentConcept: (conceptId: string) => void;

  // 进度查询
  getProgress: (conceptId: string) => LearningProgress | undefined;
  isConceptCompleted: (conceptId: string) => boolean;

  // 统计
  getTotalProgress: () => {
    totalConcepts: number;
    completedConcepts: number;
    percentage: number;
  };

  // 重置
  resetProgress: () => void;
}

/**
 * 学习进度 Store 类型
 */
export type LearningStore = LearningState & LearningActions;

/**
 * 默认偏好设置
 */
const defaultPreferences: LearningPreferences = {
  preferredLanguage: 'zh-CN',
  contentType: ['text', 'video'],
  difficulty: 'beginner',
  dailyGoal: 60, // 60 分钟/天
};

/**
 * 创建学习进度 Store
 */
export const useLearningStore = create<LearningStore>()(
  devtools(
    persist(
      (set, get) => ({
        // 初始状态
        preferences: defaultPreferences,
        progress: {},
        currentConceptId: null,
        lastVisitedAt: null,
        totalTimeSpent: 0,
        completedConcepts: 0,

        // 偏好设置
        setPreferences: (newPreferences) =>
          set((state) => ({
            preferences: {
              ...state.preferences,
              ...newPreferences,
            },
          })),

        // 进度管理
        markConceptComplete: (conceptId, score) =>
          set((state) => {
            const existing = state.progress[conceptId];
            const wasCompleted = existing?.completed || false;

            return {
              progress: {
                ...state.progress,
                [conceptId]: {
                  conceptId,
                  completed: true,
                  timeSpent: existing?.timeSpent || 0,
                  lastVisited: new Date().toISOString(),
                  score,
                },
              },
              completedConcepts: wasCompleted
                ? state.completedConcepts
                : state.completedConcepts + 1,
            };
          }),

        updateTimeSpent: (conceptId, minutes) =>
          set((state) => {
            const existing = state.progress[conceptId];

            return {
              progress: {
                ...state.progress,
                [conceptId]: {
                  conceptId,
                  completed: existing?.completed || false,
                  timeSpent: (existing?.timeSpent || 0) + minutes,
                  lastVisited: new Date().toISOString(),
                  score: existing?.score,
                },
              },
              totalTimeSpent: state.totalTimeSpent + minutes,
            };
          }),

        setCurrentConcept: (conceptId) =>
          set({
            currentConceptId: conceptId,
            lastVisitedAt: new Date().toISOString(),
          }),

        // 进度查询
        getProgress: (conceptId) => {
          return get().progress[conceptId];
        },

        isConceptCompleted: (conceptId) => {
          return get().progress[conceptId]?.completed || false;
        },

        // 统计
        getTotalProgress: () => {
          const state = get();
          const totalConcepts = Object.keys(state.progress).length;
          const completedConcepts = state.completedConcepts;
          const percentage =
            totalConcepts > 0 ? (completedConcepts / totalConcepts) * 100 : 0;

          return {
            totalConcepts,
            completedConcepts,
            percentage,
          };
        },

        // 重置
        resetProgress: () =>
          set({
            progress: {},
            totalTimeSpent: 0,
            completedConcepts: 0,
            currentConceptId: null,
            lastVisitedAt: null,
          }),
      }),
      {
        name: 'learning-storage',
        // 持久化所有状态
      }
    ),
    {
      name: 'LearningStore',
    }
  )
);
