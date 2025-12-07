/**
 * 环境变量验证脚本
 * 
 * 使用 Zod schema 验证环境变量
 * 提供类型化的环境变量导出
 * 
 * Run: npm run validate:env
 */

import { z } from 'zod';
import * as fs from 'fs';
import * as path from 'path';

/**
 * 环境变量 Schema 定义
 */
const envSchema = z.object({
  // API 配置
  NEXT_PUBLIC_API_URL: z.string().url('Invalid API URL').default('http://localhost:8000'),
  NEXT_PUBLIC_WS_URL: z.string().url('Invalid WebSocket URL').optional(),
  
  // OpenAPI Schema URL (用于类型生成)
  OPENAPI_SCHEMA_URL: z.string().url('Invalid OpenAPI URL').optional(),
  
  // 后端地址
  BACKEND_URL: z.string().url('Invalid Backend URL').optional(),
  
  // 环境类型
  NEXT_PUBLIC_ENV: z.enum(['development', 'staging', 'production']).default('development'),
  
  // 功能开关
  NEXT_PUBLIC_ENABLE_SSE: z
    .string()
    .default('true')
    .transform(val => val === 'true'),
  NEXT_PUBLIC_ENABLE_WEBSOCKET: z
    .string()
    .default('true')
    .transform(val => val === 'true'),
  NEXT_PUBLIC_ENABLE_POLLING_FALLBACK: z
    .string()
    .default('true')
    .transform(val => val === 'true'),
  
  // 调试选项
  NEXT_PUBLIC_DEBUG: z
    .string()
    .default('false')
    .transform(val => val === 'true'),
  NEXT_PUBLIC_LOG_LEVEL: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
});

/**
 * 环境变量类型
 */
export type Env = z.infer<typeof envSchema>;

/**
 * 读取 .env 文件
 */
function readEnvFile(filename: string): Record<string, string> {
  const envPath = path.join(process.cwd(), filename);
  
  if (!fs.existsSync(envPath)) {
    return {};
  }
  
  try {
    const content = fs.readFileSync(envPath, 'utf-8');
    const env: Record<string, string> = {};
    
    content.split('\n').forEach(line => {
      line = line.trim();
      
      // 跳过注释和空行
      if (line.startsWith('#') || !line) {
        return;
      }
      
      const [key, ...valueParts] = line.split('=');
      const value = valueParts.join('=').trim();
      
      if (key && value) {
        // 移除引号
        env[key.trim()] = value.replace(/^["']|["']$/g, '');
      }
    });
    
    return env;
  } catch (error) {
    console.warn(`⚠️  Failed to read ${filename}:`, error);
    return {};
  }
}

/**
 * 合并环境变量
 */
function mergeEnv(): Record<string, string> {
  // 优先级: process.env > .env.local > .env.development > .env
  const envFiles = [
    '.env',
    '.env.development',
    '.env.local',
  ];
  
  let merged: Record<string, string> = {};
  
  // 依次读取并合并
  for (const file of envFiles) {
    const env = readEnvFile(file);
    merged = { ...merged, ...env };
  }
  
  // process.env 优先级最高
  merged = { 
    ...merged, 
    ...Object.fromEntries(
      Object.entries(process.env).filter(([_, v]) => v !== undefined) as [string, string][]
    )
  };
  
  return merged;
}

/**
 * 验证环境变量
 */
function validateEnv(): { success: boolean; env?: Env; errors?: string[] } {
  console.log('🔍 Validating environment variables...\n');
  
  try {
    // 合并所有环境变量
    const rawEnv = mergeEnv();
    
    // 验证
    const env = envSchema.parse(rawEnv);
    
    console.log('✅ Environment variables are valid!\n');
    
    // 打印配置信息
    console.log('📋 Current configuration:');
    console.log(`  Environment: ${env.NEXT_PUBLIC_ENV}`);
    console.log(`  API URL: ${env.NEXT_PUBLIC_API_URL}`);
    
    if (env.NEXT_PUBLIC_WS_URL) {
      console.log(`  WebSocket URL: ${env.NEXT_PUBLIC_WS_URL}`);
    }
    
    console.log(`  SSE Enabled: ${env.NEXT_PUBLIC_ENABLE_SSE}`);
    console.log(`  WebSocket Enabled: ${env.NEXT_PUBLIC_ENABLE_WEBSOCKET}`);
    console.log(`  Polling Fallback: ${env.NEXT_PUBLIC_ENABLE_POLLING_FALLBACK}`);
    console.log(`  Debug Mode: ${env.NEXT_PUBLIC_DEBUG}`);
    console.log(`  Log Level: ${env.NEXT_PUBLIC_LOG_LEVEL}`);
    console.log('');
    
    return { success: true, env };
    
  } catch (error) {
    if (error instanceof z.ZodError) {
      console.error('❌ Environment variable validation failed:\n');
      
      const errors = error.issues.map(err => {
        const path = err.path.join('.');
        return `  • ${path}: ${err.message}`;
      });
      
      errors.forEach(err => console.error(err));
      console.log('');
      
      // 提供帮助信息
      console.log('💡 Troubleshooting:');
      console.log('  1. Check your .env.local file');
      console.log('  2. Copy .env.example to .env.local if it doesn\'t exist');
      console.log('  3. Make sure all required variables are set');
      console.log('  4. Verify URLs are valid (must include http:// or https://)');
      console.log('');
      
      return { success: false, errors: errors };
    }
    
    console.error('❌ Unexpected error:', error);
    return { success: false, errors: ['Unexpected validation error'] };
  }
}

/**
 * 生成 .env.example 文件
 */
function generateEnvExample() {
  const exampleContent = `# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Backend Configuration (for development)
BACKEND_URL=http://localhost:8000
OPENAPI_SCHEMA_URL=http://localhost:8000/openapi.json

# Environment
NEXT_PUBLIC_ENV=development

# Feature Flags
NEXT_PUBLIC_ENABLE_SSE=true
NEXT_PUBLIC_ENABLE_WEBSOCKET=true
NEXT_PUBLIC_ENABLE_POLLING_FALLBACK=true

# Debug Options
NEXT_PUBLIC_DEBUG=false
NEXT_PUBLIC_LOG_LEVEL=info
`;
  
  const examplePath = path.join(process.cwd(), '.env.example');
  
  try {
    fs.writeFileSync(examplePath, exampleContent, 'utf-8');
    console.log('✅ Generated .env.example file');
  } catch (error) {
    console.error('❌ Failed to generate .env.example:', error);
  }
}

/**
 * 主函数
 */
function main() {
  const args = process.argv.slice(2);
  
  // 如果传入 --generate-example 参数,生成示例文件
  if (args.includes('--generate-example')) {
    generateEnvExample();
    return;
  }
  
  // 验证环境变量
  const result = validateEnv();
  
  // 如果验证失败,退出代码为 1
  if (!result.success) {
    process.exit(1);
  }
  
  process.exit(0);
}

// Run the script
if (require.main === module) {
  main();
}

// 导出验证函数供其他模块使用
export { validateEnv, envSchema };
