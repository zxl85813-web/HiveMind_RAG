import fs from 'fs';
import path from 'path';
import { execSync } from 'child_process';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * 🛰️ [Architecture-Security]: SourceMap Offline Archiving Script
 * 
 * 作用:
 * 1. 自动获取当前 Git Commit Hash 作为版本标识。
 * 2. 扫描 dist 目录下的所有 .map 文件。
 * 3. 将其移动到根目录下的 debug_symbols 目录，实现跨版本隔离。
 * 4. 彻底删除 dist 目录中的 .map，确保公网无法下载到源码。
 */

const projectRoot = path.resolve(__dirname, '..');
const distDir = path.join(projectRoot, 'dist');
const symbolsBaseDir = path.join(projectRoot, 'debug_symbols');

async function run() {
  console.log('🚀 [HiveMind] Starting SourceMap archiving...');

  // 1. 获取当前版本 Hash (作为 Mapping 的 Key)
  let version = 'unknown';
  try {
    version = execSync('git rev-parse --short HEAD').toString().trim();
  } catch (e) {
    console.warn('⚠️ [Warn] Failed to get git hash, using timestamp.');
    version = new Date().toISOString().replace(/[:.]/g, '-');
  }

  const targetDir = path.join(symbolsBaseDir, version);
  console.log(`📦 Targeted version: ${version}`);

  // 2. 确保目标目录存在
  if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
  }

  // 3. 递归寻找 .map 文件
  function moveMaps(currentDir) {
    if (!fs.existsSync(currentDir)) return;

    const files = fs.readdirSync(currentDir);

    for (const file of files) {
      const fullPath = path.join(currentDir, file);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        moveMaps(fullPath);
      } else if (file.endsWith('.map')) {
        const relativePath = path.relative(distDir, fullPath);
        const targetPath = path.join(targetDir, relativePath);

        // 确保目标子目录存在
        fs.mkdirSync(path.dirname(targetPath), { recursive: true });

        // 移动文件
        fs.renameSync(fullPath, targetPath);
        console.log(`✅ Archived: ${file} -> debug_symbols/${version}/...`);
      }
    }
  }

  try {
    moveMaps(distDir);
    console.log(`✨ [Success] All SourceMaps moved to debug_symbols/${version}/`);
    console.log(`🔒 Public dist is now CLEAN and SECURE.`);
  } catch (err) {
    console.error('❌ [Error] Failed to archive maps:', err);
    process.exit(1);
  }
}

run();
