from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TodoTask:
    title: str
    body: str
    source_line: int


def parse_args() -> argparse.Namespace:
    today = dt.date.today().isoformat()
    parser = argparse.ArgumentParser(
        description="Create GitHub milestone (and optional issues) from TODO.md section."
    )
    parser.add_argument(
        "--todo",
        default="TODO.md",
        help="Path to TODO markdown file (default: TODO.md)",
    )
    parser.add_argument(
        "--section",
        default="### 0.2 本周执行序列（按依赖排序）",
        help="Exact section header to extract tasks from",
    )
    parser.add_argument(
        "--milestone-title",
        default=f"TODO Sync {today}",
        help="Milestone title (default: TODO Sync <today>)",
    )
    parser.add_argument(
        "--milestone-description",
        default="Auto-generated from TODO.md by create_github_milestone_from_todo.py",
        help="Milestone description",
    )
    parser.add_argument(
        "--due-on",
        default="",
        help="Milestone due date in YYYY-MM-DD",
    )
    parser.add_argument(
        "--repo",
        default="",
        help="GitHub repo in owner/name format, required when --apply is set",
    )
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable name containing GitHub token",
    )
    parser.add_argument(
        "--create-issues",
        action="store_true",
        help="Create issues for parsed tasks under the milestone",
    )
    parser.add_argument(
        "--labels",
        default="todo-sync,agent",
        help="Comma-separated labels for created issues",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes to GitHub. Without this flag, runs in dry-run mode.",
    )
    return parser.parse_args()


def extract_tasks(todo_path: Path, section_header: str) -> list[TodoTask]:
    if not todo_path.exists():
        raise FileNotFoundError(f"TODO file not found: {todo_path}")

    lines = todo_path.read_text(encoding="utf-8").splitlines()
    in_section = False
    tasks: list[TodoTask] = []

    pattern = re.compile(r"^\s*-\s*(?:[⬜🟡✅🔴🐛⏸️]\s*)?\*\*(.+?)\*\*\s*[：:]\s*(.+)$")

    for idx, line in enumerate(lines, start=1):
        if line.strip() == section_header.strip():
            in_section = True
            continue

        if in_section and line.startswith("### "):
            break

        if not in_section:
            continue

        matched = pattern.match(line)
        if not matched:
            continue

        title = matched.group(1).strip()
        body = matched.group(2).strip()

        if title and body:
            tasks.append(TodoTask(title=title, body=body, source_line=idx))

    return tasks


def require_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise ValueError("--repo must be in owner/name format")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise ValueError("--repo must be in owner/name format")
    return owner, name


def github_request(
    method: str,
    url: str,
    token: str,
    payload: dict | None = None,
) -> dict | list:
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GitHub API error {error.code}: {detail}") from error


def get_or_create_milestone(
    owner: str,
    repo: str,
    token: str,
    title: str,
    description: str,
    due_on: str,
) -> dict:
    base = f"https://api.github.com/repos/{owner}/{repo}"
    query = urllib.parse.urlencode({"state": "open", "per_page": 100})
    milestones = github_request("GET", f"{base}/milestones?{query}", token)

    for item in milestones:
        if item.get("title") == title:
            return item

    payload: dict[str, str] = {
        "title": title,
        "description": description,
    }
    if due_on:
        due_date = dt.datetime.strptime(due_on, "%Y-%m-%d").date()
        payload["due_on"] = f"{due_date.isoformat()}T23:59:59Z"

    return github_request("POST", f"{base}/milestones", token, payload)


def create_issues_for_tasks(
    owner: str,
    repo: str,
    token: str,
    milestone_number: int,
    tasks: list[TodoTask],
    labels: list[str],
    todo_path: Path,
) -> tuple[int, int]:
    base = f"https://api.github.com/repos/{owner}/{repo}"
    query = urllib.parse.urlencode(
        {
            "state": "all",
            "milestone": str(milestone_number),
            "per_page": 100,
        }
    )
    existing_issues = github_request("GET", f"{base}/issues?{query}", token)
    existing_titles = {issue.get("title", "") for issue in existing_issues if "pull_request" not in issue}

    created = 0
    skipped = 0

    for task in tasks:
        issue_title = f"[TODO] {task.title}"
        if issue_title in existing_titles:
            skipped += 1
            continue

        issue_body = (
            f"Auto-generated from {todo_path.name}:{task.source_line}\n\n"
            f"- Task: {task.title}\n"
            f"- Detail: {task.body}\n"
            f"- Source: {todo_path.as_posix()}#{task.source_line}\n"
        )

        payload: dict[str, object] = {
            "title": issue_title,
            "body": issue_body,
            "milestone": milestone_number,
        }
        if labels:
            payload["labels"] = labels

        github_request("POST", f"{base}/issues", token, payload)
        created += 1

    return created, skipped


def main() -> int:
    args = parse_args()
    todo_path = Path(args.todo)
    tasks = extract_tasks(todo_path, args.section)

    if not tasks:
        print(f"No tasks found under section: {args.section}")
        return 1

    print(f"Parsed {len(tasks)} tasks from {todo_path}")
    for task in tasks:
        print(f"  - {task.title}: {task.body}")

    if not args.apply:
        print("\nDry-run mode: no GitHub changes applied.")
        print("Use --apply --repo <owner/name> to create/update milestone.")
        return 0

    owner, repo = require_repo(args.repo)
    token = os.getenv(args.token_env, "")
    if not token:
        print(f"Missing token in env var: {args.token_env}")
        return 2

    milestone = get_or_create_milestone(
        owner=owner,
        repo=repo,
        token=token,
        title=args.milestone_title,
        description=args.milestone_description,
        due_on=args.due_on,
    )
    milestone_number = milestone.get("number")
    milestone_title = milestone.get("title")
    print(f"Milestone ready: #{milestone_number} {milestone_title}")

    if args.create_issues:
        labels = [item.strip() for item in args.labels.split(",") if item.strip()]
        created, skipped = create_issues_for_tasks(
            owner=owner,
            repo=repo,
            token=token,
            milestone_number=int(milestone_number),
            tasks=tasks,
            labels=labels,
            todo_path=todo_path,
        )
        print(f"Issues created: {created}, skipped(existing): {skipped}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
