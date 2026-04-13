
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.sdk.core.graph_store import get_graph_store

async def bootstrap_stabilization_graph():
    store = get_graph_store()
    try:
        print("Bootstrapping stabilization records into Neo4j...")
        
        # 1. Create SoftwareComponents
        components = [
            {"name": "AppLayout", "type": "Frontend", "desc": "Root Layout for HiveMind UI"},
            {"name": "AuthStore", "type": "Frontend", "desc": "Zustand store for authentication state"},
            {"name": "AccessGuard", "type": "Frontend", "desc": "Higher-order component for route permissions"},
            {"name": "ViteProxy", "type": "Infrastructure", "desc": "Frontend dev server proxy configuration"}
        ]
        
        for c in components:
            await store.execute_query(
                "MERGE (s:SoftwareComponent {name: $name}) "
                "SET s.type = $type, s.description = $desc "
                "RETURN s", c
            )
            print(f"  (PLUS) Component synced: {c['name']}")

        # 2. Create Incidents
        incidents = [
            {
                "id": "INC-260413-NW", 
                "title": "IPv6 Connectivity Conflict (localhost mismatch)",
                "summary": "Connection refused on port 8000 due to localhost resolving to ::1 while backend binds to 127.0.0.1.",
                "severity": "P0"
            },
            {
                "id": "INC-260413-AUTH", 
                "title": "Permissions Synchronization Lag (403 race condition)",
                "summary": "Users see unauthorized screens on refresh because routing guard fires before profile is reconciled.",
                "severity": "P1"
            },
            {
                "id": "INC-260413-UI", 
                "title": "Layout Viewport Stability Breakdown",
                "summary": "Individual scroll areas collapse into body-level scrolling, causing UI controls to shift up.",
                "severity": "P2"
            }
        ]
        
        for inc in incidents:
            await store.execute_query(
                "MERGE (i:Incident {id: $id}) "
                "SET i.title = $title, i.summary = $summary, i.severity = $severity, i.date = '2026-04-13' "
                "RETURN i", inc
            )
            print(f"  (PLUS) Incident recorded: {inc['id']}")

        # 3. Create Reflections & Links
        # Link Incidents to Components
        mapping = [
            ("INC-260413-NW", "ViteProxy", "ADDRESSES"),
            ("INC-260413-AUTH", "AuthStore", "ADDRESSES"),
            ("INC-260413-AUTH", "AccessGuard", "ADDRESSES"),
            ("INC-260413-UI", "AppLayout", "ADDRESSES")
        ]
        
        for inc_id, comp_name, rel in mapping:
            await store.execute_query(
                "MATCH (i:Incident {id: $inc_id}), (s:SoftwareComponent {name: $comp_name}) "
                "MERGE (i)-[:" + rel + "]->(s)", 
                {"inc_id": inc_id, "comp_name": comp_name}
            )
            print(f"  (LINK) Linked: {inc_id} -> {comp_name}")

        # 4. Create DecisionPoints (Reflections)
        decisions = [
            {
                "id": "DEC-260413-001",
                "title": "Atomic Auth Handshake Strategy",
                "content": "Mandate profile injection during login response to eliminate async lag."
            },
            {
                "id": "DEC-260413-002",
                "title": "Explicit IP Binding Rule",
                "content": "Forbid 'localhost' in configs; enforce 127.0.0.1 or 0.0.0.0 for deterministic resolution."
            }
        ]
        
        for dec in decisions:
            await store.execute_query(
                "MERGE (d:DecisionPoint {id: $id}) "
                "SET d.title = $title, d.content = $content, d.date = '2026-04-13' "
                "RETURN d", dec
            )
            # Link Decision to Incident
            await store.execute_query(
                "MATCH (d:DecisionPoint {id: $id}), (i:Incident) "
                "WHERE i.id CONTAINS '260413' "
                "MERGE (d)-[:RESOLVES]->(i)", {"id": dec["id"]}
            )
            print(f"  (DEC) Decision registered: {dec['title']}")

        print("SUCCESS: Graph Injection Complete. Wisdom Archiving Success.")
        
    except Exception as e:
        print(f"ERROR during injection: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(bootstrap_stabilization_graph())
