/**
 * TypeScript Type Generation Script (Enhanced)
 * 
 * 从后端 OpenAPI Schema 生成前端 TypeScript 类型
 * 
 * 功能：
 * - 自动生成类型和 API 客户端
 * - Schema 验证和变更检测
 * - 详细的错误报告
 * - 自动降级到占位符类型
 * 
 * Run: npm run generate:types
 */

import { generate } from 'openapi-typescript-codegen';
import * as fs from 'fs';
import * as path from 'path';
import * as https from 'https';
import * as http from 'http';

const OPENAPI_SCHEMA_URL = process.env.OPENAPI_SCHEMA_URL || 'http://localhost:8000/openapi.json';
const OUTPUT_DIR = './types/generated';
const CACHE_FILE = './.openapi-cache.json';
const STATS_FILE = `${OUTPUT_DIR}/.generation-stats.json`;

interface GenerationStats {
  timestamp: string;
  schemaUrl: string;
  modelsCount: number;
  servicesCount: number;
  endpointsCount: number;
  success: boolean;
  errorMessage?: string;
}

/**
 * 下载 OpenAPI Schema
 */
async function downloadSchema(url: string): Promise<any> {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    
    client.get(url, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const schema = JSON.parse(data);
          resolve(schema);
        } catch (error) {
          reject(new Error(`Invalid JSON response: ${error}`));
        }
      });
    }).on('error', (error) => {
      reject(error);
    });
  });
}

/**
 * 验证 OpenAPI Schema
 */
function validateSchema(schema: any): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  // 检查基本结构
  if (!schema.openapi) {
    errors.push('Missing "openapi" field');
  }
  
  if (!schema.info || !schema.info.title) {
    errors.push('Missing "info.title" field');
  }
  
  if (!schema.paths || Object.keys(schema.paths).length === 0) {
    errors.push('No API paths defined');
  }
  
  if (!schema.components || !schema.components.schemas) {
    errors.push('No schema definitions found');
  }
  
  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * 分析 Schema 统计信息
 */
function analyzeSchema(schema: any): Omit<GenerationStats, 'timestamp' | 'schemaUrl' | 'success'> {
  const paths = schema.paths || {};
  const schemas = schema.components?.schemas || {};
  
  // 统计端点数量
  let endpointsCount = 0;
  for (const path in paths) {
    endpointsCount += Object.keys(paths[path]).length;
  }
  
  // 统计 Schema 数量
  const modelsCount = Object.keys(schemas).length;
  
  // 统计服务数量（基于 tags）
  const tags = new Set<string>();
  for (const path in paths) {
    for (const method in paths[path]) {
      const operation = paths[path][method];
      if (operation.tags) {
        operation.tags.forEach((tag: string) => tags.add(tag));
      }
    }
  }
  const servicesCount = tags.size;
  
  return {
    modelsCount,
    servicesCount,
    endpointsCount,
  };
}

/**
 * 保存生成统计信息
 */
function saveGenerationStats(stats: GenerationStats) {
  try {
    fs.writeFileSync(STATS_FILE, JSON.stringify(stats, null, 2), 'utf-8');
    console.log('📊 Generation stats saved');
  } catch (error) {
    console.warn('⚠️  Failed to save generation stats:', error);
  }
}

