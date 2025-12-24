/**
 * Stores - 统一导出
 * 
 * 所有 Zustand 全局状态管理 Store
 */

export { useAuthStore } from './auth-store';

export { useRoadmapStore } from './roadmap-store';
export type { RoadmapStore, RoadmapState, RoadmapActions, GenerationPhase, TutorialProgress } from './roadmap-store';

export { useChatStore } from './chat-store';
export type { ChatStore, ChatState, ChatActions, Message } from './chat-store';

export { useUIStore } from './ui-store';
export type { UIStore, UIState, UIActions, ViewMode, DialogState } from './ui-store';

export { useLearningStore } from './learning-store';
export type {
  LearningStore,
  LearningState,
  LearningActions,
  LearningProgress,
  LearningPreferences,
} from './learning-store';

export { useUserProfileStore } from './user-profile-store';
export type { UserProfileState } from './user-profile-store';
