import os
import re
import sys
from pathlib import Path

# 🛡️ [Windows-Harden]: Force UTF-8 for console output to prevent charmap errors
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# 🛡️ HiveMind 架构一致性巡检器 (Governance Auditor)
# 职责: 验证代码是否符合 [DES-004] 和 [AGENT-CODING-RULES]

class GovernanceAuditor:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.violations = []

    def audit_file_size(self):
        """[RULE-B001]: 检查文件是否过大。"""
        exclude_dirs = {"venv", ".gemini", "__pycache__", "node_modules", ".git"}
        for path in self.root_dir.glob("**/*.py"):
            if any(exc in str(path) for exc in exclude_dirs): continue
            try:
                content = path.read_text(encoding="utf-8")
                line_count = len(content.splitlines())
                if line_count > 300:
                    self.violations.append(f"[RULE-B001] 文件过大: {path.relative_to(self.root_dir)} ({line_count} lines)")
            except (UnicodeDecodeError, PermissionError):
                continue

    def audit_api_normalized(self):
        """[DES-004]: 检查路由是否使用了 ApiResponse。"""
        for path in self.root_dir.glob("backend/app/api/routes/*.py"):
            content = path.read_text(encoding="utf-8")
            if "def" in content and "ApiResponse" not in content and "__init__" not in str(path):
                self.violations.append(f"[DES-004] 路由未规范化: {path.relative_to(self.root_dir)}")

    def report(self):
        if not self.violations:
            print("[OK] Governance check passed! Codebase is healthy.")
        else:
            print(f"[FAIL] Found {len(self.violations)} governance violations:")
            for v in self.violations:
                print(f"  - {v}")
            
if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    auditor = GovernanceAuditor(project_root)
    auditor.audit_file_size()
    auditor.audit_api_normalized()
    auditor.report()
