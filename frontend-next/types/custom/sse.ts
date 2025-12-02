/**
 * Server-Sent Events Types
 * Types for handling SSE streams from the backend
 */

import type { RoadmapFramework, Concept } from '../generated/models';

// Base SSE event
export interface BaseSSEEvent {
  type: string;
  [key: string]: unknown;
}

// ============================================================
// Roadmap Generation Events (matching backend implementation)
// ============================================================

// Agent streaming events
export interface ChunkEvent extends BaseSSEEvent {
  type: 'chunk';
  content: string;
  agent: string;
}

export interface CompleteEvent extends BaseSSEEvent {
  type: 'complete';
  data: unknown;
  agent: string;
}

// Tutorial generation events
export interface TutorialsStartEvent extends BaseSSEEvent {
  type: 'tutorials_start';
  total_count: number;
  batch_size: number;
}

export interface BatchStartEvent extends BaseSSEEvent {
  type: 'batch_start';
  batch_index: number;
  batch_size: number;
  total_batches: number;
  concepts: string[];
}

export interface TutorialStartEvent extends BaseSSEEvent {
  type: 'tutorial_start';
  concept_id: string;
  concept_name: string;
}

export interface TutorialChunkEvent extends BaseSSEEvent {
  type: 'tutorial_chunk';
  concept_id: string;
  content: string;
}

export interface TutorialCompleteEvent extends BaseSSEEvent {
  type: 'tutorial_complete';
  concept_id: string;
  data: {
    tutorial_id: string;
    title: string;
    summary: string;
    content_url: string;
    content_status: string;
    estimated_completion_time: number;
  };
}

export interface TutorialErrorEvent extends BaseSSEEvent {
  type: 'tutorial_error';
  concept_id: string;
  error: string;
}

export interface BatchCompleteEvent extends BaseSSEEvent {
  type: 'batch_complete';
  batch_index: number;
  progress: {
    batch_completed: number;
    batch_failed: number;
    completed: number;
    failed: number;
    total: number;
    percentage: number;
  };
}

export interface TutorialsDoneEvent extends BaseSSEEvent {
  type: 'tutorials_done';
  summary: {
    total: number;
    succeeded: number;
    failed: number;
    success_rate: number;
  };
}

export interface DoneEvent extends BaseSSEEvent {
  type: 'done';
  task_id?: string;
  roadmap_id?: string;
  summary: {
    intent_analysis: unknown;
    framework: unknown;
    design_rationale: string;
    tutorials?: unknown;
  };
}

export interface ErrorEvent extends BaseSSEEvent {
  type: 'error';
  message: string;
  agent: string;
}

export type RoadmapGenerationEvent =
  | ChunkEvent
  | CompleteEvent
  | TutorialsStartEvent
  | BatchStartEvent
  | TutorialStartEvent
  | TutorialChunkEvent
  | TutorialCompleteEvent
  | TutorialErrorEvent
  | BatchCompleteEvent
  | TutorialsDoneEvent
  | DoneEvent
  | ErrorEvent;

// ============================================================
// Chat Modification Events (matching backend implementation)
// ============================================================

export interface AnalyzingEvent extends BaseSSEEvent {
  type: 'analyzing';
  agent: string;
  step: string;
  message: string;
}

export interface IntentsEvent extends BaseSSEEvent {
  type: 'intents';
  intents: Array<{
    modification_type: string;
    target_id: string;
    target_name: string;
    specific_requirements: string[];
    priority: string;
  }>;
  count: number;
  overall_confidence: number;
  needs_clarification: boolean;
  clarification_questions: string[];
  analysis_reasoning: string;
}

export interface ModifyingEvent extends BaseSSEEvent {
  type: 'modifying';
  modification_type: string;
  target_id: string;
  target_name: string;
  requirements: string[];
  progress: {
    current: number;
    total: number;
  };
}

export interface AgentProgressEvent extends BaseSSEEvent {
  type: 'agent_progress';
  agent: string;
  step: string;
  details: string;
}

export interface ResultEvent extends BaseSSEEvent {
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
  overall_success: boolean;
  partial_success: boolean;
  summary: string;
  results: Array<{
    modification_type: string;
    target_id: string;
    target_name: string;
    success: boolean;
    modification_summary: string;
    new_version?: number;
    error_message?: string;
  }>;
  duration_ms: number;
}

export interface ModificationErrorEvent extends BaseSSEEvent {
  type: 'error';
  message: string;
}

export type ChatModificationEvent =
  | AnalyzingEvent
  | IntentsEvent
  | ModifyingEvent
  | AgentProgressEvent
  | ResultEvent
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

