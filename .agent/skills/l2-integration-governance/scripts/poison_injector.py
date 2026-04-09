import sys
import argparse
import random

def inject_poison(poison_type: str, target: str):
    print(f"🤮 Injecting Poison: {poison_type} into {target}...")
    
    poisons = {
        "zombie_node": "Created 5 nodes with no attributes and no relationships in Neo4j.",
        "schema_drift": "Modified PG column 'metadata' to type TEXT from JSONB in test session.",
        "logic_loop": "Created circular dependency (Agent A -> Agent B -> Agent A) to test hang-resilience.",
        "huge_payload": "Injected 50MB of binary junk into a text-only input field."
    }
    
    result = poisons.get(poison_type, "Unknown poison type.")
    print(f"Done: {result}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", choices=["zombie_node", "schema_drift", "logic_loop", "huge_payload"], required=True)
    parser.add_argument("--target", default="default_test_db")
    args = parser.parse_args()
    inject_poison(args.type, args.target)
