/**
 * 内容生成状态解析工具
 * 
 * 从执行日志中提取内容生成状态，并按照路线图结构组织数据
 * 
 * 后端发送的日志类型：
 * - content_generation_start: 开始生成某个概念
 * - concept_completed: 某个概念的所有内容（tutorial + resources + quiz）生成成功
 * - content_generation_failed: 某个概念生成失败
 */

import type {
  ContentGenerationOverview,
  ConceptGenerationStatus,
  ModuleGenerationStatus,
  StageGenerationStatus,
  ExecutionLog,
  ContentTypeStatus,
} from '@/types/content-generation';
import type { RoadmapFramework } from '@/types/generated/models';

/**
 * 从执行日志中解析内容生成状态
 * 
 * @param logs 执行日志数组
 * @param roadmapFramework 路线图框架数据
 * @returns 内容生成概览
 */
export function parseContentGenerationStatus(
  logs: ExecutionLog[],
  roadmapFramework: RoadmapFramework
): ContentGenerationOverview {
  // 1. 初始化 concept_id -> ConceptGenerationStatus 的映射
  const conceptStatusMap = new Map<string, ConceptGenerationStatus>();
  
  // 2. 遍历路线图框架，为每个 concept 初始化状态
  for (const stage of roadmapFramework.stages) {
    for (const module of stage.modules) {
      for (const concept of module.concepts) {
        conceptStatusMap.set(concept.concept_id, {
          concept_id: concept.concept_id,
          concept_name: concept.name,
          tutorial: { status: 'pending' },
          resources: { status: 'pending' },
          quiz: { status: 'pending' },
        });
      }
    }
  }
  
  // 3. 从日志中更新每个 concept 的状态
  updateConceptStatusFromLogs(conceptStatusMap, logs);
  
  // 4. 重新组织为分层结构
  return buildHierarchicalStatus(roadmapFramework, conceptStatusMap);
}

/**
 * 从日志中更新概念状态
 * 
 * 注意：后端只发送两种状态：
 * - concept_completed: 概念的所有内容（tutorial + resources + quiz）生成成功
 * - content_generation_failed: 概念生成失败
 */
function updateConceptStatusFromLogs(
  conceptStatusMap: Map<string, ConceptGenerationStatus>,
  logs: ExecutionLog[]
): void {
  for (const log of logs) {
    if (!log.details || !log.details.concept_id) continue;
    
    const conceptId = log.details.concept_id;
    const conceptStatus = conceptStatusMap.get(conceptId);
    if (!conceptStatus) continue;
    
    const logType = log.details.log_type;
    
    // 概念完成 - 所有内容（tutorial + resources + quiz）都生成成功
    if (logType === 'concept_completed') {
      const summary = log.details.content_summary || {};
      
      // Tutorial 状态
      conceptStatus.tutorial = {
        status: 'completed',
        // 从 content_summary 中提取信息
        tutorial_id: log.details.concept_id, // 使用 concept_id 作为临时标识
      };
      
      // Resources 状态
      conceptStatus.resources = {
        status: 'completed',
        resources_id: log.details.concept_id,
        resources_count: summary.resource_count || 0,
      };
      
      // Quiz 状态
      conceptStatus.quiz = {
        status: 'completed',
        quiz_id: log.details.concept_id,
        questions_count: summary.quiz_questions || 0,
      };
    }
    
    // 内容生成失败 - 三种内容都标记为失败
    else if (logType === 'content_generation_failed') {
      const error = log.details.error || 'Unknown error';
      conceptStatus.tutorial = { status: 'failed', error };
      conceptStatus.resources = { status: 'failed', error };
      conceptStatus.quiz = { status: 'failed', error };
    }
  }
}

/**
 * 重新组织为分层结构（Stage -> Module -> Concept）
 */
function buildHierarchicalStatus(
  roadmapFramework: RoadmapFramework,
  conceptStatusMap: Map<string, ConceptGenerationStatus>
): ContentGenerationOverview {
  const stages: StageGenerationStatus[] = [];
  
  let totalConcepts = 0;
  let completedConcepts = 0;
  let failedConcepts = 0;
  
  for (const stage of roadmapFramework.stages) {
    const modules: ModuleGenerationStatus[] = [];
    
    let stageTotalConcepts = 0;
    let stageCompletedConcepts = 0;
    let stageFailedConcepts = 0;
    
    for (const module of stage.modules) {
      const concepts: ConceptGenerationStatus[] = [];
      
      let moduleTotalConcepts = 0;
      let moduleCompletedConcepts = 0;
      let moduleFailedConcepts = 0;
      
      for (const concept of module.concepts) {
        const conceptStatus = conceptStatusMap.get(concept.concept_id);
        if (!conceptStatus) continue;
        
        concepts.push(conceptStatus);
        moduleTotalConcepts++;
        
        // 计算完成和失败数量
        const isCompleted = isConceptCompleted(conceptStatus);
        const hasFailed = isConceptFailed(conceptStatus);
        
        if (isCompleted) {
          moduleCompletedConcepts++;
        }
        if (hasFailed) {
          moduleFailedConcepts++;
        }
      }
      
      modules.push({
        module_id: module.module_id,
        module_name: module.name,
        concepts,
        total_concepts: moduleTotalConcepts,
        completed_concepts: moduleCompletedConcepts,
        failed_concepts: moduleFailedConcepts,
      });
      
      stageTotalConcepts += moduleTotalConcepts;
      stageCompletedConcepts += moduleCompletedConcepts;
      stageFailedConcepts += moduleFailedConcepts;
    }
    
    stages.push({
      stage_id: stage.stage_id,
      stage_name: stage.name,
      modules,
      total_concepts: stageTotalConcepts,
      completed_concepts: stageCompletedConcepts,
      failed_concepts: stageFailedConcepts,
    });
    
    totalConcepts += stageTotalConcepts;
    completedConcepts += stageCompletedConcepts;
    failedConcepts += stageFailedConcepts;
  }
  
  return {
    stages,
    last_updated: new Date(),
    total_concepts: totalConcepts,
    completed_concepts: completedConcepts,
    failed_concepts: failedConcepts,
    progress_percentage: totalConcepts > 0 ? Math.round((completedConcepts / totalConcepts) * 100) : 0,
  };
}

/**
 * 判断 concept 是否全部完成
 */
function isConceptCompleted(concept: ConceptGenerationStatus): boolean {
  return (
    concept.tutorial.status === 'completed' &&
    concept.resources.status === 'completed' &&
    concept.quiz.status === 'completed'
  );
}

/**
 * 判断 concept 是否有失败项
 */
function isConceptFailed(concept: ConceptGenerationStatus): boolean {
  return (
    concept.tutorial.status === 'failed' ||
    concept.resources.status === 'failed' ||
    concept.quiz.status === 'failed'
  );
}

/**
 * 格式化相对时间
 * 
 * @param date 日期对象
 * @returns 相对时间字符串（如 "2 minutes ago"）
 */
export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);
  
  if (diffSec < 60) {
    return 'just now';
  } else if (diffMin < 60) {
    return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
  } else if (diffHour < 24) {
    return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`;
  } else {
    return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
  }
}
