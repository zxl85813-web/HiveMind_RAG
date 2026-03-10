#!/usr/bin/env node
import { execSync } from 'node:child_process';
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';

const cwd = process.cwd();
const HEX_COLOR_RE = /#[0-9A-Fa-f]{3,8}\b/g;
const args = new Set(process.argv.slice(2));
const mode = args.has('--all') ? 'all' : args.has('--staged') ? 'staged' : 'changed';

const EXCLUDE_PATTERNS = [
  /(^|[\\/])mock([\\/]|$)/,
  /(^|[\\/])App\.tsx$/,
  /(^|[\\/])styles[\\/]variables\.css$/,
  /\.test\.[^\\/]+$/,
  /\.spec\.[^\\/]+$/,
];

function normalize(p) {
  return p.replace(/\\/g, '/');
}

function getPathContext() {
  const asRepoRoot = existsSync(path.join(cwd, '.git')) && existsSync(path.join(cwd, 'frontend'));
  if (asRepoRoot) {
    return {
      srcAbs: path.join(cwd, 'frontend', 'src'),
      srcPrefixes: ['frontend/src/'],
      toAbs: (relPath) => path.resolve(cwd, relPath),
    };
  }
  return {
    srcAbs: path.join(cwd, 'src'),
    srcPrefixes: ['src/', 'frontend/src/'],
    toAbs: (relPath) => (
      relPath.startsWith('frontend/') ? path.resolve(cwd, '..', relPath) : path.resolve(cwd, relPath)
    ),
  };
}

function shouldCheck(relPath) {
  const normalized = normalize(relPath);
  if (!/\.(ts|tsx|css)$/.test(normalized)) {
    return false;
  }
  return !EXCLUDE_PATTERNS.some((re) => re.test(normalized));
}

function walk(dir) {
  if (!existsSync(dir)) {
    return [];
  }
  const out = [];
  for (const name of readdirSync(dir)) {
    const abs = path.join(dir, name);
    const st = statSync(abs);
    if (st.isDirectory()) {
      out.push(...walk(abs));
    } else {
      out.push(abs);
    }
  }
  return out;
}

function safeGitList(cmd) {
  try {
    const raw = execSync(cmd, { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    if (!raw) {
      return [];
    }
    return raw.split(/\r?\n/).map((line) => normalize(line.trim())).filter(Boolean);
  } catch {
    return [];
  }
}

function getChangedFiles() {
  const localUnstaged = safeGitList('git diff --name-only --diff-filter=ACMR');
  const localStaged = safeGitList('git diff --cached --name-only --diff-filter=ACMR');
  const local = [...new Set([...localUnstaged, ...localStaged])];
  if (local.length > 0) {
    return local;
  }

  const fromMain = safeGitList('git diff --name-only --diff-filter=ACMR origin/main...HEAD');
  if (fromMain.length > 0) {
    return fromMain;
  }
  return safeGitList('git diff --name-only --diff-filter=ACMR HEAD~1...HEAD');
}

const context = getPathContext();
let candidateRelative = [];

if (mode === 'all') {
  candidateRelative = walk(context.srcAbs).map((abs) => normalize(path.relative(cwd, abs)));
} else if (mode === 'staged') {
  candidateRelative = safeGitList('git diff --cached --name-only --diff-filter=ACMR');
} else {
  candidateRelative = getChangedFiles();
}

const targetFiles = candidateRelative
  .filter((file) => context.srcPrefixes.some((prefix) => file.startsWith(prefix)))
  .filter(shouldCheck)
  .map((rel) => context.toAbs(rel))
  .filter((abs) => existsSync(abs));

if (targetFiles.length === 0) {
  console.log(`[theme-check] No frontend files to check in mode: ${mode}`);
  process.exit(0);
}

const violations = [];
for (const abs of targetFiles) {
  const rel = normalize(path.relative(cwd, abs));
  const lines = readFileSync(abs, 'utf8').split(/\r?\n/);
  for (let i = 0; i < lines.length; i += 1) {
    const matches = lines[i].match(HEX_COLOR_RE);
    if (!matches) {
      continue;
    }
    violations.push({
      file: rel,
      line: i + 1,
      values: [...new Set(matches)],
    });
  }
}

if (violations.length > 0) {
  console.error(`[theme-check] Failed. Hardcoded hex colors found (${violations.length} matches):`);
  for (const v of violations) {
    console.error(`- ${v.file}:${v.line} -> ${v.values.join(', ')}`);
  }
  process.exit(1);
}

console.log(`[theme-check] Passed in mode: ${mode} (${targetFiles.length} file(s) scanned)`);
