import os
import re
import ast
import sys
from pathlib import Path

# 🏗️ [Path Fix]: Allow script to run independently
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

# 🛰️ [Standard]: Import logging context
try:
    from app.core.logging import get_trace_logger
    logger = get_trace_logger("scripts.sync_registry")
except ImportError:
    logger = None

class UniversalRegistrySync:
    """
    HiveMind 资产同步与治理中枢 (Universal Asset Guard)
    职责:
    1. 自动发现 BE/FE 核心资产
    2. 探测可观测性(useMonitor/trace_logger)覆盖率
    3. 核对 REGISTRY.md 登记情况
    """
    def __init__(self):
        self.root = ROOT_DIR
        self.be_root = ROOT_DIR / "backend" / "app"
        self.fe_root = ROOT_DIR / "frontend" / "src"
        self.registry_path = ROOT_DIR / "REGISTRY.md"
        
        self.assets = {
            "backend_services": [],
            "backend_models": [],
            "frontend_pages": [],
            "frontend_hooks": []
        }
        self.raw_registry_content = ""
        if self.registry_path.exists():
            self.raw_registry_content = self.registry_path.read_text(encoding='utf-8')

    def scan_backend(self):
        """扫描后端服务与模型"""
        # 扫描 Services
        service_dir = self.be_root / "services"
        if service_dir.exists():
            for p in service_dir.rglob("*.py"):
                if p.name.startswith("__"): continue
                self._parse_python_file(p, "backend_services")
        
        # 扫描 Models
        model_dir = self.be_root / "models"
        if model_dir.exists():
            for p in model_dir.rglob("*.py"):
                if p.name.startswith("__"): continue
                self._parse_python_file(p, "backend_models")

    def _parse_python_file(self, file_path: Path, category: str):
        try:
            content = file_path.read_text(encoding='utf-8')
            tree = ast.parse(content)
            has_trace_logger = "get_trace_logger" in content
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self.assets[category].append({
                        "name": node.name,
                        "path": str(file_path.relative_to(self.root)),
                        "monitored": has_trace_logger,
                        "registered": node.name in self.raw_registry_content
                    })
        except Exception as e:
            if logger: logger.warning(f"Failed to parse BE file {file_path}: {e}")

    def scan_frontend(self):
        """扫描前端页面与 Hook"""
        # 扫描 Pages
        page_dir = self.fe_root / "pages"
        if page_dir.exists():
            for p in page_dir.glob("*.tsx"):
                if p.name.endswith(".test.tsx"): continue
                self._analyze_ts_file(p, "frontend_pages", r"useMonitor")
                
        # 扫描 Hooks
        hook_dir = self.fe_root / "hooks"
        if hook_dir.exists():
            for p in hook_dir.glob("*.ts"):
                if p.name.endswith(".test.ts"): continue
                self._analyze_ts_file(p, "frontend_hooks", r"track")

    def _analyze_ts_file(self, file_path: Path, category: str, monitor_pattern: str):
        try:
            content = file_path.read_text(encoding='utf-8')
            name = file_path.stem
            # 简单启发式: 包含 monitor_pattern 视为已监控
            has_monitor = bool(re.search(monitor_pattern, content))
            
            self.assets[category].append({
                "name": name,
                "path": str(file_path.relative_to(self.root)),
                "monitored": has_monitor,
                "registered": name in self.raw_registry_content
            })
        except Exception as e:
            if logger: logger.warning(f"Failed to parse FE file {file_path}: {e}")

    def generate_report(self):
        print("\n" + "="*80)
        print("🛡️  HIVE-MIND ASSET INTEGRITY AUDIT REPORT")
        print("="*80)
        
        for category, items in self.assets.items():
            print(f"\n📂 CATEGORY: {category.upper()}")
            print(f"{'-'*30:30} | Registered | Monitored")
            for item in items:
                reg = "✅" if item["registered"] else "❌"
                mon = "🛰️" if item["monitored"] else "🌑"
                print(f"{item['name']:30} | {reg:10} | {mon}")
        
        print("\n" + "="*80)
        unreg = sum(1 for c in self.assets for i in self.assets[c] if not i["registered"])
        unmon = sum(1 for c in self.assets for i in self.assets[c] if not i["monitored"])
        
        print(f"📊 SUMMARY:")
        print(f"   - Total Assets Scanned: {sum(len(v) for v in self.assets.values())}")
        print(f"   - Missing Registration: {unreg} (Action Required)")
        print(f"   - Missing Observability: {unmon} (High Risk)")
        
        if unreg > 0 or unmon > 0:
            print("\n💡 Tip: Run with --auto-fix (TBD) or manually update REGISTRY.md")
        print("="*80 + "\n")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--enforce", action="store_true", help="Fail if missing registration or monitoring")
    parser.add_argument("--max-unregistered", type=int, default=160, help="Maximum allowed unregistered assets")
    parser.add_argument("--max-unmonitored", type=int, default=180, help="Maximum allowed unmonitored assets")
    args = parser.parse_args()

    syncer = UniversalRegistrySync()
    syncer.scan_backend()
    syncer.scan_frontend()
    syncer.generate_report()

    total_unreg = sum(1 for c in syncer.assets for i in syncer.assets[c] if not i["registered"])
    total_unmon = sum(1 for c in syncer.assets for i in syncer.assets[c] if not i["monitored"])

    if args.enforce:
        failed = False
        if total_unreg > args.max_unregistered:
            print(f"❌ FAILED: Unregistered assets ({total_unreg}) exceeds limit ({args.max_unregistered})")
            failed = True
        if total_unmon > args.max_unmonitored:
            print(f"❌ FAILED: Unmonitored assets ({total_unmon}) exceeds limit ({args.max_unmonitored})")
            failed = True
        
        if failed:
            sys.exit(1)
        else:
            print("✅ CI Audit Passed!")
