/**
 * Zustand Store类型定义
 */

import type { 
  RoadmapFramework, 
  // ChatMessageResponse, // 暂未实现，注释掉
  Module as GeneratedModule,
  Stage as GeneratedStage,
  Concept as GeneratedConcept,
} from '@/types/generated';
import type { ViewMode } from './ui';

/**
 * 聊天消息（临时定义，待后端实现后使用生成的类型）
 */
export interface ChatMessage {
  message_id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

/**
 * 路线图历史记录项
 */
export interface RoadmapHistory {
  roadmap_id: string;
  title: string;
  created_at: string;
  total_concepts?: number;
  completed_concepts?: number;
  topic?: string;
  status?: string;
}

/**
 * 路线图Store状态
 */
export interface RoadmapStoreState {
  /** 当前路线图 */
  currentRoadmap: RoadmapFramework | null;
  /** 路线图历史列表 */
  history: RoadmapHistory[];
  /** 是否正在生成 */
  isGenerating: boolean;
  /** 生成进度（0-100） */
  progress: number;
  /** 当前步骤 */
  currentStep: string | null;
  /** 错误信息 */
  error: string | null;
  /** 活动的任务ID */
  activeTaskId: string | null;
}

/**
 * 路线图Store操作
 */
export interface RoadmapStoreActions {
  /** 设置当前路线图 */
  setRoadmap: (roadmap: RoadmapFramework | null) => void;
  /** 更新进度 */
  updateProgress: (step: string, progress: number) => void;
  /** 清空路线图 */
  clearRoadmap: () => void;
  /** 设置生成状态 */
  setGenerating: (isGenerating: boolean) => void;
  /** 设置错误 */
  setError: (error: string | null) => void;
  /** 设置活动任务 */
  setActiveTask: (taskId: string | null) => void;
  /** 获取历史记录 */
  fetchHistory: () => Promise<void>;
  /** 设置历史记录 */
  setHistory: (history: RoadmapHistory[]) => void;
}

/**
 * 路线图Store完整类型
 */
export type RoadmapStore = RoadmapStoreState & RoadmapStoreActions;

/**
 * 任务Store状态
 */
export interface TaskStoreState {
  /** 当前任务ID */
  currentTaskId: string | null;
  /** 任务状态 */
  taskStatus: 'pending' | 'processing' | 'completed' | 'failed' | null;
  /** 任务进度 */
  taskProgress: number;
  /** 任务错误信息 */
  taskError: string | null;
}

/**
 * 任务Store操作
 */
export interface TaskStoreActions {
  /** 设置当前任务 */
  setCurrentTask: (taskId: string | null) => void;
  /** 更新任务状态 */
  updateTaskStatus: (status: TaskStoreState['taskStatus']) => void;
  /** 更新任务进度 */
  updateTaskProgress: (progress: number) => void;
  /** 设置任务错误 */
  setTaskError: (error: string | null) => void;
  /** 清空任务 */
  clearTask: () => void;
}

/**
 * 任务Store完整类型
 */
export type TaskStore = TaskStoreState & TaskStoreActions;

/**
 * UI Store状态
 */
export interface UIStoreState {
  /** 左侧边栏是否折叠 */
  isLeftSidebarCollapsed: boolean;
  /** 右侧边栏是否折叠 */
  isRightSidebarCollapsed: boolean;
  /** 视图模式 */
  viewMode: ViewMode;
  /** 当前选中的Concept ID */
  selectedConceptId: string | null;
  /** 是否显示教程对话框 */
  isTutorialDialogOpen: boolean;
  /** 主题模式 */
  theme: 'light' | 'dark' | 'system';
}

/**
 * UI Store操作
 */
export interface UIStoreActions {
  /** 切换左侧边栏 */
  toggleLeftSidebar: () => void;
  /** 切换右侧边栏 */
  toggleRightSidebar: () => void;
  /** 设置视图模式 */
  setViewMode: (mode: ViewMode) => void;
  /** 打开教程 */
  openTutorial: (conceptId: string) => void;
  /** 关闭教程 */
  closeTutorial: () => void;
  /** 设置主题 */
  setTheme: (theme: UIStoreState['theme']) => void;
}

/**
 * UI Store完整类型
 */
export type UIStore = UIStoreState & UIStoreActions;

/**
 * 用户Store状态
 */
export interface UserStoreState {
  /** 用户ID */
  userId: string | null;
  /** 用户名 */
  username: string | null;
  /** 用户邮箱 */
  email: string | null;
  /** 是否已登录 */
  isAuthenticated: boolean;
  /** JWT Token */
  token: string | null;
}

/**
 * 用户Store操作
 */
export interface UserStoreActions {
  /** 设置用户信息 */
  setUser: (user: Partial<UserStoreState>) => void;
  /** 清空用户信息（登出） */
  clearUser: () => void;
  /** 设置Token */
  setToken: (token: string | null) => void;
}

/**
 * 用户Store完整类型
 */
export type UserStore = UserStoreState & UserStoreActions;
