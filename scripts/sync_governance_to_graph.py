import os
import re
import asyncio
from pathlib import Path
import sys

# 将 backend 目录添加到路径，以便导入 app.sdk
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, "backend"))

from app.sdk.core.graph_store import get_graph_store

async def sync_governance():
    """将 Markdown 规约同步至 Neo4j 图谱。"""
    store = get_graph_store()
    project_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    rules_dir = project_root / "docs" / "conventions" / "rules"
    
    print(f"Scanning rules in {rules_dir}...")
    
    # 建立正则表达式提取规则
    # 格式示例: ### [RULE-A001] 命名抗歧义
    rule_pattern = re.compile(r"### \[(RULE-[\w-]+)\] (.*)")
    
    for rule_file in rules_dir.glob("*.md"):
        content = rule_file.read_text(encoding="utf-8")
        matches = rule_pattern.findall(content)
        
        for rule_id, title in matches:
            print(f"Syncing Rule: {rule_id}")
            
            # 1. 创建 Rule 节点
            query = (
                "MERGE (r:GovernanceRule {id: $rule_id}) "
                "SET r.title = $title, r.source = $source, r.last_updated = timestamp() "
                "RETURN r"
            )
            await store.execute_query(query, {
                "rule_id": rule_id,
                "title": title,
                "source": str(rule_file.relative_to(project_root))
            })
            
    # 2. 同步成熟度阶段 (Maturity Model)
    maturity_file = project_root / "docs" / "conventions" / "MATURITY_MODEL.md"
    if maturity_file.exists():
        mc = maturity_file.read_text(encoding="utf-8")
        stages = re.findall(r"## (阶段 \d: .*)", mc)
        for stage in stages:
            print(f"Syncing Maturity Stage")
            query = "MERGE (s:GovernanceStage {name: $name}) SET s.last_sync = timestamp()"
            await store.execute_query(query, {"name": stage})

    print("Governance Graph Synchronization Complete.")

if __name__ == "__main__":
    asyncio.run(sync_governance())