async function generateTypes() {
  console.log('');
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║   TypeScript Type Generator (Enhanced)         ║');
  console.log('╚════════════════════════════════════════════════╝');
  console.log('');
  console.log('🔄 Starting TypeScript type generation...');
  console.log(`📥 Fetching OpenAPI schema from: ${OPENAPI_SCHEMA_URL}`);
  console.log('');

  const startTime = Date.now();

  try {
    // 1. 下载 Schema
    const schema = await downloadSchema(OPENAPI_SCHEMA_URL);
    console.log('✅ Schema downloaded successfully');
    
    // 2. 验证 Schema
    const validation = validateSchema(schema);
    if (!validation.valid) {
      console.error('❌ Schema validation failed:');
      validation.errors.forEach(error => console.error(`   - ${error}`));
      throw new Error('Invalid OpenAPI schema');
    }
    console.log('✅ Schema validation passed');
    
    // 3. 分析 Schema
    const stats = analyzeSchema(schema);
    console.log('📊 Schema statistics:');
    console.log(`   - Models: ${stats.modelsCount}`);
    console.log(`   - Services: ${stats.servicesCount}`);
    console.log(`   - Endpoints: ${stats.endpointsCount}`);
    console.log('');
    
    // 4. 保存缓存
    fs.writeFileSync(CACHE_FILE, JSON.stringify(schema, null, 2), 'utf-8');
    console.log('💾 Schema cached for future reference');
    
    // 5. 确保输出目录存在
    if (!fs.existsSync(OUTPUT_DIR)) {
      fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }

    // 6. 生成类型
    console.log('🔨 Generating TypeScript types...');
    await generate({
      input: OPENAPI_SCHEMA_URL,
      output: OUTPUT_DIR,
      httpClient: 'fetch',
      useOptions: true,
      useUnionTypes: true,
      exportCore: true,
      exportServices: true,
      exportModels: true,
      exportSchemas: false,
    });

    console.log('✅ TypeScript types generated successfully!');
    console.log(`📁 Output directory: ${OUTPUT_DIR}`);
    console.log('');

    // 7. 生成自定义索引文件
    generateIndexFile();
    
    // 8. 保存统计信息
    const duration = Date.now() - startTime;
    saveGenerationStats({
      timestamp: new Date().toISOString(),
      schemaUrl: OPENAPI_SCHEMA_URL,
      ...stats,
      success: true,
    });
    
    console.log(`⏱️  Generation completed in ${duration}ms`);
    console.log('');
    console.log('✨ All done! You can now use the generated types in your code.');
    console.log('');

  } catch (error) {
    const duration = Date.now() - startTime;
    console.error('');
    console.error('❌ Type generation failed:', error);
    console.error('');
    
    // 保存失败统计
    saveGenerationStats({
      timestamp: new Date().toISOString(),
      schemaUrl: OPENAPI_SCHEMA_URL,
      modelsCount: 0,
      servicesCount: 0,
      endpointsCount: 0,
      success: false,
      errorMessage: error instanceof Error ? error.message : String(error),
    });
    
    // 如果网络请求失败，尝试使用本地回退
    console.log('💡 Troubleshooting tips:');
    console.log(`   1. Make sure the backend server is running at ${OPENAPI_SCHEMA_URL}`);
    console.log('   2. Check if the backend is accessible from your network');
    console.log('   3. Verify the OpenAPI endpoint is working: curl ' + OPENAPI_SCHEMA_URL);
    console.log('');
    
    // 生成占位符类型
    console.log('🔄 Generating placeholder types as fallback...');
    generatePlaceholderTypes();
    
    console.error('');
    console.error(`⏱️  Failed after ${duration}ms`);
    console.error('');
    
    process.exit(1);
  }
}

function generateIndexFile() {
  const indexContent = `/**
 * Auto-generated TypeScript Types
 * 
 * Generated at: ${new Date().toISOString()}
 * Source: ${OPENAPI_SCHEMA_URL}
 * 
 * ⚠️ WARNING: Do not edit this file manually
 * Run \`npm run generate:types\` to regenerate
 */

// Re-export all generated types
export * from './models';
export * from './services';
export * from './core/ApiError';
export * from './core/ApiRequestOptions';
export * from './core/ApiResult';
`;

  fs.writeFileSync(
    path.join(OUTPUT_DIR, 'index.ts'),
    indexContent,
    'utf-8'
  );

  console.log('📝 Generated index file: types/generated/index.ts');
}

