import httpx
import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

def get_base_dir():
    return Path(r"c:\Users\linkage\Desktop\aiproject")

def load_config():
    env_path = get_base_dir() / "backend" / ".env"
    load_dotenv(env_path)
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not found in .env")
        sys.exit(1)
    return token

def create_issue(token, owner, repo, title, body, labels=None):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": title,
        "body": body
    }
    if labels:
        data["labels"] = labels
        
    response = httpx.post(url, headers=headers, json=data)
    if response.status_code == 201:
        issue = response.json()
        print(f"✅ Success: Issue '{title}' created at {issue['html_url']}")
        return issue['number'], issue['html_url']
    else:
        print(f"❌ Error: Failed to create issue '{title}'. Status: {response.status_code}, Msg: {response.text}")
        return None, None

def sync_req_to_github():
    token = load_config()
    owner = "zxl85813-web"
    repo = "HiveMind_RAG"
    
    # Mapping to avoid duplicate creation
    map_file = get_base_dir() / "docs" / "github_issue_map.json"
    sync_map = {}
    if map_file.exists():
        with open(map_file, "r", encoding="utf-8") as f:
            sync_map = json.load(f)
            
    # 1. Sync REQ-011 Main Document
    req_file = get_base_dir() / "docs" / "requirements" / "REQ-011-changelog-rag.md"
    if req_file.exists():
        with open(req_file, "r", encoding="utf-8") as f:
            content = f.read()
            title = "REQ-011: 变更履历 RAG (Changelog-Aware RAG)"
            if title not in sync_map:
                issue_num, url = create_issue(token, owner, repo, title, content, labels=["requirement", "P1"])
                if issue_num:
                    sync_map[title] = {"number": issue_num, "url": url}
            else:
                print(f"ℹ️ Skip: '{title}' already synced.")

    # 2. Sync REQ-011 Subtasks from TODO.md
    subtasks = [
        ("REQ-011: ChangelogAwareParser", "Implement Excel/Word changelog extraction logic."),
        ("REQ-011: Context Multi-Stitching", "Inject extracted changelog info (Version/Date) into metadata of related chapter chunks."),
        ("REQ-011: Changelog Summary Search", "Implement structured RAG search by time range, version, author, etc.")
    ]
    
    for st_title, st_desc in subtasks:
        if st_title not in sync_map:
            issue_num, url = create_issue(token, owner, repo, st_title, st_desc, labels=["task", "REQ-011"])
            if issue_num:
                sync_map[st_title] = {"number": issue_num, "url": url}
        else:
             print(f"ℹ️ Skip: '{st_title}' already synced.")
             
    with open(map_file, "w", encoding="utf-8") as f:
        json.dump(sync_map, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    sync_req_to_github()
