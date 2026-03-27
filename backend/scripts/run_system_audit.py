import asyncio
import subprocess
import os
import sys
import json
import time
from pathlib import Path

# Paths
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if not backend_dir.exists():
    backend_dir = Path(__file__).resolve().parent.parent # if run from root

def run_command(cmd, cwd=None):
    print(f"Executing: {' '.join(cmd)}")
    start = time.time()
    try:
        process = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        duration = time.time() - start
        return {
            "success": process.returncode == 0,
            "stdout": process.stdout,
            "stderr": process.stderr,
            "duration": round(duration, 2)
        }
    except Exception as e:
        return {"success": False, "stdout": "", "stderr": str(e), "duration": 0}

async def perform_audit():
    print("🏥 HVM-SYSTEM-HEALTH: Starting Multi-Angle Audit...")
    
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sections": []
    }

    # 1. Regression & Intelligence (Pytest System Suite)
    print("Section 1: Swarm Intelligence & Observability pytests...")
    res_pytest = run_command(["pytest", "tests/system", "-v"], cwd=backend_dir)
    report["sections"].append({
        "name": "Intelligence & Observability (Unit/System)",
        "success": res_pytest["success"],
        "duration": res_pytest["duration"],
        "summary": "Passed All" if res_pytest["success"] else "Failure in Swarm Logic"
    })

    # 2. Resilience & Governance (SG-007 Drill)
    print("Section 2: Governance & Resilience Drills...")
    res_drill = run_command([sys.executable, "scripts/run_sg007_governance_drills.py", "--no-versioned"], cwd=backend_dir)
    report["sections"].append({
        "name": "Governance Resilience (Drills)",
        "success": res_drill["success"],
        "duration": res_drill["duration"],
        "summary": "Circuit Breaker & Rate Throttling Verified" if res_drill["success"] else "Resilience Gate FAILED"
    })

    # 3. Security Torture (ACL & Poisoning)
    print("Section 3: Security Torture Tests...")
    res_acl = run_command([sys.executable, "scripts/torture_cascading_acl.py"], cwd=backend_dir)
    res_poison = run_command([sys.executable, "scripts/torture_poisoning_v1.py"], cwd=backend_dir)
    report["sections"].append({
        "name": "Security Hardening (ACL & Poisoning)",
        "success": res_acl["success"] and res_poison["success"],
        "duration": res_acl["duration"] + res_poison["duration"],
        "summary": f"ACL: {'OK' if res_acl['success'] else 'FAIL'}, Poisoning: {'OK' if res_poison['success'] else 'FAIL'}"
    })

    # 4. Swarm Logic Verification (M4.2 Intelligence)
    print("Section 4: Swarm Intelligence Reality Check...")
    res_swarm = run_command([sys.executable, "scripts/verify_swarm_intelligence.py"], cwd=backend_dir)
    report["sections"].append({
        "name": "Cognitive Workflow (Swarm Intelligence)",
        "success": res_swarm["success"],
        "duration": res_swarm["duration"],
        "summary": "Supervisor-Worker Blackboard Flow Verified" if res_swarm["success"] else "Context Loss Detected"
    })

    # RENDER REPORT
    md = f"# 🏥 HiveMind System Health Audit Report\n\nGenerated: {report['timestamp']}\n\n"
    md += "| Domain | Status | Duration | Summary |\n"
    md += "| :--- | :--- | :--- | :--- |\n"
    
    overall_success = True
    for s in report["sections"]:
        status_emoji = "✅" if s["success"] else "❌"
        if not s["success"]: overall_success = False
        md += f"| {s['name']} | {status_emoji} | {s['duration']}s | {s['summary']} |\n"

    md += "\n---\n"
    md += "## 🪵 Audit Logs\n\n"
    if not overall_success:
        md += "### 🔴 Failures Detected\n"
        for s in report["sections"]:
            if not s["success"]:
                md += f"#### {s['name']}\n```text\n{res_pytest['stderr'] if s['name'].startswith('Intelligence') else ''}\n```\n"

    audit_file = backend_dir / "logs" / "system_audit.md"
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    audit_file.write_text(md, encoding="utf-8")
    
    print(f"\n🏁 Audit Finished. Overall Status: {'PASS' if overall_success else 'FAIL'}")
    print(f"📄 Report saved to: {audit_file}")

if __name__ == "__main__":
    asyncio.run(perform_audit())
