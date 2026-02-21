"""
HiveMind Code Quality Checker — 类 SonarQube 代码质量检查系统

功能：
- 后端 Python 代码检查 (Ruff lint + format, 安全扫描, 复杂度, import 检查)
- 前端 TypeScript/React 代码检查 (ESLint, TypeScript 严格模式)
- 跨语言通用检查 (TODO/FIXME 统计, 重复代码, 文件大小)
- 生成 HTML 报告

用法：
    python .agent/checks/code_quality.py                    # 全量检查
    python .agent/checks/code_quality.py --backend          # 仅后端
    python .agent/checks/code_quality.py --frontend         # 仅前端
    python .agent/checks/code_quality.py --report           # 生成 HTML 报告
    python .agent/checks/code_quality.py --fix              # 自动修复可修复项
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

# Windows 控制台 UTF-8 支持
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════════════
# 配置常量
# ═══════════════════════════════════════════════════════

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
REPORT_DIR = PROJECT_ROOT / ".agent" / "checks" / "reports"

# 阈值配置
MAX_FILE_LINES = 500          # 单文件最大行数
MAX_FUNCTION_LINES = 80       # 单函数最大行数
MAX_CYCLOMATIC_COMPLEXITY = 15  # 圈复杂度上限
MAX_PARAMS = 7                # 函数最大参数数
MAX_FILE_SIZE_KB = 50         # 单文件最大 KB
DUPLICATE_MIN_LINES = 6       # 重复代码最小行数

# 排除目录
BACKEND_EXCLUDES = {"__pycache__", ".venv", "venv", "alembic", "node_modules"}
FRONTEND_EXCLUDES = {"node_modules", "dist", ".vite", "build"}


# ═══════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════

@dataclass
class Issue:
    """单个检查问题"""
    file: str
    line: int
    rule: str
    severity: Literal["error", "warning", "info"]
    message: str
    category: str  # lint, security, complexity, style, maintenance

@dataclass
class CheckResult:
    """检查模块结果"""
    name: str
    passed: bool
    issues: list[Issue] = field(default_factory=list)
    duration_ms: int = 0
    summary: str = ""

@dataclass
class QualityReport:
    """完整质量报告"""
    timestamp: str = ""
    duration_ms: int = 0
    results: list[CheckResult] = field(default_factory=list)
    score: int = 100  # 0-100 质量评分


# ═══════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════

def run_cmd(cmd: list[str], cwd: Path | None = None, timeout: int = 120) -> tuple[int, str, str]:
    """执行命令并返回 (returncode, stdout, stderr)"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            shell=(sys.platform == "win32"),  # Windows 需要 shell=True 才能找到 npx.cmd
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", f"Command timed out after {timeout}s"

def relative_path(file_path: str, base: Path) -> str:
    """转为相对路径"""
    try:
        return str(Path(file_path).relative_to(base))
    except ValueError:
        return file_path

def print_header(text: str):
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")

def print_check(name: str, passed: bool, detail: str = ""):
    icon = "✅" if passed else "❌"
    suffix = f" — {detail}" if detail else ""
    print(f"  {icon} {name}{suffix}")

