
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.sdk.core.graph_store import get_graph_store

async def inject_contract_wisdom():
    store = get_graph_store()
    try:
        print("Archiving 'API Contract Fragmentation' wisdom into Neo4j...")
        
        # 1. New Component: SettingsModule
        await store.execute_query(
            "MERGE (s:SoftwareComponent {name: 'SettingsPage'}) "
            "SET s.type = 'Frontend', s.description = 'Centralized governance control panel'"
        )

        # 2. New Incident: 404/422 on Settings
        await store.execute_query(
            "MERGE (i:Incident {id: 'INC-260413-CONTRACT'}) "
            "SET i.title = 'API Schema Fragmentation (422/404 on Governance Settings)', "
            "    i.summary = 'Partial form submission and missing endpoints led to governance UI failure.', "
            "    i.severity = 'P1', i.date = '2026-04-13'"
        )

        # 3. New Decision: Full State Persistence Strategy
        await store.execute_query(
            "MERGE (d:DecisionPoint {id: 'DEC-260413-003'}) "
            "SET d.title = 'Mandatory State Merging Policy', "
            "    d.content = 'All configuration endpoints must receive full-state payloads or implement JSON Merge Patch (RFC 7396) strictly.', "
            "    d.date = '2026-04-13'"
        )

        # 4. Linking
        links = [
            ("INC-260413-CONTRACT", "SettingsPage", "ADDRESSES"),
            ("DEC-260413-003", "INC-260413-CONTRACT", "RESOLVES"),
        ]
        for src, dest, rel in links:
            await store.execute_query(
                "MATCH (a), (b) WHERE (a.id = $src OR a.name = $src) AND (b.id = $dest OR b.name = $dest) "
                "MERGE (a)-[:" + rel + "]->(b)", {"src": src, "dest": dest}
            )

        print("SUCCESS: Settings Contract Wisdom Archived.")
        
    except Exception as e:
        print(f"ERROR during injection: {e}")

if __name__ == "__main__":
    asyncio.run(inject_contract_wisdom())
