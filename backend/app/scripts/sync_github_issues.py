import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def get_base_dir():
    return Path(r"c:\Users\linkage\Desktop\aiproject")


def load_config():
    env_path = get_base_dir() / "backend" / ".env"
    load_dotenv(env_path)
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        # Try finding in parent .env if any
        load_dotenv(get_base_dir() / ".env")
        token = os.getenv("GITHUB_TOKEN")
    
    if not token:
        print("Error: GITHUB_TOKEN not found in .env files")
        sys.exit(1)
    return token


def create_issue(token, owner, repo, title, body, labels=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    data = {"title": title, "body": body}
    if labels:
        data["labels"] = labels

    response = httpx.post(url, headers=headers, json=data)
    if response.status_code == 201:
        issue = response.json()
        print(f"✅ Success: Issue '{title}' created at {issue['html_url']}")
        return issue["number"], issue["html_url"]
    else:
        print(f"❌ Error: Failed to create issue '{title}'. Status: {response.status_code}, Msg: {response.text}")
        return None, None


def scan_todo_for_tasks():
    todo_path = get_base_dir() / "TODO.md"
    tasks = []
    if not todo_path.exists():
        return tasks
    
    with open(todo_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Match "- ⬜ TASK-001: Description" or "- ⬜ GOV-001: Description"
            if line.startswith("- ⬜") and ":" in line:
                parts = line.split(":", 1)
                title = parts[0].replace("- ⬜", "").strip()
                desc = parts[1].strip()
                tasks.append((title, desc))
    return tasks

def sync_req_to_github():
    token = load_config()
    owner = "zxl85813-web"
    repo = "HiveMind_RAG"

    # Mapping to avoid duplicate creation
    map_file = get_base_dir() / "docs" / "github_issue_map.json"
    sync_map = {}
    if map_file.exists():
        with open(map_file, encoding="utf-8") as f:
            sync_map = json.load(f)

    # 1. Auto-discover REQ documents
    req_dir = get_base_dir() / "docs" / "requirements"
    if req_dir.exists():
        for req_file in req_dir.glob("REQ-*.md"):
            with open(req_file, encoding="utf-8") as f:
                content = f.read()
                # Use filename stem as title or extract first H1
                title_id = req_file.stem.split("-")[0] + "-" + req_file.stem.split("-")[1]
                title = f"{title_id}: New Requirement" 
                for line in content.splitlines():
                    if line.startswith("#"):
                        title = line.replace("#", "").strip()
                        break
                
                if title not in sync_map:
                    print(f"📡 Syncing {title_id}...")
                    issue_num, url = create_issue(token, owner, repo, title, content, labels=["requirement", "P1"])
                    if issue_num:
                        sync_map[title] = {"number": issue_num, "url": url}
                else:
                    print(f"ℹ️ Skip: REQ '{title}' already synced.")

    # 2. Auto-scan TODO.md for new tasks
    print("🔍 Scanning TODO.md for new ⬜ tasks...")
    subtasks = scan_todo_for_tasks()

    for st_title, st_desc in subtasks:
        if st_title not in sync_map:
            print(f"📡 Syncing task: {st_title}...")
            # Detect labels from title (e.g. GOV-001 -> governance)
            labels = ["task"]
            if "GOV-" in st_title: labels.append("governance")
            if "ARM-" in st_title: labels.append("security")
            
            issue_num, url = create_issue(token, owner, repo, st_title, st_desc, labels=labels)
            if issue_num:
                sync_map[st_title] = {"number": issue_num, "url": url}
        else:
            # Check if it was manually added previously but not in sync_map
            pass

    with open(map_file, "w", encoding="utf-8") as f:
        json.dump(sync_map, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    sync_req_to_github()
