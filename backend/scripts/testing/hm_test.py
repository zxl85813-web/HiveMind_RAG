import sys
import argparse
import subprocess
import os
from pathlib import Path

# Force UTF-8 for windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def run_command(cmd, cwd=None):
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, text=True, capture_output=False)
    return result.returncode

def main():
    parser = argparse.ArgumentParser(description="HiveMind Testing Orchestrator (Skill-Based)")
    parser.add_argument("skill", choices=["unit", "api", "fuzz", "graph", "mutate", "all"], help="Test skill to execute")
    parser.add_argument("--path", help="Target path for the skill (file or directory)", default="tests")
    parser.add_argument("--threshold", type=int, default=60, help="Coverage threshold")

    args = parser.parse_args()

    # Ensure logs dir exists
    os.makedirs("logs/testing", exist_ok=True)

    if args.skill == "unit":
        # Skill: High-speed unit testing with coverage
        cmd = [sys.executable, "-m", "pytest", args.path, f"--cov-fail-under={args.threshold}"]
        run_command(cmd)

    elif args.skill == "api":
        # Skill: Integration/Contract testing
        cmd = ["pytest", "tests/integration", "-m", "api"]
        run_command(cmd)

    elif args.skill == "fuzz":
        # Skill: Property-based exploration
        cmd = ["pytest", args.path, "-m", "fuzz"]
        run_command(cmd)

    elif args.skill == "mutate":
        # Skill: Mutation testing for resilience verification
        # Note: target is often a specific file under app/
        target = args.path.replace("tests/", "app/").replace("test_", "").replace("tests\\", "app\\")
        cmd = ["mutmut", "run", "--paths-to-mutate", target]
        run_command(cmd)

    elif args.skill == "graph":
        # Skill: Architectural Gap Analysis
        print("🔍 Analyzing Architectural Gaps in Neo4j...")
        # Placeholder for real graph query script
        run_command(["python", "scripts/graph_alignment_diagnostics.py", "--check-tests"])

    elif args.skill == "all":
        # Mass Operation
        run_command(["pytest", "tests", f"--cov-fail-under={args.threshold}"])
        run_command(["python", "scripts/graph_alignment_diagnostics.py", "--check-tests"])

if __name__ == "__main__":
    main()
