/**
 * 路线图状态管理 Store
 * 使用 Zustand 管理全局路线图状态
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { RoadmapFramework } from '@/types/generated/models';
import type { RoadmapHistory } from '@/types/custom/store';

/**
 * 生成阶段
 */
export type GenerationPhase = 
  | 'idle'
  | 'intent_analysis'
  | 'curriculum_design'
  | 'structure_validation'
  | 'human_review'
  | 'content_generation'
  | 'completed'
  | 'failed';

/**
 * 学习进度
 */
export interface TutorialProgress {
  completed: number;
  total: number;
}

/**
 * 路线图 Store 状态
 */
export interface RoadmapState {
  // 基础状态
  currentRoadmap: RoadmapFramework | null;
  isLoading: boolean;
  error: string | null;

  // 生成状态
  isGenerating: boolean;
  generationProgress: number;
  currentStep: string | null;
  generationPhase: GenerationPhase;
  generationBuffer: string;

  // 教程进度
  tutorialProgress: TutorialProgress;

  // 实时生成追踪
  activeTaskId: string | null;
  activeGenerationPhase: GenerationPhase | null;
  isLiveGenerating: boolean;

  // 历史记录
  history: RoadmapHistory[];

  // 选中的概念
  selectedConceptId: string | null;

  // 学习进度映射
  conceptProgressMap: Record<string, boolean>; // concept_id -> is_completed
}

/**
 * 路线图 Store Actions
 */
export interface RoadmapActions {
  // 基础操作
  setRoadmap: (roadmap: RoadmapFramework | null) => void;
  clearRoadmap: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;

  // 生成状态管理
  setGenerating: (generating: boolean) => void;
  updateProgress: (step: string, progress: number) => void;

  // 历史记录
  setHistory: (history: RoadmapHistory[]) => void;
  addToHistory: (roadmap: RoadmapHistory) => void;

  // 概念选择
  selectConcept: (conceptId: string | null) => void;

  // 概念状态更新
  updateConceptStatus: (
    conceptId: string,
    status: {
      content_status?: string;  // 教程状态（匹配 Concept 类型的字段名）
      resources_status?: string;
      quiz_status?: string;
    }
  ) => void;

  // 生成流式状态
  setGenerationPhase: (phase: GenerationPhase) => void;
  appendGenerationBuffer: (chunk: string) => void;
  clearGenerationBuffer: () => void;
  updateTutorialProgress: (completed: number, total: number) => void;

  // 实时生成追踪
  setActiveTask: (taskId: string | null) => void;
  setActiveGenerationPhase: (phase: GenerationPhase | null) => void;
  setLiveGenerating: (isLive: boolean) => void;
  clearLiveGeneration: () => void;

  // 学习进度管理
  setConceptProgressMap: (progressMap: Record<string, boolean>) => void;
  updateConceptProgress: (conceptId: string, isCompleted: boolean) => void;
}

/**
 * 路线图 Store 类型
 */
export type RoadmapStore = RoadmapState & RoadmapActions;

/**
 * 创建路线图 Store
 * 生产环境优化：移除 devtools 中间件，减少运行时开销
 */
