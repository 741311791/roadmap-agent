/**
 * Generation Phase Types
 * 
 * Defines the phases of roadmap generation for the progress indicator
 * 
 * 阶段映射关系（后端步骤 → 前端阶段）：
 * - queued, intent_analysis → intent_analysis (需求分析)
 * - curriculum_design → curriculum_design (结构设计)
 * - structure_validation → structure_validation (结构验证) [可选]
 * - human_review, roadmap_edit → human_review (人工审核)
 * - content_generation → content_generation (内容生成)
 * - completed, failed → completed (完成)
 */

// Generation phase identifiers (mapped from backend WebSocket events)
export type GenerationPhase = 
  | 'intent_analysis'       // 需求分析
  | 'curriculum_design'     // 结构设计
  | 'structure_validation'  // 结构验证 (可选)
  | 'human_review'          // 人工审核 (包含 roadmap_edit 子状态)
  | 'content_generation'    // 内容生成 (tutorial, quiz, resources)
  | 'completed';            // 完成 (包含成功/部分失败的展示)

// Sub-status for human_review phase
export type HumanReviewSubStatus = 'waiting' | 'editing' | null;

// Phase configuration for display
export interface PhaseConfig {
  id: GenerationPhase;
  label: string;
  labelEn: string;
  description: string;
  optional?: boolean;  // 是否为可选阶段
}

// Extended phase state with sub-status support
export interface PhaseState {
  phase: GenerationPhase;
  subStatus?: HumanReviewSubStatus;
  modificationCount?: number;  // 编辑次数（human_review editing 状态时）
}

// Ordered phases configuration
export const GENERATION_PHASES: PhaseConfig[] = [
  {
    id: 'intent_analysis',
    label: 'Analysis',
    labelEn: 'Analysis',
    description: 'Analyze learning goals and user background',
  },
  {
    id: 'curriculum_design',
    label: 'Design',
    labelEn: 'Design',
    description: 'Design the Stage-Module-Concept structure',
  },
  {
    id: 'structure_validation',
    label: 'Validate',
    labelEn: 'Validate',
    description: 'Validate roadmap structure completeness',
    optional: true,
  },
  {
    id: 'human_review',
    label: 'Review',
    labelEn: 'Review',
    description: 'Await confirmation of the roadmap framework',
    optional: true,
  },
  {
    id: 'content_generation',
    label: 'Content',
    labelEn: 'Content',
    description: 'Generate tutorials, quizzes, and resources',
  },
  {
    id: 'completed',
    label: 'Done',
    labelEn: 'Done',
    description: 'Roadmap generation completed',
  },
];

// Map backend step names to frontend phases
export function mapStepToPhase(step: string | null): GenerationPhase | null {
  if (!step) return null;
  
  const stepMap: Record<string, GenerationPhase> = {
    // Intent analysis phase
    'queued': 'intent_analysis',
    'starting': 'intent_analysis',
    'intent_analysis': 'intent_analysis',
    
    // Curriculum design phase
    'curriculum_design': 'curriculum_design',
    'framework_generation': 'curriculum_design',
    
    // Structure validation phase
    'structure_validation': 'structure_validation',
    
    // Human review phase (includes roadmap_edit as sub-status)
    'human_review': 'human_review',
    'roadmap_edit': 'human_review',  // 编辑中状态，映射到同一阶段
    
    // Content generation phase
    'content_generation': 'content_generation',
    'tutorial_generation': 'content_generation',
    'quiz_generation': 'content_generation',
    'resource_recommendation': 'content_generation',
    
    // Completed (includes failed)
    'finalizing': 'completed',
    'completed': 'completed',
    'failed': 'completed',  // 失败也显示为完成阶段，在 UI 中展示统计
  };
  
  return stepMap[step] || null;
}

// Parse step with sub-status (for human_review phase)
export function parseStepWithSubStatus(
  step: string | null,
  subStatus?: string | null
): PhaseState | null {
  const phase = mapStepToPhase(step);
  if (!phase) return null;
  
  const state: PhaseState = { phase };
  
  // Handle human_review sub-status
  if (phase === 'human_review') {
    if (step === 'roadmap_edit') {
      state.subStatus = 'editing';
    } else if (subStatus === 'editing') {
      state.subStatus = 'editing';
    } else {
      state.subStatus = 'waiting';
    }
  }
  
  return state;
}

// Get human-readable label for sub-status
export function getSubStatusLabel(subStatus: HumanReviewSubStatus): string {
  switch (subStatus) {
    case 'waiting':
      return 'Waiting for review...';
    case 'editing':
      return 'Editing...';
    default:
      return '';
  }
}

// Get phase index (for progress calculation)
export function getPhaseIndex(phase: GenerationPhase | null): number {
  if (!phase) return -1;
  return GENERATION_PHASES.findIndex(p => p.id === phase);
}

// Check if a phase is completed relative to current phase
export function isPhaseCompleted(phase: GenerationPhase, currentPhase: GenerationPhase | null): boolean {
  if (!currentPhase) return false;
  const phaseIndex = getPhaseIndex(phase);
  const currentIndex = getPhaseIndex(currentPhase);
  return phaseIndex < currentIndex;
}

// Check if a phase is the current active phase
export function isPhaseActive(phase: GenerationPhase, currentPhase: GenerationPhase | null): boolean {
  return phase === currentPhase;
}

// Concept content status type (for card states)
export type ConceptContentStatus = 'pending' | 'generating' | 'completed' | 'failed';

// Extended concept status with metadata
export interface ConceptGenerationStatus {
  conceptId: string;
  contentStatus: ConceptContentStatus;
  resourcesStatus?: ConceptContentStatus;
  quizStatus?: ConceptContentStatus;
  error?: string;
}

