/**
 * Service Response Types
 * 
 * Generated from backend API responses
 */

/**
 * Resource item from backend
 */
export interface ResourceItem {
  title: string;
  url: string;
  type: 'article' | 'video' | 'book' | 'course' | 'documentation' | 'tool' | 'official_docs';
  description: string;
  relevance_score: number;
}

/**
 * Resources response from backend
 */
export interface ResourcesResponse {
  roadmap_id: string;
  concept_id: string;
  resources_id: string;
  resources: ResourceItem[];
  resources_count: number;
  search_queries_used: string[];
  generated_at: string | null;
}

/**
 * Quiz question from backend
 */
export interface QuizQuestionItem {
  question_id: string;
  question_type: 'single_choice' | 'multiple_choice' | 'true_false' | 'fill_blank';
  question: string;
  options: string[];
  correct_answer: number[];
  explanation: string;
  difficulty: 'easy' | 'medium' | 'hard';
}

/**
 * Quiz response from backend
 */
export interface QuizResponse {
  roadmap_id: string;
  concept_id: string;
  quiz_id: string;
  questions: QuizQuestionItem[];
  total_questions: number;
  easy_count: number;
  medium_count: number;
  hard_count: number;
  generated_at: string | null;
}

// Re-export service classes
export * from './ApprovalService';
export * from './DefaultService';
export * from './GenerationService';
export * from './ModificationService';
export * from './QuizService';
export * from './ResourceService';
export * from './RetrievalService';
export * from './RetryService';
export * from './TutorialService';
export * from './UsersService';

