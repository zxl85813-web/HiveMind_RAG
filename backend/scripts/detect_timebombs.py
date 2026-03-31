import os
import sys
from collections import defaultdict
from tabulate import tabulate

# Add backend directory to sys path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.graph_store import get_graph_store

def detect_timebombs():
    print("🔥 正在扫描架构图谱: 寻找【高耦合 + 零测试】的定时炸弹 🔥\n")
    
    store = get_graph_store()
    if not store.driver:
        print("❌ Cannot connect to Neo4j. Is it running?")
        return

    # Cypher Query:
    # Find all CodePrimitives (File, DatabaseModel, APIEndpoint, DataContract)
    # Count how many other nodes depend on it (incoming DEPENDS_ON, USES_CONTRACT, etc.)
    # Count how many tests verify it (incoming VERIFIES)
    # Filter for nodes with 0 tests and > 0 dependencies
    cypher = """
    MATCH (n:ArchNode)
    WHERE n.type IN ['File', 'DatabaseModel', 'APIEndpoint', 'DataContract']
    
    // Calculate incoming dependencies (Coupling Score)
    OPTIONAL MATCH (dependent)-[r:DEPENDS_ON|USES_CONTRACT|EXPOSES_API|DEFINES_MODEL]->(n)
    WITH n, COUNT(dependent) AS coupling_score
    
    // Calculate incoming test coverage
    OPTIONAL MATCH (t:Test)-[:VERIFIES]->(n)
    WITH n, coupling_score, COUNT(t) AS test_count
    
    // Filter for Timebombs
    WHERE test_count = 0 AND coupling_score > 0
    RETURN coalesce(n.name, n.id) AS Component, 
           n.type AS Type, 
           coupling_score AS DependencyWeight
    ORDER BY coupling_score DESC
    LIMIT 15
    """
    
    try:
        results = store.query(cypher, {})
        
        if not results:
            print("✅ 恭喜！当前代码库非常健康，没有发现【高耦合+零测试】的定时炸弹。")
            return
            
        table_data = []
        for rec in results:
            comp = rec["Component"]
            ctype = rec["Type"]
            weight = rec["DependencyWeight"]
            
            # Formatting to make it clear what kind of bomb it is
            severity = "💣💣💣" if weight >= 5 else "💣💣" if weight >= 3 else "💣"
            
            table_data.append([severity, comp, ctype, weight, "0 (Uncovered)"])
            
        report_lines = []
        report_lines.append("🔥 正在扫描架构图谱: 寻找【高耦合 + 零测试】的定时炸弹 🔥\n")
        
        headers = ["Severity", "Component", "Type", "Coupling Score", "Test Count"]
        table = tabulate(table_data, headers=headers, tablefmt="fancy_grid")
        report_lines.append(table)
        report_lines.append("\n💡 架构治理建议: 优先为上述 'Coupling Score' 最高的模块编写单元测试！一旦它们重构出错，将波及大量下游服务。")
        
        report_text = "\n".join(report_lines)
        print(report_text)
        
        # Write to file explicitly to avoid console encoding issues
        with open("timebombs_report.txt", "w", encoding="utf-8") as f:
            f.write(report_text)
            
    except Exception as e:
        print(f"❌ Query failed: {e}")

if __name__ == "__main__":
    detect_timebombs()
