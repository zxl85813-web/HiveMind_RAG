
import asyncio
import sys
from pathlib import Path

# 🏗️ [Path Fix]
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.sdk.core.graph_store import Neo4jStore

async def record_incident():
    store = Neo4jStore()
    print("🛰️ [Governance-Harvest]: Recording manual incident into knowledge graph...")

    # Incident 1
    incident_1 = {
        "id": "inc-20260413-001",
        "name": "Vite/ESM Module Export Mismatch",
        "type": "RuntimeError",
        "description": "The requested module did not provide an export named 'ForceGraph2D'. Fixed by switching to default import.",
        "severity": "High",
        "module": "/governance/assets",
        "target_file": "frontend/src/pages/ArchitectureAssetsPage.tsx"
    }

    # Incident 2
    incident_2 = {
        "id": "inc-20260413-002",
        "name": "AntD Component ReferenceError",
        "type": "ReferenceError",
        "description": "Divider is not defined in ArchitectureAssetsPage. Fixed by adding it to antd imports.",
        "severity": "Medium",
        "module": "/governance/assets",
        "target_file": "frontend/src/pages/ArchitectureAssetsPage.tsx"
    }

    incidents = [incident_1, incident_2]

    for data in incidents:
        # 1. Create Incident Node
        query = """
        MERGE (i:Incident {id: $id})
        SET i.name = $name, i.type = $type, i.description = $description, 
            i.severity = $severity, i.module = $module, i.updated_at = timestamp()
        SET i:ArchNode
        """
        await store.execute_query(query, data)

        # 2. Link to Target File
        link_query = """
        MATCH (i:Incident {id: $id})
        MATCH (f:File {id: $target_file})
        MERGE (i)-[:OCCURRED_IN]->(f)
        """
        await store.execute_query(link_query, {
            "id": data["id"],
            "target_file": data["target_file"]
        })
        print(f"✅ Registered incident {data['id']}")
    await store.close()

if __name__ == "__main__":
    asyncio.run(record_incident())
