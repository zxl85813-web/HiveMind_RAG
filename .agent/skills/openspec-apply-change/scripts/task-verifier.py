import re
import subprocess
import sys
from pathlib import Path

def extract_and_run_verification(change_name: str):
    tasks_file = Path(f"openspec/changes/{change_name}/tasks.md")
    if not tasks_file.exists():
        print(f"❌ Error: tasks.md not found for {change_name}")
        sys.exit(1)
        
    content = tasks_file.read_text(encoding='utf-8')
    # Find the last completed task and its following verification command
    # Pattern: - [x] task... followed by a backtick block
    matches = list(re.finditer(r'- \[x\] (.*?)\n(.*?)(?:```\w*\s+([\s\S]*?)```)', content, re.MULTILINE))
    
    if not matches:
        print("ℹ️ No completed tasks found with verification commands.")
        sys.exit(0)
        
    last_task = matches[-1]
    task_desc = last_task.group(1)
    verify_cmd = last_task.group(3).strip()
    
    print(f"🧪 Verifying Task: {task_desc}")
    print(f"Running: {verify_cmd}")
    
    try:
        # Note: Be careful with shell=True, but OpenSpec often uses complex shell commands
        res = subprocess.run(verify_cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0:
            print("✅ Verification Passed!")
            print(res.stdout)
        else:
            print("❌ Verification Failed.")
            print(res.stdout)
            print(res.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"❌ Execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python task-verifier.py <change_name>")
        sys.exit(1)
    extract_and_run_verification(sys.argv[1])
