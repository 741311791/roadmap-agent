/**
 * Server-Sent Events Types
 * Types for handling SSE streams from the backend
 */

import type { RoadmapFramework, Concept } from '../generated/models';

// Base SSE event
export interface BaseSSEEvent {
  type: string;
  timestamp?: number;
}

// ============================================================
// Roadmap Generation Events
// ============================================================

export interface StepStartEvent extends BaseSSEEvent {
  type: 'step_start';
  step: string;
  step_name: string;
  progress: number;
}

export interface StepCompleteEvent extends BaseSSEEvent {
  type: 'step_complete';
  step: string;
  result?: unknown;
}

export interface AgentThinkingEvent extends BaseSSEEvent {
  type: 'agent_thinking';
  agent_id: string;
  message: string;
}

export interface RoadmapPreviewEvent extends BaseSSEEvent {
  type: 'roadmap_preview';
  framework: RoadmapFramework;
}

export interface TutorialStartEvent extends BaseSSEEvent {
  type: 'tutorial_start';
  concept_id: string;
  concept_name: string;
  index: number;
  total: number;
}

export interface TutorialProgressEvent extends BaseSSEEvent {
  type: 'tutorial_progress';
  concept_id: string;
  status: 'generating' | 'completed' | 'failed';
  progress?: number;
}

export interface TutorialCompleteEvent extends BaseSSEEvent {
  type: 'tutorial_complete';
  concept_id: string;
  tutorial_id: string;
  summary: string;
}

export interface GenerationCompleteEvent extends BaseSSEEvent {
  type: 'complete';
  roadmap_id: string;
  total_concepts: number;
  successful_tutorials: number;
}

export interface GenerationErrorEvent extends BaseSSEEvent {
  type: 'error';
  message: string;
  details?: string;
}

export type GenerationEvent =
  | StepStartEvent
  | StepCompleteEvent
  | AgentThinkingEvent
  | RoadmapPreviewEvent
  | TutorialStartEvent
  | TutorialProgressEvent
  | TutorialCompleteEvent
  | GenerationCompleteEvent
  | GenerationErrorEvent;

// ============================================================
// Chat Modification Events
// ============================================================

export interface AnalyzingEvent extends BaseSSEEvent {
  type: 'analyzing';
  message: string;
}

export interface IntentsEvent extends BaseSSEEvent {
  type: 'intents';
  intents: Array<{
    modification_type: 'tutorial' | 'resources' | 'quiz' | 'concept';
    target_id: string;
    target_name: string;
    specific_requirements: string[];
    priority: 'high' | 'medium' | 'low';
  }>;
  needs_clarification: boolean;
  clarification_questions: string[];
}

export interface ModifyingEvent extends BaseSSEEvent {
  type: 'modifying';
  target_id: string;
  target_name: string;
  modification_type: string;
}

export interface ModificationResultEvent extends BaseSSEEvent {
  type: 'result';
  modification_type: string;
  target_id: string;
  target_name: string;
  success: boolean;
  modification_summary: string;
  new_version?: number;
  error_message?: string;
}

export interface ModificationDoneEvent extends BaseSSEEvent {
  type: 'done';
  summary: string;
  overall_success: boolean;
  partial_success: boolean;
}

export interface ModificationErrorEvent extends BaseSSEEvent {
  type: 'error';
  message: string;
}

export type ChatModificationEvent =
  | AnalyzingEvent
  | IntentsEvent
  | ModifyingEvent
  | ModificationResultEvent
  | ModificationDoneEvent
  | ModificationErrorEvent;

// ============================================================
// SSE Event Handler Types
// ============================================================

export type SSEEventHandler<T extends BaseSSEEvent> = (event: T) => void;

export interface SSEHandlers<T extends BaseSSEEvent> {
  onEvent: SSEEventHandler<T>;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

