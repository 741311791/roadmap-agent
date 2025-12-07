/**
 * Zustand Store Types
 * Type definitions for global state management
 */

import type { RoadmapFramework, Concept, LearningPreferences, Module, Stage } from '../generated/models';
import type { ViewMode, SidebarState } from './ui';
import type { GenerationPhase } from './phases';

// Re-export for components that use these types
export type { Module, Stage, RoadmapFramework };

// ============================================================
// Roadmap Store
// ============================================================

export interface RoadmapHistory {
  roadmap_id: string;
  title: string;
  created_at: string;
  status: 'draft' | 'completed' | 'archived';
  total_concepts: number;
  completed_concepts: number;
  topic?: string;
}

export interface RoadmapStoreState {
  // Current roadmap data
  currentRoadmap: RoadmapFramework | null;
  isLoading: boolean;
  error: string | null;
  
  // Generation state
  isGenerating: boolean;
  generationProgress: number;
  currentStep: string | null;
  
  // Generation streaming state
  generationPhase: 'idle' | 'analyzing' | 'designing' | 'generating_tutorials' | 'done';
  generationBuffer: string;
  tutorialProgress: { completed: number; total: number };
  
  // Real-time generation tracking (for early navigation)
  activeTaskId: string | null;
  activeGenerationPhase: GenerationPhase | null;
  isLiveGenerating: boolean;
  
  // History
  history: RoadmapHistory[];
  
  // Selected items
  selectedConceptId: string | null;
}

export interface RoadmapStoreActions {
  setRoadmap: (roadmap: RoadmapFramework) => void;
  clearRoadmap: () => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setGenerating: (generating: boolean) => void;
  updateProgress: (step: string, progress: number) => void;
  setHistory: (history: RoadmapHistory[]) => void;
  addToHistory: (roadmap: RoadmapHistory) => void;
  selectConcept: (conceptId: string | null) => void;
  updateConceptStatus: (
    conceptId: string,
    status: Partial<Pick<Concept, 'content_status' | 'resources_status' | 'quiz_status'>>
  ) => void;
  
  // Generation streaming actions
  setGenerationPhase: (phase: 'idle' | 'analyzing' | 'designing' | 'generating_tutorials' | 'done') => void;
  appendGenerationBuffer: (chunk: string) => void;
  clearGenerationBuffer: () => void;
  updateTutorialProgress: (completed: number, total: number) => void;
  
  // Real-time generation tracking (for early navigation)
  setActiveTask: (taskId: string | null) => void;
  setActiveGenerationPhase: (phase: GenerationPhase | null) => void;
  setLiveGenerating: (isLive: boolean) => void;
  clearLiveGeneration: () => void;
}

export type RoadmapStore = RoadmapStoreState & RoadmapStoreActions;

// ============================================================
// Chat Store
// ============================================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string; // ISO 8601 格式的时间字符串
  metadata?: {
    isStreaming?: boolean;
    modifications?: Array<{
      type: string;
      targetId: string;
      targetName: string;
      success: boolean;
    }>;
  };
}

export interface ChatStoreState {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamBuffer: string;
  error: string | null;
  
  // Context for AI assistant
  contextConceptId: string | null;
  contextRoadmapId: string | null;
}

export interface ChatStoreActions {
  addMessage: (message: Omit<ChatMessage, 'id' | 'timestamp'>) => void;
  updateMessage: (id: string, updates: Partial<ChatMessage>) => void;
  appendToStream: (chunk: string) => void;
  completeStream: () => void;
  clearMessages: () => void;
  setError: (error: string | null) => void;
  setContext: (roadmapId: string | null, conceptId: string | null) => void;
}

export type ChatStore = ChatStoreState & ChatStoreActions;

// ============================================================
// UI Store
// ============================================================

export interface UIStoreState {
  // Sidebar states
  sidebar: SidebarState;
  
  // View mode
  viewMode: ViewMode;
  
  // Tutorial dialog
  isTutorialDialogOpen: boolean;
  tutorialConceptId: string | null;
  
  // Mobile menu
  isMobileMenuOpen: boolean;
}

export interface UIStoreActions {
  toggleLeftSidebar: () => void;
  toggleRightSidebar: () => void;
  setViewMode: (mode: ViewMode) => void;
  openTutorialDialog: (conceptId: string) => void;
  closeTutorialDialog: () => void;
  setMobileMenuOpen: (open: boolean) => void;
}

export type UIStore = UIStoreState & UIStoreActions;

// ============================================================
// Learning Store
// ============================================================

export interface LearningProgress {
  conceptId: string;
  completed: boolean;
  completedAt?: string;
  quizScore?: number;
  timeSpentMinutes?: number;
}

export interface LearningStoreState {
  // User preferences (cached from creation)
  preferences: LearningPreferences | null;
  
  // Progress tracking
  progress: Record<string, LearningProgress>;
  
  // Current learning position
  currentConceptId: string | null;
  lastVisitedAt: string | null;
}

export interface LearningStoreActions {
  setPreferences: (prefs: LearningPreferences) => void;
  markConceptComplete: (conceptId: string, quizScore?: number) => void;
  markConceptIncomplete: (conceptId: string) => void;
  setCurrentConcept: (conceptId: string | null) => void;
  updateTimeSpent: (conceptId: string, minutes: number) => void;
  getCompletedCount: () => number;
  getProgress: (conceptId: string) => LearningProgress | undefined;
}

export type LearningStore = LearningStoreState & LearningStoreActions;

