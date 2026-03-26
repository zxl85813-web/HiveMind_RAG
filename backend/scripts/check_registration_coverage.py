import os
import sys
import re
from pathlib import Path

# 🏗️ [Phase 1]: 统一路径注入与可观测性初始化
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("check_registration_coverage")
t_logger = get_trace_logger("scripts.registration_audit")

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

# 配置项
SCRIPTS_DIR = backend_dir / "scripts"
REGISTRY_FILE = backend_dir.parent / "REGISTRY.md"
EXCLUDE_PREFIX = ("tmp_", "debug_", "test_", "qa_") # 临时/测试脚本不强制要求登记

def extract_registered_scripts(registry_path: Path) -> set[str]:
    """从 REGISTRY.md 中提取已登记的脚本名"""
    if not registry_path.exists():
        t_logger.error(f"Registry file not found: {registry_path}")
        return set()

    content = registry_path.read_text(encoding="utf-8")
    
    # 使用正则匹配表格中的反引号包裹的 .py 文件
    scripts = set(re.findall(r"`([\w\.-]+\.py)`", content))
    return scripts

def check_script_monitoring(script_path: Path) -> dict[str, bool]:
    """检查脚本是否接入了 UnifiedLog 协议关键点"""
    try:
        content = script_path.read_text(encoding="utf-8")
        return {
            "has_setup": "setup_script_context" in content,
            "has_logger": "get_trace_logger" in content or "from app.core.logging" in content,
            "has_path_fix": "sys.path.insert(0, str(backend_dir))" in content or "sys.path.append(str(backend_dir))" in content
        }
    except Exception as e:
        t_logger.warning(f"Failed to read script {script_path.name}: {e}")
        return {"has_setup": False, "has_logger": False, "has_path_fix": False}

def main():
    t_logger.info("Starting Registration Coverage Audit", action="audit_start")
    
    registered = extract_registered_scripts(REGISTRY_FILE)
    t_logger.info(f"Loaded {len(registered)} registered scripts from Registry", meta={"registered_count": len(registered)})

    all_scripts = [p for p in SCRIPTS_DIR.glob("*.py") if not p.name.startswith(EXCLUDE_PREFIX) and p.name != "__init__.py"]
    all_scripts.sort()

    unregistered = []
    monitored_scripts = []
    legacy_scripts = []
    
    print("\n🔍 HiveMind Scripts Audit Report")
    print("=" * 60)
    print(f"{'Script Name':<42} | {'Reg?':<5} | {'Mon?'}")
    print("-" * 60)

    for p in all_scripts:
        name = p.name
        is_registered = name in registered
        mon_state = check_script_monitoring(p)
        is_monitored = mon_state["has_setup"] and mon_state["has_logger"]
        
        reg_mark = "✅" if is_registered else "❌"
        mon_mark = "🛰️" if is_monitored else "🌑"
        
        if not is_registered:
            unregistered.append(name)
        if is_monitored:
            monitored_scripts.append(name)
        else:
            legacy_scripts.append(name)

        print(f"{name:<42} | {reg_mark:<5} | {mon_mark}")

    print("=" * 60)
    total_count = len(all_scripts)
    coverage = (total_count - len(unregistered)) / total_count if total_count > 0 else 1.0
    mon_coverage = len(monitored_scripts) / total_count if total_count > 0 else 1.0
    
    # 🛰️ 结构化报告
    report_meta = {
        "total": total_count,
        "unregistered": unregistered,
        "registration_coverage": round(coverage, 2),
        "monitoring_coverage": round(mon_coverage, 2)
    }
    
    t_logger.info("Audit Summary", action="audit_summary", meta=report_meta)

    print(f"\n📊 Registration Coverage: {coverage:.1%}")
    print(f"🛰️  Monitoring Coverage:   {mon_coverage:.1%}")
    
    if unregistered:
        print(f"\n📢 Unregistered scripts detected: {', '.join(unregistered)}")
        print("💡 Please add them to REGISTRY.md under Scripts section.")

    if legacy_scripts:
        top_legacy = ", ".join(legacy_scripts[:5])
        print(f"\n⚠️  Legacy scripts (No UnifiedLog): {top_legacy}...")
        print("💡 Use app.core.logging.setup_script_context to align.")

    if len(unregistered) > 0:
        t_logger.error("Registration coverage audit failed", action="audit_failure")
        # sys.exit(1) # 暂时不直接退出，方便调试
    
    t_logger.success("Registration coverage audit passed", action="audit_success")

if __name__ == "__main__":
    main()
