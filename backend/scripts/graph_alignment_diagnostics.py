"""
🏗️ Graph Alignment Diagnostics Tool

Purpose:
- Compare physical disk files (SOT) with Neo4j nodes.
- Detect hash mismatches (Stale content).
- Identify nodes without summaries (Hollow nodes).
- Detect disconnected logic islands (Islands).
"""

import hashlib
import os
import sys
import io
from typing import List, Dict

# Ensure UTF-8 output for Windows Console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure we're in the right python context
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from app.core.graph_store import get_graph_store

class GraphAligner:
    """
    🏗️ 图谱对齐诊断器 (Diagnostic Tool for Graph Integrity)
    """
    def __init__(self):
        # Base on parent of scripts folder
        self.root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.store = get_graph_store()
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    def _get_md5(self, path: str) -> str:
        """MD5 Hash of file content."""
        try:
            with open(path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""

    def run_diagnostics(self):
        logger.info("🕵️  正在启动 HiveMind 架构图谱全量对齐检查...")
        
        # 1. Physical Scan
        physical_files = {}
        # Includes backend and docs
        scan_targets = [
            os.path.join(self.root_path, "app"), 
            os.path.join(self.root_path, "docs"),
            os.path.abspath(os.path.join(self.root_path, "..", "docs"))
        ]
        
        for target in scan_targets:
            if not os.path.exists(target): continue
            for root, _, files in os.walk(target):
                if any(x in root for x in [".venv", "__pycache__", "node_modules", ".git"]): continue
                for file in files:
                    if file.endswith((".py", ".md")):
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, self.root_path)
                        h = self._get_md5(full_path)
                        if h:
                            physical_files[rel_path] = h

        # 2. Graph Scan
        # Fetching CodeFile and Document nodes
        cypher = """
        MATCH (f) 
        WHERE f:CodeFile OR f:Document OR f:CodeVault 
        RETURN f.id AS id, f.hash AS hash, f.summary AS summary
        """
        graph_nodes = {node['id']: node for node in self.store.query(cypher)}

        # 3. Analyze Discrepancies
        missing, stale, hollow = [], [], []
        
        for rel_path, current_hash in physical_files.items():
            # Normalized path ID (handling some relative prefixing)
            node_id = rel_path.replace("\\", "/") # Graph usually uses forward slashes
            
            # Find in graph
            node = graph_nodes.get(node_id) or graph_nodes.get(rel_path)
            
            if not node:
                missing.append(rel_path)
            else:
                if node.get('hash') != current_hash:
                    stale.append(rel_path)
                if not node.get('summary') or len(str(node.get('summary'))) < 2:
                    hollow.append(rel_path)

        # 4. Connectivity Depth (Islands - degree 0)
        # Only check nodes that were supposed to be linked (CodeFile/Document)
        islands_cypher = """
        MATCH (n) 
        WHERE (n:CodeFile OR n:Document) AND size((n)--()) = 0 
        RETURN n.id AS id
        """
        islands = [n['id'] for n in self.store.query(islands_cypher)]

        # Output Report
        self._print_report(len(physical_files), missing, stale, hollow, islands)

    def _print_report(self, total, missing, stale, hollow, islands):
        print("\n" + "═"*60)
        print(" 📊  HVM 架构图谱对齐诊断报表 (Alignment Integrity Report)")
        print("═"*60)
        print(f" ✅ 受规约管护总文件数 : {total:<4}")
        print(f" ❌ 漏登项 (Missing)    : {len(missing):<4}  -> [未在 Neo4j 中注册]")
        print(f" ⚠️ 过期项 (Stale)      : {len(stale):<4}  -> [物理哈希不匹配]")
        print(f" 🕳️ 空心项 (Hollow)     : {len(hollow):<4}  -> [节点无语义摘要]")
        print(f" 🏝️ 孤岛项 (Islands)    : {len(islands):<4}  -> [链路断层，不可达]")
        print("─" * 60)
        
        if missing:
            print("\n 🚨 漏登 top 5 (需要执行重新扫描):")
            for m in missing[:5]: print(f"   • {m}")
            
        if stale:
            print("\n ⚡ 过期项 (代码已演进，建议同步):")
            for s in stale[:3]: print(f"   • {s}")
            
        if islands:
            print("\n 🚩 孤岛预警 (这些节点无法通过关系访问):")
            for i in islands[:3]: print(f"   • {i}")
            
        if not (missing or stale or hollow or islands):
            print("\n 💎 [状态极佳]: 图谱与物理世界已完美同步。")
        else:
            print(f"\n 💡 治理建议: 请运行 `python scripts/index_architecture.py` 修复索引。")
        print("═"*60 + "\n")

if __name__ == "__main__":
    aligner = GraphAligner()
    aligner.run_diagnostics()
