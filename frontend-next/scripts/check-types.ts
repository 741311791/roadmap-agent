/**
 * 类型检查脚本
 * 
 * 从后端获取最新 OpenAPI schema 并与本地 schema 对比
 * 检测类型差异并报告不一致项
 * 
 * Run: npm run check:types
 */

import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const SCHEMA_URL = `${BACKEND_URL}/openapi.json`;
const CACHE_FILE = path.join(__dirname, '../.openapi-cache.json');
const CACHE_HASH_FILE = path.join(__dirname, '../.openapi-hash.txt');

interface CheckResult {
  hasChanges: boolean;
  schemaHash: string;
  cachedHash?: string;
  differences?: string[];
  error?: string;
}

/**
 * 计算 Schema 的哈希值
 */
function calculateHash(schema: unknown): string {
  const schemaString = JSON.stringify(schema, null, 2);
  return crypto.createHash('sha256').update(schemaString).digest('hex');
}

/**
 * 获取远程 Schema
 */
async function fetchRemoteSchema(): Promise<unknown> {
  console.log(`📥 Fetching OpenAPI schema from: ${SCHEMA_URL}`);
  
  try {
    const response = await fetch(SCHEMA_URL);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const schema = await response.json();
    return schema;
  } catch (error) {
    throw new Error(`Failed to fetch schema: ${error instanceof Error ? error.message : String(error)}`);
  }
}

/**
 * 读取本地缓存的 Schema
 */
function readCachedSchema(): unknown | null {
  if (!fs.existsSync(CACHE_FILE)) {
    console.log('📭 No cached schema found');
    return null;
  }
  
  try {
    const content = fs.readFileSync(CACHE_FILE, 'utf-8');
    return JSON.parse(content);
  } catch (error) {
    console.warn('⚠️  Failed to read cached schema:', error);
    return null;
  }
}

/**
 * 读取本地缓存的 Hash
 */
function readCachedHash(): string | null {
  if (!fs.existsSync(CACHE_HASH_FILE)) {
    return null;
  }
  
  try {
    return fs.readFileSync(CACHE_HASH_FILE, 'utf-8').trim();
  } catch (error) {
    console.warn('⚠️  Failed to read cached hash:', error);
    return null;
  }
}

/**
 * 保存 Schema 到缓存
 */
function cacheSchema(schema: unknown, hash: string): void {
  try {
    // 保存 schema
    fs.writeFileSync(
      CACHE_FILE,
      JSON.stringify(schema, null, 2),
      'utf-8'
    );
    
    // 保存 hash
    fs.writeFileSync(
      CACHE_HASH_FILE,
      hash,
      'utf-8'
    );
    
    console.log('💾 Schema cached successfully');
  } catch (error) {
    console.warn('⚠️  Failed to cache schema:', error);
  }
}

/**
 * 比较两个 Schema 并找出差异
 */
function findDifferences(remote: any, local: any): string[] {
  const differences: string[] = [];
  
  // 比较版本
  if (remote.info?.version !== local.info?.version) {
    differences.push(
      `Version changed: ${local.info?.version || 'unknown'} → ${remote.info?.version || 'unknown'}`
    );
  }
  
  // 比较路径数量
  const remotePaths = Object.keys(remote.paths || {});
  const localPaths = Object.keys(local.paths || {});
  
  if (remotePaths.length !== localPaths.length) {
    differences.push(
      `API endpoints count changed: ${localPaths.length} → ${remotePaths.length}`
    );
  }
  
  // 检查新增的端点
  const newPaths = remotePaths.filter(p => !localPaths.includes(p));
  if (newPaths.length > 0) {
    differences.push(`New endpoints: ${newPaths.join(', ')}`);
  }
  
  // 检查删除的端点
  const removedPaths = localPaths.filter(p => !remotePaths.includes(p));
  if (removedPaths.length > 0) {
    differences.push(`Removed endpoints: ${removedPaths.join(', ')}`);
  }
  
  // 比较 schemas
  const remoteSchemas = Object.keys(remote.components?.schemas || {});
  const localSchemas = Object.keys(local.components?.schemas || {});
  
  if (remoteSchemas.length !== localSchemas.length) {
    differences.push(
      `Schemas count changed: ${localSchemas.length} → ${remoteSchemas.length}`
    );
  }
  
  // 检查新增的 schemas
  const newSchemas = remoteSchemas.filter(s => !localSchemas.includes(s));
  if (newSchemas.length > 0) {
    differences.push(`New schemas: ${newSchemas.slice(0, 5).join(', ')}${newSchemas.length > 5 ? '...' : ''}`);
  }
  
  return differences;
}

/**
 * 执行类型检查
 */
async function checkTypes(): Promise<CheckResult> {
  try {
    // 1. 获取远程 schema
    const remoteSchema = await fetchRemoteSchema();
    const remoteHash = calculateHash(remoteSchema);
    
    console.log(`🔑 Remote schema hash: ${remoteHash.substring(0, 12)}...`);
    
    // 2. 读取本地缓存
    const cachedSchema = readCachedSchema();
    const cachedHash = readCachedHash();
    
    if (cachedHash) {
      console.log(`🔑 Cached schema hash: ${cachedHash.substring(0, 12)}...`);
    }
    
    // 3. 比较哈希值
    if (cachedHash && remoteHash === cachedHash) {
      console.log('✅ Types are up to date!');
      return {
        hasChanges: false,
        schemaHash: remoteHash,
        cachedHash,
      };
    }
    
    // 4. 检测差异
    let differences: string[] = [];
    if (cachedSchema) {
      differences = findDifferences(remoteSchema, cachedSchema);
    } else {
      differences = ['Initial schema fetch'];
    }
    
    // 5. 缓存新 schema
    cacheSchema(remoteSchema, remoteHash);
    
    // 6. 报告结果
    console.log('\n⚠️  Backend API schema has changed!\n');
    
    if (differences.length > 0) {
      console.log('📋 Changes detected:');
      differences.forEach((diff, index) => {
        console.log(`  ${index + 1}. ${diff}`);
      });
      console.log('');
    }
    
    console.log('🔄 Run `npm run generate:types` to update types.\n');
    
    return {
      hasChanges: true,
      schemaHash: remoteHash,
      cachedHash: cachedHash || undefined,
      differences,
    };
    
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error('\n❌ Type check failed:', errorMessage);
    console.log('\n💡 Troubleshooting:');
    console.log('  1. Make sure the backend server is running');
    console.log(`  2. Check if ${SCHEMA_URL} is accessible`);
    console.log('  3. Verify BACKEND_URL environment variable\n');
    
    return {
      hasChanges: false,
      schemaHash: '',
      error: errorMessage,
    };
  }
}

/**
 * 主函数
 */
async function main() {
  console.log('🔍 Checking type definitions...\n');
  
  const result = await checkTypes();
  
  // 如果有变更且不是错误,退出代码为 1
  if (result.hasChanges && !result.error) {
    process.exit(1);
  }
  
  // 如果有错误,退出代码为 2
  if (result.error) {
    process.exit(2);
  }
  
  // 无变更,退出代码为 0
  process.exit(0);
}

// Run the script
main();
