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

/**
 * 将后端步骤映射到前端阶段
 * 
 * 核心工作流：
 * - intent_analysis → curriculum_design → structure_validation → human_review → content_generation
 * 
 * 共享编辑节点（由edit_source区分来源）：
 * - edit_plan_analysis：编辑计划分析（validation失败或review拒绝都使用）
 * - roadmap_edit：路线图修正（validation失败或review拒绝都使用）
 */
export function mapStepToPhase(step: string | null): GenerationPhase | null {
  if (!step) return null;
  
  const stepMap: Record<string, GenerationPhase> = {
    // Intent analysis phase
    'queued': 'intent_analysis',
    'starting': 'intent_analysis',
    'intent_analysis': 'intent_analysis',
    
    // Curriculum design phase
    'curriculum_design': 'curriculum_design',
    
    // Structure validation phase (包含编辑分支，edit_source=validation_failed时)
    'structure_validation': 'structure_validation',
    
    // Human review phase (包含编辑分支，edit_source=human_review时)
    'human_review': 'human_review',
    
    // ✅ 共享编辑节点（通过edit_source区分来源）
    // - edit_source=validation_failed → 映射到structure_validation阶段
    // - edit_source=human_review → 映射到human_review阶段
    // 但这里无法获取edit_source，所以统一映射到human_review（UI上显示为同一阶段）
    'edit_plan_analysis': 'human_review',
    'roadmap_edit': 'human_review',
    
    // Content generation phase
    'content_generation_queued': 'content_generation',
    'content_generation': 'content_generation',
    
    // Completed phase
    'completed': 'completed',
    'failed': 'completed',  // 失败也显示为完成阶段，在UI中展示统计
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

