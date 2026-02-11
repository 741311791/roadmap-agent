/**
 * Schema 同步状态检查脚本
 * 
 * 用于检查前端类型是否与后端 Schema 保持同步
 * 可用于 pre-commit hook 或 CI/CD 流程
 */

import * as fs from 'fs';
import * as path from 'path';
import * as https from 'https';
import * as http from 'http';
import * as crypto from 'crypto';

const OPENAPI_SCHEMA_URL = process.env.OPENAPI_SCHEMA_URL || 'http://localhost:8000/openapi.json';
const CACHE_FILE = './.openapi-cache.json';
const STATS_FILE = './types/generated/.generation-stats.json';

/**
 * 下载 Schema
 */
async function downloadSchema(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    
    client.get(url, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        resolve(data);
      });
    }).on('error', (error) => {
      reject(error);
    });
  });
}

/**
 * 计算哈希值
 */
function calculateHash(data: string): string {
  return crypto.createHash('sha256').update(data).digest('hex');
}

/**
 * 检查同步状态
 */
async function checkSyncStatus(): Promise<void> {
  console.log('🔍 Checking frontend-backend sync status...');
  console.log('');

  try {
    // 1. 检查缓存文件是否存在
    if (!fs.existsSync(CACHE_FILE)) {
      console.error('❌ Cache file not found: ' + CACHE_FILE);
      console.error('   Run "npm run generate:types" to generate types first.');
      console.error('');
      process.exit(1);
    }

    // 2. 读取缓存的 Schema
    const cachedSchema = fs.readFileSync(CACHE_FILE, 'utf-8');
    const cachedHash = calculateHash(cachedSchema);

    console.log('📦 Cached schema hash:', cachedHash.substring(0, 16) + '...');

    // 3. 下载最新的 Schema
    console.log('📥 Fetching latest schema from:', OPENAPI_SCHEMA_URL);
    
    let latestSchema: string;
    try {
      latestSchema = await downloadSchema(OPENAPI_SCHEMA_URL);
    } catch (error) {
      console.error('❌ Failed to fetch latest schema:', error);
      console.error('   Make sure the backend server is running.');
      console.error('');
      process.exit(1);
    }

    const latestHash = calculateHash(latestSchema);
    console.log('🔄 Latest schema hash:', latestHash.substring(0, 16) + '...');
    console.log('');

    // 4. 比对哈希值
    if (cachedHash === latestHash) {
      console.log('✅ Frontend types are in sync with backend!');
      console.log('');
      
      // 显示统计信息
      if (fs.existsSync(STATS_FILE)) {
        const stats = JSON.parse(fs.readFileSync(STATS_FILE, 'utf-8'));
        console.log('📊 Generation stats:');
        console.log(`   - Last generated: ${new Date(stats.timestamp).toLocaleString()}`);
        console.log(`   - Models: ${stats.modelsCount}`);
        console.log(`   - Services: ${stats.servicesCount}`);
        console.log(`   - Endpoints: ${stats.endpointsCount}`);
        console.log('');
      }
      
      process.exit(0);
    } else {
      console.error('❌ Frontend types are OUT OF SYNC with backend!');
      console.error('');
      console.error('Backend schema has changed. Please run:');
      console.error('');
      console.error('  npm run generate:types');
      console.error('');
      console.error('Or use the sync script:');
      console.error('');
      console.error('  ../scripts/sync-frontend-backend.sh');
      console.error('');
      
      // 分析差异
      try {
        const cachedJson = JSON.parse(cachedSchema);
        const latestJson = JSON.parse(latestSchema);
        
        const cachedPaths = Object.keys(cachedJson.paths || {});
        const latestPaths = Object.keys(latestJson.paths || {});
        
        const addedPaths = latestPaths.filter(p => !cachedPaths.includes(p));
        const removedPaths = cachedPaths.filter(p => !latestPaths.includes(p));
        
        if (addedPaths.length > 0 || removedPaths.length > 0) {
          console.error('📋 Detected changes:');
          
          if (addedPaths.length > 0) {
            console.error(`   - ${addedPaths.length} new endpoint(s)`);
          }
          
          if (removedPaths.length > 0) {
            console.error(`   - ${removedPaths.length} removed endpoint(s)`);
          }
          
          console.error('');
        }
      } catch (error) {
        // JSON 解析失败，跳过详细分析
      }
      
      process.exit(1);
    }
  } catch (error) {
    console.error('❌ Sync check failed:', error);
    console.error('');
    process.exit(1);
  }
}

// 运行检查
checkSyncStatus();

