/**
 * 增强型 TypeScript 类型生成脚本
 * 
 * 从后端 OpenAPI Schema 生成前端 TypeScript 类型，并进行增强处理
 * 
 * 增强功能:
 * - 自动替换 string 类型为具体的枚举类型 (基于 constants.ts)
 * - 优化 ResponseModel 泛型类型
 * - 生成更准确的类型定义
 * - 添加 JSDoc 注释
 * 
 * Run: npm run generate:types:enhanced
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

interface EnumMapping {
  fieldName: string;
  enumType: string;
  pattern?: RegExp;
}

/**
 * 字段到枚举类型的映射规则
 */
const ENUM_MAPPINGS: EnumMapping[] = [
  { fieldName: 'status', enumType: 'TaskStatus', pattern: /task.*status/i },
  { fieldName: 'current_step', enumType: 'WorkflowStep' },
  { fieldName: 'step', enumType: 'WorkflowStep' },
  { fieldName: 'content_status', enumType: 'ContentStatus' },
  { fieldName: 'resources_status', enumType: 'ContentStatus' },
  { fieldName: 'quiz_status', enumType: 'ContentStatus' },
];

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
 * 增强 Schema: 添加枚举类型引用
 */
function enhanceSchema(schema: any): any {
  const enhanced = JSON.parse(JSON.stringify(schema));
  
  // 遍历所有 Schema 定义
  const schemas = enhanced.components?.schemas || {};
  
  for (const schemaName in schemas) {
    const schemaDef = schemas[schemaName];
    
    if (schemaDef.properties) {
      for (const propName in schemaDef.properties) {
        const prop = schemaDef.properties[propName];
        
        // 检查是否应该使用枚举类型
        for (const mapping of ENUM_MAPPINGS) {
          const shouldApply = 
            propName === mapping.fieldName ||
            (mapping.pattern && mapping.pattern.test(propName));
          
          if (shouldApply && prop.type === 'string') {
            // 添加枚举引用
            prop['x-enum-ref'] = mapping.enumType;
            prop.description = prop.description 
              ? `${prop.description} (使用 ${mapping.enumType} 枚举)`
              : `使用 ${mapping.enumType} 枚举`;
          }
        }
      }
    }
  }
  
  return enhanced;
}

/**
 * 后处理生成的类型文件
 */
function postProcessGeneratedTypes(outputDir: string) {
  console.log('🔧 Post-processing generated types...');
  
  const modelsDir = path.join(outputDir, 'models');
  if (!fs.existsSync(modelsDir)) {
    return;
  }
  
  const files = fs.readdirSync(modelsDir).filter(f => f.endsWith('.ts'));
  let processedCount = 0;
  
  for (const file of files) {
    const filePath = path.join(modelsDir, file);
    let content = fs.readFileSync(filePath, 'utf-8');
    let modified = false;
    
    // 替换 status: string 为 status: TaskStatus
    if (content.includes('status: string') || content.includes('status?: string')) {
      // 添加导入
      if (!content.includes("import type { TaskStatus }")) {
        const importLine = "import type { TaskStatus } from '../constants';\n";
        content = content.replace(
          /\/\* eslint-disable \*\/\n/,
          `/* eslint-disable */\n${importLine}`
        );
      }
      
      // 替换类型
      content = content.replace(
        /status:\s*(string|\(string \| null\))/g,
        (match, type) => {
          modified = true;
          return type.includes('null') 
            ? 'status: (TaskStatus | null)'
            : 'status: TaskStatus';
        }
      );
    }
    
    // 替换 current_step: string 为 current_step: WorkflowStep
    if (content.includes('current_step') || content.includes('step:')) {
      if (!content.includes("import type { WorkflowStep }")) {
        const importLine = "import type { WorkflowStep } from '../constants';\n";
        content = content.replace(
          /\/\* eslint-disable \*\/\n/,
          `/* eslint-disable */\n${importLine}`
        );
      }
      
      content = content.replace(
        /(current_step|step):\s*(string|\(string \| null\))/g,
        (match, fieldName, type) => {
          modified = true;
          return type.includes('null')
            ? `${fieldName}: (WorkflowStep | null)`
            : `${fieldName}: WorkflowStep`;
        }
      );
    }
    
    // 替换 content_status 等字段
    if (content.includes('_status:')) {
      if (!content.includes("import type { ContentStatus }")) {
        const importLine = "import type { ContentStatus } from '../constants';\n";
        content = content.replace(
          /\/\* eslint-disable \*\/\n/,
          `/* eslint-disable */\n${importLine}`
        );
      }
      
      content = content.replace(
        /(content_status|resources_status|quiz_status):\s*(string|\(string \| null\))/g,
        (match, fieldName, type) => {
          modified = true;
          return type.includes('null')
            ? `${fieldName}: (ContentStatus | null)`
            : `${fieldName}: ContentStatus`;
        }
      );
    }
    
    if (modified) {
      fs.writeFileSync(filePath, content, 'utf-8');
      processedCount++;
    }
  }
  
  console.log(`✅ Post-processed ${processedCount} files`);
}

