import os
import platform
import subprocess
from datetime import datetime
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def get_git_status() -> str:
    """Gets a brief git status if in a git repo."""
    try:
        is_git = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, check=False
        ).stdout.strip() == "true"
        
        if not is_git:
            return "Not a git repository"
            
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=False
        ).stdout.strip()
        
        status = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, check=False
        ).stdout.strip()
        
        return f"Branch: {branch}\nStatus:\n{status or '(clean)'}"
    except Exception:
        return "Git info unavailable"

def get_env_context() -> str:
    """Collects OS, Python, and Git context for the agent."""
    now = datetime.now()
    cwd = os.getcwd()
    git_info = get_git_status()
    
    context = [
        "# Environment Info",
        f"Date: {now.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Platform: {platform.system()} {platform.release()} ({platform.machine()})",
        f"Python Version: {platform.python_version()}",
        f"Working Directory: {cwd}",
        f"Git Status:\n{git_info}",
    ]
    
    return "\n".join(context)