def severity_color(severity: str) -> str:
    return {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(severity, "⚪")


# ═══════════════════════════════════════════════════════
# 后端检查模块
# ═══════════════════════════════════════════════════════

def check_backend_lint(fix: bool = False) -> CheckResult:
    """Ruff lint 检查"""
    start = time.time()
    issues = []
    
    cmd = ["python", "-m", "ruff", "check", "app/", "--output-format=json"]
    if fix:
        cmd.append("--fix")
    
    code, stdout, stderr = run_cmd(cmd, BACKEND_DIR)
    
    if stdout.strip():
        try:
            ruff_issues = json.loads(stdout)
            for item in ruff_issues:
                issues.append(Issue(
                    file=relative_path(item.get("filename", ""), BACKEND_DIR),
                    line=item.get("location", {}).get("row", 0),
                    rule=item.get("code", ""),
                    severity="error" if item.get("code", "").startswith(("E9", "F")) else "warning",
                    message=item.get("message", ""),
                    category="lint",
                ))
        except json.JSONDecodeError:
            pass
    
    duration = int((time.time() - start) * 1000)
    return CheckResult(
        name="Backend Lint (Ruff)",
        passed=len([i for i in issues if i.severity == "error"]) == 0,
        issues=issues,
        duration_ms=duration,
        summary=f"{len(issues)} issues found",
    )

def check_backend_format() -> CheckResult:
    """Ruff format 检查 (不修改，只检查)"""
    start = time.time()
    issues = []
    
    code, stdout, stderr = run_cmd(
        ["python", "-m", "ruff", "format", "--check", "--diff", "app/"],
        BACKEND_DIR,
    )
    
    if code != 0 and stdout.strip():
        # 解析 diff 输出找到需要格式化的文件
        for line in stdout.splitlines():
            if line.startswith("--- "):
                filepath = line[4:].strip()
                issues.append(Issue(
                    file=relative_path(filepath, BACKEND_DIR),
                    line=0,
                    rule="FORMAT",
                    severity="warning",
                    message="File needs formatting (run `ruff format app/`)",
                    category="style",
                ))
    
    duration = int((time.time() - start) * 1000)
    return CheckResult(
        name="Backend Format (Ruff)",
        passed=code == 0,
        issues=issues,
        duration_ms=duration,
        summary="All formatted" if code == 0 else f"{len(issues)} files need formatting",
    )

def check_backend_security() -> CheckResult:
    """Python 安全检查 — 检测常见安全问题"""
    start = time.time()
    issues = []
    
    # 安全模式匹配
    security_patterns = [
        (r"(?<!\.)\beval\s*\(", "SEC001", "error", "使用 eval() 存在代码注入风险"),
        (r"(?<!\.)\bexec\s*\(", "SEC002", "error", "使用 exec() 存在代码注入风险"),
        (r"__import__\s*\(", "SEC003", "warning", "动态导入可能存在安全风险"),
        (r"os\.system\s*\(", "SEC004", "error", "使用 os.system() 存在命令注入风险，请用 subprocess"),
        (r"pickle\.loads?\s*\(", "SEC005", "error", "反序列化不受信任的数据存在远程代码执行风险"),
        (r"yaml\.load\s*\([^)]*\)(?!.*Loader)", "SEC006", "warning", "yaml.load() 应指定 Loader=yaml.SafeLoader"),
        (r"(?<!hashed_)(?<!_)password\s*=\s*[\"'][^\"']+[\"']", "SEC007", "error", "硬编码密码"),
        (r"(api_key|secret_key|token)\s*=\s*[\"'][^\"']{8,}[\"']", "SEC008", "error", "硬编码密钥/Token"),
        (r"verify\s*=\s*False", "SEC009", "warning", "禁用 SSL 验证"),
        (r"debug\s*=\s*True", "SEC010", "warning", "生产环境不应开启 DEBUG"),
    ]
    
    app_dir = BACKEND_DIR / "app"
    if not app_dir.exists():
        return CheckResult(name="Backend Security", passed=True, issues=[], 
                          duration_ms=0, summary="app/ not found, skipped")
    
    for py_file in app_dir.rglob("*.py"):
        if any(ex in py_file.parts for ex in BACKEND_EXCLUDES):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            for lineno, line in enumerate(content.splitlines(), 1):
                # 跳过注释行
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for pattern, rule, severity, message in security_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append(Issue(
                            file=relative_path(str(py_file), BACKEND_DIR),
                            line=lineno,
                            rule=rule,
                            severity=severity,
                            message=message,
                            category="security",
                        ))
        except Exception:
            pass
    
    duration = int((time.time() - start) * 1000)
    errors = [i for i in issues if i.severity == "error"]
    return CheckResult(
        name="Backend Security Scan",
        passed=len(errors) == 0,
        issues=issues,
        duration_ms=duration,
        summary=f"{len(issues)} security issues ({len(errors)} critical)",
    )

def check_backend_complexity() -> CheckResult:
    """代码复杂度检查 — 文件长度、函数长度、参数数量"""
    start = time.time()
    issues = []
    
    app_dir = BACKEND_DIR / "app"
    if not app_dir.exists():
        return CheckResult(name="Backend Complexity", passed=True, issues=[],
                          duration_ms=0, summary="app/ not found, skipped")
    
    for py_file in app_dir.rglob("*.py"):
        if any(ex in py_file.parts for ex in BACKEND_EXCLUDES):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()
            rel = relative_path(str(py_file), BACKEND_DIR)
            
            # 检查文件长度
            if len(lines) > MAX_FILE_LINES:
                issues.append(Issue(
                    file=rel, line=1, rule="CMPLX001", severity="warning",
                    message=f"文件过长: {len(lines)} 行 (阈值 {MAX_FILE_LINES})",
                    category="complexity",
                ))
            
            # 检查文件大小
            size_kb = py_file.stat().st_size / 1024
            if size_kb > MAX_FILE_SIZE_KB:
                issues.append(Issue(
                    file=rel, line=1, rule="CMPLX002", severity="warning",
                    message=f"文件过大: {size_kb:.1f}KB (阈值 {MAX_FILE_SIZE_KB}KB)",
                    category="complexity",
                ))
            
            # 检查函数长度和参数数量
            func_pattern = re.compile(r"^(\s*)(async\s+)?def\s+(\w+)\s*\(([^)]*)\)", re.MULTILINE)
            for match in func_pattern.finditer(content):
                indent = len(match.group(1))
                func_name = match.group(3)
                params_str = match.group(4)
                func_start_line = content[:match.start()].count("\n") + 1
                
                # 参数数量
                params = [p.strip() for p in params_str.split(",") if p.strip() and p.strip() != "self" and p.strip() != "cls"]
                if len(params) > MAX_PARAMS:
                    issues.append(Issue(
                        file=rel, line=func_start_line, rule="CMPLX003", severity="warning",
                        message=f"函数 `{func_name}` 参数过多: {len(params)} 个 (阈值 {MAX_PARAMS})",
                        category="complexity",
                    ))
                
                # 函数长度 (简化计算: 到下一个同缩进的 def/class 或文件末尾)
                func_lines = 0
                for line in lines[func_start_line:]:
                    if func_lines > 0 and line.strip() and not line.startswith(" " * (indent + 1)):
                        if re.match(r"^\s*(async\s+)?def\s+|^\s*class\s+", line):
                            break
                    func_lines += 1
                
                if func_lines > MAX_FUNCTION_LINES:
                    issues.append(Issue(
                        file=rel, line=func_start_line, rule="CMPLX004", severity="warning",
                        message=f"函数 `{func_name}` 过长: {func_lines} 行 (阈值 {MAX_FUNCTION_LINES})",
                        category="complexity",
                    ))
        except Exception:
            pass
    
    duration = int((time.time() - start) * 1000)
    return CheckResult(
        name="Backend Complexity",
        passed=len([i for i in issues if i.severity == "error"]) == 0,
        issues=issues,
        duration_ms=duration,
        summary=f"{len(issues)} complexity issues",
    )

def check_backend_imports() -> CheckResult:
    """导入检查 — 确保没有循环导入、未使用的导入"""
    start = time.time()
    issues = []
    
    # 利用 ruff 的 F401 (未使用导入) 规则
    code, stdout, _ = run_cmd(
        ["python", "-m", "ruff", "check", "app/", "--select=F401,I", "--output-format=json"],
        BACKEND_DIR,
    )
    
    if stdout.strip():
        try:
            ruff_issues = json.loads(stdout)
            for item in ruff_issues:
                issues.append(Issue(
                    file=relative_path(item.get("filename", ""), BACKEND_DIR),
                    line=item.get("location", {}).get("row", 0),
                    rule=item.get("code", ""),
                    severity="warning",
                    message=item.get("message", ""),
                    category="maintenance",
                ))
        except json.JSONDecodeError:
            pass
    
    duration = int((time.time() - start) * 1000)
    return CheckResult(
        name="Backend Import Check",
        passed=True,  # 导入问题不阻断
        issues=issues,
        duration_ms=duration,
        summary=f"{len(issues)} import issues",
    )


# ═══════════════════════════════════════════════════════
# 前端检查模块
# ═══════════════════════════════════════════════════════

def check_frontend_eslint(fix: bool = False) -> CheckResult:
    """ESLint 检查"""
    start = time.time()
    issues = []
    
    cmd = ["npx", "eslint", ".", "--format=json"]
    if fix:
        cmd.append("--fix")
    
    code, stdout, stderr = run_cmd(cmd, FRONTEND_DIR, timeout=180)
    
    if stdout.strip():
        try:
            eslint_results = json.loads(stdout)
            for file_result in eslint_results:
                filepath = file_result.get("filePath", "")
                for msg in file_result.get("messages", []):
                    issues.append(Issue(
                        file=relative_path(filepath, FRONTEND_DIR),
                        line=msg.get("line", 0),
                        rule=msg.get("ruleId", "") or "",
                        severity="error" if msg.get("severity", 1) == 2 else "warning",
                        message=msg.get("message", ""),
                        category="lint",
                    ))
        except json.JSONDecodeError:
            pass
    
    duration = int((time.time() - start) * 1000)
    errors = [i for i in issues if i.severity == "error"]
    return CheckResult(
        name="Frontend ESLint",
        passed=len(errors) == 0,
        issues=issues,
        duration_ms=duration,
        summary=f"{len(issues)} issues ({len(errors)} errors)",
    )

def check_frontend_typescript() -> CheckResult:
    """TypeScript 类型检查"""
    start = time.time()
    issues = []
    
    code, stdout, stderr = run_cmd(["npx", "tsc", "--noEmit", "--pretty", "false"], FRONTEND_DIR, timeout=180)
    
    if code != 0:
        output = stdout + stderr
        ts_pattern = re.compile(r"(.+?)\((\d+),\d+\):\s+error\s+(TS\d+):\s+(.+)")
        for match in ts_pattern.finditer(output):
            issues.append(Issue(
                file=relative_path(match.group(1), FRONTEND_DIR),
                line=int(match.group(2)),
                rule=match.group(3),
                severity="error",
                message=match.group(4),
                category="lint",
            ))
    
    duration = int((time.time() - start) * 1000)
    return CheckResult(
        name="Frontend TypeScript",
        passed=code == 0,
        issues=issues,
        duration_ms=duration,
        summary=f"{len(issues)} type errors" if issues else "No type errors",
    )

def check_frontend_complexity() -> CheckResult:
    """前端代码复杂度检查"""
    start = time.time()
    issues = []
    
    src_dir = FRONTEND_DIR / "src"
    if not src_dir.exists():
        return CheckResult(name="Frontend Complexity", passed=True, issues=[],
                          duration_ms=0, summary="src/ not found")
    
    for ext in ("*.ts", "*.tsx", "*.css"):
        for f in src_dir.rglob(ext):
            if any(ex in f.parts for ex in FRONTEND_EXCLUDES):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                rel = relative_path(str(f), FRONTEND_DIR)
                
                if len(lines) > MAX_FILE_LINES:
                    issues.append(Issue(
                        file=rel, line=1, rule="CMPLX001", severity="warning",
                        message=f"文件过长: {len(lines)} 行 (阈值 {MAX_FILE_LINES})",
                        category="complexity",
                    ))
                
                size_kb = f.stat().st_size / 1024
                if size_kb > MAX_FILE_SIZE_KB:
                    issues.append(Issue(
                        file=rel, line=1, rule="CMPLX002", severity="warning",
                        message=f"文件过大: {size_kb:.1f}KB (阈值 {MAX_FILE_SIZE_KB}KB)",
                        category="complexity",
                    ))
            except Exception:
                pass
    
    duration = int((time.time() - start) * 1000)
    return CheckResult(
        name="Frontend Complexity",
        passed=True,
        issues=issues,
        duration_ms=duration,
        summary=f"{len(issues)} complexity issues",
    )

def check_frontend_security() -> CheckResult:
    """前端安全检查"""
    start = time.time()
    issues = []
    
    security_patterns = [
        (r"dangerouslySetInnerHTML", "FSEC001", "warning", "使用 dangerouslySetInnerHTML 存在 XSS 风险"),
        (r"innerHTML\s*=", "FSEC002", "warning", "直接设置 innerHTML 存在 XSS 风险"),
        (r"localStorage\.setItem\([^)]*token", "FSEC003", "info", "在 localStorage 存储 token，考虑使用 httpOnly cookie"),
        (r"console\.(log|debug|info|warn|error)\s*\(", "FSEC004", "info", "生产环境应移除 console 输出"),
        (r"(api_key|secret|password)\s*[:=]\s*[\"'][^\"']+[\"']", "FSEC005", "error", "前端代码中不应硬编码密钥"),
        (r"http://(?!localhost)", "FSEC006", "warning", "使用不安全的 HTTP 连接 (非 localhost)"),
    ]
    
    src_dir = FRONTEND_DIR / "src"
    if not src_dir.exists():
        return CheckResult(name="Frontend Security", passed=True, issues=[],
                          duration_ms=0, summary="src/ not found")
    
    for ext in ("*.ts", "*.tsx"):
        for f in src_dir.rglob(ext):
            if any(ex in f.parts for ex in FRONTEND_EXCLUDES):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                for lineno, line in enumerate(content.splitlines(), 1):
                    stripped = line.strip()
                    if stripped.startswith("//"):
                        continue
                    for pattern, rule, severity, message in security_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            issues.append(Issue(
                                file=relative_path(str(f), FRONTEND_DIR),
                                line=lineno,
                                rule=rule,
                                severity=severity,
                                message=message,
                                category="security",
                            ))
            except Exception:
                pass
    
    duration = int((time.time() - start) * 1000)
    errors = [i for i in issues if i.severity == "error"]
    return CheckResult(
        name="Frontend Security Scan",
        passed=len(errors) == 0,
        issues=issues,
        duration_ms=duration,
        summary=f"{len(issues)} security issues ({len(errors)} critical)",
    )


# ═══════════════════════════════════════════════════════
# 通用检查模块
# ═══════════════════════════════════════════════════════

def check_todo_fixme() -> CheckResult:
    """统计 TODO/FIXME/HACK/XXX 注释"""
    start = time.time()
    issues = []
    markers = {
        "TODO": "info",
        "FIXME": "warning",
        "HACK": "warning",
        "XXX": "warning",
        "BUG": "warning",
    }
    # 编译正则 —— 使用 \b 边界避免误匹配 (e.g. "debugging" 不应匹配 BUG)
    marker_patterns = {m: re.compile(rf"\b{m}\b", re.IGNORECASE) for m in markers}
    
    dirs_to_scan = [
        (BACKEND_DIR / "app", "*.py", BACKEND_EXCLUDES, "backend"),
        (FRONTEND_DIR / "src", "*.ts", FRONTEND_EXCLUDES, "frontend"),
        (FRONTEND_DIR / "src", "*.tsx", FRONTEND_EXCLUDES, "frontend"),
    ]
    
    for scan_dir, glob, excludes, prefix in dirs_to_scan:
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob(glob):
            if any(ex in f.parts for ex in excludes):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                for lineno, line in enumerate(content.splitlines(), 1):
                    for marker, severity in markers.items():
                        if marker_patterns[marker].search(line):
                            # 提取注释内容
                            comment = line.strip()
                            if len(comment) > 100:
                                comment = comment[:100] + "..."
                            base_dir = BACKEND_DIR if prefix == "backend" else FRONTEND_DIR
                            issues.append(Issue(
                                file=f"{prefix}/{relative_path(str(f), base_dir)}",
                                line=lineno,
                                rule=f"MAINT-{marker}",
                                severity=severity,
                                message=comment,
                                category="maintenance",
                            ))
            except Exception:
                pass
    
    duration = int((time.time() - start) * 1000)
    # 按 marker 统计
    marker_counts = defaultdict(int)
    for i in issues:
        marker = i.rule.split("-")[1]
        marker_counts[marker] += 1
    
    summary_parts = [f"{marker}: {count}" for marker, count in sorted(marker_counts.items())]
    return CheckResult(
        name="TODO/FIXME Tracker",
        passed=True,  # TODO 不阻断构建
        issues=issues,
        duration_ms=int((time.time() - start) * 1000),
        summary=", ".join(summary_parts) if summary_parts else "Clean",
    )

def check_duplicate_code() -> CheckResult:
    """简化版重复代码检测 — 基于行级指纹"""
    start = time.time()
    issues = []
    
    # 收集所有代码行的指纹
    line_groups: dict[str, list[tuple[str, int]]] = defaultdict(list)
    
    dirs_to_scan = [
        (BACKEND_DIR / "app", "*.py", BACKEND_EXCLUDES, BACKEND_DIR),
        (FRONTEND_DIR / "src", "*.ts", FRONTEND_EXCLUDES, FRONTEND_DIR),
        (FRONTEND_DIR / "src", "*.tsx", FRONTEND_EXCLUDES, FRONTEND_DIR),
    ]
    
    for scan_dir, glob, excludes, base in dirs_to_scan:
        if not scan_dir.exists():
            continue
        for f in scan_dir.rglob(glob):
            if any(ex in f.parts for ex in excludes):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                lines = content.splitlines()
                rel = relative_path(str(f), base)
                
                # 滑动窗口生成指纹
                for i in range(len(lines) - DUPLICATE_MIN_LINES + 1):
                    block = "\n".join(
                        l.strip() for l in lines[i:i + DUPLICATE_MIN_LINES]
                        if l.strip() and not l.strip().startswith(("#", "//", "/*", "*", "import", "from"))
                    )
                    if len(block) > 50:  # 忽略太短的块
                        line_groups[block].append((rel, i + 1))
            except Exception:
                pass
    
    # 找到在不同文件中出现的重复块
    seen = set()
    for block, locations in line_groups.items():
        if len(locations) < 2:
            continue
        # 去掉同文件相邻行的重复
        unique_files = set(loc[0] for loc in locations)
        if len(unique_files) < 2:
            continue
        key = frozenset((loc[0], loc[1]) for loc in locations[:3])
        if key in seen:
            continue
        seen.add(key)
        
        loc_desc = ", ".join(f"{loc[0]}:{loc[1]}" for loc in locations[:3])
        if len(locations) > 3:
            loc_desc += f" (+{len(locations) - 3} more)"
        
        issues.append(Issue(
            file=locations[0][0],
            line=locations[0][1],
            rule="DUP001",
            severity="info",
            message=f"重复代码块 ({DUPLICATE_MIN_LINES}+ 行) 出现于: {loc_desc}",
            category="maintenance",
        ))
    
    duration = int((time.time() - start) * 1000)
    return CheckResult(
        name="Duplicate Code Detection",
        passed=True,
        issues=issues[:20],  # 限制输出
        duration_ms=duration,
        summary=f"{len(issues)} potential duplicates",
    )


# ═══════════════════════════════════════════════════════
# 质量评分
# ═══════════════════════════════════════════════════════

def calculate_score(results: list[CheckResult]) -> int:
    """计算 0-100 质量评分。
    
    评分逻辑:
    - 错误 (lint/security): -5 分/个
    - 警告 (format/complexity): -1 分/个
    - 信息 (TODO/duplicate): 软惩罚，总扣分上限 15 分
    """
    score = 100.0
    info_penalty = 0.0
    
    for r in results:
        for issue in r.issues:
            if issue.severity == "error":
                score -= 5
            elif issue.severity == "warning":
                score -= 1
            elif issue.severity == "info":
                info_penalty += 0.1
    
    # TODO/重复代码等 info 级问题总扣分不超过 15 分
    score -= min(info_penalty, 15)
    return max(0, min(100, int(score)))

def score_grade(score: int) -> tuple[str, str]:
    """分数 → 等级"""
    if score >= 90: return "A", "🟢"
    if score >= 80: return "B", "🟡"
    if score >= 70: return "C", "🟠"
    if score >= 60: return "D", "🔴"
    return "F", "⛔"


# ═══════════════════════════════════════════════════════
# HTML 报告生成
# ═══════════════════════════════════════════════════════

def generate_html_report(report: QualityReport) -> str:
    """生成 HTML 质量报告"""
    grade, icon = score_grade(report.score)
    
    # 统计
    total_issues = sum(len(r.issues) for r in report.results)
    errors = sum(1 for r in report.results for i in r.issues if i.severity == "error")
    warnings = sum(1 for r in report.results for i in r.issues if i.severity == "warning")
    infos = sum(1 for r in report.results for i in r.issues if i.severity == "info")
    
    # 按类别统计
    categories = defaultdict(int)
    for r in report.results:
        for i in r.issues:
            categories[i.category] += 1
    
    # 构建 issues 表格行
    issue_rows = ""
    for r in report.results:
        for issue in r.issues:
            sev_class = {"error": "severity-error", "warning": "severity-warning", "info": "severity-info"}[issue.severity]
            sev_label = {"error": "错误", "warning": "警告", "info": "信息"}[issue.severity]
            cat_label = {
                "lint": "代码规范", "security": "安全", "complexity": "复杂度",
                "style": "风格", "maintenance": "维护",
            }.get(issue.category, issue.category)
            issue_rows += f"""
            <tr>
                <td><span class="{sev_class}">{sev_label}</span></td>
                <td>{cat_label}</td>
                <td><code>{issue.rule}</code></td>
                <td class="file-path">{issue.file}:{issue.line}</td>
                <td>{issue.message}</td>
            </tr>"""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HiveMind Code Quality Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', -apple-system, sans-serif; background: #0A0E1A; color: #F8FAFC; padding: 24px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        .header {{ text-align: center; padding: 40px 0; }}
        .header h1 {{ font-size: 28px; background: linear-gradient(135deg, #06D6A0, #118AB2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .header .timestamp {{ color: #94A3B8; margin-top: 8px; }}
        
        .score-card {{ background: #111827; border-radius: 16px; padding: 32px; text-align: center; margin: 24px 0; border: 1px solid rgba(255,255,255,0.06); }}
        .score {{ font-size: 72px; font-weight: bold; }}
        .score.grade-a {{ color: #06D6A0; }}
        .score.grade-b {{ color: #FFD166; }}
        .score.grade-c {{ color: #FF9800; }}
        .score.grade-d {{ color: #EF476F; }}
        .score.grade-f {{ color: #FF1744; }}
        .score-label {{ color: #94A3B8; font-size: 14px; margin-top: 8px; }}
        
        .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 24px 0; }}
        .stat {{ background: #111827; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid rgba(255,255,255,0.06); }}
        .stat .value {{ font-size: 32px; font-weight: bold; }}
        .stat .label {{ color: #94A3B8; font-size: 13px; margin-top: 4px; }}
        .stat.error .value {{ color: #EF476F; }}
        .stat.warning .value {{ color: #FFD166; }}
        .stat.info .value {{ color: #118AB2; }}
        .stat.total .value {{ color: #F8FAFC; }}
        
        .checks {{ margin: 24px 0; }}
        .check {{ background: #111827; border-radius: 12px; padding: 16px 20px; margin: 8px 0; display: flex; justify-content: space-between; align-items: center; border: 1px solid rgba(255,255,255,0.06); }}
        .check .name {{ font-weight: 500; }}
        .check .detail {{ color: #94A3B8; font-size: 13px; }}
        .check .status {{ font-size: 20px; }}
        .check .time {{ color: #475569; font-size: 12px; }}
        
        .issues {{ margin: 24px 0; }}
        .issues h2 {{ margin-bottom: 16px; font-size: 20px; }}
        table {{ width: 100%; border-collapse: collapse; background: #111827; border-radius: 12px; overflow: hidden; }}
        th {{ background: #1F2937; padding: 12px 16px; text-align: left; font-size: 13px; color: #94A3B8; font-weight: 500; }}
        td {{ padding: 10px 16px; border-top: 1px solid rgba(255,255,255,0.04); font-size: 13px; }}
        tr:hover {{ background: rgba(255,255,255,0.02); }}
        
        .severity-error {{ color: #EF476F; font-weight: 600; }}
        .severity-warning {{ color: #FFD166; }}
        .severity-info {{ color: #118AB2; }}
        .file-path {{ color: #94A3B8; font-family: monospace; font-size: 12px; }}
        code {{ background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
        
        .footer {{ text-align: center; color: #475569; padding: 40px 0; font-size: 12px; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🐝 HiveMind Code Quality Report</h1>
        <div class="timestamp">{report.timestamp} · 耗时 {report.duration_ms}ms</div>
    </div>
    
    <div class="score-card">
        <div class="score grade-{grade.lower()}">{grade}</div>
        <div class="score-label">质量评分: {report.score}/100</div>
    </div>
    
    <div class="stats">
        <div class="stat total"><div class="value">{total_issues}</div><div class="label">总问题数</div></div>
        <div class="stat error"><div class="value">{errors}</div><div class="label">错误</div></div>
        <div class="stat warning"><div class="value">{warnings}</div><div class="label">警告</div></div>
        <div class="stat info"><div class="value">{infos}</div><div class="label">信息</div></div>
    </div>
    
    <div class="checks">
        <h2>📋 检查项</h2>
        {"".join(f'''
        <div class="check">
            <div><span class="name">{r.name}</span><br><span class="detail">{r.summary}</span></div>
            <div><span class="status">{"✅" if r.passed else "❌"}</span> <span class="time">{r.duration_ms}ms</span></div>
        </div>''' for r in report.results)}
    </div>
    
    {"" if not issue_rows else f'''
    <div class="issues">
        <h2>🔍 详细问题列表</h2>
        <table>
            <thead><tr><th>级别</th><th>类别</th><th>规则</th><th>位置</th><th>描述</th></tr></thead>
            <tbody>{issue_rows}</tbody>
        </table>
    </div>'''}
    
    <div class="footer">
        HiveMind Code Quality System · Powered by Ruff, ESLint, TypeScript, Custom Analyzers
    </div>
</div>
</body>
</html>"""
    return html


# ═══════════════════════════════════════════════════════
# 主程序
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="HiveMind Code Quality Checker")
    parser.add_argument("--backend", action="store_true", help="仅检查后端")
    parser.add_argument("--frontend", action="store_true", help="仅检查前端")
    parser.add_argument("--report", action="store_true", help="生成 HTML 报告")
    parser.add_argument("--fix", action="store_true", help="自动修复可修复的问题")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细问题列表")
    args = parser.parse_args()
    
    # 如果没有指定范围，检查全部
    check_be = args.backend or (not args.backend and not args.frontend)
    check_fe = args.frontend or (not args.backend and not args.frontend)
    
    print_header("🐝 HiveMind Code Quality Checker")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  项目: {PROJECT_ROOT}")
    print(f"  模式: {'自动修复' if args.fix else '检查'}")
    
    total_start = time.time()
    results: list[CheckResult] = []
    
    # === 后端检查 ===
    if check_be:
        print_header("🐍 Backend Checks")
        
        checks = [
            ("Lint (Ruff)", lambda: check_backend_lint(args.fix)),
            ("Format (Ruff)", check_backend_format),
            ("Security Scan", check_backend_security),
            ("Complexity", check_backend_complexity),
            ("Import Check", check_backend_imports),
        ]
        
        for name, check_fn in checks:
            result = check_fn()
            results.append(result)
            print_check(result.name, result.passed, result.summary)
    
    # === 前端检查 ===
    if check_fe:
        print_header("⚛️ Frontend Checks")
        
        checks = [
            ("ESLint", lambda: check_frontend_eslint(args.fix)),
            ("TypeScript", check_frontend_typescript),
            ("Security Scan", check_frontend_security),
            ("Complexity", check_frontend_complexity),
        ]
        
        for name, check_fn in checks:
            result = check_fn()
            results.append(result)
            print_check(result.name, result.passed, result.summary)
    
    # === 通用检查 ===
    print_header("🔎 Cross-Language Checks")
    
    for check_fn in [check_todo_fixme, check_duplicate_code]:
        result = check_fn()
        results.append(result)
        print_check(result.name, result.passed, result.summary)
    
    # === 计算评分 ===
    total_duration = int((time.time() - total_start) * 1000)
    
    report = QualityReport(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        duration_ms=total_duration,
        results=results,
        score=calculate_score(results),
    )
    
    grade, icon = score_grade(report.score)
    
    print_header(f"📊 Quality Score: {icon} {grade} ({report.score}/100)")
    
    total_issues = sum(len(r.issues) for r in results)
    errors = sum(1 for r in results for i in r.issues if i.severity == "error")
    warnings = sum(1 for r in results for i in r.issues if i.severity == "warning")
    infos = sum(1 for r in results for i in r.issues if i.severity == "info")
    
    print(f"  🔴 Errors:   {errors}")
    print(f"  🟡 Warnings: {warnings}")
    print(f"  🔵 Info:     {infos}")
    print(f"  📑 Total:    {total_issues}")
    print(f"  ⏱️  Duration: {total_duration}ms")
    
    # === 详细输出 ===
    if args.verbose:
        print_header("📝 Detailed Issues")
        for r in results:
            if r.issues:
                print(f"\n  [{r.name}]")
                for issue in r.issues[:20]:  # 每个类别最多显示 20 条
                    print(f"    {severity_color(issue.severity)} {issue.file}:{issue.line} [{issue.rule}] {issue.message}")
                if len(r.issues) > 20:
                    print(f"    ... and {len(r.issues) - 20} more")
    
    # === 生成报告 ===
    if args.report:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_file = REPORT_DIR / f"quality-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
        report_file.write_text(generate_html_report(report), encoding="utf-8")
        print(f"\n  📄 HTML Report: {report_file}")
    
    # === 退出码 ===
    all_passed = all(r.passed for r in results)
    if not all_passed:
        print(f"\n  ⚠️ Some checks failed. Run with --fix to auto-fix, or --verbose for details.")
    
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