function generatePlaceholderTypes() {
  console.log('📝 Generating placeholder types...');

  // Create output directory
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  // Create models directory
  const modelsDir = path.join(OUTPUT_DIR, 'models');
  if (!fs.existsSync(modelsDir)) {
    fs.mkdirSync(modelsDir, { recursive: true });
  }

  // Write placeholder types based on backend models
  const placeholderTypes = `/**
 * Placeholder Types - Generated when backend is unavailable
 * 
 * These types match the backend Pydantic models in domain.py
 * Run \`npm run generate:types\` with the backend running to get full types
 */

// ============================================================
// User Input Models
// ============================================================

export interface LearningPreferences {
  learning_goal: string;
  available_hours_per_week: number;
  motivation: string;
  current_level: 'beginner' | 'intermediate' | 'advanced';
  career_background: string;
  content_preference: Array<'video' | 'text' | 'interactive' | 'project'>;
  target_deadline?: string | null;
}

export interface UserRequest {
  user_id: string;
  session_id: string;
  preferences: LearningPreferences;
  additional_context?: string | null;
}

// ============================================================
// Roadmap Framework Models
// ============================================================

export interface Concept {
  concept_id: string;
  name: string;
  description: string;
  estimated_hours: number;
  prerequisites: string[];
  difficulty: 'easy' | 'medium' | 'hard';
  keywords: string[];
  content_status: 'pending' | 'generating' | 'completed' | 'failed';
  content_ref?: string | null;
  content_version: string;
  content_summary?: string | null;
  resources_status: 'pending' | 'generating' | 'completed' | 'failed';
  resources_id?: string | null;
  resources_count: number;
  quiz_status: 'pending' | 'generating' | 'completed' | 'failed';
  quiz_id?: string | null;
  quiz_questions_count: number;
}

export interface Module {
  module_id: string;
  name: string;
  description: string;
  concepts: Concept[];
}

export interface Stage {
  stage_id: string;
  name: string;
  description: string;
  order: number;
  modules: Module[];
}

export interface RoadmapFramework {
  roadmap_id: string;
  title: string;
  stages: Stage[];
  total_estimated_hours: number;
  recommended_completion_weeks: number;
}

// ============================================================
// Tutorial Models
// ============================================================

export interface TutorialSection {
  section_id: string;
  title: string;
  content: string;
  content_type: 'theory' | 'example' | 'exercise' | 'quiz';
  estimated_minutes: number;
}

export interface Tutorial {
  tutorial_id: string;
  concept_id: string;
  title: string;
  summary: string;
  sections: TutorialSection[];
  recommended_resources: Array<{ title: string; url: string; type: string }>;
  exercises: string[];
  estimated_completion_time: number;
  version: string;
  generated_at: string;
  storage_url?: string | null;
}

// ============================================================
// Resource Models
// ============================================================

export interface Resource {
  title: string;
  url: string;
  type: 'article' | 'video' | 'book' | 'course' | 'documentation' | 'tool';
  description: string;
  relevance_score: number;
}

export interface ResourceRecommendationOutput {
  id: string;
  concept_id: string;
  resources: Resource[];
  search_queries_used: string[];
  generated_at: string;
}

// ============================================================
// Quiz Models
// ============================================================

export interface QuizQuestion {
  question_id: string;
  question_type: 'single_choice' | 'multiple_choice' | 'true_false' | 'fill_blank';
  question: string;
  options: string[];
  correct_answer: number[];
  explanation: string;
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface QuizGenerationOutput {
  concept_id: string;
  quiz_id: string;
  questions: QuizQuestion[];
  total_questions: number;
  generated_at: string;
}

// ============================================================
// Modification Models
// ============================================================

export type ModificationType = 'tutorial' | 'resources' | 'quiz' | 'concept';

export interface SingleModificationIntent {
  modification_type: ModificationType;
  target_id: string;
  target_name: string;
  specific_requirements: string[];
  priority: 'high' | 'medium' | 'low';
}

export interface ModificationAnalysisOutput {
  intents: SingleModificationIntent[];
  overall_confidence: number;
  needs_clarification: boolean;
  clarification_questions: string[];
  analysis_reasoning: string;
}

export interface SingleModificationResult {
  modification_type: ModificationType;
  target_id: string;
  target_name: string;
  success: boolean;
  modification_summary: string;
  new_version?: number | null;
  error_message?: string | null;
}

export interface BatchModificationResult {
  results: SingleModificationResult[];
  overall_success: boolean;
  partial_success: boolean;
  summary: string;
}

// ============================================================
// API Response Models
// ============================================================

export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  current_step?: string | null;
  progress?: number | null;
  error_message?: string | null;
  roadmap_id?: string | null;
}

export interface GenerateRoadmapResponse {
  task_id: string;
  status: string;
  message: string;
}
`;

  fs.writeFileSync(
    path.join(modelsDir, 'index.ts'),
    placeholderTypes,
    'utf-8'
  );

  // Create services placeholder
  const servicesDir = path.join(OUTPUT_DIR, 'services');
  if (!fs.existsSync(servicesDir)) {
    fs.mkdirSync(servicesDir, { recursive: true });
  }

  const servicesPlaceholder = `/**
 * Placeholder Services - Generated when backend is unavailable
 */

export class RoadmapService {
  // Placeholder - will be generated when backend is available
}
`;

  fs.writeFileSync(
    path.join(servicesDir, 'index.ts'),
    servicesPlaceholder,
    'utf-8'
  );

  // Create core directory with basic types
  const coreDir = path.join(OUTPUT_DIR, 'core');
  if (!fs.existsSync(coreDir)) {
    fs.mkdirSync(coreDir, { recursive: true });
  }

  const coreTypes = `/**
 * Core API Types
 */

export interface ApiError {
  status: number;
  statusText: string;
  body: unknown;
  url: string;
}

export interface ApiRequestOptions {
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  url: string;
  path?: Record<string, unknown>;
  query?: Record<string, unknown>;
  headers?: Record<string, string>;
  body?: unknown;
}

export interface ApiResult<T = unknown> {
  data: T;
  status: number;
  headers: Record<string, string>;
}
`;

  fs.writeFileSync(
    path.join(coreDir, 'ApiError.ts'),
    'export interface ApiError { status: number; statusText: string; body: unknown; url: string; }',
    'utf-8'
  );

  fs.writeFileSync(
    path.join(coreDir, 'ApiRequestOptions.ts'),
    coreTypes.split('export interface ApiRequestOptions')[1]?.split('export interface')[0] || 
    'export interface ApiRequestOptions { method: string; url: string; }',
    'utf-8'
  );

  fs.writeFileSync(
    path.join(coreDir, 'ApiResult.ts'),
    'export interface ApiResult<T = unknown> { data: T; status: number; }',
    'utf-8'
  );

  // Create main index file
  const indexContent = `/**
 * Generated Types (Placeholder)
 * 
 * These are placeholder types. Run \`npm run generate:types\` 
 * with the backend running to get full types.
 */

export * from './models';
export * from './core/ApiError';
export * from './core/ApiRequestOptions';
export * from './core/ApiResult';
`;

  fs.writeFileSync(
    path.join(OUTPUT_DIR, 'index.ts'),
    indexContent,
    'utf-8'
  );

  console.log('✅ Placeholder types generated successfully!');
}

// Run the script
generateTypes();

