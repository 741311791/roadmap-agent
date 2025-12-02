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
    label: '需求分析',
    labelEn: 'Analysis',
    description: '分析学习目标和用户背景',
  },
  {
    id: 'curriculum_design',
    label: '结构设计',
    labelEn: 'Design',
    description: '设计 Stage-Module-Concept 结构',
  },
  {
    id: 'structure_validation',
    label: '结构验证',
    labelEn: 'Validate',
    description: '验证路线图结构完整性',
    optional: true,
  },
  {
    id: 'human_review',
    label: '人工审核',
    labelEn: 'Review',
    description: '等待确认路线图框架',
    optional: true,
  },
  {
    id: 'content_generation',
    label: '内容生成',
    labelEn: 'Content',
    description: '生成教程、测验和资源推荐',
  },
  {
    id: 'completed',
    label: '完成',
    labelEn: 'Done',
    description: '路线图生成完成',
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
      return '等待审核...';
    case 'editing':
      return '正在修正...';
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