const storeImplementation = (set: any, get: any): RoadmapStore => ({
        // 初始状态
        currentRoadmap: null,
        isLoading: false,
        error: null,
        isGenerating: false,
        generationProgress: 0,
        currentStep: null,
        generationPhase: 'idle',
        generationBuffer: '',
        tutorialProgress: { completed: 0, total: 0 },
        activeTaskId: null,
        activeGenerationPhase: null,
        isLiveGenerating: false,
        history: [],
        selectedConceptId: null,
        conceptProgressMap: {},

        // 基础操作
        setRoadmap: (roadmap: RoadmapFramework | null) => set((state: RoadmapStore) => {
          // 如果切换了路线图，清除选中的概念
          const isNewRoadmap = roadmap && state.currentRoadmap && 
                               roadmap.roadmap_id !== state.currentRoadmap.roadmap_id;
          return {
            currentRoadmap: roadmap,
            selectedConceptId: isNewRoadmap ? null : state.selectedConceptId,
          };
        }),

        clearRoadmap: () =>
          set({
            currentRoadmap: null,
            selectedConceptId: null,
          }),

        setLoading: (loading: boolean) => set({ isLoading: loading }),

        setError: (error: string | null) => set({ error }),

        // 生成状态管理
        setGenerating: (generating: boolean) =>
          set({
            isGenerating: generating,
            ...(generating ? {} : { generationProgress: 0, currentStep: null }),
          }),

        updateProgress: (step: string, progress: number) =>
          set({
            currentStep: step,
            generationProgress: progress,
          }),

        // 历史记录
        setHistory: (history: RoadmapHistory[]) => set({ history }),

        addToHistory: (roadmap: RoadmapHistory) =>
          set((state: RoadmapStore) => ({
            history: [roadmap, ...state.history],
          })),

        // 概念选择
        selectConcept: (conceptId: string | null) => set({ selectedConceptId: conceptId }),

        // 概念状态更新
        updateConceptStatus: (
          conceptId: string,
          status: {
            content_status?: string;
            resources_status?: string;
            quiz_status?: string;
          }
        ) =>
          set((state: RoadmapStore) => {
            if (!state.currentRoadmap) return {}; // 返回空对象,不触发更新

            const updatedRoadmap = { ...state.currentRoadmap };

            // 查找并更新概念
            for (const stage of updatedRoadmap.stages) {
              for (const module of stage.modules) {
                const concept = module.concepts.find(
                  (c) => c.concept_id === conceptId
                );
                if (concept) {
                  Object.assign(concept, status);
                  break;
                }
              }
            }

            return { currentRoadmap: updatedRoadmap };
          }),

        // 生成流式状态
        setGenerationPhase: (phase: GenerationPhase) => set({ generationPhase: phase }),

        appendGenerationBuffer: (chunk: string) =>
          set((state: RoadmapStore) => ({
            generationBuffer: state.generationBuffer + chunk,
          })),

        clearGenerationBuffer: () => set({ generationBuffer: '' }),

        updateTutorialProgress: (completed: number, total: number) =>
          set({
            tutorialProgress: { completed, total },
          }),

        // 实时生成追踪
        setActiveTask: (taskId: string | null) => set({ activeTaskId: taskId }),

        setActiveGenerationPhase: (phase: GenerationPhase | null) =>
          set({ activeGenerationPhase: phase }),

        setLiveGenerating: (isLive: boolean) => set({ isLiveGenerating: isLive }),

        clearLiveGeneration: () =>
          set({
            activeTaskId: null,
            activeGenerationPhase: null,
            isLiveGenerating: false,
          }),

        // 学习进度管理
        setConceptProgressMap: (progressMap: Record<string, boolean>) => set({ conceptProgressMap: progressMap }),

        updateConceptProgress: (conceptId: string, isCompleted: boolean) =>
          set((state: RoadmapStore) => ({
            conceptProgressMap: {
              ...state.conceptProgressMap,
              [conceptId]: isCompleted,
            },
          })),
});

const persistConfig = {
  name: 'roadmap-storage',
  // 仅持久化部分状态
  partialize: (state: RoadmapState) => ({
    history: state.history.slice(0, 10), // 限制历史记录数量，避免存储过大
    // 不持久化 selectedConceptId，因为它与特定路线图关联，切换路线图时应该重置
  }),
  version: 1, // 版本控制，便于未来迁移
};

// 根据环境选择是否使用 devtools
export const useRoadmapStore = 
  process.env.NODE_ENV === 'development'
    ? create<RoadmapStore>()(devtools(persist(storeImplementation, persistConfig), {
        name: 'RoadmapStore',
      }))
    : create<RoadmapStore>()(persist(storeImplementation, persistConfig));
