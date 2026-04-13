
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.sdk.core.graph_store import get_graph_store

async def inject_data_integrity_wisdom():
    store = get_graph_store()
    try:
        print("Archiving 'Persistence Integrity' wisdom into Neo4j...")
        
        # 1. New Incident: JSON Corruption
        await store.execute_query(
            "MERGE (i:Incident {id: 'INC-260413-DATA'}) "
            "SET i.title = 'JSON State Corruption (Truncated Persistence)', "
            "    i.summary = 'Partial write of llm_governance.json caused JSONDecodeError and system 500.', "
            "    i.severity = 'P0', i.date = '2026-04-13'"
        )

        # 2. New Decision: Atomic Writing Pattern
        await store.execute_query(
            "MERGE (d:DecisionPoint {id: 'DEC-260413-004'}) "
            "SET d.title = 'Atomic Persistence Pattern Mandate', "
            "    d.content = 'Critical configurations must use temporary-file-rename atomic writes to prevent corruption.', "
            "    d.date = '2026-04-13'"
        )

        # 3. Linking
        links = [
            ("INC-260413-DATA", "SettingsPage", "ADDRESSES"),
            ("DEC-260413-004", "INC-260413-DATA", "RESOLVES"),
        ]
        for src, dest, rel in links:
            await store.execute_query(
                "MATCH (a), (b) WHERE (a.id = $src OR a.name = $src) AND (b.id = $dest OR b.name = $dest) "
                "MERGE (a)-[:" + rel + "]->(b)", {"src": src, "dest": dest}
            )

        print("SUCCESS: Data Integrity Wisdom Archived.")
        
    except Exception as e:
        print(f"ERROR during injection: {e}")

if __name__ == "__main__":
    asyncio.run(inject_data_integrity_wisdom())
