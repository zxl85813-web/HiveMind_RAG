import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.core.graph_store import get_graph_store

def main():
    store = get_graph_store()
    if not store or not store.driver:
        print("Neo4j driver not available.")
        return

    print("=== Nodes by Label ===")
    res = store.query("MATCH (n) RETURN DISTINCT labels(n) AS label, COUNT(n) AS count")
    for r in res:
        print(r)

    print("\n=== Edges by Type ===")
    res = store.query("MATCH ()-[r]->() RETURN type(r) AS type, COUNT(r) AS count")
    for r in res:
        print(r)

    print("\n=== Sample Nodes ===")
    res = store.query("MATCH (n) RETURN labels(n) AS lbl, n LIMIT 5")
    for r in res:
        print(r)
        
    store.close()

if __name__ == "__main__":
    main()
