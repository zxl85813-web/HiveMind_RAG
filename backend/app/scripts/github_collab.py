import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def get_base_dir():
    return Path(r"c:\Users\linkage\Desktop\aiproject")

def load_config():
    # Try multiple .env locations
    env_paths = [
        get_base_dir() / "backend" / ".env",
        get_base_dir() / ".env"
    ]
    for path in env_paths:
        if path.exists():
            load_dotenv(path)

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ Error: GITHUB_TOKEN not found.")
        sys.exit(1)
    return token

class GitHubGraphQL:
    def __init__(self, token):
        self.url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def query(self, query, variables=None):
        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        response = httpx.post(self.url, headers=self.headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"GraphQL Query Failed: {response.status_code}, {response.text}")

        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL Errors: {json.dumps(data['errors'], indent=2)}")
        return data["data"]

def create_discussion(token, owner, repo, title, body, category_name="Ideas"):
    client = GitHubGraphQL(token)

    # 1. Get Repo ID and Category ID
    get_ids_query = """
    query($owner: String!, $repo: String!) {
      repository(owner: $owner, name: $repo) {
        id
        discussionCategories(first: 10) {
          nodes {
            id
            name
          }
        }
      }
    }
    """
    res = client.query(get_ids_query, {"owner": owner, "repo": repo})
    if not res.get("repository"):
        print(f"[Error] Repository {owner}/{repo} not found.")
        return
    repo_id = res["repository"]["id"]
    categories = res["repository"]["discussionCategories"]["nodes"]

    # Debug
    # print(f"Repo ID: {repo_id}")
    # print(f"Categories raw: {categories}")

    category_id = next((c["id"] for c in categories if c["name"].lower() == category_name.lower()), None)
    if not category_id:
        if categories:
            category_id = categories[0]["id"] # Fallback to first available
        else:
            print("[Error] No discussion categories found. Ensure Discussions are enabled in GitHub Repo Settings.")
            return

    # 2. Create Discussion
    create_mutation = """
    mutation($repoId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
      createDiscussion(input: {repositoryId: $repoId, categoryId: $categoryId, title: $title, body: $body}) {
        discussion {
          url
        }
      }
    }
    """
    res = client.query(create_mutation, {
        "repoId": repo_id,
        "categoryId": category_id,
        "title": title,
        "body": body
    })
    print(f"Success: Discussion created at {res['createDiscussion']['discussion']['url']}")

def sync_projects(token, owner, repo, project_name):
    # This is a complex logic for Project V2.
    # For now, we simulate the logic or provide a placeholder that explains Project V2 sync.
    print(f"🚧 Syncing tasks from TODO.md to GitHub Project: {project_name}")
    # Logic:
    # 1. Get Project V2 ID by name
    # 2. Parse TODO.md (same as sync_github_issues.py)
    # 3. For each task, check if issue exists (via github_issue_map.json)
    # 4. Add/Move issue to Project board item
    print("ℹ️ Note: Project V2 requires project level node IDs. Syncing placeholder...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GitHub Collaboration Tool")
    subparsers = parser.add_subparsers(dest="command")

    # Discuss command
    discuss_parser = subparsers.add_parser("discuss")
    discuss_parser.add_argument("--title", required=True)
    discuss_parser.add_argument("--body", required=True)
    discuss_parser.add_argument("--category", default="Ideas")

    # Sync Project command
    sync_parser = subparsers.add_parser("sync-project")
    sync_parser.add_argument("--project-name", default="Roadmap")

    args = parser.parse_args()
    token = load_config()
    owner = "zxl85813-web"
    repo = "HiveMind_RAG"

    if args.command == "discuss":
        create_discussion(token, owner, repo, args.title, args.body, args.category)
    elif args.command == "sync-project":
        sync_projects(token, owner, repo, args.project_name)
    else:
        parser.print_help()
