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
        print("Error: GITHUB_TOKEN not found in .env")
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

    # 1. Sync REQ-011 Main Document
    req_file = get_base_dir() / "docs" / "requirements" / "REQ-011-changelog-rag.md"
    if req_file.exists():
        with open(req_file, encoding="utf-8") as f:
            content = f.read()
            title = "REQ-011: 变更履历 RAG (Changelog-Aware RAG)"
            if title not in sync_map:
                issue_num, url = create_issue(token, owner, repo, title, content, labels=["requirement", "P1"])
                if issue_num:
                    sync_map[title] = {"number": issue_num, "url": url}
            else:
                print(f"ℹ️ Skip: '{title}' already synced.")

    # 1.5. Sync REQ-012 Main Document
    req_file_012 = get_base_dir() / "docs" / "requirements" / "REQ-012-code-vault.md"
    if req_file_012.exists():
        with open(req_file_012, encoding="utf-8") as f:
            content_012 = f.read()
            title_012 = "REQ-012: Code Vault (代码资产知识库)"
            if title_012 not in sync_map:
                issue_num, url = create_issue(token, owner, repo, title_012, content_012, labels=["requirement", "P1"])
                if issue_num:
                    sync_map[title_012] = {"number": issue_num, "url": url}
            else:
                print(f"ℹ️ Skip: '{title_012}' already synced.")

    # 2. Sync Subtasks from TODO.md
    subtasks = [
        ("REQ-011: ChangelogAwareParser", "Implement Excel/Word changelog extraction logic."),
        (
            "REQ-011: Context Multi-Stitching",
            "Inject extracted changelog info (Version/Date) into metadata of related chapter chunks.",
        ),
        ("REQ-011: Changelog Summary Search", "Implement structured RAG search by time range, version, author, etc."),
        ("REQ-012: Task 1 - 基础设施扩展", "DB新增 AssetReview, Neo4j新增 CodeAsset, 增加状态机及资产类型枚举"),
        (
            "REQ-012: Task 2 - 定制化 Ingestion",
            "开发 CodeASTParserSkill 和 SwaggerIngestionSkill，并实现 SQLAssetExtractor",
        ),
        ("REQ-012: Task 3 - 独立状态流转 API 及 UI", "开发资产审核状态机及各角色的管理控制台页面的 API"),
        (
            "REQ-012: Task 4 - RAG 路由注入与积分打赏",
            "RAG 检索阶段强制注入 Common/SQL 资产，生成采用后计算贡献打赏源码作者",
        ),
        ("GOV-001: Truth Alignment 校验器", "向量与图谱的一致性治理，确保多模态检索结果不冲突"),
        ("GOV-002: Routing Watchdog", "路由自愈机制，自动升级模型 Tier 应对复杂语义"),
        ("GOV-003: Memory Retention Sampling", "记忆价值密度采样，基于重要程度的记忆留存策略"),
        ("GOV-004: JIT Route Cache", "带有 LRU 淘汰机制的即时路由缓存"),
        ("INFRA: Hook-based Skill Linkage", "实现 Rules -> Skill -> Workflow 的自动化钩子联动"),
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
