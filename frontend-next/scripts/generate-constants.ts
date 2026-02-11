/**
 * 常量类型生成脚本
 * 
 * 从后端 constants.py 生成前端 TypeScript 枚举类型
 * 
 * 功能:
 * - 解析后端 Python Enum 定义
 * - 生成对应的 TypeScript 枚举和类型
 * - 保持注释和文档
 * 
 * Run: npm run generate:constants
 */

import * as fs from 'fs';
import * as path from 'path';

const BACKEND_CONSTANTS_PATH = '../../backend/app/models/constants.py';
const OUTPUT_DIR = './types/generated';
const OUTPUT_FILE = 'constants.ts';

interface EnumMember {
  name: string;
  value: string;
  comment?: string;
}

interface EnumDefinition {
  name: string;
  docstring?: string;
  members: EnumMember[];
}

/**
 * 解析 Python Enum 定义
 */
function parsePythonEnums(content: string): EnumDefinition[] {
  const enums: EnumDefinition[] = [];
  
  // 匹配 class XXX(str, Enum): 开始的枚举定义
  const enumRegex = /class\s+(\w+)\(str,\s*Enum\):\s*\n([\s\S]*?)(?=\n\nclass|\n\n$|$)/g;
  
  let match;
  while ((match = enumRegex.exec(content)) !== null) {
    const enumName = match[1];
    const enumBody = match[2];
    
    // 提取 docstring
    const docstringMatch = enumBody.match(/"""\s*([\s\S]*?)\s*"""/);
    const docstring = docstringMatch ? docstringMatch[1].trim() : undefined;
    
    // 提取成员
    const members: EnumMember[] = [];
    const memberRegex = /(\w+)\s*=\s*"([^"]+)"\s*(?:#\s*(.+))?/g;
    
    let memberMatch;
    while ((memberMatch = memberRegex.exec(enumBody)) !== null) {
      members.push({
        name: memberMatch[1],
        value: memberMatch[2],
        comment: memberMatch[3]?.trim(),
      });
    }
    
    if (members.length > 0) {
      enums.push({
        name: enumName,
        docstring,
        members,
      });
    }
  }
  
  return enums;
}

/**
 * 生成 TypeScript 枚举代码
 */
function generateTypeScriptEnums(enums: EnumDefinition[]): string {
  let output = `/**
 * 自动生成的常量类型定义
 * 
 * 从后端 backend/app/models/constants.py 生成
 * 
 * ⚠️ WARNING: 请勿手动修改此文件
 * Run \`npm run generate:constants\` 重新生成
 * 
 * Generated at: ${new Date().toISOString()}
 */

`;

  for (const enumDef of enums) {
    // 添加 docstring
    if (enumDef.docstring) {
      output += `/**\n`;
      enumDef.docstring.split('\n').forEach(line => {
        output += ` * ${line}\n`;
      });
      output += ` */\n`;
    }
    
    // 生成 TypeScript enum
    output += `export enum ${enumDef.name} {\n`;
    for (const member of enumDef.members) {
      if (member.comment) {
        output += `  /** ${member.comment} */\n`;
      }
      output += `  ${member.name} = "${member.value}",\n`;
    }
    output += `}\n\n`;
    
    // 生成对应的 Union Type (用于类型检查)
    output += `/**\n`;
    output += ` * ${enumDef.name} 类型 (Union Type)\n`;
    output += ` */\n`;
    output += `export type ${enumDef.name}Type = ${enumDef.members.map(m => `"${m.value}"`).join(' | ')};\n\n`;
    
    // 生成类型守卫函数
    output += `/**\n`;
    output += ` * ${enumDef.name} 类型守卫\n`;
    output += ` */\n`;
    output += `export function is${enumDef.name}(value: any): value is ${enumDef.name}Type {\n`;
    output += `  return [\n`;
    for (const member of enumDef.members) {
      output += `    "${member.value}",\n`;
    }
    output += `  ].includes(value);\n`;
    output += `}\n\n`;
    
    // 生成标签映射 (用于 UI 显示)
    output += `/**\n`;
    output += ` * ${enumDef.name} 标签映射\n`;
    output += ` */\n`;
    output += `export const ${enumDef.name}Labels: Record<${enumDef.name}Type, string> = {\n`;
    for (const member of enumDef.members) {
      const label = member.comment || member.name;
      output += `  "${member.value}": "${label}",\n`;
    }
    output += `};\n\n`;
  }
  
  return output;
}

/**
 * 主函数
 */
async function generateConstants() {
  console.log('');
  console.log('╔════════════════════════════════════════════════╗');
  console.log('║   TypeScript Constants Generator               ║');
  console.log('╚════════════════════════════════════════════════╝');
  console.log('');
  console.log('🔄 Starting constants generation...');
  
  try {
    // 1. 读取后端常量文件
    const backendPath = path.resolve(__dirname, BACKEND_CONSTANTS_PATH);
    console.log(`📥 Reading backend constants from: ${backendPath}`);
    
    if (!fs.existsSync(backendPath)) {
      throw new Error(`Backend constants file not found: ${backendPath}`);
    }
    
    const content = fs.readFileSync(backendPath, 'utf-8');
    console.log('✅ Backend constants loaded');
    
    // 2. 解析枚举定义
    console.log('🔍 Parsing Python enums...');
    const enums = parsePythonEnums(content);
    console.log(`✅ Found ${enums.length} enums:`);
    enums.forEach(e => {
      console.log(`   - ${e.name} (${e.members.length} members)`);
    });
    console.log('');
    
    // 3. 生成 TypeScript 代码
    console.log('🔨 Generating TypeScript code...');
    const tsCode = generateTypeScriptEnums(enums);
    
    // 4. 确保输出目录存在
    const outputDir = path.resolve(__dirname, OUTPUT_DIR);
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }
    
    // 5. 写入文件
    const outputPath = path.join(outputDir, OUTPUT_FILE);
    fs.writeFileSync(outputPath, tsCode, 'utf-8');
    console.log(`✅ Constants generated successfully!`);
    console.log(`📁 Output file: ${outputPath}`);
    console.log('');
    
    // 6. 统计信息
    const totalMembers = enums.reduce((sum, e) => sum + e.members.length, 0);
    console.log('📊 Generation statistics:');
    console.log(`   - Enums: ${enums.length}`);
    console.log(`   - Total members: ${totalMembers}`);
    console.log(`   - Type guards: ${enums.length}`);
    console.log(`   - Label maps: ${enums.length}`);
    console.log('');
    
    console.log('✨ All done! You can now import constants from:');
    console.log(`   import { TaskStatus, WorkflowStep } from '@/types/generated/constants';`);
    console.log('');
    
  } catch (error) {
    console.error('');
    console.error('❌ Constants generation failed:', error);
    console.error('');
    
    if (error instanceof Error) {
      console.error('Error details:', error.message);
    }
    
    console.log('💡 Troubleshooting tips:');
    console.log('   1. Make sure backend/app/models/constants.py exists');
    console.log('   2. Check if the file follows the expected format');
    console.log('   3. Verify Python enum syntax is correct');
    console.log('');
    
    process.exit(1);
  }
}

// Run the script
generateConstants();

