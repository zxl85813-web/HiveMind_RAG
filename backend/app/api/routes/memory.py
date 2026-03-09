from fastapi import APIRouter, Query

from app.core.graph_store import get_graph_store

router = APIRouter()


@router.get("/graph")
async def get_memory_graph(entities: list[str] = Query(None)):
    """
    Retrieve nodes and links for a set of entities to be rendered in the GraphVisualizer.
    """
    if not entities:
        return {"nodes": [], "links": []}

    store = get_graph_store()
    if not store or not store.driver:
        return {"nodes": [], "links": []}

    # Clean entities
    safe_entities = [str(e).strip() for e in entities if e.strip()]
    if not safe_entities:
        return {"nodes": [], "links": []}

    # Query Neo4j for nodes and relationships
    cypher = """
    MATCH (n)-[r]-(m)
    WHERE n.name IN $entities OR n.id IN $entities 
       OR m.name IN $entities OR m.id IN $entities
    RETURN DISTINCT n {.*} as source, labels(n)[0] as s_label, 
                    type(r) as rel, 
                    m {.*} as target, labels(m)[0] as t_label
    LIMIT 50
    """

    results = store.query(cypher, {"entities": safe_entities})

    nodes_map = {}
    links = []

    for item in results:
        s = item["source"]
        t = item["target"]
        rel = item["rel"]

        # Senders and receivers might be interchangeably retrieved depending on match
        # We ensure they are in the nodes map
        s_id = s.get("id") or s.get("name")
        t_id = t.get("id") or t.get("name")

        if s_id not in nodes_map:
            nodes_map[s_id] = {
                "id": s_id,
                "name": s.get("name") or s_id,
                "label": item.get("s_label", "Entity"),
                "color": "#06D6A0" if item.get("s_label") == "Concept" else "#118AB2",
            }

        if t_id not in nodes_map:
            nodes_map[t_id] = {
                "id": t_id,
                "name": t.get("name") or t_id,
                "label": item.get("t_label", "Entity"),
                "color": "#06D6A0" if item.get("t_label") == "Concept" else "#118AB2",
            }

        links.append({"source": s_id, "target": t_id, "type": rel})

    return {"nodes": list(nodes_map.values()), "links": links}