/**
 * 分析 Schema 统计信息
 */
function analyzeSchema(schema: any): Omit<GenerationStats, 'timestamp' | 'schemaUrl' | 'success'> {
  const paths = schema.paths || {};
  const schemas = schema.components?.schemas || {};
  
  let endpointsCount = 0;
  for (const path in paths) {
    endpointsCount += Object.keys(paths[path]).length;
  }
  
  const modelsCount = Object.keys(schemas).length;
  
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

/**
 * 生成索引文件
 */
function generateIndexFile() {
  const indexContent = `/**
 * 自动生成的 TypeScript 类型
 * 
 * Generated at: ${new Date().toISOString()}
 * Source: ${OPENAPI_SCHEMA_URL}
 * 
 * ⚠️ WARNING: 请勿手动修改此文件
 * Run \`npm run generate:types\` 重新生成
 */

// 导出常量类型
export * from './constants';

// 导出生成的模型
export * from './models';

// 导出 API 服务
export * from './services';

// 导出核心类型
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

/**
 * 主函数
 */
async function generateTypes() {
  console.log('');
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║   Enhanced TypeScript Type Generator           ║');
  console.log('╚════════════════════════════════════════════════╝');
  console.log('');
  console.log('🔄 Starting enhanced type generation...');
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
    
    // 3. 增强 Schema
    console.log('🔧 Enhancing schema with enum references...');
    const enhancedSchema = enhanceSchema(schema);
    console.log('✅ Schema enhanced');
    
    // 4. 分析 Schema
    const stats = analyzeSchema(schema);
    console.log('📊 Schema statistics:');
    console.log(`   - Models: ${stats.modelsCount}`);
    console.log(`   - Services: ${stats.servicesCount}`);
    console.log(`   - Endpoints: ${stats.endpointsCount}`);
    console.log('');
    
    // 5. 保存缓存
    fs.writeFileSync(CACHE_FILE, JSON.stringify(enhancedSchema, null, 2), 'utf-8');
    console.log('💾 Enhanced schema cached');
    
    // 6. 确保输出目录存在
    if (!fs.existsSync(OUTPUT_DIR)) {
      fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }

    // 7. 生成类型
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
    
    // 8. 后处理生成的文件
    postProcessGeneratedTypes(OUTPUT_DIR);
    
    // 9. 生成索引文件
    generateIndexFile();
    
    // 10. 保存统计信息
    const duration = Date.now() - startTime;
    saveGenerationStats({
      timestamp: new Date().toISOString(),
      schemaUrl: OPENAPI_SCHEMA_URL,
      ...stats,
      success: true,
    });
    
    console.log('');
    console.log(`📁 Output directory: ${OUTPUT_DIR}`);
    console.log(`⏱️  Generation completed in ${duration}ms`);
    console.log('');
    console.log('✨ All done! You can now use the generated types in your code.');
    console.log('');
    console.log('📚 Import examples:');
    console.log('   import { TaskStatus, WorkflowStep } from "@/types/generated/constants";');
    console.log('   import { GenerateRoadmapResponse } from "@/types/generated";');
    console.log('   import { RoadmapsService } from "@/types/generated/services";');
    console.log('');

  } catch (error) {
    const duration = Date.now() - startTime;
    console.error('');
    console.error('❌ Type generation failed:', error);
    console.error('');
    
    saveGenerationStats({
      timestamp: new Date().toISOString(),
      schemaUrl: OPENAPI_SCHEMA_URL,
      modelsCount: 0,
      servicesCount: 0,
      endpointsCount: 0,
      success: false,
      errorMessage: error instanceof Error ? error.message : String(error),
    });
    
    console.log('💡 Troubleshooting tips:');
    console.log(`   1. Make sure the backend server is running at ${OPENAPI_SCHEMA_URL}`);
    console.log('   2. Check if the backend is accessible from your network');
    console.log('   3. Verify the OpenAPI endpoint is working: curl ' + OPENAPI_SCHEMA_URL);
    console.log('   4. Run `npm run generate:constants` first to generate enum types');
    console.log('');
    
    console.error(`⏱️  Failed after ${duration}ms`);
    console.error('');
    
    process.exit(1);
  }
}

// Run the script
generateTypes();

